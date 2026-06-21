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


def test_check_toolkit_requires_v3_1_files(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    for relative in (
        "docs/V3.1-ADOPTION-EVIDENCE.md",
        "docs/V3.1-SKILL-POLISH-BENCHMARK.md",
        "docs/V3.1-SKILL-POLISH-BENCHMARK.json",
        "docs/V3.1-AGENT-RESEARCH-20.md",
        "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md",
        "docs/V3.1-AGENT-CONTRACT-BENCHMARK.json",
        "docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md",
        "docs/agent-collaboration-smoke.md",
        "docs/codex-usage.md",
        "docs/external-component-intake.md",
        "scripts/audit_skill_contracts.py",
        "scripts/audit_external_component.py",
        "scripts/codex_runtime_smoke.py",
        "scripts/verify_reverse_ready.py",
        "scripts/benchmark_skill_polish.py",
        "scripts/benchmark_agent_contract.py",
        "tests/test_audit_skill_contracts.py",
        "tests/test_codex_runtime_smoke.py",
        "tests/test_verify_reverse_ready.py",
        "tests/test_benchmark_agent_contract.py",
        "tests/test_audit_external_component.py",
        "repo-template/docs/codegraph-pilot.md",
        "repo-template/docs/memory-recall-pilot.md",
        "skills/skill-plugin-intake-review/SKILL.md",
        "skills/release-readiness/SKILL.md",
        "skills/spec-kit-xl/references/spec-template.md",
    ):
        (shadow / relative).unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    missing_paths = {issue.path for issue in issues if issue.code in {"missing-required-file", "missing-skill"}}
    assert "docs/V3.1-ADOPTION-EVIDENCE.md" in missing_paths
    assert "docs/V3.1-SKILL-POLISH-BENCHMARK.md" in missing_paths
    assert "docs/V3.1-SKILL-POLISH-BENCHMARK.json" in missing_paths
    assert "docs/V3.1-AGENT-RESEARCH-20.md" in missing_paths
    assert "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md" in missing_paths
    assert "docs/V3.1-AGENT-CONTRACT-BENCHMARK.json" in missing_paths
    assert "docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md" in missing_paths
    assert "docs/agent-collaboration-smoke.md" in missing_paths
    assert "docs/codex-usage.md" in missing_paths
    assert "docs/external-component-intake.md" in missing_paths
    assert "scripts/audit_skill_contracts.py" in missing_paths
    assert "scripts/audit_external_component.py" in missing_paths
    assert "scripts/codex_runtime_smoke.py" in missing_paths
    assert "scripts/verify_reverse_ready.py" in missing_paths
    assert "scripts/benchmark_skill_polish.py" in missing_paths
    assert "scripts/benchmark_agent_contract.py" in missing_paths
    assert "tests/test_audit_skill_contracts.py" in missing_paths
    assert "tests/test_codex_runtime_smoke.py" in missing_paths
    assert "tests/test_verify_reverse_ready.py" in missing_paths
    assert "tests/test_benchmark_agent_contract.py" in missing_paths
    assert "tests/test_audit_external_component.py" in missing_paths
    assert "repo-template/docs/codegraph-pilot.md" in missing_paths
    assert "repo-template/docs/memory-recall-pilot.md" in missing_paths
    assert "skills/skill-plugin-intake-review/SKILL.md" in missing_paths
    assert "skills/release-readiness/SKILL.md" in missing_paths
    assert "skills/spec-kit-xl/references/spec-template.md" in missing_paths


def test_check_toolkit_requires_v3_1_external_intake_reject_lines(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    intake = shadow / "docs/external-component-intake.md"
    intake.write_text(
        intake.read_text(encoding="utf-8")
        .replace("默认 MCP server", "MCP server")
        .replace("curl-to-shell", "curl shell")
        .replace("GPL/unknown license", "unclear license"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "external-intake-missing-term" for issue in issues)


def test_check_toolkit_requires_agent_self_diagnosis_terms(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    debug_loop = shadow / "skills/debug-loop/SKILL.md"
    completion_review = shadow / "skills/completion-review/SKILL.md"
    debug_loop.write_text(debug_loop.read_text(encoding="utf-8").replace("goal drift", "goal mismatch"), encoding="utf-8")
    completion_review.write_text(
        completion_review.read_text(encoding="utf-8").replace("subagent lifecycle", "subagent cleanup"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "debug-loop-missing-agent-self-diagnosis" for issue in issues)
    assert any(issue.code == "completion-review-missing-agent-self-diagnosis" for issue in issues)


def test_check_toolkit_requires_skill_polish_contracts(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    replacements = {
        "skills/debug-loop/SKILL.md": ("deterministic loop", "stable loop"),
        "skills/completion-review/SKILL.md": ("Artifact / Release Evidence Gate", "Evidence Gate"),
        "skills/frontend-qa/SKILL.md": ("Reduced motion", "Motion"),
        "skills/decision-record/SKILL.md": ("Completion Conditions", "Done Conditions"),
        "skills/repo-onboarding/SKILL.md": ("minimal context pack", "context pack"),
        "skills/spec-kit-xl/SKILL.md": ("references/spec-template.md", "assets/spec-template.md"),
        "skills/release-readiness/SKILL.md": ("install drill", "install check"),
    }
    for relative, (old, new) in replacements.items():
        path = shadow / relative
        path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    issues = check_toolkit(shadow)
    codes = {issue.code for issue in issues}

    assert "debug-loop-missing-feedback-loop-polish" in codes
    assert "completion-review-missing-artifact-gate" in codes
    assert "frontend-qa-missing-accessibility-polish" in codes
    assert "decision-record-missing-output-contract" in codes
    assert "repo-onboarding-missing-minimal-context-pack" in codes
    assert "spec-kit-xl-missing-progressive-disclosure" in codes
    assert "release-readiness-missing-contract" in codes


def test_check_toolkit_requires_spec_template_in_references(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    old_template = shadow / "skills/spec-kit-xl/assets/spec-template.md"
    old_template.parent.mkdir(parents=True, exist_ok=True)
    old_template.write_text("# Old template\n", encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "spec-template-in-assets" for issue in issues)


def test_check_toolkit_requires_frontend_browser_routing_guidance(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    frontend_qa = shadow / "skills/frontend-qa/SKILL.md"
    global_agents = shadow / "global/AGENTS.md"
    frontend_qa.write_text(
        frontend_qa.read_text(encoding="utf-8")
        .replace("in-app Browser", "browser")
        .replace("不要静默降级到 Chrome", "可以降级到 Chrome"),
        encoding="utf-8",
    )
    global_agents.write_text(
        global_agents.read_text(encoding="utf-8").replace("in-app Browser", "browser"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "frontend-qa-missing-browser-routing" for issue in issues)
    assert any(issue.code == "global-agents-missing-browser-routing" for issue in issues)


def test_check_toolkit_requires_junwei_frontend_browser_video_contracts(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    frontend = shadow / "skills/junwei-frontend-design/SKILL.md"
    browser = shadow / "skills/junwei-browser-automation/SKILL.md"
    video = shadow / "skills/junwei-product-demo-video/SKILL.md"
    evidence = shadow / "docs/V3.2-FRONTEND-BROWSER-VIDEO-WORKFLOW.md"
    global_agents = shadow / "global/AGENTS.md"

    frontend.write_text(
        frontend.read_text(encoding="utf-8").replace("Avoid generic AI fingerprints", "Avoid generic output"),
        encoding="utf-8",
    )
    browser.write_text(
        browser.read_text(encoding="utf-8").replace("not a default install", "not default"),
        encoding="utf-8",
    )
    video.write_text(
        video.read_text(encoding="utf-8").replace("not a default global install", "not default"),
        encoding="utf-8",
    )
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("No-Conflict Matrix", "Conflict Notes"),
        encoding="utf-8",
    )
    global_agents.write_text(
        global_agents.read_text(encoding="utf-8").replace("DigitalSamba toolkit", "video toolkit"),
        encoding="utf-8",
    )

    codes = {issue.code for issue in check_toolkit(shadow)}

    assert "junwei-frontend-design-missing-contract" in codes
    assert "junwei-browser-automation-missing-contract" in codes
    assert "junwei-product-demo-video-missing-contract" in codes
    assert "v3-2-frontend-workflow-missing-term" in codes
    assert "global-agents-missing-junwei-workflow-route" in codes


def test_check_toolkit_rejects_reverse_routing_to_missing_target(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    routing = shadow / "reverse-skill/skills/routing.md"
    routing.write_text(
        routing.read_text(encoding="utf-8").replace(
            "`apk-reverse/SKILL.md`",
            "`game-security/SKILL.md`",
            1,
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "reverse-routing-missing-target" for issue in issues)


def test_check_toolkit_requires_reverse_skill_docs_to_list_supported_modules(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    readme = shadow / "reverse-skill/README.md"
    overview = shadow / "reverse-skill/OVERVIEW.md"
    readme.write_text(readme.read_text(encoding="utf-8").replace("api-security", "api security"), encoding="utf-8")
    overview.write_text(
        overview.read_text(encoding="utf-8").replace("malware-analysis", "malware analysis"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "reverse-skill-doc-missing-skill-term"
        and issue.path == "reverse-skill/README.md"
        for issue in issues
    )
    assert any(
        issue.code == "reverse-skill-doc-missing-skill-term"
        and issue.path == "reverse-skill/OVERVIEW.md"
        for issue in issues
    )


def test_check_toolkit_rejects_hardcoded_browser_plugin_paths(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    frontend_qa = shadow / "skills/frontend-qa/SKILL.md"
    hardcoded_path = (
        "/" + "Users" + "/" + "junwei" + "/" + ".codex/plugins/cache/openai-bundled/browser/"
        "26.602.40724/scripts/browser-client.mjs"
    )
    frontend_qa.write_text(
        frontend_qa.read_text(encoding="utf-8")
        + f"\n示例：{hardcoded_path}\n",
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "hardcoded-browser-plugin-path" for issue in issues)


def test_check_toolkit_requires_v2_2_closeout_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8")
        .replace("V2.2 Closeout", "Closeout")
        .replace("scripts/verify_live_install.py", "scripts/live_check.py")
        .replace("9 skills verified", "skills verified"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


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


def test_check_toolkit_requires_agent_contract_guidance(tmp_path):
    replacements = (
        ("Handoff Envelope", "Dispatch Envelope"),
        ("Return Envelope", "Result Envelope"),
        ("History/Input Filter", "Context Filter"),
        ("Command/Tool Risk Policy", "Tool Policy"),
        ("Step Budget / Stop Condition", "Step Limits"),
        ("Lifecycle Ledger", "Lifecycle Log"),
        ("No-Dispatch Decision", "No Dispatch Reason"),
    )
    targets = ("global/AGENTS.md", "repo-template/AGENTS.md", "repo-template/docs/subagents.md")
    for index, (relative, (old, new)) in enumerate((relative, replacement) for relative in targets for replacement in replacements):
        case_root = tmp_path / f"agent-contract-case-{index}"
        case_root.mkdir()
        shadow = _clean_package_copy(case_root)
        target = shadow / relative
        target.write_text(target.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

        issues = check_toolkit(shadow)

        assert any(
            issue.code == "subagents-missing-agent-contract-guidance" and issue.path == relative
            for issue in issues
        )


def test_check_toolkit_requires_agent_research_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    research = shadow / "docs/V3.1-AGENT-RESEARCH-20.md"
    research.write_text(
        research.read_text(encoding="utf-8")
        .replace("20 real git checkouts", "local checkouts")
        .replace("openai/openai-agents-python", "openai agents")
        .replace("Why This Does Not Conflict", "Compatibility"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "agent-research-missing-term" for issue in issues)


def test_check_toolkit_requires_agent_contract_benchmark_terms(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    benchmark = shadow / "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md"
    benchmark.write_text(
        benchmark.read_text(encoding="utf-8")
        .replace("pre-agent-contract", "pre")
        .replace("post-agent-contract", "post")
        .replace("Measured improvement", "Improvement"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "agent-contract-benchmark-missing-term" for issue in issues)


def test_check_toolkit_requires_agent_collaboration_smoke_contract(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    smoke = shadow / "docs/agent-collaboration-smoke.md"
    smoke.write_text(
        smoke.read_text(encoding="utf-8")
        .replace("Read-Only Dual Explorer", "Dual Explorer")
        .replace("close_agent previous_status", "close status"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "agent-collaboration-smoke-missing-term" for issue in issues)


def test_check_toolkit_requires_real_usage_trial_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    usage = shadow / "docs/codex-usage.md"
    usage.write_text(
        usage.read_text(encoding="utf-8")
        .replace("Stage Review: 4 Real V3.1 Trials", "Stage Review")
        .replace("Package verifier coverage for real usage evidence", "Verifier evidence"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "codex-usage-missing-term" for issue in issues)


def test_check_toolkit_requires_closeout_trial_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    usage = shadow / "docs/codex-usage.md"
    usage.write_text(
        usage.read_text(encoding="utf-8")
        .replace("Closeout Trial Records", "Closeout Records")
        .replace("Trial row preset helper", "Usage preset helper")
        .replace("do not auto-append docs", "do not write docs"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "codex-usage-missing-term" for issue in issues)


def test_check_toolkit_runs_skill_contract_audit(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    spec = shadow / "skills/spec-kit-xl/SKILL.md"
    spec.write_text(
        spec.read_text(encoding="utf-8")
        .replace("## 不要做", "## 边界说明")
        .replace("不要把本 skill 当成普通 M 级任务的必经流程。", "只用于正式规格。"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "skill-contract-audit-failed" for issue in issues)


def test_check_toolkit_requires_proactive_subagent_guidance(tmp_path):
    cases = (
        ("subagent suitability check", "parallel suitability check"),
        ("当前运行时或工具权限允许", "长期授权"),
        ("显式授权", "长期授权"),
        ("tool permission constraint", "tool unavailable"),
        ("2 个以上", "多个"),
        ("不使用时", "跳过时"),
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


def test_check_toolkit_rejects_unconditional_subagent_dispatch_guidance(tmp_path):
    forbidden_phrases = (
        "不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或 dispatch",
        "不要因为当前对话没有再次要求并行就跳过 suitability check 或安全 dispatch",
        "不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或安全 dispatch",
    )
    targets = ("global/AGENTS.md", "repo-template/AGENTS.md", "repo-template/docs/subagents.md")
    for index, (relative, phrase) in enumerate(
        (relative, phrase) for relative in targets for phrase in forbidden_phrases
    ):
        case_root = tmp_path / f"unconditional-dispatch-case-{index}"
        case_root.mkdir()
        shadow = _clean_package_copy(case_root)
        target = shadow / relative
        text = target.read_text(encoding="utf-8")
        if phrase not in text:
            text += f"\n- {phrase}\n"
        target.write_text(text, encoding="utf-8")

        issues = check_toolkit(shadow)

        assert any(
            issue.code == "subagents-unconditional-dispatch-guidance" and issue.path == relative
            for issue in issues
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


def test_check_toolkit_requires_v2_adoption_plan(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file"
        and issue.path == "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md"
        for issue in issues
    )


def test_check_toolkit_requires_v2_1_plan(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md").unlink(
        missing_ok=True
    )

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file"
        and issue.path == "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md"
        for issue in issues
    )


def test_check_toolkit_requires_v2_adoption_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "docs/V2-ADOPTION-EVIDENCE.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "missing-required-file"
        and issue.path == "docs/V2-ADOPTION-EVIDENCE.md"
        for issue in issues
    )


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


def test_check_toolkit_flags_incomplete_v2_adoption_plan(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    _write(shadow / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md", "# Plan\n")

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-plan-missing-term" for issue in issues)


def test_check_toolkit_flags_incomplete_v2_1_plan(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    _write(
        shadow / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md",
        "# Plan\n",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-1-plan-missing-term" for issue in issues)


def test_check_toolkit_flags_incomplete_v2_adoption_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    _write(shadow / "docs/V2-ADOPTION-EVIDENCE.md", "# Evidence\n")

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_v3_1_evidence_for_current_version(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "VERSION").write_text("2099.01.02\n", encoding="utf-8")
    evidence = shadow / "docs/V3.1-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "codex-workflow-kit-2026.06.12.tar.gz: OK",
            "codex-workflow-kit-2026.06.11.tar.gz: OK",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(
        issue.code == "v3-1-evidence-release-mismatch"
        and "codex-workflow-kit-2099.01.02.tar.gz: OK" in issue.message
        for issue in issues
    )


def test_check_toolkit_requires_repo_specific_calibration_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8")
        .replace("Repo-specific onboarding calibration", "Repo onboarding")
        .replace("manual-only test policy", "test policy"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_real_calibrated_repo_task_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "Align Go version docs with go.mod/CI",
            "Align docs",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_docs_only_repo_task_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "Guard README agent instruction append snippets",
            "Guard README snippets",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_manual_policy_task_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "Lock manual-only Go test policy with static docs test",
            "Lock policy",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_claude_path_validation_task_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "Validate CLAUDE.md repo paths with static docs test",
            "Validate CLAUDE paths",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_fail_fast_download_task_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace(
            "Make raw workflow downloads fail fast",
            "Make downloads safer",
        ),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_first_adoption_review(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("First Adoption Review", "Adoption Review"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_second_adoption_review(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("Second Adoption Review", "Adoption Review"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_final_v2_completion_audit(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(
        evidence.read_text(encoding="utf-8").replace("Final V2 Completion Audit", "Completion Audit"),
        encoding="utf-8",
    )

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


def test_check_toolkit_requires_v2_1_evidence(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    evidence = shadow / "docs/V2-ADOPTION-EVIDENCE.md"
    evidence.write_text(evidence.read_text(encoding="utf-8").replace("V2.1 Tooling Layer", "Tooling Layer"), encoding="utf-8")

    issues = check_toolkit(shadow)

    assert any(issue.code == "v2-evidence-missing-term" for issue in issues)


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
    _write(root / "reverse-skill/burp-mcp-full/build/libs/burp-mcp-full.jar", "generated jar\n")
    _write(root / "reverse-skill/reports/example.md", "generated report\n")

    manifest = build_manifest(root)

    assert "README.md" in manifest
    assert "MANIFEST.sha256" not in manifest
    assert ".pytest_cache" not in manifest
    assert ".DS_Store" not in manifest
    assert "releases/old.tar.gz" not in manifest
    assert "reverse-skill/burp-mcp-full/build/libs/burp-mcp-full.jar" not in manifest
    assert "reverse-skill/reports/example.md" not in manifest


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
