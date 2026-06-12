#!/usr/bin/env python3
"""Read-only audit for third-party Codex components before adoption."""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_TEXT_BYTES = 1024 * 1024
SKIPPED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "releases",
    "venv",
}
TEXT_SUFFIXES = {
    "",
    ".bash",
    ".cfg",
    ".cjs",
    ".env",
    ".json",
    ".lock",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
    ".zsh",
}
IMPORTANT_NAMES = {
    ".env",
    ".mcp.json",
    "config",
    "config.toml",
    "dockerfile",
    "hooks.json",
    "install",
    "install.sh",
    "makefile",
    "package.json",
    "plugin.json",
    "pyproject.toml",
    "readme",
    "readme.md",
    "requirements.txt",
    "settings.json",
    "setup",
    "setup.sh",
    "skill.md",
}
LICENSE_NAMES = {
    "copying",
    "license",
    "license.md",
    "license.txt",
    "notice",
    "notice.md",
}
README_NAMES = {
    "readme",
    "readme.md",
    "readme.txt",
}
INSTALL_SCRIPT_NAMES = {
    "bootstrap",
    "bootstrap.sh",
    "install",
    "install.py",
    "install.sh",
    "setup",
    "setup.py",
    "setup.sh",
}

SECRET_VALUE_RE = re.compile(
    r"sk-[A-Za-z0-9_-]{20,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"ghp_[A-Za-z0-9_]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|"
    r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY|"
    r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}|"
    r"authorization:\s*bearer\s+[A-Za-z0-9._-]+",
    re.IGNORECASE,
)
PRIVATE_PATH_RE = re.compile(
    r"/Users/[^\s'\"`]+|"
    r"/home/[^\s'\"`]+|"
    r"C:\\Users\\[^\s'\"`]+|"
    r"~/(?:\.ssh|\.aws|\.config/codex)|"
    r"\b(?:id_rsa|id_ed25519|\.aws/credentials)\b",
    re.IGNORECASE,
)
CURL_TO_SHELL_RE = re.compile(
    r"(?:curl|wget)\b[^\n|;]*(?:\||-O\s*-|-o\s*-)[^\n]*(?:sh|bash|zsh)\b|"
    r"(?:sh|bash|zsh)\b\s*<\s*<\s*\$?\((?:curl|wget)\b",
    re.IGNORECASE,
)
NETWORK_HINT_RE = re.compile(
    r"https?://|"
    r"\b(?:curl|wget|fetch|axios|requests\.(?:get|post)|urllib|websocket|socket|listen|server\.listen)\b|"
    r"localhost:\d+",
    re.IGNORECASE,
)
DAEMON_HINT_RE = re.compile(
    r"\b(?:daemon|systemctl|launchctl|crontab|nohup|pm2|docker\s+run\s+-d|"
    r"while\s+true|long-running|watcher)\b",
    re.IGNORECASE,
)
WRITE_HINT_RE = re.compile(
    r"\b(?:rm\s+-rf|mv\s+|cp\s+|mkdir\s+-p|touch\s+|chmod\s+|chown\s+|tee\s+|"
    r"write_text\(|writeFile\(|pip\s+install|npm\s+install|pnpm\s+install|"
    r"yarn\s+install|brew\s+install|deploy|publish|migration)\b|"
    r"open\([^)]*['\"]w['\"]|>>",
    re.IGNORECASE,
)
AUTH_HINT_RE = re.compile(
    r"\b(?:auth|authorization|bearer|credential|keychain|login|oauth|api[_ -]?key|secret|token|cookie|session)\b",
    re.IGNORECASE,
)
SUPERPOWERS_OVERLAP_TERMS = (
    "implementation-plan",
    "implementation plan",
    "debug-loop",
    "debug loop",
    "frontend-qa",
    "frontend qa",
    "security-review",
    "security review",
    "dependency-upgrade-review",
    "dependency upgrade",
    "research-brief",
    "research brief",
    "repo-onboarding",
    "repo onboarding",
    "spec-kit-xl",
    "spec kit",
    "completion-review",
    "completion review",
    "decision-record",
    "decision record",
    "orchestrator",
    "tdd workflow",
    "phase execution",
)

