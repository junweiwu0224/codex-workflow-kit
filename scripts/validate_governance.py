#!/usr/bin/env python3
"""Validate the V4.2 governance catalog and resolved upstream lock.

The validator intentionally keeps policy data in YAML and resolution data in
JSON. PyYAML is used when available; a deliberately small fallback parser
supports the mapping/list/scalar subset used by this repository so clean
checkouts can still run the gate. Skill frontmatter policy remains owned by
``audit_skill_contracts.py``.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.refresh_local_lock import TREE_HASH_SCOPE, skill_tree_directory, skill_tree_sha256


class GovernanceValidationError(ValueError):
    """Raised when governance data cannot be loaded or violates its schema."""

    def __init__(self, issues: str | list[str]):
        if isinstance(issues, str):
            issues = [issues]
        self.issues = tuple(issues)
        super().__init__("; ".join(self.issues))


REQUIRED_CATALOG_FIELDS = {
    "schema_version",
    "repository",
    "skills",
    "license_policy",
}
REQUIRED_SKILL_FIELDS = {
    "name",
    "owner",
    "role",
    "stage",
    "status",
    "implicit",
    "network",
    "write_scope",
    "license",
    "eval_suite",
    "metadata",
}
REQUIRED_SKILL_METADATA_FIELDS = {
    "risk",
    "source_repo",
    "source_type",
    "date_added",
    "setup",
    "write_surface",
    "auth",
    "network_policy",
}
REQUIRED_LOCK_FIELDS = {"schema_version", "repository", "license_policy", "entries"}
REQUIRED_LOCK_ENTRY_FIELDS = {
    "name",
    "catalog_ref",
    "source",
    "resolution",
    "content",
    "compatibility",
    "license",
}
ALLOWED_ROLES = {"driver", "overlay", "guardrail", "verifier", "governance"}
ALLOWED_STAGES = {
    "onboarding",
    "research",
    "specification",
    "implementation",
    "verification",
    "release",
    "cross-cutting",
}
ALLOWED_STATUSES = {"stable", "pilot", "lab", "deprecated", "retired"}
ALLOWED_NETWORK = {"none", "local", "conditional", "external"}
ALLOWED_WRITE_SCOPES = {"none", "docs", "workspace", "project-artifacts", "artifacts", "conditional"}
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_LICENSE_DECLARATIONS = {"resolved", "policy", "unresolved"}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_IMPLICIT_SKILLS = 8
PROFILE_STATUS = {"stable": "stable", "pilot": "pilot"}


def _require_mapping(value: Any, label: str, issues: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issues.append(f"{label} must be a mapping")
        return None
    return value


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _simple_yaml_load(text: str) -> dict[str, Any]:
    """Parse the narrow YAML subset used by catalog/components.yaml."""
    logical: list[tuple[int, str, int]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise GovernanceValidationError(f"invalid YAML at line {line_number}: tabs are not allowed")
        logical.append((len(raw) - len(raw.lstrip(" ")), raw.strip(), line_number))

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for position, (indent, content, line_number) in enumerate(logical):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise GovernanceValidationError(f"invalid YAML indentation at line {line_number}")
        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise GovernanceValidationError(f"invalid YAML list item at line {line_number}")
            item_text = content[2:].strip()
            if ":" not in item_text:
                parent.append(_parse_scalar(item_text))
                continue
            key, raw_value = item_text.split(":", 1)
            item: dict[str, Any] = {}
            parent.append(item)
            value = _parse_scalar(raw_value)
            item[key.strip()] = value
            stack.append((indent, item))
            continue

        if ":" not in content or not isinstance(parent, dict):
            raise GovernanceValidationError(f"invalid YAML mapping at line {line_number}")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise GovernanceValidationError(f"invalid empty YAML key at line {line_number}")
        if raw_value.strip():
            parent[key] = _parse_scalar(raw_value)
            continue

        next_content = logical[position + 1][1] if position + 1 < len(logical) else ""
        container: Any = [] if next_content.startswith("- ") else {}
        parent[key] = container
        stack.append((indent, container))
    return root


def _yaml_safe_load(text: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except (ModuleNotFoundError, ImportError):
        return _simple_yaml_load(text)
    safe_load = getattr(yaml, "safe_load", None)
    if not callable(safe_load):
        return _simple_yaml_load(text)
    try:
        return safe_load(text)
    except Exception as exc:  # PyYAML exposes YAMLError; keep this import optional.
        raise GovernanceValidationError(f"invalid YAML: {exc}") from exc


def load_catalog(path: str | Path) -> dict[str, Any]:
    """Load the YAML catalog with PyYAML or the repository subset parser."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GovernanceValidationError(f"cannot read catalog {path}: {exc}") from exc
    try:
        value = _yaml_safe_load(text)
    except GovernanceValidationError as exc:
        raise GovernanceValidationError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GovernanceValidationError(f"catalog {path} must contain a mapping at the document root")
    return value


