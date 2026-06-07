from pathlib import Path
import shutil
import subprocess

from scripts.build_release import build_manifest, verify_archive
from scripts.verify_toolkit import EXPECTED_SKILLS, ToolkitIssue, build_report, check_toolkit, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean_package_copy(tmp_path: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    shadow = tmp_path / "kit"
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")
    shutil.copytree(root, shadow, ignore=ignore)
    return shadow


def test_check_toolkit_accepts_current_package(tmp_path):
    root = _clean_package_copy(tmp_path)

    assert check_toolkit(root) == []


def test_check_toolkit_reports_missing_skill(tmp_path):
    shadow = _clean_package_copy(tmp_path)

    (shadow / "skills/debug-loop/SKILL.md").unlink()

    issues = check_toolkit(shadow)

    assert ToolkitIssue(
        severity="error",
        code="missing-skill",
        path="skills/debug-loop/SKILL.md",
        message="Expected personal skill is missing.",
    ) in issues


def test_check_toolkit_requires_p0_specialist_skills(tmp_path):
    shadow = _clean_package_copy(tmp_path)

    for skill_name in ("security-review", "dependency-upgrade-review", "research-brief"):
        (shadow / f"skills/{skill_name}/SKILL.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    missing_skill_paths = {issue.path for issue in issues if issue.code == "missing-skill"}
    assert "skills/security-review/SKILL.md" in missing_skill_paths
    assert "skills/dependency-upgrade-review/SKILL.md" in missing_skill_paths
    assert "skills/research-brief/SKILL.md" in missing_skill_paths


def test_check_toolkit_requires_p0_specialist_skill_routes(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    global_agents = shadow / "global/AGENTS.md"
    global_agents.write_text(
        global_agents.read_text(encoding="utf-8")
        .replace("security-review", "security review")
        .replace("dependency-upgrade-review", "dependency upgrade review")
        .replace("research-brief", "research brief"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "global-agents-missing-p0-skill-route" for issue in issues)


def test_check_toolkit_requires_live_install_verifier(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "scripts/verify_live_install.py").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file" and issue.path == "scripts/verify_live_install.py"
        for issue in issues
    )


def test_check_toolkit_requires_live_install_docs(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    readme = shadow / "README.md"
    quickstart = shadow / "QUICKSTART.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace("scripts/verify_live_install.py", ""), encoding="utf-8")
    quickstart.write_text(
        quickstart.read_text(encoding="utf-8").replace("python3 scripts/verify_live_install.py", ""),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "readme-missing-term" for issue in issues)
    assert any(issue.code == "quickstart-missing-term" for issue in issues)


def test_check_toolkit_requires_skill_frontmatter_and_boundaries(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    skill = shadow / "skills/security-review/SKILL.md"
    skill.write_text(
        "---\n"
        "name: security-review\n"
        "description: Security review helper\n"
        "---\n"
        "\n"
        "# security-review\n"
        "\n"
        "No boundaries here.\n",
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "skill-description-invalid" for issue in issues)
    assert any(issue.code == "skill-missing-boundary-guidance" for issue in issues)


def test_check_toolkit_flags_removed_implementation_plan(tmp_path):
    shadow = _clean_package_copy(tmp_path)

    _write(shadow / "skills/implementation-plan/SKILL.md", "# removed\n")

    issues = check_toolkit(shadow)

    assert any(issue.code == "removed-skill-present" for issue in issues)


def test_check_toolkit_requires_reusable_quality_gate_guidance(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    quality_gates = shadow / "repo-template/docs/quality-gates.md"
    text = quality_gates.read_text(encoding="utf-8")
    quality_gates.write_text(
        text.replace("针对性单元测试", "单元测试").replace("按受影响范围选择", "每次全部运行"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "quality-gates-missing-targeted-guidance" for issue in issues)


def test_check_toolkit_requires_static_docs_contract_gate_guidance(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    quality_gates = shadow / "repo-template/docs/quality-gates.md"
    text = quality_gates.read_text(encoding="utf-8")
    quality_gates.write_text(
        text.replace("静态文档契约测试", "静态文档测试").replace("安装说明", "说明"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "quality-gates-missing-static-doc-contract-guidance" for issue in issues)


def test_check_toolkit_requires_usage_to_review_quality_gate_promotion(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    usage = shadow / "repo-template/docs/codex-usage.md"
    text = usage.read_text(encoding="utf-8")
    usage.write_text(text.replace("质量门禁", "验证规则"), encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "usage-missing-quality-gate-review" for issue in issues)


def test_check_toolkit_requires_v2_1_observability_docs(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "repo-template/docs/observability.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file" and issue.path == "repo-template/docs/observability.md"
        for issue in issues
    )


def test_check_toolkit_requires_v2_1_mcp_pilot_docs(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "repo-template/docs/mcp-pilot.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file" and issue.path == "repo-template/docs/mcp-pilot.md"
        for issue in issues
    )


def test_check_toolkit_requires_v2_1_observability_guidance(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    observability = shadow / "repo-template/docs/observability.md"
    observability.write_text("# Observability\nccusage\n", encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "observability-missing-guidance" for issue in issues)


def test_check_toolkit_requires_v2_1_mcp_pilot_guidance(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    mcp_pilot = shadow / "repo-template/docs/mcp-pilot.md"
    mcp_pilot.write_text("# MCP Pilot\ndeepcontext-mcp\n", encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "mcp-pilot-missing-guidance" for issue in issues)


def test_check_toolkit_requires_subagent_prompt_cards(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    subagents = shadow / "repo-template/docs/subagents.md"
    subagents.write_text(subagents.read_text(encoding="utf-8").replace("read-only code mapper", "code mapper"), encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "subagents-missing-prompt-cards" for issue in issues)


def test_check_toolkit_requires_proactive_subagent_guidance(tmp_path):
    cases = (
        ("subagent suitability check", "parallel suitability check"),
        ("长期授权", "临时授权"),
        ("没有再次说", "没有说"),
        ("2 个以上", "多个"),
        ("不使用时", "跳过时"),
        ("每 2-3 个切片", "阶段性"),
        ("只读 explorer", "reviewer"),
    )
    targets = ("global/AGENTS.md", "repo-template/AGENTS.md", "repo-template/docs/subagents.md")
    for index, (relative, (old, new)) in enumerate((relative, case) for relative in targets for case in cases):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        shadow = _clean_package_copy(case_root)
        target = shadow / relative
        target.write_text(target.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

        issues = check_toolkit(shadow)

        assert any(
            issue.code == "subagents-missing-proactive-guidance" and issue.path == relative for issue in issues
        )


def test_check_toolkit_requires_workflow_review_summary(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "WORKFLOW-REVIEW.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(issue.code == "missing-required-file" and issue.path == "WORKFLOW-REVIEW.md" for issue in issues)


def test_check_toolkit_requires_quickstart(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "QUICKSTART.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(issue.code == "missing-required-file" and issue.path == "QUICKSTART.md" for issue in issues)


def test_check_toolkit_flags_incomplete_workflow_review(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    _write(shadow / "WORKFLOW-REVIEW.md", "# Review\n")

    issues = check_toolkit(shadow)

    assert any(issue.code == "workflow-review-missing-term" for issue in issues)


def test_check_toolkit_flags_incomplete_quickstart(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    _write(shadow / "QUICKSTART.md", "# Quickstart\n")

    issues = check_toolkit(shadow)

    assert any(issue.code == "quickstart-missing-term" for issue in issues)


def test_build_report_counts_errors(tmp_path):
    report = build_report(tmp_path)

    assert report["ok"] is False
    assert report["error_count"] > 0


def test_main_returns_zero_for_current_package(tmp_path, capsys):
    root = _clean_package_copy(tmp_path)

    exit_code = main([str(root)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Workflow toolkit OK" in output


def test_release_manifest_excludes_generated_and_release_files(tmp_path):
    root = _clean_package_copy(tmp_path)
    (root / ".pytest_cache").mkdir()
    _write(root / ".pytest_cache/README.md", "cache\n")
    (root / "releases").mkdir(exist_ok=True)
    _write(root / "releases/old.tar.gz", "archive\n")
    _write(root / "docs/.DS_Store", "mac metadata\n")

    manifest = build_manifest(root)

    assert "README.md" in manifest
    assert "MANIFEST.sha256" not in manifest
    assert ".pytest_cache" not in manifest
    assert ".DS_Store" not in manifest
    assert "releases/old.tar.gz" not in manifest


def test_install_preflights_repo_conflicts_before_writing(tmp_path):
    root = _clean_package_copy(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    repo = tmp_path / "repo"
    repo.mkdir()
    _write(repo / "AGENTS.md", "# Existing project rules\n")

    result = subprocess.run(
        [
            str(root / "install.sh"),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--repo",
            str(repo),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "conflict:" in result.stdout
    assert not (codex_home / "AGENTS.md").exists()
    assert not (agents_home / "skills").exists()


def test_install_repo_only_skips_global_files(tmp_path):
    root = _clean_package_copy(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    repo = tmp_path / "repo"
    repo.mkdir()

    result = subprocess.run(
        [
            str(root / "install.sh"),
            "--repo-only",
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--repo",
            str(repo),
            "--dry-run",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "create:" in result.stdout
    assert str(repo / "AGENTS.md") in result.stdout
    assert str(codex_home / "AGENTS.md") not in result.stdout
    assert str(agents_home / "skills") not in result.stdout


def test_install_dry_run_lists_all_expected_skills(tmp_path):
    root = _clean_package_copy(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"

    result = subprocess.run(
        [
            str(root / "install.sh"),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--dry-run",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    for skill_name in EXPECTED_SKILLS:
        assert f"{agents_home}/skills/{skill_name}/SKILL.md" in result.stdout


def test_release_archive_checksum_matches_manifest(tmp_path):
    root = _clean_package_copy(tmp_path)
    archive = root / "releases" / f"codex-workflow-kit-{(root / 'VERSION').read_text(encoding='utf-8').strip()}.tar.gz"

    verify_archive(archive)
