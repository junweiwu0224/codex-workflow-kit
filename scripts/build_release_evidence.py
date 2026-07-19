#!/usr/bin/env python3
"""Generate and verify deterministic V4.2 release evidence.

The evidence is deliberately emitted outside the source tree by default.  It
references the source commit, content manifest, locked components, Eval
reports, and optional archive/plugin artifacts without embedding timestamps or
machine-specific paths.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import subprocess
import stat
import tempfile
from pathlib import Path

try:
    from scripts.audit_floating_dependencies import _load_yaml_mapping
    from scripts.build_plugin import plugin_manifest, profile_names, validate_plugin, verify_profile_lock
    from scripts.build_release import build_archive, build_manifest as build_content_manifest
    from scripts.build_release import require_clean_worktree, verify_archive
    from scripts.refresh_local_lock import skill_tree_sha256
    from scripts.validate_governance import validate_governance
except ImportError:  # pragma: no cover - direct script execution
    from audit_floating_dependencies import _load_yaml_mapping
    from build_plugin import plugin_manifest, profile_names, validate_plugin, verify_profile_lock
    from build_release import build_archive, build_manifest as build_content_manifest
    from build_release import require_clean_worktree, verify_archive
    from refresh_local_lock import skill_tree_sha256
    from validate_governance import validate_governance


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def manifest_files(root: Path) -> list[dict[str, str]]:
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    rows = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, relative = line.split(maxsplit=1)
        rows.append({"path": relative, "sha256": checksum})
    return rows


def lock_entries(root: Path) -> list[dict]:
    path = root / "catalog/upstreams.lock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("entries", []))


def reverse_lock_entries(root: Path) -> list[dict]:
    """Load the reverse lock through the repository's strict YAML subset parser."""
    path = root / "catalog/reverse-dependencies.lock.yaml"
    if not path.is_file():
        return []
    value = _load_yaml_mapping(path)
    dependencies = value.get("dependencies") if isinstance(value, dict) else None
    if not isinstance(dependencies, list) or any(not isinstance(entry, dict) for entry in dependencies):
        raise ValueError(f"invalid reverse dependency lock: {path}")
    return list(dependencies)


def canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def suite_index(root: Path) -> dict[tuple[str, str], dict[str, object]]:
    result: dict[tuple[str, str], dict[str, object]] = {}
    for kind, directory in (("fixture", root / "eval/fixtures"), ("suite", root / "eval/suites")):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid Eval suite {path}: {exc}") from exc
            if not isinstance(value, dict) or not isinstance(value.get("suite_id"), str):
                raise ValueError(f"invalid Eval suite identity: {path}")
            key = (value["suite_id"], canonical_json_sha256(value))
            if key in result:
                raise ValueError(f"duplicate Eval suite identity: {path}")
            result[key] = {"kind": kind, "value": value, "path": str(path)}
    return result


def profile_content_sha256(root: Path, profile: str) -> str:
    names = profile_entries(root, profile)
    entries = {entry.get("name"): entry for entry in lock_entries(root)}
    bindings = []
    for name in names:
        value = entries.get(name, {}).get("content", {}).get("value")
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"profile contains an unlocked component: {name}")
        bindings.append({"name": name, "content_sha256": value})
    return canonical_json_sha256(bindings)


def validate_eval_subject(root: Path, subject: object) -> dict[str, str]:
    if not isinstance(subject, dict):
        raise ValueError("Eval report subject must be an object")
    kind = subject.get("kind")
    subject_id = subject.get("id")
    content_sha256 = subject.get("content_sha256")
    if kind not in {"component", "profile"} or not isinstance(subject_id, str):
        raise ValueError("non-fixture Eval subject must identify a component or profile")
    if not isinstance(content_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", content_sha256) is None:
        raise ValueError("Eval subject content hash is invalid")
    if kind == "component":
        entries = {entry.get("name"): entry for entry in lock_entries(root)}
        expected = entries.get(subject_id, {}).get("content", {}).get("value")
    else:
        if subject_id not in {"stable", "pilot"}:
            raise ValueError(f"unknown Eval profile subject: {subject_id}")
        expected = profile_content_sha256(root, subject_id)
    if content_sha256 != expected:
        raise ValueError(f"Eval subject does not match current locked content: {subject_id}")
    return {"kind": str(kind), "id": subject_id, "content_sha256": content_sha256}


def attestation_signature(entry: dict, key: bytes) -> str:
    payload = {field: value for field, value in entry.items() if field not in {"signature", "_authenticated"}}
    return hmac.new(key, json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()


def eval_trust_keys(root: Path) -> dict[str, dict]:
    path = root / "catalog/eval-trust-policy.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Eval trust policy {path}: {exc}") from exc
    entries = value.get("keys") if isinstance(value, dict) and value.get("schema_version") == "4.2" else None
    if not isinstance(entries, list):
        raise ValueError(f"invalid Eval trust policy: {path}")
    result: dict[str, dict] = {}
    fingerprints: set[str] = set()
    for index, entry in enumerate(entries):
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("key_id"), str)
            or not entry["key_id"]
            or entry.get("algorithm") != "hmac-sha256"
            or not isinstance(entry.get("key_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", entry["key_sha256"]) is None
            or entry.get("status") not in {"active", "revoked"}
        ):
            raise ValueError(f"invalid Eval trust policy key {index}")
        if entry["key_id"] in result or entry["key_sha256"] in fingerprints:
            raise ValueError("Eval trust policy key IDs and fingerprints must be unique")
        result[entry["key_id"]] = dict(entry)
        fingerprints.add(entry["key_sha256"])
    return result


