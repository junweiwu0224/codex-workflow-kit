#!/usr/bin/env python3
"""Resolve catalog intent against an existing lock without fabricating data."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256
    from scripts.validate_governance import load_catalog, load_lock
except ImportError:  # pragma: no cover - supports direct module execution from eval/
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256
    from scripts.validate_governance import load_catalog, load_lock


SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FLOATING_RE = re.compile(r"(?:^|[/@:])(?:main|master|HEAD|latest|edge|nightly)(?:$|[/@:])", re.IGNORECASE)
SCHEMA_VERSION = "4.2"


class ResolverError(ValueError):
    """Raised for malformed catalog/lock input."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _has_floating(value: Any) -> bool:
    if isinstance(value, str):
        return bool(FLOATING_RE.search(value))
    if isinstance(value, Mapping):
        return any(_has_floating(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_floating(item) for item in value)
    return False


def _find_entry(entries: list[Any], name: str) -> Mapping[str, Any] | None:
    for entry in entries:
        if isinstance(entry, Mapping) and (entry.get("name") == name or entry.get("catalog_ref") == name):
            return entry
    return None


def _has_expected_repo_local_path(entry: Mapping[str, Any], name: str) -> bool:
    source = entry.get("source")
    if not isinstance(source, Mapping) or source.get("kind") != "repo-local":
        return True
    directory = Path("skills") / name
    return source.get("path") in {directory.as_posix(), (directory / "SKILL.md").as_posix()}


def _entry_resolution(entry: Mapping[str, Any] | None) -> tuple[str, list[str]]:
    if entry is None:
        return "missing", ["no lock entry"]
    issues: list[str] = []
    source = entry.get("source")
    source_kind = source.get("kind") if isinstance(source, Mapping) else None
    resolution = entry.get("resolution")
    if not isinstance(resolution, Mapping) or resolution.get("status") != "resolved":
        issues.append("resolution is not resolved")
    elif source_kind == "repo-local":
        if resolution.get("kind") != "repo-local-content":
            issues.append("repo-local resolution.kind is not repo-local-content")
        if "commit" in resolution or "digest" in resolution:
            issues.append("repo-local resolution must use content SHA-256 identity")
    else:
        resolution_kind = resolution.get("kind")
        commit = resolution.get("commit")
        digest = resolution.get("digest")
        if resolution_kind in {"commit", "git-commit"} and (
            not isinstance(commit, str) or not SHA1_RE.fullmatch(commit)
        ):
            issues.append("resolution.commit is not a full 40-character SHA")
        elif resolution_kind in {"digest", "container-digest"} and (
            not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest)
        ):
            issues.append("resolution.digest is not an immutable sha256 digest")
        elif resolution_kind not in {"commit", "git-commit", "digest", "container-digest"}:
            issues.append("external resolution is not pinned to an immutable commit or digest")
    content = entry.get("content")
    if not isinstance(content, Mapping) or content.get("status") != "resolved":
        issues.append("content hash is not resolved")
    else:
        value = content.get("value")
        if content.get("algorithm") != "sha256" or not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            issues.append("content.value is not a SHA-256 hash")
        if source_kind == "repo-local" and content.get("scope") != TREE_HASH_SCOPE:
            issues.append(f"repo-local content.scope is not {TREE_HASH_SCOPE}")
    compatibility = entry.get("compatibility")
    if not isinstance(compatibility, Mapping) or compatibility.get("status") != "resolved":
        issues.append("compatibility is unresolved")
    license_info = entry.get("license")
    if not isinstance(license_info, Mapping) or license_info.get("status") != "resolved":
        issues.append("license is unresolved")
    if _has_floating(entry):
        issues.append("lock contains a floating reference")
    return ("resolved" if not issues else "unresolved"), issues


def _observe_local_content(entry: Mapping[str, Any] | None, repository_root: Path | None) -> tuple[str | None, str | None]:
    """Return (observed hash, issue) for a repo-local lock entry.

    The resolver never rewrites the lock.  It only compares a present local
    file with the recorded content hash so a stale lock cannot silently pass.
    """
    if entry is None or repository_root is None:
        return None, None
    source = entry.get("source")
    if not isinstance(source, Mapping) or source.get("kind") != "repo-local":
        return None, None
    relative = source.get("path")
    if not isinstance(relative, str) or not relative:
        return None, "repo-local source path is missing"
    try:
        directory = skill_tree_directory(repository_root, relative)
        observed = skill_tree_sha256(directory)
    except ValueError as exc:
        return None, str(exc)
    recorded = entry.get("content", {}).get("value") if isinstance(entry.get("content"), Mapping) else None
    if isinstance(recorded, str) and recorded != observed:
        return observed, "local content hash does not match lock"
    return observed, None


