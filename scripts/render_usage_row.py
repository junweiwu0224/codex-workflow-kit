#!/usr/bin/env python3
"""Render reusable Codex usage rows for repo adoption evidence."""
from __future__ import annotations

import argparse
from datetime import date as date_type


def _markdown_cell(text: object) -> str:
    return str(text).replace("|", r"\|").replace("\n", " ")


PILOT_DEFAULTS = {
    "observability": {
        "tools": "observability, pilot evidence",
        "evidence": "`docs/observability.md` candidate reviewed",
    },
    "subagents": {
        "tools": "subagents, pilot evidence",
        "evidence": "`docs/subagents.md` prompt cards reviewed",
    },
    "mcp-code-graph": {
        "tools": "MCP/code graph, rg baseline",
        "evidence": "`docs/mcp-pilot.md` baseline compared",
    },
}


def build_baseline_row(
    *,
    date: str,
    task: str = "Baseline context pack install",
    level: str = "M",
    tools: str = "repo-onboarding, context pack verifier",
    verification_command: str = "python3 scripts/verify_context_pack.py",
    verification_result: str = "Context pack OK",
    effect: str = "Repo has portable commands/testing/quality docs; no hooks enabled yet",
    next_action: str = "Collect 3-5 real task records before promotion",
) -> str:
    verification = f"`{verification_command}` -> {verification_result}"
    cells = (date, task, level, tools, verification, effect, next_action)
    return "| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |"


def build_pilot_row(
    *,
    date: str,
    pilot: str,
    level: str = "L",
    tools: str | None = None,
    evidence: str | None = None,
    effect: str = "Pilot signal captured; no default automation enabled",
    next_action: str = "Keep documented; promote only after repeated positive signals",
) -> str:
    defaults = PILOT_DEFAULTS.get(pilot, PILOT_DEFAULTS["subagents"])
    task = f"{pilot} pilot"
    tools = tools if tools is not None else defaults["tools"]
    evidence = evidence if evidence is not None else defaults["evidence"]
    evidence_cell = evidence if "`" in evidence else f"`{evidence}`"
    cells = (date, task, level, tools, evidence_cell, effect, next_action)
    return "| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Codex usage table rows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    baseline = subparsers.add_parser("baseline", help="Render a baseline context pack install row.")
    baseline.add_argument("--date", default=date_type.today().isoformat(), help="Usage row date. Default: today.")
    baseline.add_argument("--task", default="Baseline context pack install", help="Task/scope cell.")
    baseline.add_argument("--level", default="M", help="Task level cell.")
    baseline.add_argument("--tools", default="repo-onboarding, context pack verifier", help="Workflow/tools cell.")
    baseline.add_argument(
        "--verification-command",
        default="python3 scripts/verify_context_pack.py",
        help="Verification command used after install.",
    )
    baseline.add_argument("--verification-result", default="Context pack OK", help="Verification result.")
    baseline.add_argument(
        "--effect",
        default="Repo has portable commands/testing/quality docs; no hooks enabled yet",
        help="Effect signal cell.",
    )
    baseline.add_argument(
        "--next-action",
        default="Collect 3-5 real task records before promotion",
        help="Next action cell.",
    )

    pilot = subparsers.add_parser("pilot", help="Render a V2.1 optional tooling pilot row.")
    pilot.add_argument("--date", default=date_type.today().isoformat(), help="Usage row date. Default: today.")
    pilot.add_argument("--pilot", required=True, help="Pilot name, for example observability, subagents, or mcp-code-graph.")
    pilot.add_argument("--level", default="L", help="Task level cell.")
    pilot.add_argument("--tools", help="Workflow/tools cell. Defaults are selected from --pilot when omitted.")
    pilot.add_argument("--evidence", help="Evidence cell. Defaults are selected from --pilot when omitted.")
    pilot.add_argument(
        "--effect",
        default="Pilot signal captured; no default automation enabled",
        help="Effect signal cell.",
    )
    pilot.add_argument(
        "--next-action",
        default="Keep documented; promote only after repeated positive signals",
        help="Next action cell.",
    )
    args = parser.parse_args(argv)

    if args.command == "baseline":
        print(
            build_baseline_row(
                date=args.date,
                task=args.task,
                level=args.level,
                tools=args.tools,
                verification_command=args.verification_command,
                verification_result=args.verification_result,
                effect=args.effect,
                next_action=args.next_action,
            )
        )
    elif args.command == "pilot":
        print(
            build_pilot_row(
                date=args.date,
                pilot=args.pilot,
                level=args.level,
                tools=args.tools,
                evidence=args.evidence,
                effect=args.effect,
                next_action=args.next_action,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
