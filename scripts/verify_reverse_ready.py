#!/usr/bin/env python3
"""Check whether a machine is reverse-task ready after workflow-kit install."""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


CORE_TOOLS = (
    ("jadx", "APK decode"),
    ("apktool", "APK unpack/rebuild"),
    ("frida", "dynamic instrumentation"),
    ("r2", "free binary triage"),
    ("nmap", "network scan"),
    ("sqlmap", "SQL injection automation"),
    ("ffuf", "web fuzzing"),
    ("nuclei", "template scanning"),
    ("binwalk", "firmware extraction"),
    ("dot", "diagram rendering via Graphviz"),
)

OPTIONAL_TOOLS = (
    ("apksigner", "APK signing"),
    ("zipalign", "APK alignment"),
    ("adb", "Android device bridge"),
    ("plantuml", "UML-heavy diagrams"),
)

CLAUDE_MCP_CONFIG_RELATIVE = ".claude/mcp.json"
CODEX_MCP_CONFIG_RELATIVE = ".codex/config.toml"


@dataclass(frozen=True)
class ReverseReadyIssue:
    severity: str
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def _find_tool(name: str) -> str | None:
    return shutil.which(name)


def _existing_path(path: Path | None) -> Path | None:
    if path and path.exists():
        return path
    return None


def _find_mcp_configs(user_home: Path, codex_config: Path | None = None) -> tuple[Path | None, Path | None]:
    codex_candidate = _existing_path(codex_config) or _existing_path(user_home / CODEX_MCP_CONFIG_RELATIVE)
    claude_candidate = _existing_path(user_home / CLAUDE_MCP_CONFIG_RELATIVE)
    return codex_candidate, claude_candidate


def check_reverse_ready(
    user_home: str | Path | None = None,
    codex_config: str | Path | None = None,
) -> tuple[list[ReverseReadyIssue], dict]:
    user_home_path = Path(user_home).expanduser().resolve() if user_home else Path.home()
    codex_config_path = Path(codex_config).expanduser().resolve() if codex_config else None
    issues: list[ReverseReadyIssue] = []
    core_status = []
    optional_status = []

    for name, purpose in CORE_TOOLS:
        path = _find_tool(name)
        core_status.append({"name": name, "purpose": purpose, "available": bool(path), "path": path})
        if not path:
            issues.append(
                ReverseReadyIssue(
                    severity="error",
                    code="missing-core-tool",
                    path=name,
                    message=f"Reverse core tool is missing: {name} ({purpose}).",
                )
            )

    for name, purpose in OPTIONAL_TOOLS:
        path = _find_tool(name)
        optional_status.append({"name": name, "purpose": purpose, "available": bool(path), "path": path})
        if not path:
            issues.append(
                ReverseReadyIssue(
                    severity="warning",
                    code="missing-optional-tool",
                    path=name,
                    message=f"Optional reverse tool is missing: {name} ({purpose}).",
                )
            )

    codex_mcp_config, claude_mcp_config = _find_mcp_configs(user_home_path, codex_config_path)
    if codex_mcp_config is None and claude_mcp_config is None:
        issues.append(
            ReverseReadyIssue(
                severity="warning",
                code="missing-mcp-config",
                path=str(user_home_path),
                message="No Codex/Claude MCP config file found; MCP-backed reverse flows may still need manual registration.",
            )
        )
    elif codex_mcp_config is None:
        issues.append(
            ReverseReadyIssue(
                severity="warning",
                code="missing-codex-mcp-config",
                path=str((codex_config_path or (user_home_path / CODEX_MCP_CONFIG_RELATIVE)).resolve()),
                message="Codex MCP config is missing; Codex Desktop reverse flows may still need manual registration even if Claude MCP is present.",
            )
        )

    report = {
        "ok": not any(issue.severity == "error" for issue in issues),
        "user_home": str(user_home_path),
        "mcp_config": str(codex_mcp_config or claude_mcp_config) if (codex_mcp_config or claude_mcp_config) else None,
        "codex_mcp_config": str(codex_mcp_config) if codex_mcp_config else None,
        "claude_mcp_config": str(claude_mcp_config) if claude_mcp_config else None,
        "core_tools": core_status,
        "optional_tools": optional_status,
        "issues": [issue.to_dict() for issue in issues],
    }
    return issues, report


def _print_report(report: dict) -> None:
    print("Reverse ready OK" if report["ok"] else "Reverse ready has gaps")
    for tool in report["core_tools"]:
        status = "OK" if tool["available"] else "MISSING"
        print(f"- core {tool['name']}: {status}")
    for tool in report["optional_tools"]:
        status = "OK" if tool["available"] else "MISSING"
        print(f"- optional {tool['name']}: {status}")
    print(f"- codex_mcp_config: {report['codex_mcp_config'] or 'MISSING'}")
    print(f"- claude_mcp_config: {report['claude_mcp_config'] or 'MISSING'}")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify reverse-task readiness on the current machine.")
    parser.add_argument("--user-home", default=None, help="User home used to look up MCP config. Default: ~")
    parser.add_argument(
        "--codex-config",
        default=None,
        help="Explicit Codex config.toml path to verify. Default: <user-home>/.codex/config.toml",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args(argv)

    _, report = check_reverse_ready(args.user_home, args.codex_config)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