def load_eval_attestations(
    root: Path,
    key: bytes | None = None,
    registry_path: Path | None = None,
) -> list[dict]:
    path = (registry_path or (root / "eval/attestations.json")).resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Eval attestation registry {path}: {exc}") from exc
    entries = value.get("attestations") if isinstance(value, dict) and value.get("schema_version") == "4.2" else None
    if not isinstance(entries, list):
        raise ValueError(f"invalid Eval attestation registry: {path}")
    seen: set[str] = set()
    now = dt.datetime.now(dt.timezone.utc)
    trusted = eval_trust_keys(root)
    key_fingerprint = hashlib.sha256(key).hexdigest() if key is not None else None
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"invalid Eval attestation {index}")
        required = {
            "report_sha256", "run_id", "suite_id", "suite_sha256", "subject",
            "source_commit", "decision", "reviewed_by", "reviewed_at", "isolation_verifier",
            "key_id", "signature",
        }
        if required - set(entry):
            raise ValueError(f"Eval attestation {index} is incomplete")
        report_sha = entry.get("report_sha256")
        if not isinstance(report_sha, str) or re.fullmatch(r"[0-9a-f]{64}", report_sha) is None or report_sha in seen:
            raise ValueError(f"Eval attestation {index} has an invalid or duplicate report hash")
        seen.add(report_sha)
        if entry.get("decision") not in {"qualified", "rejected"}:
            raise ValueError(f"Eval attestation {index} has an invalid decision")
        if not all(isinstance(entry.get(field), str) and entry[field] for field in (
            "run_id", "suite_id", "suite_sha256", "source_commit", "reviewed_by", "reviewed_at",
            "isolation_verifier", "key_id", "signature"
        )):
            raise ValueError(f"Eval attestation {index} has invalid identity fields")
        if re.fullmatch(r"[0-9a-f]{64}", entry["suite_sha256"]) is None or re.fullmatch(r"[0-9a-f]{40}", entry["source_commit"]) is None:
            raise ValueError(f"Eval attestation {index} has invalid digests")
        validate_eval_subject(root, entry.get("subject"))
        try:
            reviewed_at = dt.datetime.fromisoformat(entry["reviewed_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Eval attestation {index} has invalid reviewed_at") from exc
        if reviewed_at.tzinfo is None or reviewed_at > now + dt.timedelta(minutes=5):
            raise ValueError(f"Eval attestation {index} has invalid reviewed_at")
        if re.fullmatch(r"[0-9a-f]{64}", entry["signature"]) is None:
            raise ValueError(f"Eval attestation {index} has an invalid signature shape")
        trusted_key = trusted.get(entry["key_id"])
        authenticated = bool(
            key is not None
            and trusted_key is not None
            and trusted_key.get("status") == "active"
            and trusted_key.get("key_sha256") == key_fingerprint
            and hmac.compare_digest(entry["signature"], attestation_signature(entry, key))
        )
        if key is not None and trusted_key is not None and trusted_key.get("key_sha256") == key_fingerprint and not authenticated:
            raise ValueError(f"Eval attestation {index} signature verification failed")
        entry["_authenticated"] = authenticated
    return entries


def read_attestation_key(path: Path | None) -> bytes | None:
    if path is None:
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Eval attestation key must be a regular file: {path}")
    key = path.read_bytes().strip()
    if len(key) < 32:
        raise ValueError("Eval attestation key must contain at least 32 bytes")
    return key


def eval_report_record(
    path: Path,
    root: Path,
    *,
    attestations: list[dict] | None = None,
    suites: dict[tuple[str, str], dict[str, object]] | None = None,
    source_commit: str | None = None,
) -> dict[str, object]:
    record = artifact_record(path, root)
    if record is None or record.get("kind") != "file":
        raise ValueError(f"Eval report must be a file: {path}")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Eval report {path}: {exc}") from exc
    required = {
        "schema_version",
        "report_type",
        "run_id",
        "suite_id",
        "suite_sha256",
        "subject",
        "source_commit",
        "metrics",
        "verdict",
        "fixture_only",
        "mode",
        "promotion_decision",
        "evidence",
        "assertion_failures",
        "safety_findings",
        "blind_review",
    }
    if (
        not isinstance(report, dict)
        or report.get("schema_version") != "4.2"
        or report.get("report_type") != "eval"
        or required - set(report)
        or not isinstance(report.get("run_id"), str)
        or not report.get("run_id")
        or not isinstance(report.get("metrics"), dict)
        or not report.get("metrics")
        or not isinstance(report.get("evidence"), dict)
    ):
        raise ValueError(f"invalid V4.2 Eval report: {path}")
    if report.get("mode") not in {"paired", "shadow"} or report.get("verdict") not in {"pass", "fail", "needs_human_review"}:
        raise ValueError(f"invalid V4.2 Eval report decision fields: {path}")
    if report.get("promotion_decision") not in {"promote", "hold", "tighten", "rollback", "retire"}:
        raise ValueError(f"invalid V4.2 Eval promotion decision: {path}")
    suite_sha = report.get("suite_sha256")
    if not isinstance(suite_sha, str) or re.fullmatch(r"[0-9a-f]{64}", suite_sha) is None:
        raise ValueError(f"invalid Eval suite hash: {path}")
    suites = suites if suites is not None else suite_index(root)
    suite_record = suites.get((str(report.get("suite_id")), suite_sha))
    if suite_record is None:
        raise ValueError(f"Eval report does not match a frozen repository suite: {path}")
    suite_kind = suite_record["kind"]
    suite_value = suite_record["value"]
    evidence = report.get("evidence") if isinstance(report.get("evidence"), dict) else {}
    attestation_key_id: str | None = None
    if report.get("fixture_only") and report.get("promotion_decision") != "hold":
        raise ValueError(f"fixture Eval report must remain hold: {path}")
    if report.get("fixture_only"):
        subject = report.get("subject")
        if (
            not isinstance(subject, dict)
            or subject.get("kind") != "fixture"
            or suite_kind != "fixture"
            or report.get("source_commit") is not None
        ):
            raise ValueError(f"fixture Eval report has an invalid subject or suite: {path}")
        qualification = "fixture-only"
    else:
        if evidence.get("isolation_enforcement") != "trusted-adapter-verified" or suite_kind != "suite":
            raise ValueError(f"non-fixture Eval report lacks trusted isolation or formal suite evidence: {path}")
        subject = validate_eval_subject(root, report.get("subject"))
        qualification = "unattested"
        current_commit = source_commit or git(root, "rev-parse", "HEAD")
        if report.get("source_commit") != current_commit:
            raise ValueError(f"non-fixture Eval report does not bind the current source commit: {path}")
        attestations = attestations if attestations is not None else load_eval_attestations(root)
        for attestation in attestations:
            if (
                attestation.get("decision") == "qualified"
                and attestation.get("_authenticated") is True
                and attestation.get("report_sha256") == record.get("sha256")
                and attestation.get("run_id") == report.get("run_id")
                and attestation.get("suite_id") == report.get("suite_id")
                and attestation.get("suite_sha256") == suite_sha
                and attestation.get("subject") == subject
                and attestation.get("source_commit") == current_commit
            ):
                qualification = "hmac-attested"
                attestation_key_id = str(attestation.get("key_id"))
                break
    safety = report.get("metrics", {}).get("safety")
    if (
        not isinstance(safety, dict)
        or not isinstance(safety.get("violations"), int)
        or isinstance(safety.get("violations"), bool)
        or safety.get("violations", -1) < 0
        or not isinstance(safety.get("passed"), bool)
        or not isinstance(report.get("assertion_failures"), int)
        or isinstance(report.get("assertion_failures"), bool)
        or report.get("assertion_failures", -1) < 0
        or not isinstance(report.get("safety_findings"), list)
        or not isinstance(report.get("blind_review"), dict)
    ):
        raise ValueError(f"invalid Eval safety or review evidence: {path}")
    blind = report["blind_review"]
    suite_cases = suite_value.get("cases", []) if isinstance(suite_value, dict) else []
    subjective_required = any(isinstance(case, dict) and case.get("subjective") is True for case in suite_cases)
    if not report.get("fixture_only"):
        trigger = report.get("metrics", {}).get("trigger")
        behavior = report.get("metrics", {}).get("behavior")
        held_out = trigger.get("held_out") if isinstance(trigger, dict) else None
        if (
            not isinstance(trigger, dict)
            or not isinstance(behavior, dict)
            or not isinstance(held_out, dict)
            or not all(isinstance(held_out.get(field), (int, float)) for field in ("precision", "recall", "false_positive_rate"))
            or not isinstance(behavior.get("passed"), bool)
        ):
            raise ValueError(f"non-fixture Eval report lacks trigger or behavior metrics: {path}")
        if blind.get("required") is not subjective_required:
            raise ValueError(f"Eval blind-review requirement does not match its frozen suite: {path}")
    if report.get("promotion_decision") == "promote" and (
        report.get("fixture_only")
        or report.get("mode") != "paired"
        or report.get("verdict") != "pass"
        or safety.get("violations") != 0
        or safety.get("passed") is not True
        or report.get("assertion_failures") != 0
        or bool(report.get("safety_findings"))
        or report.get("metrics", {}).get("trigger", {}).get("held_out", {}).get("precision", 0) < 0.90
        or report.get("metrics", {}).get("trigger", {}).get("held_out", {}).get("recall", 0) < 0.85
        or report.get("metrics", {}).get("trigger", {}).get("held_out", {}).get("false_positive_rate", 1) > 0.05
        or report.get("metrics", {}).get("behavior", {}).get("passed") is not True
        or (blind.get("required") is True and (blind.get("complete") is not True or blind.get("passed") is not True))
    ):
        raise ValueError(f"Eval promote decision is not supported by passing paired evidence: {path}")
    record.update(
        {
            "suite_id": report.get("suite_id"),
            "mode": report.get("mode"),
            "fixture_only": bool(report.get("fixture_only")),
            "promotion_decision": report.get("promotion_decision"),
            "verdict": report.get("verdict"),
            "isolation_enforcement": evidence.get("isolation_enforcement"),
            "suite_sha256": suite_sha,
            "subject": report.get("subject"),
            "qualification": qualification,
            "attestation_key_id": attestation_key_id if not report.get("fixture_only") else None,
        }
    )
    return record


def report_files(
    root: Path,
    explicit: list[Path] | None = None,
    *,
    attestation_key: bytes | None = None,
    attestation_registry: Path | None = None,
) -> list[dict[str, object]]:
    paths = list(explicit or [])
    unique: dict[str, Path] = {str(path.resolve()): path.resolve() for path in paths}
    attestations = load_eval_attestations(root, attestation_key, attestation_registry)
    suites = suite_index(root)
    source_commit = git(root, "rev-parse", "HEAD")
    records = [
        eval_report_record(
            unique[key], root, attestations=attestations, suites=suites, source_commit=source_commit
        )
        for key in sorted(unique)
    ]
    displays = [str(record.get("path")) for record in records]
    if len(displays) != len(set(displays)):
        raise ValueError("Eval report filenames must be unique across external evidence inputs")
    return records


def directory_digest(path: Path) -> tuple[str, int]:
    """Hash a directory from relative paths and file contents, independent of mtimes."""
    h = hashlib.sha256()
    entries = sorted(path.rglob("*"))
    symlinks = [item for item in entries if item.is_symlink()]
    if symlinks:
        raise ValueError(f"artifact directories must not contain symlinks: {symlinks[0]}")
    files = [item for item in entries if item.is_file()]
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        h.update(len(relative).to_bytes(8, "big"))
        h.update(relative)
        h.update(b"\x01" if item.stat().st_mode & stat.S_IXUSR else b"\x00")
        h.update(bytes.fromhex(digest(item)))
    return h.hexdigest(), len(files)


def artifact_record(path: Path | None, root: Path) -> dict[str, object] | None:
    if path is None:
        return None
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        display = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        display = f"external/{path.name}"
    if path.is_file():
        return {"path": display, "kind": "file", "sha256": digest(path)}
    if path.is_dir():
        tree_sha256, file_count = directory_digest(path)
        return {
            "path": display,
            "kind": "directory",
            "sha256": tree_sha256,
            "file_count": file_count,
        }
    raise ValueError(f"unsupported release artifact type: {path}")


def source_file_record(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"release input must be a regular file: {relative}")
    return {"path": relative, "sha256": digest(path)}


def archive_record(path: Path | None, root: Path) -> dict[str, object] | None:
    if path is None:
        return None
    path = path.resolve()
    verify_archive(path, expected_manifest=(root / "MANIFEST.sha256").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="codex-release-rebuild-") as temporary:
        expected_archive = build_archive(root, Path(temporary))
        if digest(path) != digest(expected_archive) or path.read_bytes() != expected_archive.read_bytes():
            raise ValueError("archive is not the reproducible byte-for-byte build of the current source")
    record = artifact_record(path, root)
    if record is None:
        return None
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    checksum = artifact_record(checksum_path, root)
    if checksum is None:
        raise ValueError(f"archive checksum is missing: {checksum_path}")
    record.update({"checksum_file": checksum, "validation": "archive-manifest-and-checksum-verified"})
    return record


def plugin_record(path: Path | None, root: Path, profile: str) -> dict[str, object] | None:
    if path is None:
        return None
    path = path.resolve()
    errors = validate_plugin(path)
    if errors:
        raise ValueError("plugin validation failed: " + "; ".join(errors))
    names = profile_names(root, profile)
    verify_profile_lock(root, names)
    top_level = sorted(item.name for item in path.iterdir())
    if top_level != [".codex-plugin", "skills"]:
        raise ValueError("plugin staging contains unexpected top-level content")
    manifest_entries = sorted(item.name for item in (path / ".codex-plugin").iterdir())
    if manifest_entries != ["plugin.json"]:
        raise ValueError("plugin staging contains unexpected manifest content")
    manifest_path = path / ".codex-plugin/plugin.json"
    actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = plugin_manifest(
        path.name,
        (root / "VERSION").read_text(encoding="utf-8").strip(),
        profile,
    )
    if actual_manifest != expected_manifest:
        raise ValueError("plugin manifest does not match the canonical profile build")
    actual_names = sorted(item.name for item in (path / "skills").iterdir() if item.is_dir())
    if actual_names != names or any(not item.is_dir() for item in (path / "skills").iterdir()):
        raise ValueError(f"plugin Skills do not match the {profile} profile")
    lock = json.loads((root / "catalog/upstreams.lock.json").read_text(encoding="utf-8"))
    entries = {entry.get("name"): entry for entry in lock.get("entries", []) if isinstance(entry, dict)}
    for name in names:
        expected = entries.get(name, {}).get("content", {}).get("value")
        if skill_tree_sha256(path / "skills" / name) != expected:
            raise ValueError(f"plugin Skill tree does not match locked content: {name}")
    record = artifact_record(path, root)
    if record is not None:
        record.update(
            {
                "profile": profile,
                "skills": names,
                "manifest_sha256": digest(manifest_path),
                "validation": "plugin-profile-and-locked-content-verified",
            }
        )
    return record


def profile_entries(root: Path, profile: str) -> list[str]:
    path = root / f"catalog/profiles/{profile}.txt"
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def entry_is_resolved(entry: dict) -> bool:
    source = entry.get("source", {})
    resolution = entry.get("resolution", {})
    content = entry.get("content", {})
    compatibility = entry.get("compatibility", {})
    license_data = entry.get("license", {})
    if resolution.get("status") != "resolved":
        return False
    if source.get("kind") == "repo-local":
        if resolution.get("kind") != "repo-local-content":
            return False
        if (
            content.get("status") != "resolved"
            or content.get("algorithm") != "sha256"
            or content.get("scope") != "skill-tree"
        ):
            return False
        if re.fullmatch(r"[0-9a-f]{64}", str(content.get("value", ""))) is None:
            return False
    elif not resolution.get("commit") and not resolution.get("digest"):
        return False
    return (
        compatibility.get("status") in {"resolved", "not-applicable"}
        and license_data.get("status") in {"resolved", "not-applicable"}
    )


def component_version(entry: dict) -> str:
    resolution = entry.get("resolution", {})
    content = entry.get("content", {})
    if resolution.get("kind") == "repo-local-content" and content.get("value"):
        return f"sha256:{content['value']}"
    return str(resolution.get("commit") or resolution.get("digest") or "unresolved")


def distribution_policy(root: Path) -> dict:
    policy_path = root / "catalog/license-policy.yaml"
    license_path = root / "LICENSE"
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else ""
    license_text = license_path.read_text(encoding="utf-8") if license_path.is_file() else ""
    policy_match = re.search(r"^\s*public_release:\s*([^#\n]+)", policy_text, re.MULTILINE)
    declared_public_release = policy_match.group(1).strip().strip("'\"") if policy_match else "unspecified"
    spdx_match = re.search(r"^SPDX-License-Identifier:\s*([^\s]+)\s*$", license_text, re.MULTILINE)
    spdx = spdx_match.group(1) if spdx_match else "NOASSERTION"
    public_eligible = declared_public_release == "allowed" and spdx not in {
        "NOASSERTION",
        "LicenseRef-Proprietary",
    }
    if public_eligible:
        reason = f"License policy explicitly allows public release under {spdx}."
    elif declared_public_release != "allowed":
        reason = f"License policy declares public_release={declared_public_release}; explicit approval is required."
    else:
        reason = "Public release is fail-closed because the root LICENSE has no public SPDX grant."
    return {
        "mode": "public" if public_eligible else "internal-only",
        "public_release_eligible": public_eligible,
        "reason": reason,
        "policy": {
            "path": "catalog/license-policy.yaml",
            "sha256": digest(policy_path) if policy_path.is_file() else None,
            "declared_public_release": declared_public_release,
        },
        "root_license": {
            "path": "LICENSE",
            "sha256": digest(license_path) if license_path.is_file() else None,
            "spdx": spdx,
        },
    }


def build_manifest(
    root: Path,
    archive: Path | None = None,
    plugin: Path | None = None,
    eval_reports: list[Path] | None = None,
    plugin_profile: str = "stable",
    eval_attestation_key: bytes | None = None,
    eval_attestation_registry: Path | None = None,
) -> dict:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    entries = lock_entries(root)
    reverse_entries = reverse_lock_entries(root)
    unresolved = [entry["name"] for entry in entries if not entry_is_resolved(entry)]
    blocked_reverse = [entry.get("id") for entry in reverse_entries if entry.get("status") == "blocked"]
    enforcement_counts = {state: 0 for state in ("enforced", "verified", "metadata-only", "blocked")}
    for entry in reverse_entries:
        enforcement = entry.get("enforcement")
        if not isinstance(enforcement, dict):
            raise ValueError(f"reverse dependency lacks field enforcement: {entry.get('id')}")
        for state in enforcement.values():
            if state not in enforcement_counts:
                raise ValueError(f"reverse dependency has invalid enforcement state: {entry.get('id')}")
            enforcement_counts[str(state)] += 1
    status_output = git(root, "status", "--porcelain", "--untracked-files=all")
    stable_profile = source_file_record(root, "catalog/profiles/stable.txt")
    stable_profile["components"] = profile_entries(root, "stable")
    pilot_profile = source_file_record(root, "catalog/profiles/pilot.txt")
    pilot_profile["components"] = profile_entries(root, "pilot")
    result = {
        "schema_version": "4.2",
        "package": "codex-workflow-kit",
        "version": version,
        "source": {
            "commit": git(root, "rev-parse", "HEAD"),
            "dirty": None if status_output == "unknown" else bool(status_output),
        },
        "manifest": {
            "path": "MANIFEST.sha256",
            "sha256": digest(root / "MANIFEST.sha256"),
            "file_count": len(manifest_files(root)),
        },
        "governance_inputs": {
            "catalog": source_file_record(root, "catalog/components.yaml"),
            "component_lock": source_file_record(root, "catalog/upstreams.lock.json"),
            "reverse_lock": source_file_record(root, "catalog/reverse-dependencies.lock.yaml"),
            "license_policy": source_file_record(root, "catalog/license-policy.yaml"),
            "eval_attestation_template": source_file_record(root, "eval/attestations.json"),
            "eval_trust_policy": source_file_record(root, "catalog/eval-trust-policy.json"),
            "profiles": {"stable": stable_profile, "pilot": pilot_profile},
        },
        "profiles": {
            "stable": stable_profile["components"],
            "pilot": pilot_profile["components"],
        },
        "locked_components": len(entries),
        "unresolved_components": unresolved,
        "repo_local_content_components": sum(
            entry.get("resolution", {}).get("kind") == "repo-local-content" for entry in entries
        ),
        "reverse_dependencies": {
            "path": "catalog/reverse-dependencies.lock.yaml",
            "sha256": digest(root / "catalog/reverse-dependencies.lock.yaml") if (root / "catalog/reverse-dependencies.lock.yaml").is_file() else None,
            "count": len(reverse_entries),
            "blocked_optional": blocked_reverse,
            "field_enforcement_counts": enforcement_counts,
        },
        "distribution": distribution_policy(root),
        "eval_attestations": (
            artifact_record(eval_attestation_registry, root)
            if eval_attestation_registry is not None
            else source_file_record(root, "eval/attestations.json")
        ),
        "eval_reports": report_files(
            root,
            eval_reports,
            attestation_key=eval_attestation_key,
            attestation_registry=eval_attestation_registry,
        ),
        "archive": archive_record(archive, root),
        "plugin": plugin_record(plugin, root, plugin_profile),
        "sbom": "sbom.cdx.json",
        "third_party_notices": "THIRD-PARTY-NOTICES.txt",
        "release_process": {
            "target": "portable-source-archive",
            "reproduce": [
                "python3 scripts/refresh_local_lock.py",
                "python3 scripts/build_plugin.py --root . --output <plugin-dir> --profile stable",
                "python3 scripts/build_release.py --require-clean --output-dir <archive-dir>",
                "python3 scripts/build_release_evidence.py write --root . --output <evidence-dir> --archive <archive> --plugin <plugin-dir> --eval-report <report> --require-clean-source",
                "python3 scripts/build_release_evidence.py verify --root . --output <evidence-dir> --archive <archive> --plugin <plugin-dir> --eval-report <report> --require-resolved --require-clean-source --require-eval",
                "python3 scripts/build_release_evidence.py attest-eval --root . --eval-report <real-report> --eval-attestation-key <external-key> --key-id <trusted-key-id> --reviewed-by <reviewer> --isolation-verifier <broker-id> --output <external-registry>",
            ],
            "rollback": {
                "mechanism": "scripts/manage_install.py rollback",
                "last_known_good": "the exact ownership/profile state and file preimages from the most recent committed install transaction",
            },
            "platform_evidence": {
                "posix": "repository tests and clean-checkout drill required",
                "windows": "PowerShell execution drill required before a Windows support claim",
            },
        },
    }
    return result


def build_sbom(root: Path) -> dict:
    entries = lock_entries(root)
    stable = set(profile_entries(root, "stable"))
    components = []
    for entry in entries:
        source = entry.get("source", {})
        resolution = entry.get("resolution", {})
        content = entry.get("content", {})
        license_data = entry.get("license", {})
        license_name = str(license_data.get("spdx") or "NOASSERTION")
        components.append(
            {
                "type": "library",
                "bom-ref": entry.get("name"),
                "name": entry.get("name"),
                "version": component_version(entry),
                "scope": "required" if entry.get("catalog_ref") in stable else "optional",
                "licenses": [{"license": {"name": license_name}}],
                "properties": [
                    {"name": "source.kind", "value": str(source.get("kind", "unknown"))},
                    {"name": "source.path", "value": str(source.get("path", ""))},
                    {"name": "resolution.kind", "value": str(resolution.get("kind", "unknown"))},
                    {"name": "resolution.status", "value": str(resolution.get("status", "unresolved"))},
                    {"name": "content.sha256", "value": str(content.get("value", ""))},
                    {"name": "license.status", "value": str(license_data.get("status", "unresolved"))},
                ],
            }
        )
    for entry in reverse_lock_entries(root):
        integrity = entry.get("integrity") or entry.get("sha256") or entry.get("commit") or ""
        enforcement = entry.get("enforcement") if isinstance(entry.get("enforcement"), dict) else {}
        components.append(
            {
                "type": "library" if entry.get("kind") != "container" else "container",
                "bom-ref": entry.get("id"),
                "name": entry.get("package") or entry.get("module") or entry.get("repository") or entry.get("image") or entry.get("id"),
                "version": entry.get("version") or entry.get("tag") or entry.get("commit") or "blocked",
                "scope": "optional",
                "licenses": [{"license": {"name": "NOASSERTION"}}],
                "properties": [
                    {"name": "source.kind", "value": str(entry.get("kind", "unknown"))},
                    {"name": "lock.status", "value": str(entry.get("status", "unknown"))},
                    {"name": "integrity", "value": str(integrity)},
                    {"name": "license.status", "value": "NOASSERTION"},
                    *[
                        {"name": f"enforcement.{field}", "value": str(state)}
                        for field, state in sorted(enforcement.items())
                    ],
                ],
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": "codex-workflow-kit",
                "name": "codex-workflow-kit",
                "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
            }
        },
        "components": components,
    }


