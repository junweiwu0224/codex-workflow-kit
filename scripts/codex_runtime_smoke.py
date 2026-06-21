#!/usr/bin/env python3
"""Summarize local Codex runtime evidence for V3.1 workflow checks."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

_old_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    try:
        from .codex_doctor import build_report as build_doctor_report
        from .verify_live_install import build_report as build_live_install_report
    except ImportError:
        from codex_doctor import build_report as build_doctor_report
        from verify_live_install import build_report as build_live_install_report
finally:
    sys.dont_write_bytecode = _old_dont_write_bytecode


CUSTOM_SKILLS = (
    "completion-review",
    "debug-loop",
    "decision-record",
    "dependency-upgrade-review",
    "frontend-qa",
    "release-readiness",
    "repo-onboarding",
    "research-brief",
    "security-review",
    "skill-plugin-intake-review",
    "spec-kit-xl",
)

SUPERPOWERS_SKILLS = (
    "superpowers:brainstorming",
    "superpowers:dispatching-parallel-agents",
    "superpowers:executing-plans",
    "superpowers:finishing-a-development-branch",
    "superpowers:receiving-code-review",
    "superpowers:requesting-code-review",
    "superpowers:subagent-driven-development",
    "superpowers:systematic-debugging",
    "superpowers:test-driven-development",
    "superpowers:using-git-worktrees",
    "superpowers:using-superpowers",
    "superpowers:verification-before-completion",
    "superpowers:writing-plans",
    "superpowers:writing-skills",
)

PROMPT_VISIBLE_SKILLS = CUSTOM_SKILLS + SUPERPOWERS_SKILLS


def _run(command: list[str], cwd: Path, timeout: int = 30) -> dict[str, object]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _skill_visibility(prompt_input: str) -> dict[str, object]:
    visible = [skill for skill in PROMPT_VISIBLE_SKILLS if skill in prompt_input]
    missing = [skill for skill in PROMPT_VISIBLE_SKILLS if skill not in prompt_input]
    return {
        "checked": bool(prompt_input),
        "visible": visible,
        "missing": missing,
        "ok": bool(prompt_input) and not missing,
    }


def build_report(
    root: str | Path = ".",
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    user_home: str | Path | None = None,
    check_prompt_input: bool = False,
) -> dict[str, object]:
    root_path = Path(root).resolve()
    live_install = build_live_install_report(root_path, codex_home, agents_home, user_home)
    local_doctor = build_doctor_report(root_path, codex_home, agents_home, user_home)
    codex_path = shutil.which("codex")
    codex_version = _run(["codex", "--version"], root_path) if codex_path else {
        "ok": False,
        "command": ["codex", "--version"],
        "returncode": None,
        "stdout": "",
        "stderr": "codex executable not found on PATH",
    }
    prompt_input = {"ok": None, "skipped": True, "reason": "pass --check-prompt-input to run codex debug prompt-input"}
    if check_prompt_input and codex_path:
        prompt_command = _run(["codex", "debug", "prompt-input", "List available skills briefly"], root_path, timeout=60)
        prompt_input = {
            "ok": prompt_command["ok"] and _skill_visibility(str(prompt_command["stdout"]))["ok"],
            "skipped": False,
            "command": prompt_command,
            "skills": _skill_visibility(str(prompt_command["stdout"])),
        }

    manual_agent_smoke = {
        "ok": None,
        "checklist": "docs/agent-collaboration-smoke.md",
        "reason": "multi-agent runtime actions remain manual/HITL; record agent ids and close evidence in the checklist",
    }
    ok = bool(live_install["ok"] and local_doctor["ok"] and codex_version["ok"])
    if check_prompt_input:
        ok = ok and bool(prompt_input["ok"])
    return {
        "ok": ok,
        "root": str(root_path),
        "checks": {
            "live_install": {
                "ok": live_install["ok"],
                "checked_count": live_install["checked_count"],
                "issue_count": len(live_install["issues"]),
            },
            "local_doctor": {
                "ok": local_doctor["ok"],
                "checks": local_doctor["checks"],
                "issue_count": len(local_doctor["issues"]),
            },
            "codex_cli": {
                "ok": bool(codex_path and codex_version["ok"]),
                "path": codex_path or "",
                "version": codex_version["stdout"],
                "stderr": codex_version["stderr"],
            },
            "prompt_input": prompt_input,
            "manual_agent_smoke": manual_agent_smoke,
        },
    }


def _markdown(report: dict[str, object]) -> str:
    checks = report["checks"]
    lines = [
        "# Codex Runtime Smoke",
        "",
        f"- Root: `{report['root']}`",
        f"- Overall: `{'OK' if report['ok'] else 'ISSUES'}`",
        "",
        "| Check | Result | Evidence |",
        "|---|---|---|",
        "| live_install | "
        f"{'OK' if checks['live_install']['ok'] else 'ISSUES'} | "
        f"{checks['live_install']['checked_count']} files checked, {checks['live_install']['issue_count']} issues |",
        "| local_doctor | "
        f"{'OK' if checks['local_doctor']['ok'] else 'ISSUES'} | "
        f"{checks['local_doctor']['issue_count']} issues |",
        "| codex_cli | "
        f"{'OK' if checks['codex_cli']['ok'] else 'ISSUES'} | "
        f"{checks['codex_cli']['version'] or checks['codex_cli']['stderr']} |",
    ]
    prompt = checks["prompt_input"]
    if prompt.get("skipped"):
        lines.append("| prompt_input | SKIPPED | pass `--check-prompt-input` to verify model-visible skills |")
    else:
        skills = prompt["skills"]
        lines.append(
            "| prompt_input | "
            f"{'OK' if prompt['ok'] else 'ISSUES'} | "
            f"{len(skills['visible'])} visible, {len(skills['missing'])} missing |"
        )
    lines.append("| manual_agent_smoke | MANUAL | `docs/agent-collaboration-smoke.md` |")
    lines.append("")
    return "\n".join(lines)


def _print_text(report: dict[str, object]) -> None:
    print("Codex runtime smoke OK" if report["ok"] else "Codex runtime smoke found issues")
    for name, check in report["checks"].items():
        if name == "manual_agent_smoke":
            print(f"- {name}: MANUAL ({check['checklist']})")
        elif name == "prompt_input" and check.get("skipped"):
            print(f"- {name}: SKIPPED ({check['reason']})")
        else:
            print(f"- {name}: {'OK' if check.get('ok') else 'ISSUES'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Codex runtime smoke checks.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--codex-home", default=None, help="Codex home. Default: ~/.codex")
    parser.add_argument("--agents-home", default=None, help="Agents home. Default: ~/.agents")
    parser.add_argument("--user-home", default=None, help="User home for plugin/native-host path checks. Default: ~")
    parser.add_argument("--check-prompt-input", action="store_true", help="Run codex debug prompt-input to verify skill visibility.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report.")
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown summary.")
    args = parser.parse_args(argv)

    report = build_report(args.root, args.codex_home, args.agents_home, args.user_home, args.check_prompt_input)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.markdown:
        print(_markdown(report))
    else:
        _print_text(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