REJECT_TAGS = {"curl-to-shell", "invalid-config", "missing-path", "secret-like"}
HOLD_TAGS = {"daemon", "hook", "install-risk", "missing-license", "missing-readme", "private-path"}
REPO_LOCAL_TAGS = {"auth", "mcp", "network", "plugin", "write"}
SEVERITY_RANK = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class ComponentFinding:
    severity: str
    code: str
    path: str
    message: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "tags": list(self.tags),
        }


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _is_text_candidate(path: Path) -> bool:
    name = path.name.lower()
    if name in IMPORTANT_NAMES:
        return True
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return any(part.lower() in {"hooks", "scripts"} for part in path.parts)


def _iter_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]

    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(target, followlinks=False):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in SKIPPED_DIRS and not (Path(current_root) / name).is_symlink()
        )
        current = Path(current_root)
        for file_name in sorted(file_names):
            path = current / file_name
            if path.is_symlink() or not path.is_file():
                continue
            files.append(path)
    return files


def _read_text(path: Path) -> tuple[str, bool]:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_TEXT_BYTES + 1)
    except OSError:
        return "", False
    truncated = len(data) > MAX_TEXT_BYTES
    if truncated:
        data = data[:MAX_TEXT_BYTES]
    if b"\0" in data:
        return "", truncated
    return data.decode("utf-8", errors="ignore"), truncated


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}

    frontmatter: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip("\"'")
    return frontmatter


def _walk_json(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key), nested
            yield from _walk_json(nested)
    elif isinstance(value, list):
        for nested in value:
            if isinstance(nested, (dict, list)):
                yield from _walk_json(nested)
            else:
                yield "", nested


def _add(
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
    severity: str,
    code: str,
    path: str,
    message: str,
    tags: tuple[str, ...] = (),
) -> None:
    key = (severity, code, path)
    if key in seen:
        return
    seen.add(key)
    findings.append(
        ComponentFinding(
            severity=severity,
            code=code,
            path=path,
            message=message,
            tags=tuple(sorted(set(tags))),
        )
    )