def build_notices(root: Path) -> str:
    entries = lock_entries(root)
    lines = [
        "Codex Workflow Kit third-party and licensing notice",
        "====================================================",
        "",
        "The repository grants no open-source license. Distribution rights are not granted by this notice.",
        "Repo-local and external components remain subject to their recorded licenses and original authors' rights.",
        "",
        "Locked workflow components:",
    ]
    for entry in entries:
        license_data = entry.get("license", {})
        source = entry.get("source", {})
        content = entry.get("content", {})
        lines.append(
            f"- {entry.get('name')}: {license_data.get('spdx', 'NOASSERTION')} "
            f"({license_data.get('status', 'unresolved')}); {source.get('kind', 'unknown')} "
            f"{source.get('path', '')}; sha256={content.get('value', 'unresolved')}"
        )
    lines.append("")
    lines.append("Reverse optional dependencies (locked identity; per-field enforcement is explicit):")
    for entry in reverse_lock_entries(root):
        dependency = entry.get("package") or entry.get("module") or entry.get("repository") or entry.get("image") or entry.get("id")
        reference = entry.get("version") or entry.get("tag") or entry.get("commit") or entry.get("image") or ""
        integrity = entry.get("integrity") or entry.get("sha256") or entry.get("commit") or "unresolved"
        enforcement = entry.get("enforcement") if isinstance(entry.get("enforcement"), dict) else {}
        enforcement_text = ",".join(f"{field}:{state}" for field, state in sorted(enforcement.items()))
        lines.append(
            f"- {entry.get('id')} ({dependency}): {entry.get('status', 'unknown')} "
            f"{reference}; integrity={integrity}; enforcement={enforcement_text}; license=NOASSERTION"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    output = args.output.resolve()
    validate_governance(root)
    if args.require_clean_source:
        require_clean_worktree(root, "release evidence write")
    output.mkdir(parents=True, exist_ok=True)
    eval_reports = [path.resolve() for path in args.eval_report]
    attestation_key = read_attestation_key(args.eval_attestation_key)
    attestation_registry = args.eval_attestations.resolve() if args.eval_attestations else None
    manifest = build_manifest(
        root,
        args.archive,
        args.plugin,
        eval_reports,
        args.plugin_profile,
        attestation_key,
        attestation_registry,
    )
    if args.require_clean_source and manifest.get("source", {}).get("dirty") is not False:
        raise RuntimeError("release evidence requires a clean, verifiable Git source")
    (output / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "sbom.cdx.json").write_text(json.dumps(build_sbom(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "THIRD-PARTY-NOTICES.txt").write_text(build_notices(root), encoding="utf-8")
    print(f"Release evidence written: {output}")
    return 0


def attest_eval(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    output = args.output.resolve()
    if output == root or output.is_relative_to(root):
        raise RuntimeError("real Eval attestation registry must remain outside the source repository")
    require_clean_worktree(root, "Eval attestation")
    key = read_attestation_key(args.eval_attestation_key)
    if key is None:
        raise RuntimeError("Eval attestation requires an external key")
    trusted = eval_trust_keys(root).get(args.key_id)
    fingerprint = hashlib.sha256(key).hexdigest()
    if (
        trusted is None
        or trusted.get("status") != "active"
        or trusted.get("key_sha256") != fingerprint
    ):
        raise RuntimeError("Eval attestation key is not active in catalog/eval-trust-policy.json")

    report_path = args.eval_report.resolve()
    commit = git(root, "rev-parse", "HEAD")
    record = eval_report_record(report_path, root, attestations=[], source_commit=commit)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if record.get("fixture_only"):
        raise RuntimeError("fixture Eval reports cannot be signed as real evidence")
    if args.decision == "qualified" and not (
        record.get("mode") == "paired"
        and record.get("verdict") == "pass"
        and record.get("promotion_decision") == "promote"
    ):
        raise RuntimeError("qualified attestation requires paired/pass/promote evidence")
    entry = {
        "report_sha256": digest(report_path),
        "run_id": report["run_id"],
        "suite_id": report["suite_id"],
        "suite_sha256": report["suite_sha256"],
        "subject": report["subject"],
        "source_commit": commit,
        "decision": args.decision,
        "reviewed_by": args.reviewed_by,
        "reviewed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "isolation_verifier": args.isolation_verifier,
        "key_id": args.key_id,
    }
    entry["signature"] = attestation_signature(entry, key)

    if output.exists():
        if not args.append or output.is_symlink() or not output.is_file():
            raise RuntimeError("attestation output exists; use --append with a regular external registry")
        registry = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(registry, dict) or registry.get("schema_version") != "4.2" or not isinstance(registry.get("attestations"), list):
            raise RuntimeError("existing attestation registry is invalid")
        # Refuse to append behind malformed, stale-subject, or invalidly signed
        # entries. Existing records may use another trusted key, which permits
        # deliberate key rotation without weakening registry validation.
        load_eval_attestations(root, key, output)
    else:
        registry = {
            "schema_version": "4.2",
            "description": "Externally retained, owner-signed Eval attestations for one clean source commit.",
            "attestations": [],
        }
    if any(item.get("report_sha256") == entry["report_sha256"] for item in registry["attestations"] if isinstance(item, dict)):
        raise RuntimeError("attestation registry already contains this Eval report")
    registry["attestations"].append(entry)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Eval attestation written: {output}")
    return 0


def verify(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    output = args.output.resolve()
    validate_governance(root)
    if args.require_clean_source or args.public:
        require_clean_worktree(root, "release evidence verify")
    manifest_path = output / "release-manifest.json"
    sbom_path = output / "sbom.cdx.json"
    notices_path = output / "THIRD-PARTY-NOTICES.txt"
    if not all(path.is_file() for path in (manifest_path, sbom_path, notices_path)):
        raise RuntimeError("release evidence requires release-manifest.json, sbom.cdx.json and THIRD-PARTY-NOTICES.txt")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "4.2" or sbom.get("bomFormat") != "CycloneDX":
        raise RuntimeError("invalid release evidence schema")

    content_manifest_path = root / "MANIFEST.sha256"
    if content_manifest_path.read_text(encoding="utf-8") != build_content_manifest(root):
        raise RuntimeError("source MANIFEST.sha256 is stale")

    archive = args.archive.resolve() if args.archive else None
    plugin = args.plugin.resolve() if args.plugin else None
    eval_reports = [path.resolve() for path in args.eval_report]
    attestation_key = read_attestation_key(args.eval_attestation_key)
    attestation_registry = args.eval_attestations.resolve() if args.eval_attestations else None
    if args.require_real_eval or args.public:
        if attestation_key is None:
            raise RuntimeError("real Eval qualification requires an external attestation key")
        if attestation_registry is None:
            raise RuntimeError("real Eval qualification requires an explicit external attestation registry")
        if attestation_registry == root or attestation_registry.is_relative_to(root):
            raise RuntimeError("real Eval attestation registry must remain outside the source repository")
    if archive is not None:
        verify_archive(archive)
    if plugin is not None:
        plugin_errors = validate_plugin(plugin)
        if plugin_errors:
            raise RuntimeError("plugin validation failed: " + "; ".join(plugin_errors))

    expected_manifest = build_manifest(
        root,
        archive,
        plugin,
        eval_reports,
        args.plugin_profile,
        attestation_key,
        attestation_registry,
    )
    expected_sbom = build_sbom(root)
    expected_notices = build_notices(root)
    if manifest != expected_manifest:
        raise RuntimeError("release-manifest.json does not match current source and explicit artifacts")
    if sbom != expected_sbom:
        raise RuntimeError("sbom.cdx.json does not match current locks")
    if notices_path.read_text(encoding="utf-8") != expected_notices:
        raise RuntimeError("THIRD-PARTY-NOTICES.txt does not match current locks")

    qualifying_real = [
        record
        for record in expected_manifest.get("eval_reports", [])
        if (
            not record.get("fixture_only")
            and record.get("qualification") == "hmac-attested"
            and record.get("mode") == "paired"
            and record.get("verdict") == "pass"
            and record.get("promotion_decision") == "promote"
        )
    ]
    stable_subject = {
        "kind": "profile",
        "id": "stable",
        "content_sha256": profile_content_sha256(root, "stable"),
    }
    qualifying_stable = [record for record in qualifying_real if record.get("subject") == stable_subject]
    if (args.require_clean_source or args.public) and expected_manifest.get("source", {}).get("dirty") is not False:
        raise RuntimeError("release evidence records a dirty or unverifiable source")
    if expected_manifest.get("unresolved_components") and (args.require_resolved or args.public):
        raise RuntimeError("unresolved components: " + ", ".join(expected_manifest["unresolved_components"]))
    if args.require_eval and not expected_manifest.get("eval_reports"):
        raise RuntimeError("at least one explicit Eval report is required")
    if args.require_real_eval and not qualifying_real:
        raise RuntimeError("at least one HMAC-attested paired/pass/promote non-fixture Eval report is required")
    if args.public:
        if expected_manifest.get("archive") is None or expected_manifest.get("plugin") is None:
            raise RuntimeError("public release requires an explicitly bound archive and plugin")
        if expected_manifest.get("plugin", {}).get("profile") != "stable":
            raise RuntimeError("public release requires the stable plugin profile")
        if not expected_manifest.get("eval_reports") or not qualifying_stable:
            raise RuntimeError("public release requires HMAC-attested paired/pass/promote evidence for the locked stable profile")
        if not expected_manifest.get("distribution", {}).get("public_release_eligible", False):
            raise RuntimeError("public release is blocked by the repository license policy")
    print(f"Release evidence OK: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--root", type=Path, default=Path.cwd())
    write.add_argument("--output", type=Path, required=True)
    write.add_argument("--archive", type=Path)
    write.add_argument("--plugin", type=Path)
    write.add_argument("--plugin-profile", choices=("stable", "pilot", "all"), default="stable")
    write.add_argument("--eval-report", type=Path, action="append", default=[])
    write.add_argument("--eval-attestations", type=Path)
    write.add_argument("--eval-attestation-key", type=Path)
    write.add_argument("--require-clean-source", action="store_true")
    check = sub.add_parser("verify")
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--archive", type=Path)
    check.add_argument("--plugin", type=Path)
    check.add_argument("--plugin-profile", choices=("stable", "pilot", "all"), default="stable")
    check.add_argument("--eval-report", type=Path, action="append", default=[])
    check.add_argument("--eval-attestations", type=Path)
    check.add_argument("--eval-attestation-key", type=Path)
    check.add_argument("--require-resolved", action="store_true")
    check.add_argument("--require-clean-source", action="store_true")
    check.add_argument("--require-eval", action="store_true")
    check.add_argument("--require-real-eval", action="store_true")
    check.add_argument("--public", action="store_true", help="Require an explicitly public-compatible license policy.")
    attest = sub.add_parser("attest-eval")
    attest.add_argument("--root", type=Path, default=Path.cwd())
    attest.add_argument("--eval-report", type=Path, required=True)
    attest.add_argument("--eval-attestation-key", type=Path, required=True)
    attest.add_argument("--key-id", required=True)
    attest.add_argument("--reviewed-by", required=True)
    attest.add_argument("--isolation-verifier", required=True)
    attest.add_argument("--decision", choices=("qualified", "rejected"), default="qualified")
    attest.add_argument("--output", type=Path, required=True)
    attest.add_argument("--append", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "write":
            return write_outputs(args)
        if args.command == "attest-eval":
            return attest_eval(args)
        return verify(args)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
