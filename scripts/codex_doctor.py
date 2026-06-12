#!/usr/bin/env python3
"""Run read-only diagnostics for the local Codex workflow install."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_old_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    try:
        from .verify_live_install import build_report as build_live_install_report
    except ImportError:
        from verify_live_install import build_report as build_live_install_report
finally:
    sys.dont_write_bytecode = _old_dont_write_bytecode



def _active_plugin_path_issue_count(live_report: dict) -> int:
    return len(
        [
            issue
            for issue in live_report["issues"]
            if issue.get("code") == "foreign-user-plugin-path"
        ]
    )


def build_report(
    root: str | Path = ".",
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    user_home: str | Path | None = None,
) -> dict:
    live_report = build_live_install_report(root, codex_home, agents_home, user_home)
    plugin_path_issue_count = _active_plugin_path_issue_count(live_report)
    non_plugin_issues = [
        issue
        for issue in live_report["issues"]
        if issue.get("code") != "foreign-user-plugin-path"
    ]

    return {
        "ok": not live_report["issues"],
        "root": live_report["root"],
        "checks": {
            "live_install": {
                "ok": not non_plugin_issues,
                "checked_count": live_report["checked_count"],
                "issue_count": len(non_plugin_issues),
            },
            "active_plugin_paths": {
                "ok": plugin_path_issue_count == 0,
                "issue_count": plugin_path_issue_count,
                "codex_home": live_report["codex_home"],
                "user_home": live_report["user_home"],
            },
        },
        "issues": live_report["issues"],
    }


def _print_report(report: dict) -> None:
    print("Codex doctor OK" if report["ok"] else "Codex doctor found issues")
    for name, check in report["checks"].items():
        status = "OK" if check["ok"] else "ISSUES"
        print(f"- {name}: {status}")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only Codex workflow diagnostics.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--codex-home", default=None, help="Codex home. Default: ~/.codex")
    parser.add_argument("--agents-home", default=None, help="Agents home. Default: ~/.agents")
    parser.add_argument("--user-home", default=None, help="User home for plugin/native-host path checks. Default: ~")
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
