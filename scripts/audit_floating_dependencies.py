#!/usr/bin/env python3
"""Reject floating dependency references in installer entry points.

The baseline is retained as a change detector, while
``catalog/reverse-dependencies.lock.yaml`` is the authoritative exact pin
inventory. A clean report has zero floating findings; blocked entries in the
lock are explicit manual-review gates, never implicit latest installs.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TARGET_FILES = (
    "reverse-skill/skills/scripts/bootstrap-reverse.sh",
    "reverse-skill/kali/scripts/bootstrap-reverse.sh",
    "reverse-skill/kali/scripts/quick-setup.sh",
    "install.sh",
    "install.ps1",
)
DEFAULT_BASELINE = "catalog/floating-dependencies-baseline.json"
DEFAULT_REVERSE_LOCK = "catalog/reverse-dependencies.lock.yaml"
BASELINE_SCHEMA_VERSION = 1
ENFORCEMENT_STATES = {"enforced", "verified", "metadata-only", "blocked"}
LOCK_FIELDS_BY_KIND = {
    "npm": ("package", "version", "integrity"),
    "pypi": ("package", "version", "sha256"),
    "git": ("repository", "commit"),
    "go": ("module", "repository", "version", "commit"),
    "github-release": ("repository", "tag", "asset", "url", "sha256", "commit"),
    "container": ("image",),
}

GO_LATEST_RE = re.compile(r"\bgo\s+install\s+[^\s\"']+@latest\b", re.IGNORECASE)
AT_LATEST_RE = re.compile(r"@latest\b", re.IGNORECASE)
CONTAINER_LATEST_RE = re.compile(r":latest\b", re.IGNORECASE)
RELEASE_LATEST_RE = re.compile(r"\breleases/latest\b", re.IGNORECASE)
GIT_PLUS_RE = re.compile(r"\bgit\+https?://[^\s\"']+", re.IGNORECASE)
GIT_CLONE_RE = re.compile(r"\bgit\s+clone\b", re.IGNORECASE)
NPM_INSTALL_RE = re.compile(r"\bnpm\s+(?:install|i)\b", re.IGNORECASE)
NPX_RE = re.compile(r"\bnpx\b", re.IGNORECASE)
PIPX_RE = re.compile(r"\bpipx\s+(?:install|upgrade|run)\b", re.IGNORECASE)
PIP_INSTALL_RE = re.compile(
    r"""
    (?:^|(?:&&|\|\||;)\s*)\s*
    (?:if\s+|then\s+)?(?:sudo\s+)?
    (?:
        pip(?:3(?:\.\d+)?)?
        |
        (?:"[^"]*python(?:3(?:\.\d+)?)?"|'[^']*python(?:3(?:\.\d+)?)?'|[^\s;&|]*python(?:3(?:\.\d+)?)?)
        \s+-m\s+pip
    )
    \s+install\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

PIP_OPTIONS_WITH_VALUES = {
    "--abi",
    "--cache-dir",
    "--config-settings",
    "--constraint",
    "--extra-index-url",
    "--find-links",
    "--implementation",
    "--index-url",
    "--platform",
    "--prefix",
    "--proxy",
    "--python-version",
    "--root",
    "--src",
    "--target",
    "--timeout",
    "--trusted-host",
    "-c",
    "-f",
    "-t",
}


@dataclass(frozen=True)
class FloatingReference:
    path: str
    line: int
    kind: str
    reference: str
    signature: str

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (self.path, self.kind, self.signature, self.reference)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _signature(line: str, reference: str, start: int | None = None, end: int | None = None) -> str:
    if start is not None and end is not None:
        return _normalize_space(f"{line[:start]}<floating-ref>{line[end:]}")
    return _normalize_space(line.replace(reference, "<floating-ref>", 1))


def _finding(
    path: str,
    line_number: int,
    line: str,
    kind: str,
    reference: str,
    start: int | None = None,
    end: int | None = None,
) -> FloatingReference:
    raw_reference = reference
    reference = raw_reference.strip().strip(";,)")
    return FloatingReference(
        path=path,
        line=line_number,
        kind=kind,
        reference=reference,
        signature=_signature(line, raw_reference, start, end),
    )


