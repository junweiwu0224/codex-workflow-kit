#!/usr/bin/env python3
"""Refresh content-addressed lock entries for repo-local Skill trees.

Repo-local files cannot truthfully lock themselves to the commit that contains
the lock file: changing the embedded commit changes that commit again.  Their
stable identity is therefore the source path plus a deterministic Skill-tree
SHA-256. The release manifest records the clean source commit separately.
External components are not modified by this command and still require exact
upstream commits/digests.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any
from unicodedata import normalize


TREE_HASH_SCOPE = "skill-tree"
TREE_HASH_VERSION = b"codex-workflow-kit-skill-tree-sha256-v1\0"


def _framed_update(digest: Any, tag: bytes, value: bytes) -> None:
    """Add an unambiguous record to a deterministic tree digest."""
    digest.update(tag)
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def skill_tree_directory(root: Path, raw_path: object) -> Path:
    """Resolve a repo-local Skill source to its directory without following links.

    A historical lock may name ``SKILL.md`` while new locks may name the Skill
    directory. Both identify the directory that plugin builders copy. Any
    symbolic link in the source path is rejected before resolution so a lock
    cannot hash content outside the repository.
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("repo-local source path is missing")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("repo-local source path must not be absolute or escape the repository")

    root = root.resolve()
    candidate = root / relative
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("repo-local source path must not contain symlinks")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except FileNotFoundError as exc:
        raise ValueError(f"repo-local source path is missing: {raw_path}") from exc
    except ValueError as exc:
        raise ValueError("repo-local source path escapes repository") from exc

    if candidate.is_file():
        if candidate.name != "SKILL.md":
            raise ValueError("repo-local source file must be named SKILL.md")
        directory = candidate.parent
    elif candidate.is_dir():
        directory = candidate
    else:
        raise ValueError(f"repo-local source must be a Skill directory or SKILL.md: {raw_path}")
    skill_file = directory / "SKILL.md"
    if skill_file.is_symlink() or not skill_file.is_file():
        raise ValueError("repo-local Skill directory must contain a regular SKILL.md")
    return directory


def skill_tree_sha256(directory: Path) -> str:
    """Hash the complete packaged Skill tree, rejecting ambiguous file types."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"Skill tree must be a regular directory: {directory}")
    digest = hashlib.sha256(TREE_HASH_VERSION)
    normalized_paths: set[str] = set()
    entries = sorted(
        directory.rglob("*"),
        key=lambda path: normalize("NFC", path.relative_to(directory).as_posix()).encode("utf-8"),
    )
    for path in entries:
        relative = normalize("NFC", path.relative_to(directory).as_posix())
        if relative in normalized_paths:
            raise ValueError(f"Skill tree contains duplicate normalized path: {relative}")
        normalized_paths.add(relative)
        encoded_path = relative.encode("utf-8")
        if path.is_symlink():
            raise ValueError(f"Skill tree must not contain symlinks: {relative}")
        if path.is_dir():
            _framed_update(digest, b"D", encoded_path)
            continue
        if not path.is_file():
            raise ValueError(f"Skill tree contains unsupported file type: {relative}")
        _framed_update(digest, b"F", encoded_path)
        _framed_update(digest, b"X", b"1" if path.stat().st_mode & 0o111 else b"0")
        content = path.read_bytes()
        _framed_update(digest, b"C", content)
    return digest.hexdigest()


def expected_lock(root: Path, data: dict) -> dict:
    result = copy.deepcopy(data)
    repository = result.setdefault("repository", {})
    repository.pop("commit", None)
    repository["commit_policy"] = "release-manifest"
    for entry in result.get("entries", []):
        if not isinstance(entry, dict) or entry.get("source", {}).get("kind") != "repo-local":
            continue
        raw_path = entry.get("source", {}).get("path")
        if not isinstance(raw_path, str):
            raise ValueError(f"{entry.get('name')}: repo-local source path is missing")
        try:
            directory = skill_tree_directory(root, raw_path)
            value = skill_tree_sha256(directory)
        except ValueError as exc:
            raise ValueError(f"{entry.get('name')}: {exc}") from exc
        entry["resolution"] = {"status": "resolved", "kind": "repo-local-content"}
        entry["content"] = {
            "status": "resolved",
            "algorithm": "sha256",
            "scope": TREE_HASH_SCOPE,
            "value": value,
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--lock", default="catalog/upstreams.lock.json")
    parser.add_argument("--write", action="store_true", help="Atomically update the lock; default is check-only.")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    path = (root / args.lock).resolve()
    try:
        path.relative_to(root)
        current = json.loads(path.read_text(encoding="utf-8"))
        expected = expected_lock(root, current)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if current == expected:
        print(f"Repo-local lock OK: {path}")
        return 0
    if not args.write:
        print(f"Repo-local lock is stale: {path}")
        return 1
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    print(f"Repo-local lock refreshed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
