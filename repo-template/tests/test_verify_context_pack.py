from pathlib import Path

from scripts.verify_context_pack import (
    REQUIRED_FILES,
    ContextPackIssue,
    build_report,
    check_context_pack,
    main,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_context_pack(root: Path) -> None:
    for relative in REQUIRED_FILES:
        _write(root / relative, f"# {relative}\n")

    _write(root / "AGENTS.md", "架构文档：`docs/architecture.md`。\n")
    _write(root / "docs/architecture.md", "# Architecture\n")
    _write(root / "docs/commands.md", ".venv/bin/python -m pytest -q\n")
    _write(root / "docs/testing.md", ".venv/bin/python -m pytest tests/test_example.py -q\n")
    _write(root / "docs/quality-gates.md", ".venv/bin/python scripts/verify_context_pack.py\n")
    _write(
        root / "docs/codex-usage.md",
        "\n".join(
            [
                "| 2026-06-07 | baseline |",
                "## 周期复盘",
                "## 阶段复盘模板",
            ]
        ),
    )


def test_check_context_pack_accepts_minimal_valid_pack(tmp_path):
    _minimal_context_pack(tmp_path)

    assert check_context_pack(tmp_path) == []


def test_check_context_pack_reports_missing_required_files(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/testing.md").unlink()

    issues = check_context_pack(tmp_path)

    assert ContextPackIssue(
        severity="error",
        code="missing-required-file",
        path="docs/testing.md",
        message="Required context pack file is missing.",
    ) in issues


def test_check_context_pack_requires_architecture_document(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/architecture.md").unlink()

    issues = check_context_pack(tmp_path)

    assert ContextPackIssue(
        severity="error",
        code="missing-required-file",
        path="docs/architecture.md",
        message="Required context pack file is missing.",
    ) in issues


def test_check_context_pack_requires_observability_document(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/observability.md").unlink(missing_ok=True)

    issues = check_context_pack(tmp_path)

    assert ContextPackIssue(
        severity="error",
        code="missing-required-file",
        path="docs/observability.md",
        message="Required context pack file is missing.",
    ) in issues


def test_check_context_pack_requires_mcp_pilot_document(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/mcp-pilot.md").unlink(missing_ok=True)

    issues = check_context_pack(tmp_path)

    assert ContextPackIssue(
        severity="error",
        code="missing-required-file",
        path="docs/mcp-pilot.md",
        message="Required context pack file is missing.",
    ) in issues


def test_check_context_pack_flags_architecture_reference_mismatch(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/architecture.md").unlink()
    _write(tmp_path / "docs/ARCHITECTURE.md", "# Architecture\n")
    _write(tmp_path / "AGENTS.md", "架构文档：`docs/architecture.md`。\n")

    issues = check_context_pack(tmp_path)

    assert any(issue.code == "missing-architecture-reference" for issue in issues)


def test_check_context_pack_flags_bare_python_commands(tmp_path):
    _minimal_context_pack(tmp_path)
    _write(tmp_path / "docs/commands.md", "python scripts/verify_context_pack.py\n")

    issues = check_context_pack(tmp_path)

    assert any(issue.code == "bare-python-command" for issue in issues)


def test_check_context_pack_allows_historical_failure_in_usage_log(tmp_path):
    _minimal_context_pack(tmp_path)
    _write(
        tmp_path / "docs/codex-usage.md",
        "\n".join(
            [
                "曾经运行 `python scripts/verify_context_pack.py` 失败，后来改用 `.venv/bin/python`。",
                "## 周期复盘",
                "## 阶段复盘模板",
            ]
        ),
    )

    issues = check_context_pack(tmp_path)

    assert not any(issue.code == "bare-python-command" for issue in issues)


def test_check_context_pack_requires_usage_review_mechanism(tmp_path):
    _minimal_context_pack(tmp_path)
    _write(tmp_path / "docs/codex-usage.md", "| 2026-06-07 | baseline |\n")

    issues = check_context_pack(tmp_path)

    assert ContextPackIssue(
        severity="error",
        code="missing-usage-review",
        path="docs/codex-usage.md",
        message="docs/codex-usage.md must include periodic or stage review guidance.",
    ) in issues


def test_check_context_pack_flags_secret_patterns(tmp_path):
    _minimal_context_pack(tmp_path)
    _write(tmp_path / "docs/commands.md", "OPENAI_API_KEY=sk-thisisnotarealkeybutshouldbeflagged\n")

    issues = check_context_pack(tmp_path)

    assert any(issue.code == "sensitive-pattern" for issue in issues)


def test_check_context_pack_allows_documented_local_urls(tmp_path):
    _minimal_context_pack(tmp_path)
    _write(tmp_path / "docs/testing.md", "PLAYWRIGHT_BASE_URL=http://127.0.0.1:8001\n")

    issues = check_context_pack(tmp_path)

    assert not any(issue.code == "sensitive-pattern" for issue in issues)


def test_build_report_counts_errors_and_warnings(tmp_path):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/testing.md").unlink()

    report = build_report(tmp_path)

    assert report["ok"] is False
    assert report["error_count"] == 1
    assert report["warning_count"] == 0
    assert report["issues"][0]["path"] == "docs/testing.md"


def test_main_returns_nonzero_for_invalid_pack(tmp_path, capsys):
    _minimal_context_pack(tmp_path)
    (tmp_path / "docs/testing.md").unlink()

    exit_code = main([str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "missing-required-file" in output


def test_main_returns_zero_for_valid_pack(tmp_path, capsys):
    _minimal_context_pack(tmp_path)

    exit_code = main([str(tmp_path)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Context pack OK" in output