def _shell_tokens(fragment: str) -> list[str]:
    try:
        return shlex.split(fragment, comments=False, posix=True)
    except ValueError:
        return re.findall(r"[^\s]+", fragment)


def _clean_token(token: str) -> str:
    return token.strip().strip("\"'[]{}(),;")


def _has_explicit_npm_version(spec: str) -> bool:
    spec = _clean_token(spec)
    if not spec or spec.startswith((".", "/", "file:", "workspace:")):
        return True
    if spec.startswith("git+"):
        return "@" in spec.removeprefix("git+")
    if "#" in spec:
        return True
    if spec.startswith("@"):
        return "@" in spec[1:]
    return "@" in spec


def _first_package_token(tokens: Iterable[str]) -> str | None:
    skip_next = False
    for raw_token in tokens:
        token = _clean_token(raw_token)
        if not token:
            continue
        if skip_next:
            skip_next = False
            continue
        if token in {"-p", "--package", "--cache", "--prefix", "--registry"}:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        if token in {"||", "&&", "|", "then", "fi", "true", "false"}:
            break
        if token == "\\" or re.match(r"^\d*(?:>>?|<<?)", token):
            continue
        return token
    return None


def _pip_package_tokens(tokens: Iterable[str]) -> list[str]:
    """Return literal pip requirement specs, ignoring option values.

    Shell variables are intentionally left to their call sites. This permits a
    helper such as the Kali bootstrap's ``install_pip_package`` to receive a
    lock-derived exact spec without treating the helper body as an unpinned
    literal install.
    """
    packages: list[str] = []
    skip_next = False
    for raw_token in tokens:
        token = _clean_token(raw_token)
        if not token:
            continue
        if skip_next:
            skip_next = False
            continue
        if token in {"||", "&&", "|", "then", "fi", "true", "false"}:
            break
        if token == "\\" or re.match(r"^\d*(?:>>?|<<?)", token):
            continue
        if token in PIP_OPTIONS_WITH_VALUES:
            skip_next = True
            continue
        if any(token.startswith(f"{option}=") for option in PIP_OPTIONS_WITH_VALUES if option.startswith("--")):
            continue
        if token.startswith("-"):
            continue
        if token.startswith(("$", "${")):
            continue
        packages.append(token)
    return packages


def _has_explicit_pip_identity(spec: str) -> bool:
    spec = _clean_token(spec)
    if not spec:
        return True
    if spec.startswith((".", "/", "file:")):
        return True
    if spec.endswith(".whl"):
        return bool(re.search(r"-[0-9][A-Za-z0-9_.!+-]*-", Path(spec).name))
    if spec.startswith("git+"):
        return bool(re.search(r"@[0-9a-f]{40}(?:$|[#?])", spec, re.IGNORECASE))
    if spec.startswith(("http://", "https://")):
        return bool(re.search(r"[#&]sha256=[0-9a-f]{64}(?:$|&)", spec, re.IGNORECASE))
    exact = re.search(r"(?<![<>!~])={2,3}([^=\s]+)$", spec)
    return bool(exact and "*" not in exact.group(1))


def _scan_pip_commands(path: str, line_number: int, line: str) -> list[FloatingReference]:
    findings: list[FloatingReference] = []
    for match in PIP_INSTALL_RE.finditer(line):
        fragment = line[match.end() :]
        for package in _pip_package_tokens(_shell_tokens(fragment)):
            if _has_explicit_pip_identity(package):
                continue
            package_start = line.find(package, match.end())
            package_end = package_start + len(package) if package_start >= 0 else None
            findings.append(
                _finding(
                    path,
                    line_number,
                    line,
                    "pip-unpinned",
                    package,
                    package_start if package_start >= 0 else None,
                    package_end,
                )
            )
    return findings


