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


def _profile_skill_names(root: Path, profile: str) -> set[str] | None:
    path = root / "catalog" / "profiles" / f"{profile}.txt"
    if not path.is_file():
        return None
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _iter_profile_skill_files(root: Path, include_pilots: bool) -> list[Path]:
    stable = _profile_skill_names(root, "stable")
    pilot = _profile_skill_names(root, "pilot")
    if stable is None or pilot is None:
        return _iter_skill_files(root)
    selected = set(stable)
    if include_pilots:
        selected.update(pilot)
    files: list[Path] = []
    for name in sorted(selected):
        skill_root = root / "skills" / name
        files.extend(path for path in skill_root.rglob("*") if path.is_file())
    return sorted(files)


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
    include_reverse: bool | None = None,
    include_pilots: bool | None = None,
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

    # Pilot verification is opt-in. Installed pilot remnants must not expand
    # the default stable profile after a profile change or prune operation.
    include_pilots = bool(include_pilots)
    skills_root = root / "skills"
    for skill_file in _iter_profile_skill_files(root, bool(include_pilots)):
        relative = skill_file.relative_to(skills_root)
        issue = _compare_file(
            skill_file,
            agents_home / "skills" / relative,
            f"skill {relative.as_posix()}",
        )
        if issue:
            issues.append(issue)

    reverse_router_root = root / "reverse-skill-router"
    reverse_pack_root = root / "reverse-skill"
    if include_reverse is None:
        # Default installation is intentionally reverse-free. If either
        # target exists, treat the profile as enabled and verify the full
        # profile so partial installs still surface as drift.
        include_reverse = (
            (codex_home / "skills" / "reverse-engineering").exists()
            or (codex_home / "reverse-skill").exists()
        )
    if include_reverse:
        lock_source = root / "catalog/reverse-dependencies.lock.yaml"
        if lock_source.is_file():
            lock_issue = _compare_file(
                lock_source,
                codex_home / "catalog/reverse-dependencies.lock.yaml",
                "reverse dependency lock",
            )
            if lock_issue:
                issues.append(lock_issue)
        for router_file in _iter_files(reverse_router_root):
            relative = router_file.relative_to(reverse_router_root)
            issue = _compare_file(
                router_file,
                codex_home / "skills" / relative,
                f"reverse router {relative.as_posix()}",
            )
            if issue:
                issues.append(issue)

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
    include_reverse: bool | None = None,
    include_pilots: bool | None = None,
) -> dict:
    root = Path(root).resolve()
    codex_home_path = Path(codex_home).expanduser().resolve() if codex_home else Path.home() / ".codex"
    agents_home_path = Path(agents_home).expanduser().resolve() if agents_home else Path.home() / ".agents"
    user_home_path = Path(user_home).expanduser().resolve() if user_home else Path.home()
    issues = check_live_install(
        root,
        codex_home_path,
        agents_home_path,
        user_home_path,
        include_reverse=include_reverse,
        include_pilots=include_pilots,
    )
    reverse_enabled = include_reverse
    if reverse_enabled is None:
        reverse_enabled = (
            (codex_home_path / "skills" / "reverse-engineering").exists()
            or (codex_home_path / "reverse-skill").exists()
        )
    pilots_enabled = bool(include_pilots)
    checked_count = (
        1
        + len(_iter_profile_skill_files(root, bool(pilots_enabled)))
        + (
            len(_iter_files(root / "reverse-skill-router"))
            + len(_iter_files(root / "reverse-skill"))
            + (1 if (root / "catalog/reverse-dependencies.lock.yaml").is_file() else 0)
            if reverse_enabled
            else 0
        )
    )
    return {
        "ok": not issues,
        "root": str(root),
        "codex_home": str(codex_home_path),
        "agents_home": str(agents_home_path),
        "user_home": str(user_home_path),
        "reverse_enabled": bool(reverse_enabled),
        "pilots_enabled": bool(pilots_enabled),
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
    parser.add_argument(
        "--with-reverse",
        action="store_true",
        help="Require and verify the optional reverse router and capability pack.",
    )
    parser.add_argument(
        "--with-pilots",
        action="store_true",
        help="Require and verify pilot skills in addition to the stable profile.",
    )
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    args = parser.parse_args(argv)

    include_reverse = True if args.with_reverse else None
    include_pilots = args.with_pilots
    report = build_report(
        args.root,
        args.codex_home,
        args.agents_home,
        args.user_home,
        include_reverse,
        include_pilots,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