def load_lock(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except OSError as exc:
        raise GovernanceValidationError(f"cannot read lock {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GovernanceValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GovernanceValidationError(f"lock {path} must contain a mapping at the document root")
    return value


def _skill_names(root: Path) -> set[str]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return set()
    return {path.parent.name for path in skills_root.glob("*/SKILL.md")}


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the deliberately small standard Skill frontmatter surface."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip("\"'")
    return result


def validate_skill_frontmatter(root: Path) -> list[str]:
    """Ensure packaged Skills keep only the portable Agent Skills fields."""
    issues: list[str] = []
    allowed = {"name", "description"}
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        metadata = _frontmatter(path.read_text(encoding="utf-8"))
        name = path.parent.name
        if set(metadata) - allowed:
            issues.append(
                f"{name}: frontmatter contains non-standard fields: "
                + ", ".join(sorted(set(metadata) - allowed))
            )
        if metadata.get("name") != name:
            issues.append(f"{name}: frontmatter name must match skill directory")
        if not metadata.get("description", "").strip():
            issues.append(f"{name}: frontmatter description must be non-empty")
    return issues


def _missing(required: set[str], value: dict[str, Any]) -> list[str]:
    return sorted(required - set(value))


def _load_profile(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise GovernanceValidationError(f"cannot read install profile {path}: {exc}") from exc
    names = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if len(names) != len(set(names)):
        raise GovernanceValidationError(f"install profile contains duplicate skills: {path}")
    return names


def validate_profiles(root: Path, catalog: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    issues: list[str] = []
    rows = [item for item in catalog.get("skills", []) if isinstance(item, dict)]
    status_by_name = {
        item.get("name"): item.get("status")
        for item in rows
        if isinstance(item.get("name"), str)
    }
    profiles: dict[str, list[str]] = {}
    for profile, status in PROFILE_STATUS.items():
        try:
            names = _load_profile(root / "catalog" / "profiles" / f"{profile}.txt")
        except GovernanceValidationError as exc:
            issues.extend(exc.issues)
            names = []
        profiles[profile] = names
        expected = {name for name, current_status in status_by_name.items() if current_status == status}
        actual = set(names)
        for name in sorted(expected - actual):
            issues.append(f"{profile} profile is missing {status} skill: {name}")
        for name in sorted(actual - expected):
            issues.append(
                f"{profile} profile contains {name}, but catalog status is {status_by_name.get(name)!r}"
            )
    overlap = set(profiles.get("stable", [])) & set(profiles.get("pilot", []))
    if overlap:
        issues.append("stable and pilot profiles overlap: " + ", ".join(sorted(overlap)))
    explicit_only = {
        item.get("name")
        for item in rows
        if isinstance(item.get("name"), str) and item.get("implicit") is False
    }
    for name in sorted(explicit_only):
        policy_path = root / "skills" / name / "agents" / "openai.yaml"
        try:
            policy_text = policy_path.read_text(encoding="utf-8")
        except OSError:
            issues.append(f"implicit:false skill must define agents/openai.yaml policy: {name}")
            continue
        if not re.search(r"(?m)^\s*allow_implicit_invocation:\s*false\s*$", policy_text):
            issues.append(f"implicit:false skill must disable implicit invocation: {name}")
    return issues, profiles


def validate_catalog_data(root: str | Path, catalog: dict[str, Any]) -> list[str]:
    """Return schema and filesystem issues for an already-loaded catalog."""
    root = Path(root).resolve()
    issues: list[str] = []
    missing = _missing(REQUIRED_CATALOG_FIELDS, catalog)
    if missing:
        issues.append(f"catalog missing required fields: {', '.join(missing)}")
    if catalog.get("schema_version") != "4.2":
        issues.append("catalog schema_version must be '4.2'")
    policy_path = _safe_repo_path(root, catalog.get("license_policy"), "catalog.license_policy", issues)
    if policy_path is not None:
        policy_text = policy_path.read_text(encoding="utf-8")
        if "fail_closed: true" not in policy_text:
            issues.append("catalog.license_policy must declare fail_closed: true")
        policy = _yaml_safe_load(policy_text)
        default_license = policy.get("default", {}) if isinstance(policy, dict) else {}
        if not isinstance(default_license, dict):
            issues.append("catalog.license_policy default must be a mapping")
        else:
            if default_license.get("status") != "resolved":
                issues.append("catalog.license_policy default.status must be resolved")
            if default_license.get("spdx") != "LicenseRef-Proprietary":
                issues.append("catalog.license_policy default.spdx must be LicenseRef-Proprietary")
            if default_license.get("distribution") != "internal-only":
                issues.append("catalog.license_policy default.distribution must be internal-only")
    root_license = root / "LICENSE"
    if not root_license.is_file():
        issues.append("root LICENSE is required for resolved repo-local licensing")
    else:
        license_text = root_license.read_text(encoding="utf-8")
        for term in ("No open-source license", "All rights are reserved"):
            if term not in license_text:
                issues.append(f"root LICENSE must include conservative declaration: {term}")
    repository = _require_mapping(catalog.get("repository"), "catalog.repository", issues)
    if repository is not None:
        if not isinstance(repository.get("name"), str) or not repository["name"].strip():
            issues.append("catalog.repository.name must be a non-empty string")
        if repository.get("commit_policy") != "release-manifest":
            issues.append("catalog.repository.commit_policy must be release-manifest")
        if "commit" in repository:
            issues.append("catalog.repository must not embed a self-referential commit")

    rows = catalog.get("skills")
    if not isinstance(rows, list):
        issues.append("catalog.skills must be a list")
        rows = []
    names: list[str] = []
    for index, row in enumerate(rows):
        item = _require_mapping(row, f"catalog.skills[{index}]", issues)
        if item is None:
            continue
        missing = _missing(REQUIRED_SKILL_FIELDS, item)
        if missing:
            issues.append(f"catalog.skills[{index}] missing required fields: {', '.join(missing)}")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"catalog.skills[{index}].name must be a non-empty string")
            continue
        names.append(name)
        if item.get("owner") != "junweiwu0224":
            issues.append(f"{name}: owner must be junweiwu0224")
        if len(name) > 64 or not SKILL_NAME_RE.fullmatch(name):
            issues.append(f"{name}: name must be lowercase kebab-case and at most 64 characters")
        if item.get("role") not in ALLOWED_ROLES:
            issues.append(f"{name}: invalid role {item.get('role')!r}")
        if item.get("stage") not in ALLOWED_STAGES:
            issues.append(f"{name}: invalid stage {item.get('stage')!r}")
        if item.get("status") not in ALLOWED_STATUSES:
            issues.append(f"{name}: invalid status {item.get('status')!r}")
        if not isinstance(item.get("implicit"), bool):
            issues.append(f"{name}: implicit must be boolean")
        elif item.get("implicit") and item.get("status") in {"pilot", "lab"}:
            issues.append(f"{name}: pilot/lab skills cannot be implicit")
        if item.get("network") not in ALLOWED_NETWORK:
            issues.append(f"{name}: invalid network {item.get('network')!r}")
        if item.get("write_scope") not in ALLOWED_WRITE_SCOPES:
            issues.append(f"{name}: invalid write_scope {item.get('write_scope')!r}")
        for field in ("license", "eval_suite"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                issues.append(f"{name}: {field} must be a non-empty string")
        if item.get("license") not in ALLOWED_LICENSE_DECLARATIONS:
            issues.append(
                f"{name}: license must be one of {sorted(ALLOWED_LICENSE_DECLARATIONS)}"
            )
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            issues.append(f"{name}: metadata must be a mapping")
        else:
            missing_metadata = sorted(REQUIRED_SKILL_METADATA_FIELDS - set(metadata))
            if missing_metadata:
                issues.append(
                    f"{name}: metadata missing required fields: {', '.join(missing_metadata)}"
                )
            if metadata.get("risk") not in ALLOWED_RISKS:
                issues.append(f"{name}: metadata.risk must be one of {sorted(ALLOWED_RISKS)}")
            for field in REQUIRED_SKILL_METADATA_FIELDS - {"risk"}:
                value = metadata.get(field)
                if not isinstance(value, str) or not value.strip():
                    issues.append(f"{name}: metadata.{field} must be a non-empty string")
    if len(names) != len(set(names)):
        issues.append("catalog.skills contains duplicate names")
    actual = _skill_names(root)
    declared = set(names)
    for name in sorted(actual - declared):
        issues.append(f"skill directory is missing from catalog: {name}")
    for name in sorted(declared - actual):
        issues.append(f"catalog entry has no skills/{name}/SKILL.md")
    if not actual:
        issues.append("skills directory contains no */SKILL.md files")
    issues.extend(validate_skill_frontmatter(root))
    implicit_count = sum(1 for row in rows if isinstance(row, dict) and row.get("implicit") is True)
    if implicit_count > MAX_IMPLICIT_SKILLS:
        issues.append(
            f"catalog enables {implicit_count} implicit skills; maximum is {MAX_IMPLICIT_SKILLS}"
        )
    return issues


def _safe_repo_path(root: Path, raw: Any, label: str, issues: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        issues.append(f"{label} must be a non-empty relative path")
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        issues.append(f"{label} must not be absolute or escape the repository")
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        issues.append(f"{label} escapes the repository")
        return None
    if not resolved.is_file():
        issues.append(f"{label} does not exist: {raw}")
        return None
    return resolved


def _safe_repo_skill_directory(root: Path, raw: Any, label: str, issues: list[str]) -> Path | None:
    try:
        return skill_tree_directory(root, raw)
    except ValueError as exc:
        issues.append(f"{label}: {exc}")
        return None


def _validate_resolved_skill_tree_hash(path: Path, expected: Any, label: str, issues: list[str]) -> None:
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        issues.append(f"{label} must be a 64-character lowercase SHA-256 value")
        return
    try:
        actual = skill_tree_sha256(path)
    except ValueError as exc:
        issues.append(f"{label} cannot hash Skill tree: {exc}")
        return
    if actual != expected:
        issues.append(f"{label} does not match {path.as_posix()}")


def validate_lock_data(root: str | Path, lock: dict[str, Any], catalog_names: set[str]) -> list[str]:
    """Return schema, reference, and content-integrity issues for a lock."""
    root = Path(root).resolve()
    issues: list[str] = []
    missing = _missing(REQUIRED_LOCK_FIELDS, lock)
    if missing:
        issues.append(f"lock missing required fields: {', '.join(missing)}")
    if lock.get("schema_version") != "4.2":
        issues.append("lock schema_version must be '4.2'")
    lock_policy = _safe_repo_path(root, lock.get("license_policy"), "lock.license_policy", issues)
    if lock_policy is None or lock.get("license_policy") != "catalog/license-policy.yaml":
        issues.append("lock.license_policy must reference catalog/license-policy.yaml")
    repository = _require_mapping(lock.get("repository"), "lock.repository", issues)
    if repository is not None:
        if not isinstance(repository.get("name"), str) or not repository["name"].strip():
            issues.append("lock.repository.name must be a non-empty string")
        if repository.get("commit_policy") != "release-manifest":
            issues.append("lock.repository.commit_policy must be release-manifest")
        if "commit" in repository:
            issues.append("lock.repository must not embed a self-referential commit")

    entries = lock.get("entries")
    if not isinstance(entries, list):
        issues.append("lock.entries must be a list")
        entries = []
    names: list[str] = []
    for index, raw_entry in enumerate(entries):
        entry = _require_mapping(raw_entry, f"lock.entries[{index}]", issues)
        if entry is None:
            continue
        missing = _missing(REQUIRED_LOCK_ENTRY_FIELDS, entry)
        if missing:
            issues.append(f"lock.entries[{index}] missing required fields: {', '.join(missing)}")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"lock.entries[{index}].name must be a non-empty string")
            continue
        names.append(name)
        if entry.get("catalog_ref") != name:
            issues.append(f"{name}: catalog_ref must equal name")
        source = _require_mapping(entry.get("source"), f"{name}.source", issues)
        resolution = _require_mapping(entry.get("resolution"), f"{name}.resolution", issues)
        content = _require_mapping(entry.get("content"), f"{name}.content", issues)
        compatibility = _require_mapping(entry.get("compatibility"), f"{name}.compatibility", issues)
        license_data = _require_mapping(entry.get("license"), f"{name}.license", issues)
        source_path: Path | None = None
        source_kind: str | None = None
        if source is not None:
            source_kind = source.get("kind")
            if not isinstance(source_kind, str) or not source_kind.strip():
                issues.append(f"{name}: source.kind must be a non-empty string")
            if not isinstance(source.get("repository"), str) or not source["repository"].strip():
                issues.append(f"{name}: source.repository must be a non-empty string")
            if source_kind == "repo-local":
                source_path = _safe_repo_skill_directory(root, source.get("path"), f"{name}.source.path", issues)
                expected_directory = Path("skills") / name
                allowed_paths = {expected_directory.as_posix(), (expected_directory / "SKILL.md").as_posix()}
                if source.get("path") not in allowed_paths:
                    issues.append(
                        f"{name}: source.path must be {expected_directory.as_posix()} or "
                        f"{(expected_directory / 'SKILL.md').as_posix()}"
                    )
        if resolution is not None:
            if resolution.get("status") == "resolved":
                resolution_kind = resolution.get("kind")
                if source_kind == "repo-local":
                    if resolution_kind != "repo-local-content":
                        issues.append(
                            f"{name}: resolved repo-local entries must use resolution.kind repo-local-content"
                        )
                    if "commit" in resolution or "digest" in resolution:
                        issues.append(f"{name}: repo-local resolution identity must come from content SHA-256")
                elif resolution_kind in {"commit", "git-commit"}:
                    commit = resolution.get("commit")
                    if not isinstance(commit, str) or not SHA1_RE.fullmatch(commit):
                        issues.append(f"{name}: external commit must be a full 40-character lowercase SHA")
                elif resolution_kind in {"digest", "container-digest"}:
                    digest = resolution.get("digest")
                    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
                        issues.append(f"{name}: external digest must be an immutable sha256 digest")
                else:
                    issues.append(f"{name}: resolved external entries must use an immutable commit or digest")
            elif resolution.get("status") == "unresolved":
                if resolution.get("kind") != "unresolved":
                    issues.append(f"{name}: unresolved entries must use resolution.kind unresolved")
            else:
                issues.append(f"{name}: resolution.status must be resolved or unresolved")
        if content is not None:
            content_status = content.get("status")
            if content_status == "resolved":
                if content.get("algorithm") != "sha256":
                    issues.append(f"{name}: resolved content.algorithm must be sha256")
                if source_path is not None:
                    if content.get("scope") != TREE_HASH_SCOPE:
                        issues.append(f"{name}: resolved repo-local content.scope must be {TREE_HASH_SCOPE}")
                    _validate_resolved_skill_tree_hash(source_path, content.get("value"), f"{name}.content.value", issues)
                elif not isinstance(content.get("value"), str) or not SHA256_RE.fullmatch(content["value"]):
                    issues.append(f"{name}.content.value must be a 64-character lowercase SHA-256 value")
            elif content_status == "unresolved":
                if content.get("algorithm") not in (None, ""):
                    issues.append(f"{name}: unresolved content must not claim an algorithm")
            else:
                issues.append(f"{name}: content.status must be resolved or unresolved")
        if compatibility is not None:
            compatibility_status = compatibility.get("status")
            if compatibility_status not in {"resolved", "unresolved"}:
                issues.append(f"{name}: compatibility.status must be resolved or unresolved")
            if compatibility_status == "resolved":
                if compatibility.get("codex") != "agentskills-standard-v1":
                    issues.append(f"{name}: resolved compatibility must identify agentskills-standard-v1")
                if compatibility.get("evidence") != "scripts/validate_governance.py":
                    issues.append(f"{name}: resolved compatibility must cite local validator evidence")
        if license_data is not None:
            license_status = license_data.get("status")
            if license_status not in {"resolved", "unresolved", "policy"}:
                issues.append(f"{name}: license.status must be resolved, policy, or unresolved")
            if license_status == "policy":
                if license_data.get("spdx") != "NOASSERTION":
                    issues.append(f"{name}: policy license must use SPDX NOASSERTION")
                if license_data.get("policy_ref") != "catalog/license-policy.yaml":
                    issues.append(f"{name}: policy license must reference catalog/license-policy.yaml")
                if not isinstance(license_data.get("reason"), str) or not license_data["reason"].strip():
                    issues.append(f"{name}: policy license must include a non-empty reason")
            if license_status == "resolved":
                if source_kind == "repo-local":
                    if license_data.get("spdx") != "LicenseRef-Proprietary":
                        issues.append(f"{name}: resolved repo-local license must use LicenseRef-Proprietary")
                    if license_data.get("policy_ref") != "catalog/license-policy.yaml":
                        issues.append(f"{name}: resolved repo-local license must reference catalog/license-policy.yaml")
                elif not isinstance(license_data.get("spdx"), str) or not license_data["spdx"].strip():
                    issues.append(f"{name}: resolved external license must include an SPDX expression")
    if len(names) != len(set(names)):
        issues.append("lock.entries contains duplicate names")
    locked = set(names)
    for name in sorted(catalog_names - locked):
        issues.append(f"catalog skill is missing from lock: {name}")
    for name in sorted(locked - catalog_names):
        issues.append(f"lock entry is missing from catalog: {name}")
    return issues


def validate_eval_trust_policy(root: Path) -> list[str]:
    issues: list[str] = []
    try:
        policy = load_lock(root / "catalog/eval-trust-policy.json")
    except GovernanceValidationError as exc:
        return list(exc.issues)
    if policy.get("schema_version") != "4.2":
        issues.append("eval trust policy schema_version must be 4.2")
    if not isinstance(policy.get("policy_id"), str) or not policy.get("policy_id", "").strip():
        issues.append("eval trust policy policy_id must be non-empty")
    keys = policy.get("keys")
    if not isinstance(keys, list):
        return issues + ["eval trust policy keys must be a list"]
    key_ids: set[str] = set()
    fingerprints: set[str] = set()
    for index, entry in enumerate(keys):
        if not isinstance(entry, dict):
            issues.append(f"eval trust policy key {index} must be an object")
            continue
        key_id = entry.get("key_id")
        fingerprint = entry.get("key_sha256")
        if not isinstance(key_id, str) or not key_id.strip():
            issues.append(f"eval trust policy key {index} has an invalid key_id")
        elif key_id in key_ids:
            issues.append(f"eval trust policy contains duplicate key_id: {key_id}")
        else:
            key_ids.add(key_id)
        if entry.get("algorithm") != "hmac-sha256":
            issues.append(f"eval trust policy key {index} must use hmac-sha256")
        if not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint):
            issues.append(f"eval trust policy key {index} has an invalid key_sha256")
        elif fingerprint in fingerprints:
            issues.append(f"eval trust policy contains duplicate key fingerprint: {fingerprint}")
        else:
            fingerprints.add(fingerprint)
        if entry.get("status") not in {"active", "revoked"}:
            issues.append(f"eval trust policy key {index} status must be active or revoked")
    return issues


def validate_governance(root: str | Path = ".") -> dict[str, Any]:
    root = Path(root).resolve()
    catalog = load_catalog(root / "catalog/components.yaml")
    lock = load_lock(root / "catalog/upstreams.lock.json")
    issues = validate_catalog_data(root, catalog)
    profile_issues, profiles = validate_profiles(root, catalog)
    issues.extend(profile_issues)
    names = {
        item.get("name")
        for item in catalog.get("skills", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    issues.extend(validate_lock_data(root, lock, names))
    issues.extend(validate_eval_trust_policy(root))
    if issues:
        raise GovernanceValidationError(issues)
    return {
        "ok": True,
        "root": str(root),
        "skills": len(names),
        "implicit": sum(
            1
            for item in catalog.get("skills", [])
            if isinstance(item, dict) and item.get("implicit") is True
        ),
        "profiles": {name: len(skills) for name, skills in profiles.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate V4.2 governance catalog and lock.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable result.")
    args = parser.parse_args(argv)
    try:
        result = validate_governance(args.root)
    except GovernanceValidationError as exc:
        if args.json:
            print(json.dumps({"ok": False, "issues": list(exc.issues)}, indent=2, sort_keys=True))
        else:
            print("Governance validation failed")
            for issue in exc.issues:
                print(f"- {issue}")
        return 1
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Governance validation OK: {result['skills']} skills, {result['implicit']} implicit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
