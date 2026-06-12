import re

from scripts.render_usage_row import build_baseline_row, build_pilot_row, main


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
