from pathlib import Path
import json
import subprocess
import pytest

from scripts.audit_repo_adoption import AdoptionFinding, audit_repo, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_audit_repo_recommends_repo_only_for_empty_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    report = audit_repo(repo)

    assert report["recommendation"] == "repo-only-install"
    assert report["command"] == f"./install.sh --repo-only --repo {repo} --backup"
    assert report["finding_count"] == 0
    assert report["findings"] == []


def test_audit_repo_requires_manual_merge_when_agents_exists(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "AGENTS.md", "# Existing rules\n")

    report = audit_repo(repo)

    assert report["recommendation"] == "manual-merge"
    assert AdoptionFinding(
        severity="warning",
        code="existing-agents",
        path="AGENTS.md",
        message="Existing AGENTS.md should be merged manually instead of overwritten.",
    ).to_dict() in report["findings"]


def test_audit_repo_flags_case_equivalent_architecture_doc(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "docs/ARCHITECTURE.md", "# Architecture\n")

    report = audit_repo(repo)

    assert report["recommendation"] == "manual-merge"
    assert any(finding["code"] == "architecture-case-match" for finding in report["findings"])


def test_audit_repo_reports_existing_context_pack_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "docs/testing.md", "# Testing\n")
    _write(repo / "scripts/verify_context_pack.py", "# verifier\n")

    report = audit_repo(repo)

    assert report["recommendation"] == "manual-merge"
    assert any(finding["code"] == "existing-context-file" for finding in report["findings"])


def test_audit_repo_flags_dirty_git_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    _write(repo / "scratch.txt", "local change\n")

    report = audit_repo(repo)

    assert report["recommendation"] == "manual-merge"
    assert any(finding["code"] == "dirty-worktree" for finding in report["findings"])


def test_main_prints_readable_report(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()

    exit_code = main([str(repo)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Recommendation: repo-only-install" in output
    assert "./install.sh --repo-only --repo" in output


def test_main_prints_json_report(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()

    exit_code = main(["--json", str(repo)])
    output = capsys.readouterr().out
    reports = json.loads(output)

    assert exit_code == 0
    assert reports[0]["repo"] == str(repo.resolve())
    assert reports[0]["recommendation"] == "repo-only-install"
    assert reports[0]["findings"] == []


def test_main_prints_markdown_report(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()

    exit_code = main(["--markdown", str(repo)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "| Repo | Recommendation | Findings | Command |" in output
    assert f"| `{repo.resolve()}` | `repo-only-install` | 0 |" in output
    assert "`./install.sh --repo-only --repo" in output


def test_main_summarizes_repeated_markdown_findings(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "docs/testing.md", "# Testing\n")
    _write(repo / "docs/commands.md", "# Commands\n")

    exit_code = main(["--markdown", str(repo)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "`existing-context-file` x2" in output
    assert output.count("existing-context-file") == 1


def test_audit_repo_reports_v2_1_context_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "docs/observability.md", "# Observability\n")
    _write(repo / "docs/mcp-pilot.md", "# MCP Pilot\n")

    report = audit_repo(repo)

    assert report["recommendation"] == "manual-merge"
    assert any(finding["path"] == "docs/observability.md" for finding in report["findings"])
    assert any(finding["path"] == "docs/mcp-pilot.md" for finding in report["findings"])


def test_main_rejects_multiple_output_formats(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        main(["--json", "--markdown", str(repo)])

    assert exc_info.value.code == 2
