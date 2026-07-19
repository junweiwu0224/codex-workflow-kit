#!/usr/bin/env python3
"""Record and safely manage files installed by the workflow kit.

The shell and PowerShell installers orchestrate this dependency-free helper,
which owns preimage-checked copies, the write-ahead transaction, prune,
uninstall, and rollback. It never infers ownership from post-install files or
from an arbitrary ``.bak-*`` file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


STATE_DIR_NAME = ".codex-workflow-kit"
STATE_FILE_NAME = "install-state.json"
TRANSACTION_FILE_NAME = "install-transaction.json"
TRANSACTION_DATA_DIR_NAME = "install-transaction-data"
ROLLBACK_DATA_PREFIX = "install-rollback-"
STATE_VERSION = 1
PROFILES = frozenset(("core", "stable", "pilot", "reverse", "repo-template"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_lines(path: Path) -> list[str]:
    if not path.is_file():
        raise RuntimeError(f"skill profile missing: {path}")
    return sorted(
        {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    )


@dataclass
class ManagedFile:
    target: str
    source: str
    sha256: str
    profile: str
    active: bool = True
    rollback_action: str = "unknown"
    rollback_backup: str | None = None
    rollback_backup_sha256: str | None = None


@dataclass(frozen=True)
class InstallContext:
    kit_root: Path
    codex_home: Path
    agents_home: Path
    repo: Path | None
    repo_only: bool


@dataclass(frozen=True)
class TransactionFile:
    target: str
    source: str
    profile: str
    source_sha256: str
    before_exists: bool
    before_sha256: str | None
    journal_backup: str | None
    planned_backup: str | None


@dataclass(frozen=True)
class RollbackFile:
    target: str
    source: str
    profile: str
    installed_sha256: str
    before_exists: bool
    before_sha256: str | None
    rollback_snapshot: str | None
    rollback_snapshot_sha256: str | None
    public_backup: str | None


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return ()
    return (path for path in sorted(root.rglob("*")) if path.is_file())


def expected_files(
    kit_root: Path,
    codex_home: Path,
    agents_home: Path,
    *,
    pilots: bool,
    reverse: bool,
    repo: Path | None,
    repo_only: bool = False,
) -> list[tuple[Path, Path, str]]:
    """Return ``(source, target, profile)`` entries for this install."""

    entries: list[tuple[Path, Path, str]] = []

    def add(source: Path, target: Path, profile: str) -> None:
        if source.is_file():
            entries.append((source, target, profile))

    if not repo_only:
        add(kit_root / "global/AGENTS.md", codex_home / "AGENTS.md", "core")

        stable = profile_lines(kit_root / "catalog/profiles/stable.txt")
        pilot = profile_lines(kit_root / "catalog/profiles/pilot.txt") if pilots else []
        skills = stable + pilot
        for skill in sorted(set(skills)):
            source_root = kit_root / "skills" / skill
            if not source_root.is_dir():
                raise RuntimeError(f"profile skill missing: {source_root}")
            for source in _iter_files(source_root):
                profile = "pilot" if skill in pilot else "stable"
                add(source, agents_home / "skills" / skill / source.relative_to(source_root), profile)

        if reverse:
            add(
                kit_root / "catalog/reverse-dependencies.lock.yaml",
                codex_home / "catalog/reverse-dependencies.lock.yaml",
                "reverse",
            )
            add(
                kit_root / "reverse-skill-router/reverse-engineering/SKILL.md",
                codex_home / "skills/reverse-engineering/SKILL.md",
                "reverse",
            )
            source_root = kit_root / "reverse-skill"
            for source in _iter_files(source_root):
                add(source, codex_home / "reverse-skill" / source.relative_to(source_root), "reverse")

    if repo is not None:
        source_root = kit_root / "repo-template"
        for source in _iter_files(source_root):
            add(source, repo / source.relative_to(source_root), "repo-template")

    return entries


def state_path(agents_home: Path, *, repo: Path | None = None, repo_only: bool = False) -> Path:
    base = repo if repo_only and repo is not None else agents_home
    return base / STATE_DIR_NAME / STATE_FILE_NAME


def install_context(args: argparse.Namespace) -> InstallContext:
    if args.repo_only and args.repo is None:
        raise RuntimeError("--repo-only requires --repo")
    return InstallContext(
        kit_root=args.kit_root.resolve(),
        codex_home=args.codex_home.resolve(),
        agents_home=args.agents_home.resolve(),
        repo=args.repo.resolve() if args.repo else None,
        repo_only=bool(args.repo_only),
    )


def is_strictly_within(path: Path, root: Path) -> bool:
    try:
        return path != root and path.is_relative_to(root)
    except ValueError:
        return False


def managed_state_path(context: InstallContext) -> Path:
    base = context.repo if context.repo_only else context.agents_home
    if base is None:
        raise RuntimeError("--repo-only requires --repo")
    path = state_path(context.agents_home, repo=context.repo, repo_only=context.repo_only)
    resolved_parent = path.parent.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    if not is_strictly_within(resolved_parent, base) or not is_strictly_within(resolved_path, base):
        raise RuntimeError(f"install state escapes its root: {path}")
    if path.is_symlink():
        raise RuntimeError(f"install state must not be a symlink: {path}")
    return path


def transaction_paths(context: InstallContext) -> tuple[Path, Path]:
    state = managed_state_path(context)
    transaction = state.with_name(TRANSACTION_FILE_NAME)
    data_dir = state.with_name(TRANSACTION_DATA_DIR_NAME)
    for candidate in (transaction, data_dir):
        if candidate.is_symlink() or not is_strictly_within(candidate.resolve(strict=False), state.parent.parent):
            raise RuntimeError(f"install transaction path escapes its root: {candidate}")
    return transaction, data_dir


def rollback_data_path(context: InstallContext, transaction_id: str) -> Path:
    if len(transaction_id) != 32 or any(char not in "0123456789abcdef" for char in transaction_id):
        raise RuntimeError("invalid rollback transaction identifier")
    path = managed_state_path(context).parent / f"{ROLLBACK_DATA_PREFIX}{transaction_id}"
    if path.is_symlink() or not is_strictly_within(path.resolve(strict=False), path.parent.parent):
        raise RuntimeError(f"rollback data path escapes its root: {path}")
    return path


def remove_rollback_storage(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or not path.is_dir() or not path.name.startswith(ROLLBACK_DATA_PREFIX):
        raise RuntimeError(f"rollback data must be a managed directory: {path}")
    shutil.rmtree(path)


def cleanup_unreferenced_rollback_storage(context: InstallContext, *, keep: Path | None = None) -> None:
    state_dir = managed_state_path(context).parent
    if not state_dir.is_dir() or state_dir.is_symlink():
        return
    for candidate in sorted(state_dir.glob(f"{ROLLBACK_DATA_PREFIX}*")):
        if keep is not None and candidate == keep:
            continue
        remove_rollback_storage(candidate)


def remove_transaction_storage(transaction: Path, data_dir: Path) -> None:
    if data_dir.exists():
        if data_dir.is_symlink() or not data_dir.is_dir():
            raise RuntimeError(f"install transaction data must be a directory: {data_dir}")
    transaction.unlink(missing_ok=True)
    if data_dir.exists():
        shutil.rmtree(data_dir)
    try:
        transaction.parent.rmdir()
    except OSError:
        pass


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": STATE_VERSION, "files": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"invalid install state: {path}: {exc}") from exc
    if data.get("schema_version") != STATE_VERSION or not isinstance(data.get("files"), list):
        raise RuntimeError(f"unsupported install state: {path}")
    return data


def save_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def state_entries(data: dict, context: InstallContext) -> dict[str, ManagedFile]:
    result: dict[str, ManagedFile] = {}
    for index, item in enumerate(data.get("files", [])):
        if not isinstance(item, dict):
            raise RuntimeError(f"invalid install state entry {index}: expected object")
        required = ("target", "source", "sha256", "profile", "active")
        if any(key not in item for key in required):
            raise RuntimeError(f"invalid install state entry {index}: missing required field")
        if not all(isinstance(item[key], str) for key in ("target", "source", "sha256", "profile")):
            raise RuntimeError(f"invalid install state entry {index}: expected string fields")
        if not isinstance(item["active"], bool):
            raise RuntimeError(f"invalid install state entry {index}: active must be boolean")
        rollback_action = item.get("rollback_action", "unknown")
        rollback_backup = item.get("rollback_backup")
        rollback_backup_sha256 = item.get("rollback_backup_sha256")
        if rollback_action not in {"unknown", "restore-backup", "remove-created"}:
            raise RuntimeError(f"invalid install state entry {index}: invalid rollback action")
        if rollback_backup is not None and not isinstance(rollback_backup, str):
            raise RuntimeError(f"invalid install state entry {index}: rollback backup must be a string or null")
        if rollback_backup_sha256 is not None and not isinstance(rollback_backup_sha256, str):
            raise RuntimeError(f"invalid install state entry {index}: rollback backup checksum must be a string or null")
        entry = ManagedFile(
            target=item["target"],
            source=item["source"],
            sha256=item["sha256"],
            profile=item["profile"],
            active=item["active"],
            rollback_action=rollback_action,
            rollback_backup=rollback_backup,
            rollback_backup_sha256=rollback_backup_sha256,
        )
        validate_entry(entry, context)
        if entry.target in result:
            raise RuntimeError(f"invalid install state entry {index}: duplicate target {entry.target}")
        result[entry.target] = entry
    return result


def source_path(entry: ManagedFile, context: InstallContext) -> Path:
    source = Path(entry.source)
    if not entry.source or source.is_absolute() or not source.parts or ".." in source.parts:
        raise RuntimeError(f"invalid install state source: {entry.source!r}")
    resolved_source = (context.kit_root / source).resolve(strict=False)
    if not is_strictly_within(resolved_source, context.kit_root) or not resolved_source.is_file():
        raise RuntimeError(f"install state source escapes kit root or is missing: {entry.source}")
    return source


def expected_target(entry: ManagedFile, source: Path, context: InstallContext) -> tuple[Path, Path]:
    parts = source.parts
    if parts == ("global", "AGENTS.md") and entry.profile == "core" and not context.repo_only:
        return context.codex_home / "AGENTS.md", context.codex_home
    if len(parts) >= 3 and parts[0] == "skills" and entry.profile in {"stable", "pilot"} and not context.repo_only:
        return context.agents_home / "skills" / Path(*parts[1:]), context.agents_home
    if parts == ("catalog", "reverse-dependencies.lock.yaml") and entry.profile == "reverse" and not context.repo_only:
        return context.codex_home / "catalog/reverse-dependencies.lock.yaml", context.codex_home
    if (
        parts == ("reverse-skill-router", "reverse-engineering", "SKILL.md")
        and entry.profile == "reverse"
        and not context.repo_only
    ):
        return context.codex_home / "skills/reverse-engineering/SKILL.md", context.codex_home
    if len(parts) >= 2 and parts[0] == "reverse-skill" and entry.profile == "reverse" and not context.repo_only:
        return context.codex_home / "reverse-skill" / Path(*parts[1:]), context.codex_home
    if (
        len(parts) >= 2
        and parts[0] == "repo-template"
        and entry.profile == "repo-template"
        and context.repo is not None
    ):
        return context.repo / Path(*parts[1:]), context.repo
    raise RuntimeError(f"install state source is not a managed kit file: {entry.source}")


def validate_entry(entry: ManagedFile, context: InstallContext) -> Path:
    if entry.profile not in PROFILES:
        raise RuntimeError(f"invalid install state profile: {entry.profile!r}")
    if len(entry.sha256) != 64 or any(char not in "0123456789abcdef" for char in entry.sha256):
        raise RuntimeError(f"invalid install state checksum for {entry.target}")

    source = source_path(entry, context)
    expected, root = expected_target(entry, source, context)
    target = Path(entry.target)
    if not target.is_absolute() or ".." in target.parts:
        raise RuntimeError(f"invalid install state target: {entry.target!r}")
    if target != expected:
        raise RuntimeError(f"install state target does not match its source: {entry.target}")
    resolved_target = target.resolve(strict=False)
    if not is_strictly_within(resolved_target, root):
        raise RuntimeError(f"install state target escapes its root: {entry.target}")
    if target.is_symlink():
        raise RuntimeError(f"install state target must not be a symlink: {entry.target}")
    if entry.rollback_action == "restore-backup" and not entry.rollback_backup:
        raise RuntimeError(f"install state restore action has no backup: {entry.target}")
    if entry.rollback_action == "remove-created" and entry.rollback_backup is not None:
        raise RuntimeError(f"install state remove action unexpectedly names a backup: {entry.target}")
    if entry.rollback_backup_sha256 is not None and (
        len(entry.rollback_backup_sha256) != 64
        or any(char not in "0123456789abcdef" for char in entry.rollback_backup_sha256)
    ):
        raise RuntimeError(f"invalid rollback backup checksum for {entry.target}")
    if entry.rollback_backup is not None:
        validate_backup_path(Path(entry.rollback_backup), target, context)
    return target


def validate_backup_path(backup: Path, target: Path, context: InstallContext) -> Path:
    if not backup.is_absolute() or ".." in backup.parts:
        raise RuntimeError(f"invalid rollback backup path: {backup}")
    if not backup.name.startswith(target.name + ".bak-") or backup.name == target.name + ".bak-":
        raise RuntimeError(f"rollback backup name does not match its target: {backup}")
    resolved_backup = backup.resolve(strict=False)
    resolved_parent = target.parent.resolve(strict=False)
    roots = (
        context.codex_home,
        context.agents_home,
        *(() if context.repo is None else (context.repo,)),
    )
    if resolved_backup.parent != resolved_parent or not any(
        is_strictly_within(resolved_backup, root) for root in roots
    ):
        raise RuntimeError(f"rollback backup escapes its target directory: {backup}")
    return backup


def record(args: argparse.Namespace) -> int:
    # Backward-compatible command name.  A post-hoc record cannot distinguish
    # fresh files from overwritten or identical pre-existing files, so it now
    # requires and commits a write-ahead transaction created by ``begin``.
    return commit(args)


def current_status(entry: ManagedFile, target: Path) -> str:
    if not target.exists():
        return "missing"
    if not target.is_file():
        return "not-file"
    return "unchanged" if sha256(target) == entry.sha256 else "modified"


def target_snapshot(entry: ManagedFile, target: Path) -> tuple[str, str | None]:
    status = current_status(entry, target)
    digest = sha256(target) if status in {"unchanged", "modified"} else None
    return status, digest


def load_managed_state(args: argparse.Namespace) -> tuple[InstallContext, Path, dict, dict[str, ManagedFile]]:
    context = install_context(args)
    path = managed_state_path(context)
    data = load_state(path)
    return context, path, data, state_entries(data, context)


def candidates(
    args: argparse.Namespace,
) -> tuple[InstallContext, Path, dict, dict[str, ManagedFile], list[dict[str, str]]]:
    context, path, data, entries = load_managed_state(args)
    rows = []
    for entry in sorted(entries.values(), key=lambda item: item.target):
        if entry.active:
            continue
        target = validate_entry(entry, context)
        rows.append({"target": entry.target, "profile": entry.profile, "status": current_status(entry, target)})
    return context, path, data, entries, rows


def remove_state(path: Path) -> None:
    path.unlink(missing_ok=True)
    try:
        path.parent.rmdir()
    except OSError:
        pass


def validate_backup(backup: Path, target: Path, context: InstallContext) -> Path:
    validate_backup_path(backup, target, context)
    if backup.is_symlink() or not backup.is_file():
        raise RuntimeError(f"rollback backup must be a regular file: {backup}")
    return backup


def journal_path(data_dir: Path, target: Path) -> Path:
    name = hashlib.sha256(str(target).encode("utf-8")).hexdigest() + ".before"
    return data_dir / name


def transaction_context(data: dict, context: InstallContext) -> None:
    expected = {
        "kit_root": str(context.kit_root),
        "codex_home": str(context.codex_home),
        "agents_home": str(context.agents_home),
        "repo": str(context.repo) if context.repo is not None else None,
        "repo_only": context.repo_only,
    }
    if data.get("schema_version") != STATE_VERSION or any(data.get(key) != value for key, value in expected.items()):
        raise RuntimeError("install transaction does not match the requested installation context")
    transaction_id = data.get("transaction_id")
    if not isinstance(transaction_id, str) or len(transaction_id) != 32 or any(
        char not in "0123456789abcdef" for char in transaction_id
    ):
        raise RuntimeError("install transaction has an invalid identifier")


def load_transaction(context: InstallContext) -> tuple[Path, Path, dict, list[TransactionFile]]:
    transaction, data_dir = transaction_paths(context)
    if not transaction.is_file() or transaction.is_symlink():
        raise RuntimeError(f"pending install transaction missing: {transaction}")
    try:
        data = json.loads(transaction.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"invalid install transaction: {transaction}: {exc}") from exc
    transaction_context(data, context)
    if (
        not isinstance(data.get("files"), list)
        or not isinstance(data.get("options"), dict)
        or not isinstance(data.get("previous_state_exists"), bool)
        or not isinstance(data.get("previous_state"), dict)
    ):
        raise RuntimeError(f"invalid install transaction: {transaction}")
    previous_state_sha = data.get("previous_state_sha256")
    if data["previous_state_exists"]:
        if not isinstance(previous_state_sha, str) or len(previous_state_sha) != 64:
            raise RuntimeError("install transaction has an invalid previous state checksum")
    elif previous_state_sha is not None:
        raise RuntimeError("install transaction records a checksum for an absent previous state")
    if data_dir.is_symlink() or not data_dir.is_dir():
        raise RuntimeError(f"install transaction data missing or invalid: {data_dir}")

    result: list[TransactionFile] = []
    targets: set[str] = set()
    for index, item in enumerate(data["files"]):
        if not isinstance(item, dict):
            raise RuntimeError(f"invalid install transaction entry {index}: expected object")
        required = {
            "target": str,
            "source": str,
            "profile": str,
            "source_sha256": str,
            "before_exists": bool,
        }
        if any(key not in item or not isinstance(item[key], kind) for key, kind in required.items()):
            raise RuntimeError(f"invalid install transaction entry {index}: invalid fields")
        before_sha = item.get("before_sha256")
        backup_value = item.get("journal_backup")
        planned_value = item.get("planned_backup")
        if before_sha is not None and not isinstance(before_sha, str):
            raise RuntimeError(f"invalid install transaction entry {index}: invalid prior checksum")
        if backup_value is not None and not isinstance(backup_value, str):
            raise RuntimeError(f"invalid install transaction entry {index}: invalid journal backup")
        if planned_value is not None and not isinstance(planned_value, str):
            raise RuntimeError(f"invalid install transaction entry {index}: invalid planned backup")

        reference = ManagedFile(
            target=item["target"],
            source=item["source"],
            sha256=item["source_sha256"],
            profile=item["profile"],
        )
        target = validate_entry(reference, context)
        if item["target"] in targets:
            raise RuntimeError(f"invalid install transaction entry {index}: duplicate target")
        targets.add(item["target"])
        if item["before_exists"]:
            if not before_sha or not backup_value:
                raise RuntimeError(f"invalid install transaction entry {index}: prior file snapshot missing")
            backup = Path(backup_value)
            if backup != journal_path(data_dir, target) or backup.is_symlink() or not backup.is_file():
                raise RuntimeError(f"invalid install transaction journal backup: {backup}")
            if len(before_sha) != 64 or sha256(backup) != before_sha:
                raise RuntimeError(f"install transaction journal backup checksum mismatch: {backup}")
        elif before_sha is not None or backup_value is not None:
            raise RuntimeError(f"invalid install transaction entry {index}: absent target has a snapshot")
        needs_public_backup = bool(data["options"].get("backup")) and item["before_exists"] and before_sha != item["source_sha256"]
        if needs_public_backup:
            expected_backup = target.with_name(
                f"{target.name}.bak-{data['transaction_id']}-{hashlib.sha256(str(target).encode('utf-8')).hexdigest()[:12]}"
            )
            if planned_value is None or Path(planned_value) != expected_backup:
                raise RuntimeError(f"invalid install transaction planned backup: {target}")
            validate_backup_path(expected_backup, target, context)
        elif planned_value is not None:
            raise RuntimeError(f"unexpected planned backup for unchanged target: {target}")
        result.append(
            TransactionFile(
                target=item["target"],
                source=item["source"],
                profile=item["profile"],
                source_sha256=item["source_sha256"],
                before_exists=item["before_exists"],
                before_sha256=before_sha,
                journal_backup=backup_value,
                planned_backup=planned_value,
            )
        )
    return transaction, data_dir, data, result


def begin(args: argparse.Namespace) -> int:
    context = install_context(args)
    transaction, data_dir = transaction_paths(context)
    if transaction.exists():
        _transaction, _data_dir, pending, _files = load_transaction(context)
        current = load_state(managed_state_path(context))
        if current.get("last_transaction_id") != pending["transaction_id"]:
            raise RuntimeError(f"pending install transaction already exists; abort it first: {transaction}")
        remove_transaction_storage(transaction, data_dir)
        print("Stale committed install journal removed")
    if data_dir.exists():
        remove_transaction_storage(transaction, data_dir)

    state = managed_state_path(context)
    previous_state_exists = state.is_file()
    previous_state_sha = sha256(state) if previous_state_exists else None
    previous_data = load_state(state)
    previous_entries = state_entries(previous_data, context)
    previous_state = {
        key: value
        for key, value in previous_data.items()
        if key not in {"last_transaction", "last_transaction_id"}
    }
    previous_state["files"] = [
        asdict(entry) for entry in sorted(previous_entries.values(), key=lambda value: value.target)
    ]
    transaction_id = secrets.token_hex(16)

    expected = expected_files(
        context.kit_root,
        context.codex_home,
        context.agents_home,
        pilots=args.with_pilots,
        reverse=args.with_reverse,
        repo=context.repo,
        repo_only=context.repo_only,
    )
    observations: list[tuple[Path, Path, str, str, str | None, Path | None]] = []
    for source, target, profile in expected:
        source_relative = source.relative_to(context.kit_root).as_posix()
        source_hash = sha256(source)
        reference = ManagedFile(str(target), source_relative, source_hash, profile)
        validate_entry(reference, context)
        if target.exists() and not target.is_file():
            raise RuntimeError(f"install target must be a regular file: {target}")
        before_hash = sha256(target) if target.is_file() else None
        planned_backup: Path | None = None
        if args.backup and before_hash is not None and before_hash != source_hash:
            suffix = hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:12]
            planned_backup = target.with_name(f"{target.name}.bak-{transaction_id}-{suffix}")
            validate_backup_path(planned_backup, target, context)
            if planned_backup.exists() or planned_backup.is_symlink():
                raise RuntimeError(f"planned install backup already exists: {planned_backup}")
        observations.append((source, target, profile, source_hash, before_hash, planned_backup))

    data_dir.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(mode=0o700)
    records: list[dict[str, object]] = []
    try:
        for source, target, profile, source_hash, before_hash, planned_backup in observations:
            snapshot: Path | None = None
            if before_hash is not None:
                snapshot = journal_path(data_dir, target)
                shutil.copy2(target, snapshot)
                if sha256(snapshot) != before_hash or sha256(target) != before_hash:
                    raise RuntimeError(f"install target changed while its transaction snapshot was created: {target}")
            records.append(
                {
                    "target": str(target),
                    "source": source.relative_to(context.kit_root).as_posix(),
                    "profile": profile,
                    "source_sha256": source_hash,
                    "before_exists": before_hash is not None,
                    "before_sha256": before_hash,
                    "journal_backup": str(snapshot) if snapshot is not None else None,
                    "planned_backup": str(planned_backup) if planned_backup is not None else None,
                }
            )
        data = {
            "schema_version": STATE_VERSION,
            "transaction_id": transaction_id,
            "kit_root": str(context.kit_root),
            "codex_home": str(context.codex_home),
            "agents_home": str(context.agents_home),
            "repo": str(context.repo) if context.repo is not None else None,
            "repo_only": context.repo_only,
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "options": {
                "pilots": bool(args.with_pilots),
                "reverse": bool(args.with_reverse),
                "backup": bool(args.backup),
                "force": bool(args.force),
            },
            "previous_state_exists": previous_state_exists,
            "previous_state_sha256": previous_state_sha,
            "previous_state": previous_state,
            "files": records,
        }
        save_state(transaction, data)
    except Exception:
        remove_transaction_storage(transaction, data_dir)
        raise
    print(f"Install transaction started: {transaction} ({len(records)} targets)")
    return 0


def _assert_transaction_options(data: dict, args: argparse.Namespace) -> None:
    expected = {
        "pilots": bool(args.with_pilots),
        "reverse": bool(args.with_reverse),
        "backup": bool(args.backup),
        "force": bool(args.force),
    }
    if data.get("options") != expected:
        raise RuntimeError("install transaction options do not match the requested operation")


def _transaction_target(args: argparse.Namespace) -> tuple[InstallContext, dict, TransactionFile]:
    if args.target is None:
        raise RuntimeError("this install transaction operation requires --target")
    context = install_context(args)
    _transaction, _data_dir, data, files = load_transaction(context)
    _assert_transaction_options(data, args)
    requested = str(args.target.resolve(strict=False))
    match = next((item for item in files if item.target == requested), None)
    if match is None:
        raise RuntimeError(f"target is not part of the pending install transaction: {args.target}")
    return context, data, match


def _verify_preimage(item: TransactionFile, context: InstallContext) -> Path:
    target = Path(item.target)
    reference = ManagedFile(item.target, item.source, item.source_sha256, item.profile)
    validate_entry(reference, context)
    source = context.kit_root / item.source
    if sha256(source) != item.source_sha256:
        raise RuntimeError(f"install source changed after transaction begin: {source}")
    if item.before_exists:
        if target.is_symlink() or not target.is_file() or sha256(target) != item.before_sha256:
            raise RuntimeError(f"install target changed after transaction begin: {target}")
    elif target.exists() or target.is_symlink():
        raise RuntimeError(f"install target appeared after transaction begin: {target}")
    return target


def preflight_copy(args: argparse.Namespace) -> int:
    context, _data, item = _transaction_target(args)
    _verify_preimage(item, context)
    return 0


def _create_planned_backup(
    context: InstallContext,
    data: dict,
    item: TransactionFile,
    target: Path,
) -> Path:
    if not data["options"]["backup"] or item.planned_backup is None or item.before_sha256 is None:
        raise RuntimeError(f"transaction did not plan a backup for target: {target}")
    backup = Path(item.planned_backup)
    validate_backup_path(backup, target, context)
    if backup.exists() or backup.is_symlink():
        if backup.is_symlink() or not backup.is_file() or sha256(backup) != item.before_sha256:
            raise RuntimeError(f"planned install backup already exists with different content: {backup}")
        return backup
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with target.open("rb") as source_handle, os.fdopen(descriptor, "wb") as backup_handle:
            descriptor = None
            shutil.copyfileobj(source_handle, backup_handle, length=1024 * 1024)
            backup_handle.flush()
            os.fsync(backup_handle.fileno())
        shutil.copystat(target, backup, follow_symlinks=False)
        if sha256(backup) != item.before_sha256:
            raise RuntimeError(f"created install backup checksum mismatch: {backup}")
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            backup.unlink(missing_ok=True)
        raise
    return backup


def create_backup(args: argparse.Namespace) -> int:
    context, data, item = _transaction_target(args)
    target = _verify_preimage(item, context)
    backup = _create_planned_backup(context, data, item, target)
    print(backup)
    return 0


def copy_target(args: argparse.Namespace) -> int:
    """Copy one transaction target after verifying its exact preimage.

    Centralising the copy keeps POSIX and PowerShell on the same write path and
    removes timestamp/glob backup inference from both installers.
    """

    context, data, item = _transaction_target(args)
    target = _verify_preimage(item, context)
    source = context.kit_root / item.source
    if item.before_sha256 == item.source_sha256:
        return 0
    if item.before_exists and not (data["options"]["backup"] or data["options"]["force"]):
        raise RuntimeError(f"pre-existing target requires backup or force: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.planned_backup is not None:
        _create_planned_backup(context, data, item, target)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.install-stage.", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        if sha256(temporary) != item.source_sha256:
            raise RuntimeError(f"staged install source checksum mismatch: {source}")
        # Recheck immediately before the atomic replacement. Cooperative
        # installers cannot overwrite a target that drifted after begin.
        _verify_preimage(item, context)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return 0


def commit(args: argparse.Namespace) -> int:
    context = install_context(args)
    transaction, data_dir, transaction_data, transaction_files = load_transaction(context)
    _assert_transaction_options(transaction_data, args)
    expected = expected_files(
        context.kit_root,
        context.codex_home,
        context.agents_home,
        pilots=args.with_pilots,
        reverse=args.with_reverse,
        repo=context.repo,
        repo_only=context.repo_only,
    )
    expected_targets = {str(target) for _source, target, _profile in expected}
    if expected_targets != {item.target for item in transaction_files}:
        raise RuntimeError("install transaction target set no longer matches the selected profiles")

    state = managed_state_path(context)
    state_exists = state.is_file()
    if state_exists != transaction_data["previous_state_exists"]:
        raise RuntimeError("install state changed after transaction begin")
    if state_exists and sha256(state) != transaction_data["previous_state_sha256"]:
        raise RuntimeError("install state changed after transaction begin")
    data = load_state(state)
    entries = state_entries(data, context)
    for entry in entries.values():
        entry.active = False

    for item in transaction_files:
        target = Path(item.target)
        reference = ManagedFile(item.target, item.source, item.source_sha256, item.profile)
        validate_entry(reference, context)
        if not target.is_file() or target.is_symlink() or sha256(target) != item.source_sha256:
            raise RuntimeError(f"installed target does not match its transaction source: {target}")

        previous = entries.get(item.target)
        if not item.before_exists:
            entry = ManagedFile(
                item.target,
                item.source,
                item.source_sha256,
                item.profile,
                active=True,
            )
            entries[item.target] = entry
            continue
        if item.before_sha256 == item.source_sha256:
            # An identical pre-existing file is user-owned unless a prior state
            # record proves this kit already managed the exact contents.
            if previous is not None and previous.sha256 == item.before_sha256:
                previous.source = item.source
                previous.sha256 = item.source_sha256
                previous.profile = item.profile
                previous.active = True
            else:
                entries.pop(item.target, None)
            continue

        options = transaction_data["options"]
        if options["backup"]:
            if item.planned_backup is None:
                raise RuntimeError(f"install transaction is missing its planned backup: {target}")
            backup = validate_backup(Path(item.planned_backup), target, context)
            if sha256(backup) != item.before_sha256:
                raise RuntimeError(f"install backup does not match its exact preimage: {backup}")
            entry = ManagedFile(item.target, item.source, item.source_sha256, item.profile, active=True)
        elif options["force"]:
            entry = ManagedFile(item.target, item.source, item.source_sha256, item.profile, active=True)
        else:
            raise RuntimeError(f"pre-existing target changed without backup or force: {target}")
        validate_entry(entry, context)
        entries[item.target] = entry

    transaction_id = transaction_data["transaction_id"]
    rollback_dir = rollback_data_path(context, transaction_id)
    if rollback_dir.exists() or rollback_dir.is_symlink():
        raise RuntimeError(f"rollback data already exists: {rollback_dir}")
    rollback_dir.mkdir(mode=0o700)
    rollback_files: list[dict[str, object]] = []
    try:
        for item in transaction_files:
            if item.before_sha256 == item.source_sha256:
                continue
            snapshot: Path | None = None
            snapshot_hash: str | None = None
            if item.before_exists:
                journal = Path(item.journal_backup or "")
                snapshot = rollback_dir / (hashlib.sha256(item.target.encode("utf-8")).hexdigest() + ".before")
                shutil.copy2(journal, snapshot)
                snapshot_hash = sha256(snapshot)
                if snapshot_hash != item.before_sha256:
                    raise RuntimeError(f"durable rollback snapshot checksum mismatch: {item.target}")
            rollback_files.append(
                {
                    "target": item.target,
                    "source": item.source,
                    "profile": item.profile,
                    "installed_sha256": item.source_sha256,
                    "before_exists": item.before_exists,
                    "before_sha256": item.before_sha256,
                    "rollback_snapshot": str(snapshot) if snapshot is not None else None,
                    "rollback_snapshot_sha256": snapshot_hash,
                    "public_backup": item.planned_backup,
                }
            )

        new_state = {
            "schema_version": STATE_VERSION,
            "kit_root": str(context.kit_root),
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "profiles": {
                "pilots": bool(args.with_pilots),
                "reverse": bool(args.with_reverse),
                "repo": str(context.repo) if context.repo else None,
            },
            "last_transaction_id": transaction_id,
            "last_transaction": {
                "transaction_id": transaction_id,
                "previous_state_exists": transaction_data["previous_state_exists"],
                "previous_state": transaction_data["previous_state"],
                "rollback_data": str(rollback_dir),
                "files": rollback_files,
            },
            "files": [asdict(entry) for entry in sorted(entries.values(), key=lambda value: value.target)],
        }
        save_state(state, new_state)
    except Exception:
        remove_rollback_storage(rollback_dir)
        raise

    # The new state is authoritative after the atomic replace. Cleanup failures
    # must not make the installer abort behind that committed state.
    try:
        cleanup_unreferenced_rollback_storage(context, keep=rollback_dir)
        remove_transaction_storage(transaction, data_dir)
    except (OSError, RuntimeError) as exc:
        print(f"Install transaction cleanup warning: {exc}", file=sys.stderr)
    print(f"Install transaction committed: {state} ({sum(entry.active for entry in entries.values())} active files)")
    return 0


def abort(args: argparse.Namespace) -> int:
    context = install_context(args)
    transaction, data_dir, transaction_data, transaction_files = load_transaction(context)
    committed_state = load_state(managed_state_path(context))
    if committed_state.get("last_transaction_id") == transaction_data["transaction_id"]:
        remove_transaction_storage(transaction, data_dir)
        print("Install transaction was already committed; stale journal removed")
        return 0
    operations: list[dict[str, object]] = []
    conflicts: list[str] = []
    generated_backups: list[Path] = []

    for item in transaction_files:
        target = Path(item.target)
        reference = ManagedFile(item.target, item.source, item.source_sha256, item.profile)
        validate_entry(reference, context)
        if target.exists() and not target.is_file():
            raise RuntimeError(f"install abort target must be a regular file: {target}")
        current_hash = sha256(target) if target.is_file() else None
        if item.before_exists:
            if current_hash in {None, item.source_sha256}:
                action = "restore"
            elif current_hash == item.before_sha256:
                action = "unchanged"
            else:
                action = "preserve"
        elif current_hash is None:
            action = "unchanged"
        elif current_hash == item.source_sha256:
            action = "remove"
        else:
            action = "preserve"
        operations.append({"item": item, "target": target, "hash": current_hash, "action": action})

        if item.planned_backup is not None:
            backup = Path(item.planned_backup)
            validate_backup_path(backup, target, context)
            if backup.exists() or backup.is_symlink():
                if backup.is_symlink() or not backup.is_file() or sha256(backup) != item.before_sha256:
                    conflicts.append(f"{backup} (planned backup changed outside this install transaction)")
                else:
                    generated_backups.append(backup)

    if conflicts:
        print("Install abort conflicts:\n" + "\n".join(conflicts), file=sys.stderr)
        return 1

    staged: dict[str, Path] = {}
    originals: dict[str, Path] = {}
    try:
        for operation in operations:
            if operation["action"] != "restore":
                continue
            item = operation["item"]
            target = operation["target"]
            assert isinstance(item, TransactionFile) and isinstance(target, Path)
            source = Path(item.journal_backup or "")
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.abort-stage.", dir=target.parent)
            os.close(descriptor)
            temporary = Path(temporary_name)
            staged[str(target)] = temporary
            shutil.copy2(source, temporary)
            if sha256(temporary) != item.before_sha256:
                raise RuntimeError(f"install abort staging checksum mismatch: {target}")

        for operation in operations:
            target = operation["target"]
            assert isinstance(target, Path)
            if operation["action"] not in {"restore", "remove"}:
                continue
            if target.exists():
                descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.abort-original.", dir=target.parent)
                os.close(descriptor)
                temporary = Path(temporary_name)
                temporary.unlink()
                os.replace(target, temporary)
                originals[str(target)] = temporary
            if operation["action"] == "restore":
                os.replace(staged[str(target)], target)
    except Exception:
        for operation in reversed(operations):
            target = operation["target"]
            assert isinstance(target, Path)
            original = originals.get(str(target))
            if original is None:
                item = operation["item"]
                assert isinstance(item, TransactionFile)
                if target.is_file() and not item.before_exists:
                    target.unlink()
                continue
            if target.exists():
                target.unlink()
            if original.exists():
                os.replace(original, target)
        raise
    finally:
        for temporary in (*staged.values(), *originals.values()):
            temporary.unlink(missing_ok=True)

    for backup in generated_backups:
        backup.unlink(missing_ok=True)
    remove_transaction_storage(transaction, data_dir)
    print(f"Install transaction aborted: restored={sum(op['action'] == 'restore' for op in operations)} removed={sum(op['action'] == 'remove' for op in operations)}")
    return 0


def prune(args: argparse.Namespace, *, preview: bool) -> int:
    context, path, data, entries, rows = candidates(args)
    if preview:
        print(json.dumps({"state": str(path), "candidates": rows}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    removed: list[str] = []
    skipped: list[str] = []
    components: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        entry = entries[row["target"]]
        source = Path(entry.source)
        if entry.profile in {"stable", "pilot"} and len(source.parts) >= 3 and source.parts[0] == "skills":
            # A Skill is one operational unit even though state records hashes
            # per file. Leaving a modified SKILL.md while deleting its agents
            # or references produces a broken user-owned customization.
            key = ("skill", source.parts[1])
        elif entry.profile in {"reverse", "repo-template"}:
            # Optional profile trees are also installed and rolled back as one
            # capability. Do not leave a user-modified profile half-pruned.
            key = ("profile", entry.profile)
        else:
            key = ("file", entry.target)
        components.setdefault(key, []).append(row)

    for component_key, component_rows in components.items():
        component_entries = [entries[row["target"]] for row in component_rows]
        component_targets = [validate_entry(entry, context) for entry in component_entries]
        observed = [current_status(entry, target) for entry, target in zip(component_entries, component_targets)]
        unsafe_index = next(
            (index for index, status in enumerate(observed) if status not in {"missing", "unchanged"}),
            None,
        )
        component_label = (
            f"{component_key[0]} {component_key[1]}"
            if component_key[0] != "file"
            else component_entries[0].target
        )
        if unsafe_index is not None and not args.force:
            skipped.append(
                f"{component_label} (contains {observed[unsafe_index]} file "
                f"{component_targets[unsafe_index]}; use --force to remove)"
            )
            continue

        # Recheck every file in a component before touching any of them. This
        # keeps a late user edit from turning a safe prune into a partial Skill
        # deletion under cooperative concurrent installers.
        refreshed = [current_status(entry, target) for entry, target in zip(component_entries, component_targets)]
        unsafe_index = next(
            (index for index, status in enumerate(refreshed) if status not in {"missing", "unchanged"}),
            None,
        )
        if unsafe_index is not None and not args.force:
            skipped.append(
                f"{component_label} (changed during validation: {refreshed[unsafe_index]} file "
                f"{component_targets[unsafe_index]}; use --force to remove)"
            )
            continue

        for entry, target, status in zip(component_entries, component_targets, refreshed):
            if status == "missing":
                entries.pop(entry.target, None)
                removed.append(entry.target)
            else:
                target.unlink(missing_ok=True)
                entries.pop(entry.target, None)
                removed.append(entry.target)
    if skipped:
        print("Prune conflicts:\n" + "\n".join(skipped), file=sys.stderr)
    if entries:
        data["files"] = [asdict(entry) for entry in sorted(entries.values(), key=lambda item: item.target)]
        save_state(path, data)
    elif path.exists():
        remove_state(path)
    print(f"Prune complete: removed={len(removed)} skipped={len(skipped)}")
    return 1 if skipped else 0


def uninstall(args: argparse.Namespace) -> int:
    context, path, data, entries = load_managed_state(args)
    rollback_dir: Path | None = None
    if data.get("last_transaction") is not None:
        _transaction, rollback_dir, _files = load_last_transaction(data, context)
    operations: list[tuple[ManagedFile, Path, tuple[str, str | None]]] = []
    conflicts: list[str] = []
    for entry in sorted(entries.values(), key=lambda item: item.target):
        target = validate_entry(entry, context)
        snapshot = target_snapshot(entry, target)
        status = snapshot[0]
        if status == "not-file":
            raise RuntimeError(f"managed uninstall target must be a regular file: {target}")
        if status == "modified" and not args.force:
            conflicts.append(f"{entry.target} (modified; use --force to remove)")
        operations.append((entry, target, snapshot))

    # Do not partially uninstall when any target needs a decision.
    if conflicts:
        print("Uninstall conflicts:\n" + "\n".join(conflicts), file=sys.stderr)
        print(f"Uninstall complete: removed=0 skipped={len(conflicts)}")
        return 1
    for entry, target, snapshot in operations:
        validate_entry(entry, context)
        if target_snapshot(entry, target) != snapshot:
            raise RuntimeError(f"managed uninstall target changed during validation: {target}")

    removed = 0
    for _entry, target, snapshot in operations:
        if snapshot[0] != "missing":
            target.unlink()
            removed += 1
    remove_state(path)
    if rollback_dir is not None:
        remove_rollback_storage(rollback_dir)
    cleanup_unreferenced_rollback_storage(context)
    print(f"Uninstall complete: removed={removed} skipped=0")
    return 0


def load_last_transaction(
    data: dict,
    context: InstallContext,
) -> tuple[dict, Path, list[RollbackFile]]:
    value = data.get("last_transaction")
    if not isinstance(value, dict):
        raise RuntimeError("no committed install transaction is available to roll back")
    transaction_id = value.get("transaction_id")
    if not isinstance(transaction_id, str) or data.get("last_transaction_id") != transaction_id:
        raise RuntimeError("install rollback transaction identity is invalid")
    rollback_dir = rollback_data_path(context, transaction_id)
    if value.get("rollback_data") != str(rollback_dir):
        raise RuntimeError("install rollback data path is invalid")
    if rollback_dir.is_symlink() or not rollback_dir.is_dir():
        raise RuntimeError(f"install rollback data is missing or invalid: {rollback_dir}")
    if not isinstance(value.get("previous_state_exists"), bool) or not isinstance(value.get("previous_state"), dict):
        raise RuntimeError("install rollback previous state is invalid")
    previous_state = value["previous_state"]
    if previous_state.get("schema_version") != STATE_VERSION or not isinstance(previous_state.get("files"), list):
        raise RuntimeError("install rollback previous state schema is invalid")
    if "last_transaction" in previous_state or "last_transaction_id" in previous_state:
        raise RuntimeError("install rollback previous state must not contain a nested transaction")
    state_entries(previous_state, context)
    if not isinstance(value.get("files"), list):
        raise RuntimeError("install rollback file list is invalid")

    result: list[RollbackFile] = []
    targets: set[str] = set()
    for index, item in enumerate(value["files"]):
        if not isinstance(item, dict):
            raise RuntimeError(f"invalid rollback file {index}: expected object")
        required = {
            "target": str,
            "source": str,
            "profile": str,
            "installed_sha256": str,
            "before_exists": bool,
        }
        if any(key not in item or not isinstance(item[key], kind) for key, kind in required.items()):
            raise RuntimeError(f"invalid rollback file {index}: invalid fields")
        before_sha = item.get("before_sha256")
        snapshot_value = item.get("rollback_snapshot")
        snapshot_sha = item.get("rollback_snapshot_sha256")
        public_backup = item.get("public_backup")
        if any(value is not None and not isinstance(value, str) for value in (before_sha, snapshot_value, snapshot_sha, public_backup)):
            raise RuntimeError(f"invalid rollback file {index}: invalid optional fields")
        reference = ManagedFile(
            item["target"], item["source"], item["installed_sha256"], item["profile"]
        )
        target = validate_entry(reference, context)
        if item["target"] in targets:
            raise RuntimeError(f"invalid rollback file {index}: duplicate target")
        targets.add(item["target"])
        if item["before_exists"]:
            expected_snapshot = rollback_dir / (
                hashlib.sha256(item["target"].encode("utf-8")).hexdigest() + ".before"
            )
            if (
                not isinstance(before_sha, str)
                or not isinstance(snapshot_value, str)
                or not isinstance(snapshot_sha, str)
                or Path(snapshot_value) != expected_snapshot
                or expected_snapshot.is_symlink()
                or not expected_snapshot.is_file()
                or sha256(expected_snapshot) != before_sha
                or snapshot_sha != before_sha
            ):
                raise RuntimeError(f"invalid rollback snapshot for target: {target}")
        elif before_sha is not None or snapshot_value is not None or snapshot_sha is not None:
            raise RuntimeError(f"new rollback target unexpectedly has a prior snapshot: {target}")
        if public_backup is not None:
            validate_backup_path(Path(public_backup), target, context)
        result.append(
            RollbackFile(
                target=item["target"],
                source=item["source"],
                profile=item["profile"],
                installed_sha256=item["installed_sha256"],
                before_exists=item["before_exists"],
                before_sha256=before_sha,
                rollback_snapshot=snapshot_value,
                rollback_snapshot_sha256=snapshot_sha,
                public_backup=public_backup,
            )
        )
    return value, rollback_dir, result


def rollback(args: argparse.Namespace) -> int:
    context, path, data, entries = load_managed_state(args)
    del entries  # Ownership is restored from the transaction's previous-state snapshot.
    if not path.is_file():
        raise RuntimeError("no committed install transaction is available to roll back")
    state_hash = sha256(path)
    transaction, rollback_dir, files = load_last_transaction(data, context)
    operations: list[dict[str, object]] = []
    conflicts: list[str] = []

    for item in files:
        target = Path(item.target)
        reference = ManagedFile(item.target, item.source, item.installed_sha256, item.profile)
        validate_entry(reference, context)
        if target.exists() and (target.is_symlink() or not target.is_file()):
            raise RuntimeError(f"managed rollback target must be a regular file: {target}")
        current_hash = sha256(target) if target.is_file() else None
        action = "restore" if item.before_exists else "remove"
        if item.before_exists and current_hash not in {None, item.installed_sha256} and not args.force:
            conflicts.append(f"{target} (modified; use --force to restore the transaction preimage)")
        elif not item.before_exists and current_hash not in {None, item.installed_sha256}:
            conflicts.append(f"{target} (modified after install; rollback will not discard user data)")
        operations.append(
            {
                "item": item,
                "target": target,
                "action": action,
                "current_hash": current_hash,
            }
        )

    if conflicts:
        print("Rollback conflicts:\n" + "\n".join(conflicts), file=sys.stderr)
        print(f"Rollback complete: restored=0 removed_created=0 skipped={len(conflicts)}")
        return 1

    # Recheck every observation as one barrier. --force never bypasses path,
    # file-type, state-integrity, or private-snapshot checks.
    if not path.is_file() or sha256(path) != state_hash:
        raise RuntimeError("install state changed during rollback validation")
    for operation in operations:
        item = operation["item"]
        target = operation["target"]
        assert isinstance(item, RollbackFile) and isinstance(target, Path)
        reference = ManagedFile(item.target, item.source, item.installed_sha256, item.profile)
        validate_entry(reference, context)
        current_hash = sha256(target) if target.is_file() and not target.is_symlink() else None
        if current_hash != operation["current_hash"] or (target.exists() and not target.is_file()):
            raise RuntimeError(f"managed rollback target changed during validation: {target}")

    staged: dict[str, Path] = {}
    originals: dict[str, Path] = {}
    touched: set[str] = set()
    try:
        # Stage and verify every private preimage before touching any target.
        for operation in operations:
            if operation["action"] != "restore":
                continue
            item = operation["item"]
            target = operation["target"]
            assert isinstance(item, RollbackFile) and isinstance(target, Path)
            snapshot = Path(item.rollback_snapshot or "")
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.rollback-stage.", dir=target.parent
            )
            os.close(descriptor)
            temporary = Path(temporary_name)
            staged[str(target)] = temporary
            shutil.copy2(snapshot, temporary)
            if sha256(temporary) != item.before_sha256:
                raise RuntimeError(f"staged rollback snapshot checksum mismatch: {snapshot}")

        for operation in operations:
            target = operation["target"]
            assert isinstance(target, Path)
            if operation["action"] == "remove" and operation["current_hash"] is None:
                continue
            if target.exists():
                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=f".{target.name}.rollback-original.", dir=target.parent
                )
                os.close(descriptor)
                temporary = Path(temporary_name)
                temporary.unlink()
                os.replace(target, temporary)
                originals[str(target)] = temporary
            touched.add(str(target))
            if operation["action"] == "restore":
                os.replace(staged[str(target)], target)

        if not path.is_file() or sha256(path) != state_hash:
            raise RuntimeError("install state changed before rollback commit")
        if transaction["previous_state_exists"]:
            save_state(path, transaction["previous_state"])
        else:
            remove_state(path)
    except Exception:
        for operation in reversed(operations):
            target = operation["target"]
            assert isinstance(target, Path)
            original = originals.get(str(target))
            if original is None:
                if str(target) in touched and target.is_file():
                    target.unlink()
                continue
            if target.exists():
                target.unlink()
            if original.exists():
                os.replace(original, target)
        raise
    finally:
        for temporary in (*staged.values(), *originals.values()):
            temporary.unlink(missing_ok=True)

    # Restoration and state replacement have already committed. A cleanup
    # failure should be visible as a warning, not misreported as a failed
    # rollback after the caller-visible state has changed.
    try:
        remove_rollback_storage(rollback_dir)
    except (OSError, RuntimeError) as exc:
        print(f"Rollback cleanup warning: {exc}", file=sys.stderr)
    restored = sum(operation["action"] == "restore" for operation in operations)
    removed_created = sum(
        operation["action"] == "remove" and operation["current_hash"] is not None
        for operation in operations
    )
    print(f"Rollback complete: restored={restored} removed_created={removed_created} skipped=0")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "mode",
        choices=(
            "begin",
            "preflight-copy",
            "create-backup",
            "copy-target",
            "commit",
            "abort",
            "record",
            "prune-preview",
            "prune",
            "uninstall",
            "rollback",
        ),
    )
    p.add_argument("--kit-root", type=Path, default=Path.cwd())
    p.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    p.add_argument("--agents-home", type=Path, default=Path.home() / ".agents")
    p.add_argument("--repo", type=Path)
    p.add_argument("--repo-only", action="store_true")
    p.add_argument("--with-pilots", action="store_true")
    p.add_argument("--with-reverse", action="store_true")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--target", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.backup and args.force:
            raise RuntimeError("--backup and --force cannot be used together")
        if args.mode == "begin":
            return begin(args)
        if args.mode == "preflight-copy":
            return preflight_copy(args)
        if args.mode == "create-backup":
            return create_backup(args)
        if args.mode == "copy-target":
            return copy_target(args)
        if args.mode == "commit":
            return commit(args)
        if args.mode == "abort":
            return abort(args)
        if args.mode == "record":
            return record(args)
        if args.mode == "prune-preview":
            return prune(args, preview=True)
        if args.mode == "prune":
            return prune(args, preview=False)
        if args.mode == "uninstall":
            return uninstall(args)
        return rollback(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"install state error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