def _git_clone_reference(line: str, match: re.Match[str]) -> str | None:
    fragment = line[match.end() :]
    tokens = _shell_tokens(fragment)
    branch: str | None = None
    url: str | None = None
    skip_next = False
    for index, raw_token in enumerate(tokens):
        token = _clean_token(raw_token)
        if not token:
            continue
        if skip_next:
            skip_next = False
            continue
        if token in {"-b", "--branch"}:
            skip_next = True
            try:
                branch = _clean_token(tokens[index + 1])
            except IndexError:
                branch = None
            continue
        if token in {"--depth", "--origin", "--config", "--reference"}:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        if token in {"||", "&&", "|", "then", "fi"}:
            break
        url = token
        break

    if not url:
        return None
    if re.search(r"@[0-9a-f]{7,40}(?:$|[#?])", url, re.IGNORECASE):
        return None
    if branch and re.fullmatch(r"v?\d+(?:\.\d+){1,3}(?:[-+][A-Za-z0-9.-]+)?", branch):
        return None
    return url


def _scan_package_command(
    path: str,
    line_number: int,
    line: str,
    pattern: re.Pattern[str],
    kind: str,
) -> list[FloatingReference]:
    findings: list[FloatingReference] = []
    for match in pattern.finditer(line):
        fragment = line[match.end() :]
        package = _first_package_token(_shell_tokens(fragment))
        if not package:
            continue
        if kind in {"npm-unpinned", "npx-unpinned"} and _has_explicit_npm_version(package):
            continue
        if kind == "pipx-unpinned":
            if "==" in package or (package.startswith("git+") and "@" in package.removeprefix("git+")):
                continue
            if package.startswith((".", "/")):
                continue
        package_start = line.find(package, match.end())
        package_end = package_start + len(package) if package_start >= 0 else None
        findings.append(
            _finding(
                path,
                line_number,
                line,
                kind,
                package,
                package_start if package_start >= 0 else None,
                package_end,
            )
        )
    return findings


def _scan_line(path: str, line_number: int, line: str) -> list[FloatingReference]:
    findings: list[FloatingReference] = []
    covered_latest: list[tuple[int, int]] = []

    for match in GO_LATEST_RE.finditer(line):
        reference = match.group(0)
        findings.append(
            _finding(path, line_number, line, "go-install-latest", reference, match.start(), match.end())
        )
        latest_start = line.lower().find("@latest", match.start(), match.end())
        if latest_start >= 0:
            covered_latest.append((latest_start, latest_start + len("@latest")))

    for match in AT_LATEST_RE.finditer(line):
        if any(start <= match.start() and match.end() <= end for start, end in covered_latest):
            continue
        findings.append(
            _finding(path, line_number, line, "at-latest", match.group(0), match.start(), match.end())
        )

    for match in CONTAINER_LATEST_RE.finditer(line):
        findings.append(
            _finding(path, line_number, line, "container-latest", match.group(0), match.start(), match.end())
        )

    for match in RELEASE_LATEST_RE.finditer(line):
        findings.append(
            _finding(path, line_number, line, "release-latest", match.group(0), match.start(), match.end())
        )

    for match in GIT_PLUS_RE.finditer(line):
        reference = match.group(0).rstrip(";,)")
        if "@" not in reference.removeprefix("git+"):
            findings.append(
                _finding(path, line_number, line, "git-plus-unpinned", reference, match.start(), match.end())
            )

    for match in GIT_CLONE_RE.finditer(line):
        reference = _git_clone_reference(line, match)
        if reference:
            reference_start = line.find(reference, match.end())
            findings.append(
                _finding(
                    path,
                    line_number,
                    line,
                    "git-clone-unpinned",
                    reference,
                    reference_start if reference_start >= 0 else None,
                    reference_start + len(reference) if reference_start >= 0 else None,
                )
            )

    findings.extend(_scan_package_command(path, line_number, line, NPM_INSTALL_RE, "npm-unpinned"))
    findings.extend(_scan_package_command(path, line_number, line, NPX_RE, "npx-unpinned"))
    findings.extend(_scan_package_command(path, line_number, line, PIPX_RE, "pipx-unpinned"))
    findings.extend(_scan_pip_commands(path, line_number, line))

    unique: dict[tuple[str, str, str, str], FloatingReference] = {}
    for finding in findings:
        unique[finding.identity] = finding
    return sorted(unique.values(), key=lambda item: (item.kind, item.reference, item.signature))


def scan_floating_dependencies(root: str | Path = ".") -> list[FloatingReference]:
    root_path = Path(root).resolve()
    findings: list[FloatingReference] = []
    for relative in TARGET_FILES:
        path = root_path / relative
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            findings.extend(_scan_line(relative, line_number, line))
    return sorted(findings, key=lambda item: (item.path, item.line, item.kind, item.reference))


