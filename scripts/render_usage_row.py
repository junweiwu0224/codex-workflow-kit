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
    "codegraph": {
        "tools": "code graph pilot, rg baseline",
        "evidence": "`docs/codegraph-pilot.md` baseline compared",
    },
    "memory-recall": {
        "tools": "memory/recall pilot, repo docs baseline",
        "evidence": "`docs/memory-recall-pilot.md` provenance reviewed",
    },
    "plugin-mcp-trust": {
        "tools": "skill-plugin-intake-review, external component audit",
        "evidence": "`docs/external-component-intake.md` trust review recorded",
    },
    "agent-config-lint": {
        "tools": "agent config lint pilot, read-only hygiene",
        "evidence": "`docs/quality-gates.md` agent config lint candidate recorded",
    },
    "domain-pilot": {
        "tools": "domain skill boundary, repo-local checklist",
        "evidence": "`docs/external-component-intake.md` domain boundary reviewed",
    },
    "external-component-intake": {
        "tools": "skill/plugin intake review, read-only audit",
        "evidence": "`scripts/audit_external_component.py` decision recorded",
    },
    "subagent-contract": {
        "tools": "subagent handoff/return contract, lifecycle evidence",
        "evidence": "`docs/subagents.md` Handoff Envelope and Return Envelope used",
    },
    "agent-lifecycle-ledger": {
        "tools": "subagent lifecycle ledger, close evidence",
        "evidence": "`docs/subagents.md` Lifecycle Ledger recorded",
    },
    "agent-eval-evidence": {
        "tools": "agent eval evidence, trajectory replay checklist",
        "evidence": "`docs/subagents.md` Return Envelope evidence paths reviewed",
    },
}

TRIAL_PRESETS = {
    "release-evidence-alignment": {
        "task": "Release evidence version alignment",
        "level": "M",
        "tools": "rg audit, verify_toolkit, release-readiness",
        "verification": "`rg 2026.06.13` and `python3 scripts/verify_toolkit.py` -> stale release references found before build",
        "effect": "Caught old archive/version wording before publishing a new checksum",
        "friction": "Version strings still appear in multiple human docs",
        "decision": "Keep strict release evidence; bump VERSION for content changes instead of mutating old archives",
    },
    "trial-preset-helper": {
        "task": "Trial row preset helper",
        "level": "M",
        "tools": "render_usage_row --preset, targeted pytest",
        "verification": "`python3 -m pytest -p no:cacheprovider tests/test_render_usage_row.py -q` -> passed",
        "effect": "Common usage rows no longer require repeating all eight trial fields",
        "friction": "Presets can hide task-specific context if overused",
        "decision": "Keep render-only presets with explicit overrides; do not auto-append docs",
    },
    "package-doc-contract-alignment": {
        "task": "Package and docs contract alignment",
        "level": "M",
        "tools": "verify_toolkit, content contract tests",
        "verification": "`python3 scripts/verify_toolkit.py` -> Workflow toolkit OK",
        "effect": "Docs, helper CLI, usage evidence, and verifier terms stay aligned",
        "friction": "Every new durable term adds a small verifier maintenance cost",
        "decision": "Add only closeout/preset terms; avoid turning verifier into a full prose linter",
    },
    "release-readiness-closeout": {
        "task": "Release-readiness closeout drill",
        "level": "L",
        "tools": "release-readiness, build_release, checksum, unpack/install drill",
        "verification": "new archive checksum, unpack, install, live install, doctor, runtime smoke, skill audit, and context-pack drill -> OK",
        "effect": "Portable package claims are backed by archive and temporary-install evidence",
        "friction": "Full drill is slower than targeted tests but only needed for release artifacts",
        "decision": "Keep for toolkit releases; batch doc/code edits before final build",
    },
}


def _trial_preset_help() -> str:
    return ", ".join(sorted(TRIAL_PRESETS))


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


def build_trial_row(
    *,
    date: str,
    task: str,
    level: str,
    tools: str,
    verification: str,
    effect: str,
    friction: str,
    decision: str,
) -> str:
    cells = (date, task, level, tools, verification, effect, friction, decision)
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

    pilot = subparsers.add_parser("pilot", help="Render an optional tooling or V3.1 intake pilot row.")
    pilot.add_argument("--date", default=date_type.today().isoformat(), help="Usage row date. Default: today.")
    pilot.add_argument(
        "--pilot",
        required=True,
        help=(
            "Pilot name, for example observability, subagents, mcp-code-graph, codegraph, "
            "memory-recall, plugin-mcp-trust, agent-config-lint, domain-pilot, external-component-intake, "
            "subagent-contract, agent-lifecycle-ledger, or agent-eval-evidence."
        ),
    )
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
    trial = subparsers.add_parser("trial", help="Render a real M/L/XL workflow trial row.")
    trial.add_argument("--date", default=date_type.today().isoformat(), help="Usage row date. Default: today.")
    trial.add_argument(
        "--preset",
        choices=sorted(TRIAL_PRESETS),
        help=f"Optional real-task preset to reduce repeated flags. Choices: {_trial_preset_help()}.",
    )
    trial.add_argument("--task", help="Task/scope cell.")
    trial.add_argument("--level", choices=("M", "L", "XL"), help="Task level cell.")
    trial.add_argument("--tools", help="Workflow/tools used.")
    trial.add_argument("--verification", help="Verification evidence.")
    trial.add_argument("--effect", help="Positive efficiency or quality signal.")
    trial.add_argument("--friction", help="Observed friction or cost.")
    trial.add_argument("--decision", help="Keep/tighten/loosen/remove decision.")
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
    elif args.command == "trial":
        defaults = TRIAL_PRESETS.get(args.preset or "", {})
        missing = [
            field
            for field in ("task", "level", "tools", "verification", "effect", "friction", "decision")
            if getattr(args, field) is None and field not in defaults
        ]
        if missing:
            trial.error(
                "the following arguments are required without a preset or explicit override: "
                + ", ".join(f"--{field.replace('_', '-')}" for field in missing)
            )
        print(
            build_trial_row(
                date=args.date,
                task=args.task or defaults["task"],
                level=args.level or defaults["level"],
                tools=args.tools or defaults["tools"],
                verification=args.verification or defaults["verification"],
                effect=args.effect or defaults["effect"],
                friction=args.friction or defaults["friction"],
                decision=args.decision or defaults["decision"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
