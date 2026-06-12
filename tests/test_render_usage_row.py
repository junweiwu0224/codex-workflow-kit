import re

import pytest

from scripts.render_usage_row import build_baseline_row, build_pilot_row, build_trial_row, main


def test_build_baseline_row_uses_defaults():
    row = build_baseline_row(date="2026-06-07")

    assert row == (
        "| 2026-06-07 | Baseline context pack install | M | repo-onboarding, context pack verifier | "
        "`python3 scripts/verify_context_pack.py` -> Context pack OK | "
        "Repo has portable commands/testing/quality docs; no hooks enabled yet | "
        "Collect 3-5 real task records before promotion |"
    )


def test_build_baseline_row_escapes_markdown_cells():
    row = build_baseline_row(
        date="2026-06-07",
        task="Baseline | context pack",
        effect="Docs ready\nNo hooks",
    )

    assert "Baseline \\| context pack" in row
    assert "Docs ready No hooks" in row


def test_build_pilot_row_uses_defaults():
    row = build_pilot_row(date="2026-06-07", pilot="subagents")

    assert row == (
        "| 2026-06-07 | subagents pilot | L | subagents, pilot evidence | "
        "`docs/subagents.md` prompt cards reviewed | "
        "Pilot signal captured; no default automation enabled | "
        "Keep documented; promote only after repeated positive signals |"
    )


def test_build_pilot_row_escapes_markdown_cells():
    row = build_pilot_row(
        date="2026-06-07",
        pilot="mcp | graph",
        evidence="A\nB",
    )

    assert "mcp \\| graph pilot" in row
    assert "`A B`" in row


def test_main_prints_baseline_row_with_today(capsys):
    exit_code = main(["baseline"])
    output = capsys.readouterr().out.strip()

    assert exit_code == 0
    assert re.match(r"^\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \| Baseline context pack install \|", output)
    assert "`python3 scripts/verify_context_pack.py` -> Context pack OK" in output