def resolve_catalog(
    catalog_path: str | Path,
    lock_path: str | Path,
    *,
    repository_root: str | Path | None = None,
    resolver_version: str = "4.2.0",
) -> dict[str, Any]:
    """Produce a resolution report from catalog intent and lock state.

    This function is read-only.  An unresolved source is reported as
    ``unresolved`` and never replaced with a guessed tag, network response, or
    synthetic hash.
    """
    catalog = load_catalog(catalog_path)
    lock = load_lock(lock_path)
    skills = catalog.get("skills", [])
    entries = lock.get("entries", [])
    if not isinstance(skills, list) or not isinstance(entries, list):
        raise ResolverError("catalog.skills and lock.entries must be lists")
    rows: list[dict[str, Any]] = []
    root_path = Path(repository_root).resolve() if repository_root else None
    for skill in skills:
        if not isinstance(skill, Mapping) or not isinstance(skill.get("name"), str):
            raise ResolverError("each catalog skill must have a name")
        name = str(skill["name"])
        entry = _find_entry(entries, name)
        status, issues = _entry_resolution(entry)
        if isinstance(entry, Mapping) and not _has_expected_repo_local_path(entry, name):
            issues.append("repo-local source.path does not match catalog skill tree")
            status = "unresolved"
        observed_hash, observed_issue = _observe_local_content(entry, root_path)
        if observed_issue:
            issues.append(observed_issue)
            status = "unresolved"
        if entry is not None and _has_floating(skill):
            issues.append("catalog contains a floating reference")
            status = "unresolved"
        rows.append(
            {
                "name": name,
                "catalog_status": skill.get("status"),
                "catalog_implicit": bool(skill.get("implicit", False)),
                "lock_present": entry is not None,
                "resolution_status": status,
                "issues": sorted(set(issues)),
                "stable_eligible": bool(skill.get("status") == "stable" and status == "resolved"),
                "source": entry.get("source") if isinstance(entry, Mapping) else None,
                "resolution": entry.get("resolution") if isinstance(entry, Mapping) else None,
                "content": entry.get("content") if isinstance(entry, Mapping) else None,
                "observed_content_sha256": observed_hash,
                "compatibility": entry.get("compatibility") if isinstance(entry, Mapping) else None,
                "license": entry.get("license") if isinstance(entry, Mapping) else None,
            }
        )
    unresolved = [row for row in rows if row["resolution_status"] != "resolved"]
    stable_unresolved = [row for row in rows if row["catalog_status"] == "stable" and row["resolution_status"] != "resolved"]
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": "resolver-result",
        "resolver_version": resolver_version,
        "generated_at": _now(),
        "catalog_path": str(Path(catalog_path)),
        "lock_path": str(Path(lock_path)),
        # Preserve the caller's logical root rather than embedding a private
        # absolute home path in a report that may be checked into Git.
        "repository_root": str(Path(repository_root)) if repository_root else None,
        "catalog_sha256": _sha256(catalog),
        "lock_sha256": _sha256(lock),
        "summary": {
            "total": len(rows),
            "resolved": len(rows) - len(unresolved),
            "unresolved": len(unresolved),
            "stable_unresolved": len(stable_unresolved),
            "release_eligible": not stable_unresolved,
        },
        "entries": rows,
        "disclaimer": "Read-only resolution report; unresolved data was not guessed or fetched.",
    }


def write_result(result: Mapping[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


# Short integration aliases; both remain read-only.
resolve = resolve_catalog
resolve_components = resolve_catalog


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve catalog intent against a lock file without network guesses.")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = resolve_catalog(args.catalog, args.lock, repository_root=args.root)
        if args.output:
            write_result(result, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["summary"]["release_eligible"] else 1
    except (ResolverError, OSError, ValueError) as exc:
        print(f"resolver failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