def _check_skill(
    path: Path,
    relative: str,
    text: str,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> bool:
    if path.name != "SKILL.md":
        return False

    frontmatter = _parse_frontmatter(text)
    if not frontmatter:
        _add(
            findings,
            seen,
            "warning",
            "skill-frontmatter-missing",
            relative,
            "SKILL.md is missing parseable frontmatter with name and description.",
            ("skill", "skill-metadata"),
        )
        return True

    if not frontmatter.get("name"):
        _add(
            findings,
            seen,
            "warning",
            "skill-name-missing",
            relative,
            "SKILL.md frontmatter is missing a name.",
            ("skill", "skill-metadata"),
        )
    elif frontmatter["name"] != path.parent.name:
        _add(
            findings,
            seen,
            "warning",
            "skill-name-folder-mismatch",
            relative,
            "SKILL.md frontmatter name does not match its folder name.",
            ("skill", "skill-metadata"),
        )

    description = frontmatter.get("description", "")
    if not description:
        _add(
            findings,
            seen,
            "warning",
            "skill-description-missing",
            relative,
            "SKILL.md frontmatter is missing a description.",
            ("skill", "skill-metadata"),
        )
    elif not description.startswith("Use when"):
        _add(
            findings,
            seen,
            "warning",
            "skill-description-trigger-missing",
            relative,
            'Skill description should start with "Use when" and state trigger conditions.',
            ("skill", "skill-metadata"),
        )
    return True


def _check_plugin_json(
    relative: str,
    text: str,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> bool:
    if Path(relative).name != "plugin.json":
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        _add(
            findings,
            seen,
            "error",
            "plugin-json-invalid",
            relative,
            "plugin.json is not valid JSON.",
            ("invalid-config", "plugin"),
        )
        return True

    _add(
        findings,
        seen,
        "info",
        "plugin-json-present",
        relative,
        "plugin.json was found; review declared capabilities before adoption.",
        ("plugin",),
    )
    if isinstance(data, dict) and not any(data.get(key) for key in ("name", "id")):
        _add(
            findings,
            seen,
            "warning",
            "plugin-metadata-missing",
            relative,
            "plugin.json does not declare a name or id.",
            ("plugin", "plugin-metadata"),
        )

    keys = {key.lower() for key, _ in _walk_json(data)}
    values = [value for _, value in _walk_json(data)]
    text_values = " ".join(value for value in values if isinstance(value, str))
    if keys & {"auth", "authorization", "credentials", "permissions", "permission", "secrets", "tokens"}:
        _add(
            findings,
            seen,
            "warning",
            "plugin-auth-hint",
            relative,
            "plugin.json references auth, permissions, credentials, or secrets.",
            ("auth", "plugin"),
        )
    if keys & {"hooks", "commands", "tools", "mcpservers", "mcp_servers", "apps"}:
        _add(
            findings,
            seen,
            "warning",
            "plugin-execution-hint",
            relative,
            "plugin.json references hooks, commands, tools, apps, or MCP servers.",
            ("plugin", "write"),
        )
    if re.search(r"\bwrite\b", text_values, re.IGNORECASE):
        _add(
            findings,
            seen,
            "warning",
            "plugin-write-capability",
            relative,
            "plugin.json advertises write capability.",
            ("plugin", "write"),
        )
    return True


def _check_mcp_json(
    relative: str,
    text: str,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> bool:
    if Path(relative).name != ".mcp.json":
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        _add(
            findings,
            seen,
            "error",
            "mcp-json-invalid",
            relative,
            ".mcp.json is not valid JSON.",
            ("invalid-config", "mcp"),
        )
        return True

    _add(
        findings,
        seen,
        "warning",
        "mcp-config-present",
        relative,
        ".mcp.json can launch local tools or connect to external systems; review manually.",
        ("mcp",),
    )
    for key, value in _walk_json(data):
        lowered_key = key.lower()
        if lowered_key in {"command", "args"}:
            _add(
                findings,
                seen,
                "warning",
                "mcp-command-hint",
                relative,
                ".mcp.json declares executable command or args.",
                ("mcp", "write"),
            )
        if lowered_key in {"env", "headers"}:
            _add(
                findings,
                seen,
                "warning",
                "mcp-auth-hint",
                relative,
                ".mcp.json references environment or header configuration.",
                ("auth", "mcp"),
            )
        if isinstance(value, str) and NETWORK_HINT_RE.search(value):
            _add(
                findings,
                seen,
                "warning",
                "mcp-network-hint",
                relative,
                ".mcp.json references a network endpoint.",
                ("mcp", "network"),
            )
    return True


def _check_hooks(
    path: Path,
    relative: str,
    text: str,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> bool:
    found = False
    if any(part.lower() == "hooks" for part in Path(relative).parts):
        _add(
            findings,
            seen,
            "warning",
            "hook-file-present",
            relative,
            "Hook file found; hooks can run automatically and should stay repo-local until reviewed.",
            ("hook", "write"),
        )
        found = True

    if path.name.lower() in {"settings.json", "config.toml", "hooks.json"} and re.search(
        r"\bhooks?\b|PreToolUse|PostToolUse|Stop|Notification",
        text,
        re.IGNORECASE,
    ):
        _add(
            findings,
            seen,
            "warning",
            "hook-config-present",
            relative,
            "Configuration references hooks or hook events.",
            ("hook", "write"),
        )
        found = True
    return found


def _is_install_script(path: Path) -> bool:
    name = path.name.lower()
    if name in INSTALL_SCRIPT_NAMES:
        return True
    return "install" in name and any(part.lower() == "scripts" for part in path.parts)


def _check_install_script(
    path: Path,
    relative: str,
    text: str,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> bool:
    if not _is_install_script(path):
        return False

    _add(
        findings,
        seen,
        "info",
        "install-script-present",
        relative,
        "Install or bootstrap script found; inspect before running.",
        ("install-script",),
    )
    if re.search(
        r"\b(?:sudo|pip\s+install|npm\s+install|pnpm\s+install|yarn\s+install|"
        r"brew\s+install|rm\s+-rf|chmod|chown|cp\s+|mv\s+)\b",
        text,
        re.IGNORECASE,
    ):
        _add(
            findings,
            seen,
            "warning",
            "install-script-risk",
            relative,
            "Install script contains package, permission, deletion, or filesystem-write hints.",
            ("install-risk", "write"),
        )
    return True


def _check_generic_text(
    relative: str,
    text: str,
    truncated: bool,
    findings: list[ComponentFinding],
    seen: set[tuple[str, str, str]],
) -> None:
    if truncated:
        _add(
            findings,
            seen,
            "info",
            "file-truncated",
            relative,
            "File exceeded the audit read limit; only the first 1 MiB was scanned.",
            ("large-file",),
        )
    if not text:
        return

    if SECRET_VALUE_RE.search(text):
        _add(
            findings,
            seen,
            "error",
            "secret-like-content",
            relative,
            "Secret-like content was found; value redacted.",
            ("auth", "secret-like"),
        )
    if PRIVATE_PATH_RE.search(text):
        _add(
            findings,
            seen,
            "warning",
            "private-path-reference",
            relative,
            "Private local path reference was found; value redacted.",
            ("private-path",),
        )
    if CURL_TO_SHELL_RE.search(text):
        _add(
            findings,
            seen,
            "error",
            "curl-to-shell",
            relative,
            "curl/wget-to-shell execution pattern found.",
            ("curl-to-shell", "network", "write"),
        )
    if DAEMON_HINT_RE.search(text):
        _add(
            findings,
            seen,
            "warning",
            "daemon-hint",
            relative,
            "Daemon, background process, or scheduler hint found.",
            ("daemon",),
        )
    if NETWORK_HINT_RE.search(text):
        _add(
            findings,
            seen,
            "warning",
            "network-hint",
            relative,
            "Network access hint found.",
            ("network",),
        )
    if WRITE_HINT_RE.search(text):
        _add(
            findings,
            seen,
            "warning",
            "write-hint",
            relative,
            "Filesystem write, install, or permission-change hint found.",
            ("write",),
        )
    if AUTH_HINT_RE.search(text):
        _add(
            findings,
            seen,
            "warning",
            "auth-hint",
            relative,
            "Auth, token, credential, or login hint found.",
            ("auth",),
        )

    lowered = text.lower()
    if any(term in lowered for term in SUPERPOWERS_OVERLAP_TERMS):
        _add(
            findings,
            seen,
            "warning",
            "superpowers-overlap",
            relative,
            "Content appears to overlap an existing Superpowers workflow or specialist skill.",
            ("superpowers-overlap",),
        )


def _root_has_file(root: Path, files: list[Path], names: set[str]) -> bool:
    if root.is_file():
        return False
    return any(path.parent == root and path.name.lower() in names for path in files)


def _recommend(findings: list[ComponentFinding]) -> str:
    tags = {tag for finding in findings for tag in finding.tags}
    if tags & REJECT_TAGS or any(finding.severity == "error" for finding in findings):
        return "reject"
    if tags & HOLD_TAGS:
        return "hold"
    if tags & REPO_LOCAL_TAGS:
        return "repo-local"
    if "superpowers-overlap" in tags or any(finding.severity == "warning" for finding in findings):
        return "pilot"
    return "promote"


def audit_component(target: str | Path) -> dict[str, object]:
    target_path = Path(target).resolve()
    findings: list[ComponentFinding] = []
    seen: set[tuple[str, str, str]] = set()

    if not target_path.exists():
        _add(
            findings,
            seen,
            "error",
            "path-missing",
            str(target_path),
            "Target path does not exist.",
            ("missing-path",),
        )
        return _build_report(target_path, [], False, False, findings)

    root = target_path if target_path.is_dir() else target_path.parent
    files = _iter_files(target_path)
    component_types: set[str] = set()

    readme_present = _root_has_file(root, files, README_NAMES)
    license_present = _root_has_file(root, files, LICENSE_NAMES)
    if target_path.is_dir() and not readme_present:
        _add(
            findings,
            seen,
            "warning",
            "readme-missing",
            ".",
            "No root README file was found.",
            ("missing-readme",),
        )
    if target_path.is_dir() and not license_present:
        _add(
            findings,
            seen,
            "warning",
            "license-missing",
            ".",
            "No root license file was found.",
            ("missing-license",),
        )

    for path in files:
        if not _is_text_candidate(path):
            continue
        relative = _relative(root, path)
        text, truncated = _read_text(path)

        if _check_skill(path, relative, text, findings, seen):
            component_types.add("skill")
        if _check_plugin_json(relative, text, findings, seen):
            component_types.add("plugin")
        if _check_mcp_json(relative, text, findings, seen):
            component_types.add("mcp")
        if _check_hooks(path, relative, text, findings, seen):
            component_types.add("hook")
        if _check_install_script(path, relative, text, findings, seen):
            component_types.add("install-script")

        _check_generic_text(relative, text, truncated, findings, seen)

    return _build_report(target_path, sorted(component_types), readme_present, license_present, findings)


def _build_report(
    target_path: Path,
    component_types: list[str],
    readme_present: bool,
    license_present: bool,
    findings: list[ComponentFinding],
) -> dict[str, object]:
    sorted_findings = sorted(
        findings,
        key=lambda finding: (SEVERITY_RANK.get(finding.severity, 99), finding.path, finding.code),
    )
    risk_tags = sorted({tag for finding in sorted_findings for tag in finding.tags})
    decision = _recommend(sorted_findings)
    return {
        "ok": decision != "reject",
        "target": str(target_path),
        "recommended_decision": decision,
        "decision": decision,
        "risk_tags": risk_tags,
        "component_types": component_types,
        "surfaces": component_types,
        "readme_present": readme_present,
        "license_present": license_present,
        "finding_count": len(sorted_findings),
        "findings": [finding.to_dict() for finding in sorted_findings],
    }


def _print_text(report: dict[str, object]) -> None:
    print("External component audit:")
    print(f"- Target: {report['target']}")
    print(f"- Recommended decision: {report['recommended_decision']}")
    print(f"- Components: {', '.join(report['component_types']) or 'none-detected'}")
    print(f"- Risk tags: {', '.join(report['risk_tags']) or 'none'}")
    print(f"- README: {'present' if report['readme_present'] else 'missing'}")
    print(f"- License: {'present' if report['license_present'] else 'missing'}")
    print(f"- Findings: {report['finding_count']}")
    for finding in report["findings"]:
        tags = ",".join(finding["tags"]) or "none"
        print(f"  - [{finding['severity']}] {finding['code']} {finding['path']} tags={tags}: {finding['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit an external Codex component without installing or running it.")
    parser.add_argument("path", help="Component directory or file to audit.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args(argv)

    output_format = "json" if args.json else args.format
    report = audit_component(args.path)
    if output_format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)

    return 1 if report["recommended_decision"] == "reject" else 0


if __name__ == "__main__":
    raise SystemExit(main())
