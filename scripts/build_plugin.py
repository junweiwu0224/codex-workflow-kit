#!/usr/bin/env python3
"""Build a Codex plugin staging directory from a workflow-kit profile.

The repository remains the source of truth for Skills.  This command copies a
selected, locked profile into a clean staging directory and writes a validated
`.codex-plugin/plugin.json`; it never creates a second in-repo Skill tree.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

try:
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def plugin_version(version: str) -> str:
    """Map the toolkit's date-style version to valid plugin semver."""
    if SEMVER.match(version):
        return version
    parts = version.split(".")
    if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
        major, minor, patch = (str(int(part)) for part in parts[:3])
        suffix = ".".join(parts[3:])
        return f"{major}.{minor}.{patch}" + (f"+workflow.{int(suffix)}" if suffix.isdigit() else "+workflow.build")
    return "0.1.0+workflow.build"


def plugin_manifest(name: str, version: str, profile: str) -> dict:
    """Return the canonical manifest for a generated profile plugin."""
    return {
        "name": name,
        "version": plugin_version(version),
        "description": "Junwei Codex workflow profile with explicit governance and verification boundaries.",
        "author": {"name": "Junwei Wu", "url": "https://github.com/junweiwu0224"},
        "repository": "https://github.com/junweiwu0224/codex-workflow-kit",
        "license": "LicenseRef-Proprietary",
        "keywords": ["codex", "workflow", "governance", profile],
        "skills": "./skills/",
        "interface": {
            "displayName": f"Junwei {profile.title()}",
            "shortDescription": "Governed Codex workflow skills.",
            "longDescription": "A profile-built Codex plugin generated from locked repository Skills.",
            "developerName": "Junwei Wu",
            "category": "Productivity",
            "capabilities": ["Interactive", "Write"],
            "defaultPrompt": ["Use the governed Junwei workflow for this task."],
        },
    }


def profile_names(root: Path, profile: str) -> list[str]:
    profiles = {"stable": [root / "catalog/profiles/stable.txt"], "pilot": [root / "catalog/profiles/pilot.txt"], "all": [root / "catalog/profiles/stable.txt", root / "catalog/profiles/pilot.txt"]}
    paths = profiles.get(profile)
    if paths is None:
        raise ValueError(f"unknown profile: {profile}")
    names: list[str] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        names.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))
    return sorted(set(names))


def verify_profile_lock(root: Path, names: list[str]) -> None:
    lock = json.loads((root / "catalog/upstreams.lock.json").read_text(encoding="utf-8"))
    entries = {entry.get("name"): entry for entry in lock.get("entries", []) if isinstance(entry, dict)}
    for name in names:
        entry = entries.get(name)
        if not entry or entry.get("resolution", {}).get("status") != "resolved" or entry.get("content", {}).get("status") != "resolved":
            raise RuntimeError(f"profile skill is not fully locked: {name}")
        if entry.get("source", {}).get("kind") != "repo-local":
            raise RuntimeError(f"profile skill is not repo-local: {name}")
        if entry.get("resolution", {}).get("kind") != "repo-local-content":
            raise RuntimeError(f"profile skill has an invalid resolution kind: {name}")
        if entry.get("content", {}).get("algorithm") != "sha256" or entry.get("content", {}).get("scope") != TREE_HASH_SCOPE:
            raise RuntimeError(f"profile skill has an invalid content hash scope: {name}")
        expected = entry.get("content", {}).get("value")
        try:
            source = skill_tree_directory(root, entry.get("source", {}).get("path"))
            actual = skill_tree_sha256(source)
        except ValueError as exc:
            raise RuntimeError(f"profile skill has an unsafe source tree: {name}: {exc}") from exc
        if source != root / "skills" / name:
            raise RuntimeError(f"profile skill source does not match profile name: {name}")
        if actual != expected:
            raise RuntimeError(f"profile content hash mismatch: {name}")


def validate_plugin(plugin_root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = plugin_root / ".codex-plugin/plugin.json"
    if not manifest_path.is_file():
        return ["missing .codex-plugin/plugin.json"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid plugin manifest: {exc}"]
    for field in ("name", "version", "description", "author", "interface"):
        if not manifest.get(field):
            errors.append(f"missing manifest field: {field}")
    if manifest.get("name") != plugin_root.name:
        errors.append("manifest name must match plugin directory")
    if not SEMVER.match(str(manifest.get("version", ""))):
        errors.append("manifest version must be semver")
    if not isinstance(manifest.get("author"), dict) or not manifest.get("author", {}).get("name"):
        errors.append("author.name is required")
    interface = manifest.get("interface") if isinstance(manifest.get("interface"), dict) else {}
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        if not interface.get(field):
            errors.append(f"missing interface field: {field}")
    skills_path = manifest.get("skills")
    if skills_path != "./skills/":
        errors.append("skills must be ./skills/")
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir() or not any(skills_root.iterdir()):
        errors.append("plugin must contain at least one skill")
    for path in plugin_root.rglob("*"):
        if path.is_file() and "[TODO:" in path.read_text(encoding="utf-8", errors="ignore"):
            errors.append(f"placeholder found: {path.relative_to(plugin_root)}")
    return errors


def build(args: argparse.Namespace) -> Path:
    root = args.root.resolve()
    output = args.output.resolve()
    if output.exists():
        if not args.force:
            raise FileExistsError(f"output exists; use --force: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".codex-plugin").mkdir()
    skills_root = output / "skills"
    names = profile_names(root, args.profile)
    verify_profile_lock(root, names)
    lock = json.loads((root / "catalog/upstreams.lock.json").read_text(encoding="utf-8"))
    entries = {entry.get("name"): entry for entry in lock.get("entries", []) if isinstance(entry, dict)}
    for name in names:
        source = skill_tree_directory(root, entries[name].get("source", {}).get("path"))
        if source != root / "skills" / name:
            raise RuntimeError(f"profile skill source does not match profile name: {name}")
        destination = skills_root / name
        shutil.copytree(source, destination)
        if skill_tree_sha256(destination) != entries[name].get("content", {}).get("value"):
            raise RuntimeError(f"profile content hash mismatch after copy: {name}")

    name = args.name or output.name
    manifest = plugin_manifest(
        name,
        args.version or (root / "VERSION").read_text(encoding="utf-8").strip(),
        args.profile,
    )
    (output / ".codex-plugin/plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = validate_plugin(output)
    if errors:
        raise RuntimeError("plugin validation failed:\n" + "\n".join(errors))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name")
    parser.add_argument("--profile", choices=("stable", "pilot", "all"), default="stable")
    parser.add_argument("--version")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = build(args)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"Plugin staging validated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