def test_main_prints_baseline_row_with_overrides(capsys):
    exit_code = main(
        [
            "baseline",
            "--date",
            "2026-06-07",
            "--verification-command",
            ".venv/bin/python scripts/verify_context_pack.py",
            "--verification-result",
            "Context pack OK",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-07 | Baseline context pack install | M |" in output
    assert "`.venv/bin/python scripts/verify_context_pack.py` -> Context pack OK" in output


def test_main_prints_pilot_row_with_defaults(capsys):
    exit_code = main(["pilot", "--pilot", "observability", "--date", "2026-06-07"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-07 | observability pilot | L | observability, pilot evidence |" in output
    assert "`docs/observability.md` candidate reviewed" in output
    assert "Pilot signal captured; no default automation enabled" in output


def test_main_prints_mcp_pilot_row_with_context_defaults(capsys):
    exit_code = main(["pilot", "--pilot", "mcp-code-graph", "--date", "2026-06-07"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-07 | mcp-code-graph pilot | L | MCP/code graph, rg baseline |" in output
    assert "`docs/mcp-pilot.md` baseline compared" in output


def test_main_prints_v3_1_pilot_rows_with_defaults(capsys):
    cases = {
        "codegraph": ("code graph pilot, rg baseline", "`docs/codegraph-pilot.md` baseline compared"),
        "memory-recall": (
            "memory/recall pilot, repo docs baseline",
            "`docs/memory-recall-pilot.md` provenance reviewed",
        ),
        "plugin-mcp-trust": (
            "skill-plugin-intake-review, external component audit",
            "`docs/external-component-intake.md` trust review recorded",
        ),
        "agent-config-lint": (
            "agent config lint pilot, read-only hygiene",
            "`docs/quality-gates.md` agent config lint candidate recorded",
        ),
        "domain-pilot": (
            "domain skill boundary, repo-local checklist",
            "`docs/external-component-intake.md` domain boundary reviewed",
        ),
        "external-component-intake": (
            "skill/plugin intake review, read-only audit",
            "`scripts/audit_external_component.py` decision recorded",
        ),
        "subagent-contract": (
            "subagent handoff/return contract, lifecycle evidence",
            "`docs/subagents.md` Handoff Envelope and Return Envelope used",
        ),
        "agent-lifecycle-ledger": (
            "subagent lifecycle ledger, close evidence",
            "`docs/subagents.md` Lifecycle Ledger recorded",
        ),
        "agent-eval-evidence": (
            "agent eval evidence, trajectory replay checklist",
            "`docs/subagents.md` Return Envelope evidence paths reviewed",
        ),
    }

    for pilot, (tools, evidence) in cases.items():
        exit_code = main(["pilot", "--pilot", pilot, "--date", "2026-06-07"])
        output = capsys.readouterr().out

        assert exit_code == 0
        assert f"| 2026-06-07 | {pilot} pilot | L | {tools} |" in output
        assert evidence in output


def test_main_prints_pilot_row_with_overrides(capsys):
    exit_code = main(
        [
            "pilot",
            "--pilot",
            "mcp-code-graph",
            "--date",
            "2026-06-07",
            "--level",
            "M",
            "--tools",
            "deepcontext-mcp, rg baseline",
            "--evidence",
            "rg baseline compared",
            "--effect",
            "No improvement yet",
            "--next-action",
            "Keep as candidate",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-07 | mcp-code-graph pilot | M | deepcontext-mcp, rg baseline |" in output
    assert "`rg baseline compared`" in output
    assert "Keep as candidate" in output


def test_build_trial_row_records_effect_and_friction():
    row = build_trial_row(
        date="2026-06-13",
        task="Runtime smoke evidence",
        level="M",
        tools="codex_runtime_smoke, release-readiness",
        verification="`python3 scripts/codex_runtime_smoke.py` -> OK",
        effect="Caught live install drift before release",
        friction="Prompt-input remains optional",
        decision="Keep runtime smoke separate from package verifier",
    )

    assert row == (
        "| 2026-06-13 | Runtime smoke evidence | M | codex_runtime_smoke, release-readiness | "
        "`python3 scripts/codex_runtime_smoke.py` -> OK | Caught live install drift before release | "
        "Prompt-input remains optional | Keep runtime smoke separate from package verifier |"
    )


def test_main_prints_trial_row(capsys):
    exit_code = main(
        [
            "trial",
            "--date",
            "2026-06-13",
            "--task",
            "Usage evidence loop",
            "--level",
            "L",
            "--tools",
            "completion-review, verify_toolkit",
            "--verification",
            "`python3 scripts/verify_toolkit.py` -> Workflow toolkit OK",
            "--effect",
            "Evidence table made completion auditable",
            "--friction",
            "Manual table writing was repetitive",
            "--decision",
            "Promote trial row helper",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-13 | Usage evidence loop | L | completion-review, verify_toolkit |" in output
    assert "Manual table writing was repetitive" in output


def test_main_prints_trial_row_from_preset(capsys):
    exit_code = main(["trial", "--preset", "trial-preset-helper", "--date", "2026-06-13"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-13 | Trial row preset helper | M | render_usage_row --preset, targeted pytest |" in output
    assert "Common usage rows no longer require repeating all eight trial fields" in output
    assert "do not auto-append docs" in output


def test_main_allows_trial_preset_overrides(capsys):
    exit_code = main(
        [
            "trial",
            "--preset",
            "release-readiness-closeout",
            "--date",
            "2026-06-13",
            "--level",
            "XL",
            "--decision",
            "Keep release drill; do not add background automation",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| 2026-06-13 | Release-readiness closeout drill | XL |" in output
    assert "Keep release drill; do not add background automation" in output


def test_main_requires_complete_trial_fields_without_preset(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["trial", "--date", "2026-06-13", "--task", "Incomplete"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--level" in captured.err
    assert "--decision" in captured.err