def _aggregate(findings: Iterable[FloatingReference]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for finding in findings:
        entry = grouped.setdefault(
            finding.identity,
            {
                "path": finding.path,
                "kind": finding.kind,
                "reference": finding.reference,
                "signature": finding.signature,
                "count": 0,
                "lines": [],
            },
        )
        entry["count"] += 1
        entry["lines"].append(finding.line)
    return sorted(
        grouped.values(),
        key=lambda entry: (entry["path"], entry["kind"], entry["signature"], entry["reference"]),
    )


def _baseline_payload(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "kind": "zero-floating-reference-baseline",
        "description": (
            "Machine-generated zero-finding baseline. Reverse lock field-consumption states are "
            "reported by catalog/reverse-dependencies.lock.yaml; any new floating reference fails closed."
        ),
        "generator": "scripts/audit_floating_dependencies.py --refresh-baseline",
        "targets": list(TARGET_FILES),
        "findings": findings,
    }


def _entry_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("path", "")),
        str(entry.get("kind", "")),
        str(entry.get("signature", "")),
        str(entry.get("reference", "")),
    )


def _entry_shape(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("path", "")),
        str(entry.get("kind", "")),
        str(entry.get("signature", "")),
    )


def _compare(
    baseline: list[dict[str, Any]], current: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    baseline_map = {_entry_key(entry): entry for entry in baseline}
    current_map = {_entry_key(entry): entry for entry in current}

    changed: list[dict[str, Any]] = []
    remaining_added = set(current_map) - set(baseline_map)
    remaining_removed = set(baseline_map) - set(current_map)

    for key in sorted(set(baseline_map) & set(current_map)):
        old_count = int(baseline_map[key].get("count", 1))
        new_count = int(current_map[key].get("count", 1))
        if old_count != new_count:
            changed.append({"baseline": baseline_map[key], "current": current_map[key], "reason": "count"})

    removed_by_shape: dict[tuple[str, str, str], list[tuple[str, str, str, str]]] = {}
    added_by_shape: dict[tuple[str, str, str], list[tuple[str, str, str, str]]] = {}
    for key in remaining_removed:
        removed_by_shape.setdefault(_entry_shape(baseline_map[key]), []).append(key)
    for key in remaining_added:
        added_by_shape.setdefault(_entry_shape(current_map[key]), []).append(key)

    for shape in sorted(set(removed_by_shape) & set(added_by_shape)):
        old_keys = sorted(removed_by_shape[shape])
        new_keys = sorted(added_by_shape[shape])
        for old_key, new_key in zip(old_keys, new_keys):
            changed.append(
                {"baseline": baseline_map[old_key], "current": current_map[new_key], "reason": "reference"}
            )
            remaining_removed.remove(old_key)
            remaining_added.remove(new_key)

    return {
        "added": [current_map[key] for key in sorted(remaining_added)],
        "changed": changed,
        "removed": [baseline_map[key] for key in sorted(remaining_removed)],
    }


def _resolve_baseline(root: Path, baseline: str | Path | None) -> Path:
    if baseline is None:
        return root / DEFAULT_BASELINE
    candidate = Path(baseline)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _resolve_reverse_lock(root: Path, lock: str | Path | None = None) -> Path:
    if lock is None:
        return root / DEFAULT_REVERSE_LOCK
    candidate = Path(lock)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load lock YAML through the standard-library-capable governance parser."""
    try:
        try:
            from validate_governance import _yaml_safe_load
            value = _yaml_safe_load(path.read_text(encoding="utf-8"))
        except (ImportError, ModuleNotFoundError):
            from scripts.validate_governance import _yaml_safe_load
            value = _yaml_safe_load(path.read_text(encoding="utf-8"))
    except (ImportError, OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _record_field_enforcement(
    result: dict[str, Any], dependency_id: str, kind: str, entry: dict[str, Any]
) -> None:
    required_fields = list(LOCK_FIELDS_BY_KIND.get(kind, ()))
    if kind == "github-release" and dependency_id == "ghidra-release":
        required_fields.extend(("pyghidra_version", "pyghidra_wheel"))
    enforcement = entry.get("enforcement")
    fields: dict[str, str] = {}
    if not isinstance(enforcement, dict):
        result["errors"].append(f"reverse-lock-missing-field-enforcement:{dependency_id}")
        result["field_enforcement"].append({"id": dependency_id, "fields": fields})
        return
    for field in required_fields:
        state = enforcement.get(field)
        if state not in ENFORCEMENT_STATES:
            result["errors"].append(f"reverse-lock-invalid-field-enforcement:{dependency_id}:{field}")
            continue
        fields[field] = state
        result["enforcement_summary"][state].append(f"{dependency_id}.{field}")
        if entry.get("status") == "blocked" and state != "blocked":
            result["errors"].append(f"reverse-lock-blocked-field-must-remain-blocked:{dependency_id}:{field}")
    result["field_enforcement"].append({"id": dependency_id, "fields": fields})


def validate_reverse_lock(root: str | Path = ".", lock: str | Path | None = None) -> dict[str, Any]:
    """Validate exact pins and explicit blocked entries without resolving them."""
    root_path = Path(root).resolve()
    lock_path = _resolve_reverse_lock(root_path, lock)
    result: dict[str, Any] = {
        "path": str(lock_path),
        "present": lock_path.is_file(),
        "ok": False,
        "errors": [],
        "dependencies": 0,
        "field_enforcement": [],
        "enforcement_summary": {state: [] for state in sorted(ENFORCEMENT_STATES)},
    }
    if not lock_path.is_file():
        result["errors"] = ["reverse-lock-missing"]
        return result
    payload = _load_yaml_mapping(lock_path)
    if not payload:
        result["errors"] = ["reverse-lock-invalid-yaml"]
        return result
    if payload.get("schema_version") != "4.2":
        result["errors"].append("reverse-lock-invalid-schema-version")
    if payload.get("policy") != "fail-closed":
        result["errors"].append("reverse-lock-policy-must-be-fail-closed")
    entries = payload.get("dependencies")
    if not isinstance(entries, list) or not entries:
        result["errors"].append("reverse-lock-dependencies-missing")
        entries = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            result["errors"].append(f"reverse-lock-entry-{index}-not-mapping")
            continue
        dependency_id = entry.get("id")
        if not isinstance(dependency_id, str) or not dependency_id.strip():
            result["errors"].append(f"reverse-lock-entry-{index}-missing-id")
            continue
        if dependency_id in seen:
            result["errors"].append(f"reverse-lock-duplicate-id:{dependency_id}")
        seen.add(dependency_id)
        status = entry.get("status")
        kind = entry.get("kind")
        if not isinstance(kind, str):
            result["errors"].append(f"reverse-lock-unknown-kind:{dependency_id}")
            continue
        _record_field_enforcement(result, dependency_id, kind, entry)
        if status == "resolved":
            if kind in {"git", "go"}:
                if not re.fullmatch(r"[0-9a-f]{40}", str(entry.get("commit", ""))):
                    result["errors"].append(f"reverse-lock-unpinned-commit:{dependency_id}")
                if not re.fullmatch(r"https://.+\.git", str(entry.get("repository", ""))):
                    result["errors"].append(f"reverse-lock-missing-repository:{dependency_id}")
            elif kind in {"npm", "pypi"}:
                if not str(entry.get("package", "")):
                    result["errors"].append(f"reverse-lock-missing-package:{dependency_id}")
                if not str(entry.get("version", "")):
                    result["errors"].append(f"reverse-lock-missing-version:{dependency_id}")
                if kind == "npm" and not str(entry.get("integrity", "")).startswith("sha512-"):
                    result["errors"].append(f"reverse-lock-missing-integrity:{dependency_id}")
                if kind == "pypi" and not re.fullmatch(
                    r"[0-9a-f]{64}", str(entry.get("sha256", ""))
                ):
                    result["errors"].append(f"reverse-lock-missing-sha256:{dependency_id}")
            elif kind == "github-release":
                for field in ("repository", "tag", "asset"):
                    if not str(entry.get(field, "")):
                        result["errors"].append(f"reverse-lock-missing-{field}:{dependency_id}")
                if not str(entry.get("url", "")).startswith("https://github.com/"):
                    result["errors"].append(f"reverse-lock-missing-url:{dependency_id}")
                if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
                    result["errors"].append(f"reverse-lock-missing-sha256:{dependency_id}")
                if not re.fullmatch(r"[0-9a-f]{40}", str(entry.get("commit", ""))):
                    result["errors"].append(f"reverse-lock-unpinned-commit:{dependency_id}")
                if dependency_id == "ghidra-release":
                    pyghidra_version = str(entry.get("pyghidra_version", ""))
                    pyghidra_wheel = str(entry.get("pyghidra_wheel", ""))
                    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[A-Za-z0-9.+-]*)", pyghidra_version):
                        result["errors"].append("reverse-lock-missing-pyghidra-version:ghidra-release")
                    wheel_path = Path(pyghidra_wheel)
                    if (
                        not pyghidra_wheel.endswith(".whl")
                        or wheel_path.is_absolute()
                        or ".." in wheel_path.parts
                        or pyghidra_version not in wheel_path.name
                    ):
                        result["errors"].append("reverse-lock-invalid-pyghidra-wheel:ghidra-release")
            else:
                result["errors"].append(f"reverse-lock-unknown-kind:{dependency_id}")
        elif status == "blocked":
            if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
                result["errors"].append(f"reverse-lock-blocked-without-reason:{dependency_id}")
        else:
            result["errors"].append(f"reverse-lock-invalid-status:{dependency_id}")
    result["dependencies"] = len(seen)
    for values in result["enforcement_summary"].values():
        values.sort()
    result["ok"] = not result["errors"]
    return result


BOOTSTRAP_CONTROL_MARKERS = (
    "git -C \"$destination\" remote get-url origin",
    "git -C \"$destination\" status --porcelain --untracked-files=all",
    "git -C \"$destination\" rev-parse HEAD",
    "pnpm install --frozen-lockfile",
    "install_locked_go_package nuclei-go",
    "install_locked_go_package pentestswarm-go",
    "REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES",
    "unpinned apt",
)


def validate_bootstrap_controls(root: str | Path = ".") -> dict[str, Any]:
    """Ensure both installer paths retain the lock-consumption gates.

    This is intentionally a narrow static audit. Shell regression tests cover
    the checkout behavior; this report catches removal of those guards from a
    packaged installer before it can silently regress to a floating path.
    """
    root_path = Path(root).resolve()
    result: dict[str, Any] = {"ok": True, "paths": [], "errors": []}
    for relative in TARGET_FILES[:2]:
        path = root_path / relative
        path_result: dict[str, Any] = {"path": relative, "present": path.is_file(), "missing": []}
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            path_result["missing"] = [marker for marker in BOOTSTRAP_CONTROL_MARKERS if marker not in content]
        else:
            path_result["missing"] = list(BOOTSTRAP_CONTROL_MARKERS)
        for marker in path_result["missing"]:
            result["errors"].append(f"bootstrap-control-missing:{relative}:{marker}")
        result["paths"].append(path_result)
    result["ok"] = not result["errors"]
    return result


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def refresh_baseline(root: str | Path = ".", baseline: str | Path | None = None) -> Path:
    root_path = Path(root).resolve()
    baseline_path = _resolve_baseline(root_path, baseline)
    if not _is_within(baseline_path, root_path):
        raise ValueError("baseline must be inside the audited repository root")
    findings = _aggregate(scan_floating_dependencies(root_path))
    if findings:
        first = findings[0]
        raise ValueError(
            "cannot refresh a zero-finding baseline while floating references exist: "
            f"{first['path']} {first['kind']} {first['reference']}"
        )
    payload = _baseline_payload(findings)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = baseline_path.with_suffix(baseline_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(baseline_path)
    return baseline_path


def build_report(
    root: str | Path = ".",
    baseline: str | Path | None = None,
    reverse_lock: str | Path | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    baseline_path = _resolve_baseline(root_path, baseline)
    current = _aggregate(scan_floating_dependencies(root_path))
    report: dict[str, Any] = {
        "ok": False,
        "root": str(root_path),
        "baseline": str(baseline_path),
        "baseline_present": baseline_path.is_file(),
        "note": (
            "No floating references found in the scanned npm, PyPI, Git, Go, GitHub release, and container "
            "ecosystems. Unpinned apt/Homebrew installs are disabled by default and are outside this zero-finding "
            "claim. Reverse lock reports identify which fields are enforced, metadata-only, or blocked."
        ),
        "targets": list(TARGET_FILES),
        "findings": current,
        "drift": {"added": [], "changed": [], "removed": []},
        "errors": [],
    }
    lock_report = validate_reverse_lock(root_path, reverse_lock)
    report["reverse_lock"] = lock_report
    bootstrap_report = validate_bootstrap_controls(root_path)
    report["bootstrap_controls"] = bootstrap_report
    if (root_path / "catalog/components.yaml").is_file() and not lock_report["ok"]:
        report["errors"].extend(lock_report["errors"])
    if (root_path / "catalog/components.yaml").is_file() and not bootstrap_report["ok"]:
        report["errors"].extend(bootstrap_report["errors"])
    if not baseline_path.is_file():
        report["errors"].append("baseline-missing")
        return report

    try:
        payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        report["errors"].append("baseline-invalid-json")
        return report
    if payload.get("schema_version") != BASELINE_SCHEMA_VERSION or not isinstance(payload.get("findings"), list):
        report["errors"].append("baseline-invalid-schema")
        return report
    if payload["findings"]:
        report["errors"].append("baseline-must-remain-zero")
    if current:
        report["errors"].append("floating-references-present")

    drift = _compare(payload["findings"], current)
    report["drift"] = drift
    report["ok"] = not report["errors"] and not current and not payload["findings"] and not any(drift.values())
    return report


def _print_text(report: dict[str, Any]) -> None:
    print("Floating dependency ratchet OK" if report["ok"] else "Floating dependency ratchet found drift")
    print(f"Baseline: {report['baseline']}")
    print(f"Known floating references: {sum(int(item.get('count', 1)) for item in report['findings'])}")
    print(
        "Note: zero findings cover the scanned npm/PyPI/Git/Go/GitHub-release/container ecosystems; "
        "unpinned apt/Homebrew installs are disabled by default and excluded from that claim. "
        "Reverse lock field statuses distinguish enforced values from metadata-only evidence; blocked entries fail closed."
    )
    for error in report["errors"]:
        print(f"[error] {error}")
    for change_type in ("added", "changed", "removed"):
        for entry in report["drift"][change_type]:
            if change_type == "changed":
                old = entry["baseline"]
                new = entry["current"]
                print(
                    f"[changed:{entry['reason']}] {new['path']} {new['kind']}: "
                    f"{old['reference']} -> {new['reference']}"
                )
            else:
                print(f"[{change_type}] {entry['path']} {entry['kind']}: {entry['reference']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject floating installer dependencies and validate the exact reverse dependency lock."
    )
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument(
        "--baseline",
        default=None,
        help=f"Baseline path relative to root. Default: {DEFAULT_BASELINE}.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    parser.add_argument(
        "--reverse-lock",
        default=None,
        help=f"Reverse dependency lock path relative to root. Default: {DEFAULT_REVERSE_LOCK}.",
    )
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Rewrite the repository-local zero-finding baseline; exact pins remain in the reverse lock.",
    )
    args = parser.parse_args(argv)

    try:
        if args.refresh_baseline:
            baseline_path = refresh_baseline(args.root, args.baseline)
            report = build_report(args.root, args.baseline, args.reverse_lock)
            report["refreshed"] = str(baseline_path)
        else:
            report = build_report(args.root, args.baseline, args.reverse_lock)
    except ValueError as error:
        report = {
            "ok": False,
            "root": str(Path(args.root).resolve()),
            "baseline": str(args.baseline or DEFAULT_BASELINE),
            "baseline_present": False,
            "note": (
                "No floating references found in the scanned npm, PyPI, Git, Go, GitHub release, and container "
                "ecosystems. Unpinned apt/Homebrew installs are disabled by default and are outside this "
                "zero-finding claim."
            ),
            "targets": list(TARGET_FILES),
            "findings": [],
            "drift": {"added": [], "changed": [], "removed": []},
            "errors": [str(error)],
        }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_text(report)
        if args.refresh_baseline and report["ok"]:
            print(f"Refreshed baseline: {report['refreshed']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
