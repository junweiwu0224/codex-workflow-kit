#!/usr/bin/env python3
"""Verify that the installed Codex workflow files match this toolkit."""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

FOREIGN_USER_CODEX_PATH_RE = re.compile(r"/Users/([^/]+)/\.(?:codex|cache/codex-runtimes)(?:/|$)")
ACTIVE_PLUGIN_CONFIG_RELATIVES = (
    "chrome-native-hosts-v2.json",
    "Library/Application Support/OpenAI/Codex/chrome-native-hosts-v2.json",
    "Library/Application Support/Google/Chrome/NativeMessagingHosts/com.openai.codexextension.json",
    "Library/Application Support/Google/Chrome for Testing/NativeMessagingHosts/com.openai.codexextension.json",
    "Library/Application Support/Google/ChromeForTesting/NativeMessagingHosts/com.openai.codexextension.json",
    "Library/Application Support/Chromium/NativeMessagingHosts/com.openai.codexextension.json",
)


@dataclass(frozen=True, order=True)
class LiveInstallIssue:
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


def _iter_skill_files(root: Path) -> list[Path]:
    skills_root = root / "skills"
    if not skills_root.exists():
        return []
    return sorted(path for path in skills_root.rglob("*") if path.is_file())


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _compare_file(source: Path, target: Path, label: str) -> LiveInstallIssue | None:
    if not source.exists():
        return LiveInstallIssue(
            severity="error",
            code="missing-source",
            path=str(source),
            message=f"Toolkit source file is missing: {label}.",
        )
    if not target.exists():
        return LiveInstallIssue(
            severity="error",
            code="missing",
            path=str(target),
            message=f"Installed {label} is missing.",
        )
    if not filecmp.cmp(source, target, shallow=False):
        return LiveInstallIssue(
            severity="error",
            code="drift",
            path=str(target),
            message=f"Installed {label} differs from toolkit {source.relative_to(source.parents[1]).as_posix()}.",
        )
    return None


def _foreign_user_path_issues(path: Path, text: str, expected_user: str) -> list[LiveInstallIssue]:
    issues: list[LiveInstallIssue] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in FOREIGN_USER_CODEX_PATH_RE.finditer(line):
            found_user = match.group(1)
            if found_user == expected_user:
                continue
            issues.append(
                LiveInstallIssue(
                    severity="error",
                    code="foreign-user-plugin-path",
                    path=f"{path}:{line_number}",
                    message=(
                        "Active Codex plugin/runtime path points at a different macOS user "
                        f"({found_user}); expected paths owned by {expected_user}."
                    ),
                )
            )
    return issues


def _check_active_plugin_paths(codex_home: Path, user_home: Path) -> list[LiveInstallIssue]:
    issues: list[LiveInstallIssue] = []
    expected_user = user_home.name
    sources = [codex_home / ACTIVE_PLUGIN_CONFIG_RELATIVES[0]]
    sources.extend(user_home / relative for relative in ACTIVE_PLUGIN_CONFIG_RELATIVES[1:])

    for source in sources:
        if source.exists() and source.is_file():
            issues.extend(_foreign_user_path_issues(source, source.read_text(encoding="utf-8"), expected_user))

    plugin_cache = codex_home / "plugins/cache"
    if plugin_cache.exists():
        for path in sorted(plugin_cache.rglob("*")):
            if not path.is_symlink():
                continue
            target = os.readlink(path)
            issues.extend(_foreign_user_path_issues(path, target, expected_user))

    return issues


def check_live_install(
    root: str | Path = ".",
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    user_home: str | Path | None = None,
) -> list[LiveInstallIssue]:
    root = Path(root).resolve()
    codex_home = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    agents_home = Path(agents_home).expanduser().resolve() if agents_home else Path.home() / ".agents"
    user_home = Path(user_home).expanduser().resolve() if user_home else Path.home()
    issues: list[LiveInstallIssue] = []

    global_issue = _compare_file(
        root / "global/AGENTS.md",
        codex_home / "AGENTS.md",
        "global AGENTS.md",
    )
    if global_issue:
        issues.append(global_issue)

    skills_root = root / "skills"
    for skill_file in _iter_skill_files(root):
        relative = skill_file.relative_to(skills_root)
        issue = _compare_file(
            skill_file,
            agents_home / "skills" / relative,
            f"skill {relative.as_posix()}",
        )
        if issue:
            issues.append(issue)

    reverse_router_root = root / "reverse-skill-router"
    for router_file in _iter_files(reverse_router_root):
        relative = router_file.relative_to(reverse_router_root)
        issue = _compare_file(
            router_file,
            codex_home / "skills" / relative,
            f"reverse router {relative.as_posix()}",
        )
        if issue:
            issues.append(issue)

    reverse_pack_root = root / "reverse-skill"
    for reverse_file in _iter_files(reverse_pack_root):
        relative = reverse_file.relative_to(reverse_pack_root)
        issue = _compare_file(
            reverse_file,
            codex_home / "reverse-skill" / relative,
            f"reverse pack {relative.as_posix()}",
        )
        if issue:
            issues.append(issue)

    issues.extend(_check_active_plugin_paths(codex_home, user_home))

    return sorted(issues)


def build_report(
    root: str | Path = ".",
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    user_home: str | Path | None = None,
) -> dict:
    root = Path(root).resolve()
    codex_home_path = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    agents_home_path = Path(agents_home).expanduser().resolve() if agents_home else Path.home() / ".agents"
    user_home_path = Path(user_home).expanduser().resolve() if user_home else Path.home()
    issues = check_live_install(root, codex_home_path, agents_home_path, user_home_path)
    checked_count = (
        1
        + len(_iter_skill_files(root))
        + len(_iter_files(root / "reverse-skill-router"))
        + len(_iter_files(root / "reverse-skill"))
    )
    return {
        "ok": not issues,
        "root": str(root),
        "codex_home": str(codex_home_path),
        "agents_home": str(agents_home_path),
        "user_home": str(user_home_path),
        "checked_count": checked_count,
        "error_count": len([issue for issue in issues if issue.severity == "error"]),
        "issues": [issue.to_dict() for issue in issues],
    }


def _print_report(report: dict) -> None:
    if report["ok"]:
        print(f"Live install OK ({report['checked_count']} files checked)")
        return

    print("Live install drift detected")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify installed Codex workflow files against this toolkit.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--codex-home", default=None, help="Codex home containing AGENTS.md. Default: ~/.codex")
    parser.add_argument("--agents-home", default=None, help="Agents home containing skills/. Default: ~/.agents")
    parser.add_argument("--user-home", default=None, help="User home for active plugin/native-host path checks. Default: ~")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    args = parser.parse_args(argv)

    report = build_report(args.root, args.codex_home, args.agents_home, args.user_home)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
