#!/usr/bin/env python3
"""Verify the portable Codex workflow kit package."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


EXPECTED_SKILLS = (
    "repo-onboarding",
    "spec-kit-xl",
    "debug-loop",
    "frontend-qa",
    "decision-record",
    "completion-review",
    "security-review",
    "dependency-upgrade-review",
    "research-brief",
    "skill-plugin-intake-review",
    "release-readiness",
)

REQUIRED_FILES = (
    "README.md",
    "QUICKSTART.md",
    "WORKFLOW-REVIEW.md",
    "VERSION",
    "MANIFEST.sha256",
    "install.sh",
    "install.ps1",
    "docs/V2-ADOPTION-EVIDENCE.md",
    "docs/V3.1-ADOPTION-EVIDENCE.md",
    "docs/V3.1-BENCHMARK.json",
    "docs/V3.1-BENCHMARK.md",
    "docs/V3.1-SKILL-POLISH-BENCHMARK.json",
    "docs/V3.1-SKILL-POLISH-BENCHMARK.md",
    "docs/V3.1-AGENT-RESEARCH-20.md",
    "docs/V3.1-AGENT-CONTRACT-BENCHMARK.json",
    "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md",
    "docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md",
    "docs/agent-collaboration-smoke.md",
    "docs/codex-usage.md",
    "docs/external-component-intake.md",
    "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md",
    "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md",
    "global/AGENTS.md",
    "reverse-skill/README.md",
    "reverse-skill/PLATFORMS.md",
    "reverse-skill/skills/SKILL.md",
    "reverse-skill/skills/routing.md",
    "reverse-skill/skills/reverse-engineering/SKILL.md",
    "reverse-skill/skills/apk-reverse/SKILL.md",
    "reverse-skill/skills/ida-reverse/SKILL.md",
    "reverse-skill/skills/js-reverse/SKILL.md",
    "reverse-skill/skills/mobile-reverse/SKILL.md",
    "reverse-skill/skills/pentest-tools/SKILL.md",
    "reverse-skill/skills/api-security/SKILL.md",
    "reverse-skill/skills/llm-security/SKILL.md",
    "reverse-skill/skills/supply-chain-security/SKILL.md",
    "reverse-skill/skills/docs-generator/SKILL.md",
    "reverse-skill/skills/diagram-generator/SKILL.md",
    "reverse-skill/CTF-Sandbox-Orchestrator/ctf-sandbox-orchestrator/SKILL.md",
    "reverse-skill/burp-mcp-full/mcp-bridge.js",
    "reverse-skill/ghidra-mcp/headless/ghidra_headless_mcp.py",
    "reverse-skill-router/reverse-engineering/SKILL.md",
    "scripts/audit_skill_contracts.py",
    "scripts/audit_external_component.py",
    "scripts/audit_repo_adoption.py",
    "scripts/benchmark_v31_vs_v22.py",
    "scripts/benchmark_skill_polish.py",
    "scripts/benchmark_agent_contract.py",
    "scripts/build_release.py",
    "scripts/codex_doctor.py",
    "scripts/codex_runtime_smoke.py",
    "scripts/verify_apk_decode_smoke.py",
    "scripts/render_usage_row.py",
    "scripts/verify_live_install.py",
    "scripts/verify_reverse_ready.py",
    "repo-template/AGENTS.md",
    "repo-template/scripts/verify_context_pack.py",
    "repo-template/tests/test_verify_context_pack.py",
    "repo-template/docs/architecture.md",
    "repo-template/docs/commands.md",
    "repo-template/docs/testing.md",
    "repo-template/docs/quality-gates.md",
    "repo-template/docs/subagents.md",
    "repo-template/docs/observability.md",
    "repo-template/docs/mcp-pilot.md",
    "repo-template/docs/codegraph-pilot.md",
    "repo-template/docs/memory-recall-pilot.md",
    "repo-template/docs/codex-usage.md",
    "repo-template/docs/codex-playbook.md",
    "repo-template/docs/glossary.md",
    "repo-template/docs/decisions/README.md",
    "repo-template/docs/specs/README.md",
    "scripts/verify_toolkit.py",
    "skills/spec-kit-xl/references/spec-template.md",
    "tests/test_audit_skill_contracts.py",
    "tests/test_audit_external_component.py",
    "tests/test_benchmark_skill_polish.py",
    "tests/test_benchmark_agent_contract.py",
    "tests/test_codex_runtime_smoke.py",
    "tests/test_verify_apk_decode_smoke.py",
    "tests/test_verify_reverse_ready.py",
    "tests/test_verify_toolkit.py",
)

REQUIRED_README_TERMS = (
    "QUICKSTART.md",
    "VERSION",
    "MANIFEST.sha256",
    "scripts/build_release.py",
    "scripts/codex_doctor.py",
    "install.sh",
    "install.ps1",
    "--repo-only",
    "scripts/verify_toolkit.py",
    "scripts/audit_repo_adoption.py",
    "scripts/render_usage_row.py",
    "scripts/verify_live_install.py",
    "scripts/codex_doctor.py",
    "scripts/verify_reverse_ready.py",
    "scripts/verify_apk_decode_smoke.py",
    "pilot",
    "--json",
    "--markdown",
    "--with-reverse-core",
    "--start-reverse-services",
    "--verify-reverse-ready",
    "--reverse-capabilities",
    "-WithReverseCore",
    "-VerifyReverseReady",
    "scripts/verify_context_pack.py",
    "WORKFLOW-REVIEW.md",
    "docs/V3.1-ADOPTION-EVIDENCE.md",
    "docs/V3.1-BENCHMARK.md",
    "docs/V3.1-SKILL-POLISH-BENCHMARK.md",
    "docs/V3.1-AGENT-RESEARCH-20.md",
    "docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md",
    "docs/agent-collaboration-smoke.md",
    "docs/codex-usage.md",
    "docs/external-component-intake.md",
    "docs/V2-ADOPTION-EVIDENCE.md",
    "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md",
    "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md",
    "scripts/audit_skill_contracts.py",
    "scripts/audit_external_component.py",
    "scripts/benchmark_v31_vs_v22.py",
    "scripts/benchmark_skill_polish.py",
    "scripts/benchmark_agent_contract.py",
    "scripts/codex_runtime_smoke.py",
    "scripts/render_usage_row.py trial",
    "scripts/render_usage_row.py trial --preset",
    "~/.codex/AGENTS.md",
    "~/.agents/skills/",
    "~/.codex/reverse-skill/",
    "~/.codex/skills/reverse-engineering/",
    "11 个个人 Codex skills",
    "release-readiness",
    "reverse-skill",
    "v3.2",
    "reverse-ready",
)
REQUIRED_CODEX_USAGE_TERMS = (
    "Real Trial Records",
    "Stage Review: 4 Real V3.1 Trials",
    "Closeout Trial Records",
    "Closeout Review: 4 Additional V3.1 Trials",
    "Trial row helper for real M/L/XL samples",
    "Runtime smoke and skill audit evidence layer",
    "Package verifier coverage for real usage evidence",
    "Release-readiness drill after workflow changes",
    "Release evidence version alignment",
    "Trial row preset helper",
    "Package and docs contract alignment",
    "Release-readiness closeout drill",
    "Positive Signal",
    "Friction",
    "Tighten next",
    "Do not advance",
    "do not auto-append docs",
)

REQUIRED_WORKFLOW_REVIEW_TERMS = (
    "最终路线",
    "完成状态",
    "可复用",
    "候选",
    "新机器演练",
    "触发条件",
    "Superpowers",
    "spec-kit-xl",
    "质量门禁",
    "subagents",
    "security-review",
    "dependency-upgrade-review",
    "research-brief",
    "skill-plugin-intake-review",
    "V3.1",
    "promote != install",
    "pilot != enable",
    "core != runtime/background",
    "reverse-skill",
    "reverse-ready",
)
REQUIRED_P0_SKILL_ROUTE_TERMS = (
    "security-review",
    "dependency-upgrade-review",
    "research-brief",
)
REQUIRED_QUICKSTART_TERMS = (
    "最短安装命令",
    "最短验证命令",
    "10 分钟流程",
    "python3 scripts/verify_toolkit.py",
    "python3 scripts/verify_live_install.py",
    "python3 scripts/verify_reverse_ready.py",
    "python3 scripts/verify_apk_decode_smoke.py",
    "python3 scripts/codex_doctor.py",
    "python3 scripts/codex_runtime_smoke.py",
    "python3 scripts/audit_skill_contracts.py",
    "python3 scripts/audit_external_component.py",
    "scripts/render_usage_row.py baseline",
    "scripts/render_usage_row.py trial",
    "scripts/render_usage_row.py trial --preset",
    "./install.sh --dry-run",
    "./install.sh --with-reverse-core",
    "powershell -ExecutionPolicy Bypass -File .\\install.ps1",
    ".\\install.ps1 -WithReverseCore",
    "./install.sh --repo-only --repo /path/to/repo --backup",
    "--start-reverse-services",
    "--verify-reverse-ready",
    "--reverse-capabilities",
    "python3 scripts/verify_context_pack.py",
    "reverse-ready",
    "docs/codex-usage.md",
    "11 个个人 Codex skills",
    "release-readiness",
    "V3.1",
    "~/.codex/reverse-skill/",
    "~/.codex/skills/reverse-engineering/",
)
REQUIRED_REVERSE_PACK_TERMS = (
    "Routing Execution Protocol",
    "tool-index",
    "docs-generator",
    "diagram-generator",
    "field-journal",
    "CTF-Sandbox-Orchestrator",
    "BurpSuite MCP",
    "Ghidra",
)
REQUIRED_V2_PLAN_TERMS = (
    "Workflow Kit V2 Adoption Implementation Plan",
    "Freeze V1 Baseline",
    "Select 3-5 Representative Trial Repositories",
    "Run Real M/L/XL Tasks",
    "First Adoption Review",
    "Evaluate Hooks Candidates",
    "Evaluate MCP, Code Graph, and Memory",
    "Evaluate Subagents Parallelism",
    "Browser and Frontend QA Calibration",
    "Prepare V2 Toolkit Update",
    "Final V2 Verification and Migration Drill",
)
REQUIRED_V2_1_PLAN_TERMS = (
    "Workflow Kit V2.1 Observability, Subagents, and MCP Pilot Implementation Plan",
    "observability",
    "subagent prompt cards",
    "MCP/code graph pilot",
    "render_usage_row pilot",
    "no default automation",
    "Build and Verify Release",
)
REQUIRED_V2_EVIDENCE_TERMS = (
    "V2 Adoption Evidence",
    "Baseline Verification",
    "Trial Repo Scan",
    "Real Usage Evidence",
    "Promotions",
    "Rejections",
    "Deferred Work",
    "install.sh --repo-only",
    "scripts/audit_repo_adoption.py",
    "scripts/render_usage_row.py",
    "--json",
    "--markdown",
    "repo-only-install",
    "manual-merge",
    "dirty worktree",
    "dirty-worktree",
    "docs/architecture.md",
    "Repo-specific onboarding calibration",
    "manual-only test policy",
    "Align Go version docs with go.mod/CI",
    "Guard README agent instruction append snippets",
    "Lock manual-only Go test policy with static docs test",
    "Validate CLAUDE.md repo paths with static docs test",
    "Make raw workflow downloads fail fast",
    "First Adoption Review",
    "Second Adoption Review",
    "Final V2 Completion Audit",
    "V2.1 Tooling Layer",
    "V2.2 P0 Specialist Skills",
    "V2.2 Closeout",
    "scripts/verify_live_install.py",
    "9 skills verified",
    "skill metadata/boundary quality gates",
    "observability",
    "prompt cards",
    "MCP/code graph pilot",
    "render_usage_row.py pilot",
    "no default automation",
)
REQUIRED_V3_1_EVIDENCE_TERMS = (
    "V3.1 Adoption Evidence",
    "Core Semantics",
    "promote != install",
    "pilot != enable",
    "core != runtime/background",
    "External Component Intake",
    "Code Graph Pilot",
    "Memory Recall Pilot",
    "Hook Discipline",
    "Subagent Prompt Cards",
    "Agent Research 20",
    "Agent Self-Diagnosis",
    "Skill Polish",
    "Reject Lines",
    "11 skills verified",
    "release-readiness",
    "Feedback Loop First",
    "Output Shape",
    "accessibility",
    "references/spec-template.md",
    "scripts/audit_external_component.py",
    "scripts/benchmark_skill_polish.py",
    "scripts/benchmark_agent_contract.py",
    "scripts/audit_skill_contracts.py",
    "scripts/codex_runtime_smoke.py",
    "scripts/verify_toolkit.py",
    "scripts/verify_context_pack.py",
    "no default MCP server",
    "no default memory writer",
    "no default hook stack",
)
REQUIRED_AGENT_COLLABORATION_SMOKE_TERMS = (
    "Agent Collaboration Smoke",
    "Read-Only Dual Explorer",
    "No-Dispatch Strong Coupling",
    "Local-Write Boundary",
    "Visibility Policy",
    "Skill Coupling",
    "Handoff Envelope",
    "Return Envelope",
    "Lifecycle Ledger",
    "close_agent previous_status",
    "Do Not",
)
REQUIRED_V3_1_BENCHMARK_TERMS = (
    "V3.1 vs V2.2 Benchmark",
    "Repetitions",
    "package-health",
    "repo-context-pack",
    "live-install-drill",
    "external-component-intake",
    "Runtime delta",
    "Coverage delta",
    "Issue-detection delta",
)
REQUIRED_SKILL_POLISH_BENCHMARK_TERMS = (
    "V3.1 Skill Polish Benchmark",
    "pre-polish",
    "post-polish",
    "Skill count",
    "Output Shape",
    "Accessibility coverage",
    "Release readiness",
    "Progressive disclosure",
    "Measured improvement",
)
REQUIRED_EXTERNAL_INTAKE_TERMS = (
    "promote",
    "pilot",
    "repo-local",
    "hold",
    "reject",
    "DAILY",
    "LIBRARY",
    "REJECT",
    "license",
    "auth",
    "side_effect",
    "daemon",
    "network",
    "install",
    "superpowers_overlap",
    "private_path_secret",
    "promote` 不等于 install",
    "默认拒绝",
    "orchestrator",
    "planner",
    "dispatcher",
    "queue",
    "implementation-plan",
    "默认 MCP server",
    "默认 memory writer",
    "curl-to-shell",
    "GPL/unknown license",
)
REQUIRED_V3_1_MCP_PERMISSION_TERMS = (
    "docs-only",
    "read-only local",
    "local write",
    "external read",
    "external write",
    "destructive / production-risk",
    "allowed tools",
    "denied tools",
    "rollback/fallback",
    "pilot` 不等于启用",
)
REQUIRED_V3_1_HOOK_TERMS = (
    "Hook Review Checklist",
    "advisory",
    "fail-open",
    "blocking",
    "External Component Gate",
    "curl-to-shell",
    "自动 memory 写入",
    "后台 watcher",
    "长期 daemon",
)
REQUIRED_V3_1_CODEGRAPH_TERMS = (
    "Code Graph Pilot",
    "orientation",
    "不是真相源",
    "rg",
    "源码回读",
    "不默认安装",
    "不默认启用",
    "python3 scripts/render_usage_row.py pilot --pilot codegraph",
)
REQUIRED_V3_1_MEMORY_TERMS = (
    "Memory Recall Pilot",
    "不是真相源",
    "repo `AGENTS.md`",
    "不默认启用 memory hook",
    "不默认启用 MCP memory writer",
    "raw transcript",
    "provenance",
    "python3 scripts/render_usage_row.py pilot --pilot memory-recall",
)
REQUIRED_V3_1_SUBAGENT_TERMS = (
    "V3.1 Prompt Contract",
    "Handoff Envelope",
    "Return Envelope",
    "History/Input Filter",
    "Command/Tool Risk Policy",
    "Step Budget / Stop Condition",
    "Lifecycle Ledger",
    "No-Dispatch Decision",
    "allowed write set",
    "off-limits",
    "lifecycle close",
    "implementation worker",
    "coverage-gap auditor",
    "batch worker",
)
REQUIRED_AGENT_CONTRACT_TERMS = REQUIRED_V3_1_SUBAGENT_TERMS[1:8]
REQUIRED_V3_1_AGENT_RESEARCH_TERMS = (
    "V3.1 Agent Research 20",
    "20 real git checkouts",
    "Handoff Envelope",
    "Return Envelope",
    "History/Input Filter",
    "Command/Tool Risk Policy",
    "Step Budget / Stop Condition",
    "Lifecycle Ledger",
    "No-Dispatch Decision",
    "Promote Now",
    "Pilot",
    "Hold / Reject",
    "Why This Does Not Conflict",
    "langchain-ai/langgraph",
    "microsoft/autogen",
    "openai/openai-agents-python",
    "browser-use/browser-use",
    "langfuse/langfuse",
)
REQUIRED_AGENT_CONTRACT_BENCHMARK_TERMS = (
    "V3.1 Agent Contract Benchmark",
    "pre-agent-contract",
    "post-agent-contract",
    "Handoff Envelope",
    "Return Envelope",
    "Lifecycle Ledger",
    "Measured improvement",
)
REQUIRED_AGENT_SELF_DIAGNOSIS_TERMS = (
    "goal drift",
    "context drift",
    "unsupported claim",
    "subagent lifecycle",
)
REQUIRED_DEBUG_LOOP_POLISH_TERMS = (
    "Feedback Loop First",
    "failing test",
    "captured trace replay",
    "property/fuzz loop",
    "regression test",
    "deterministic loop",
    "Output Shape",
)
REQUIRED_COMPLETION_REVIEW_POLISH_TERMS = (
    "Artifact / Release Evidence Gate",
    "archive listing",
    "checksum",
    "install docs",
    "Output Shape",
)
REQUIRED_FRONTEND_ACCESSIBILITY_TERMS = (
    "Keyboard",
    "Focus",
    "Contrast",
    "ARIA",
    "Reduced motion",
    "Output Shape",
)
REQUIRED_DECISION_RECORD_POLISH_TERMS = (
    "Output Shape",
    "Completion Conditions",
    "Superseded",
    "Consequences",
)
REQUIRED_REPO_ONBOARDING_POLISH_TERMS = (
    "minimal context pack",
    "Core context pack",
    "Optional context pack",
    "Output Shape",
)
REQUIRED_SPEC_PROGRESSIVE_DISCLOSURE_TERMS = (
    "references/spec-template.md",
    "progressive disclosure",
    "Output Shape",
)
REQUIRED_RELEASE_READINESS_TERMS = (
    "status: pilot",
    "artifact quality gate",
    "manifest",
    "archive",
    "checksum",
    "install drill",
    "live install",
    "rollback",
    "Output Shape",
    "不要",
)
REQUIRED_PROACTIVE_SUBAGENT_TERMS = (
    "长期授权",
    "subagent suitability check",
    "L/XL",
    "已有实施计划",
    "跨模块",
    "多个独立失败源",
    "多文件审查",
    "2 个以上",
    "不使用时",
    "主 agent",
    "最终集成",
    "diff review",
    "垂直切片",
    "只读 explorer",
)
REQUIRED_SUBAGENT_PROMPT_CARDS = (
    "read-only code mapper",
    "test/debug investigator",
    "frontend QA reviewer",
    "docs/content-contract reviewer",
    "architecture/migration reviewer",
)
REQUIRED_OBSERVABILITY_TERMS = (
    "ccusage",
    "CodexBar",
    "候选",
    "默认不安装",
    "docs/codex-usage.md",
    "render_usage_row.py pilot --pilot observability",
    "不自动晋升",
)
REQUIRED_MCP_PILOT_TERMS = (
    "rg + context pack",
    "deepcontext-mcp",
    "试点候选",
    "默认使用",
    "baseline",
    "回滚",
    "render_usage_row.py pilot --pilot mcp-code-graph",
)
REQUIRED_FRONTEND_BROWSER_ROUTING_TERMS = (
    "in-app Browser",
    "localhost",
    "不要静默降级到 Chrome",
    "用户明确要求 Chrome",
    "现有 Chrome 登录态",
    "不要硬编码 Browser 插件缓存路径",
    "scripts/browser-client.mjs",
)
GENERATED_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
)
MANIFEST_PATH = "MANIFEST.sha256"
MANIFEST_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "releases",
    ".venv",
}
MANIFEST_EXCLUDED_SUFFIXES = {
    ".pyc",
    ".bak",
}
MANIFEST_EXCLUDED_FILES = {
    ".DS_Store",
}

SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{20,}|BEGIN (?:RSA|OPENSSH|PRIVATE) KEY|"
    r"(?:api[_-]?key|secret|password)\s*=",
    re.IGNORECASE,
)
PRIVATE_HOME_PATH_RE = re.compile(r"/(?:Users|home)/(?!\[|\<|path/to/)([A-Za-z0-9._-]+)(?:/|$)")
HARDCODED_BROWSER_PLUGIN_PATH_RE = re.compile(
    r"/Users/[^/]+/\.codex/plugins/cache/openai-bundled/browser/|"
    r"openai-bundled/browser/\d+\.\d+\.\d+/scripts/browser-client\.mjs"
)
ALLOWED_SECRET_FIXTURES = ("sk-thisisnotarealkeybutshouldbeflagged", "api_key=bad")
ALLOWED_PRIVATE_PATH_FIXTURES = (
    '"/Users/[^',
    'r"/Users/[^',
    '"/home/[^',
    'r"/home/[^',
    '"/Users/"',
    '"/home/"',
    "/path/to/",
)
REVERSE_PACK_PRIVATE_PATH_ALLOWED_PREFIXES = (
    "reverse-skill/skills/field-journal/",
    "reverse-skill/skills/pentest-tools/src-hunter/references/",
    "reverse-skill/skills/reverse-engineering/",
)
REVERSE_PACK_SECRET_ALLOWED_PREFIXES = (
    "reverse-skill/skills/field-journal/",
    "reverse-skill/skills/pentest-tools/src-hunter/references/",
    "reverse-skill/skills/reverse-engineering/",
)
SKILL_BOUNDARY_TERMS = (
    "不要",
    "Do not",
    "Boundaries",
    "边界",
    "不替代",
    "不默认",
)


@dataclass(frozen=True, order=True)
class ToolkitIssue:
    severity: str
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_executable(path: Path) -> bool:
    mode = path.stat().st_mode
    return bool(mode & stat.S_IXUSR)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_manifest_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(name for name in dir_names if name not in MANIFEST_EXCLUDED_DIRS)
        current = Path(current_root)
        for file_name in sorted(file_names):
            if file_name in MANIFEST_EXCLUDED_FILES:
                continue
            path = current / file_name
            relative = _relative(root, path)
            if relative == MANIFEST_PATH:
                continue
            if any(relative.endswith(suffix) for suffix in MANIFEST_EXCLUDED_SUFFIXES):
                continue
            if ".bak-" in relative:
                continue
            files.append(path)
    return files


def _expected_manifest(root: Path) -> str:
    lines = []
    for path in _iter_manifest_files(root):
        lines.append(f"{_hash_file(path)}  {_relative(root, path)}")
    return "\n".join(lines) + "\n"


def _load_script_module(root: Path, relative: str, module_name: str):
    script = root / relative
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode
    return module


def _load_context_pack_module(root: Path):
    return _load_script_module(root, "repo-template/scripts/verify_context_pack.py", "verify_context_pack_template")


def _secret_line_allowed(line: str) -> bool:
    return any(fixture in line for fixture in ALLOWED_SECRET_FIXTURES)


def _private_path_line_allowed(line: str) -> bool:
    return any(fixture in line for fixture in ALLOWED_PRIVATE_PATH_FIXTURES)


def _allow_reverse_pack_private_path(relative: str, line: str) -> bool:
    if relative in {
        "reverse-skill/README-kali.md",
        "reverse-skill/ghidra-mcp/headless/ghidra_headless_mcp.py",
        "reverse-skill/skills/apk-reverse/scripts/frida-run.sh",
    }:
        return True
    return any(relative.startswith(prefix) for prefix in REVERSE_PACK_PRIVATE_PATH_ALLOWED_PREFIXES)


def _allow_reverse_pack_secret_pattern(relative: str) -> bool:
    if relative == "reverse-skill/kali/scripts/bootstrap-reverse.sh":
        return True
    return any(relative.startswith(prefix) for prefix in REVERSE_PACK_SECRET_ALLOWED_PREFIXES)


def _parse_skill_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end_marker = "\n---\n"
    end = text.find(end_marker, 4)
    if end == -1:
        return {}
    frontmatter: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter


def check_toolkit(root: str | Path = ".") -> list[ToolkitIssue]:
    root = Path(root).resolve()
    issues: list[ToolkitIssue] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).exists():
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="missing-required-file",
                    path=relative,
                    message="Required toolkit file is missing.",
                )
            )

    install_script = root / "install.sh"
    if install_script.exists() and not _is_executable(install_script):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="install-not-executable",
                path="install.sh",
                message="install.sh must be executable.",
            )
        )

    for relative in (
        "install.sh",
        "scripts/audit_skill_contracts.py",
        "scripts/audit_external_component.py",
        "scripts/audit_repo_adoption.py",
        "scripts/benchmark_skill_polish.py",
        "scripts/benchmark_agent_contract.py",
        "scripts/build_release.py",
        "scripts/codex_doctor.py",
        "scripts/codex_runtime_smoke.py",
        "scripts/render_usage_row.py",
        "scripts/verify_apk_decode_smoke.py",
        "scripts/verify_live_install.py",
        "scripts/verify_toolkit.py",
    ):
        script = root / relative
        if script.exists() and not _is_executable(script):
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="script-not-executable",
                    path=relative,
                    message="Release and install scripts must be executable.",
                )
            )

    version_text = _read_text(root / "VERSION").strip() if (root / "VERSION").exists() else ""
    if version_text and not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}(?:\.\d+)?", version_text):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="invalid-version",
                path="VERSION",
                message="VERSION must use YYYY.MM.DD or YYYY.MM.DD.N format.",
            )
        )

    manifest_path = root / MANIFEST_PATH
    if manifest_path.exists():
        actual_manifest = _read_text(manifest_path)
        expected_manifest = _expected_manifest(root)
        if actual_manifest != expected_manifest:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="manifest-out-of-date",
                    path=MANIFEST_PATH,
                    message="Run scripts/build_release.py to refresh MANIFEST.sha256.",
                )
            )

    for skill in EXPECTED_SKILLS:
        skill_file = root / "skills" / skill / "SKILL.md"
        if not skill_file.exists():
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="missing-skill",
                    path=f"skills/{skill}/SKILL.md",
                    message="Expected personal skill is missing.",
                )
            )
            continue

        skill_text = _read_text(skill_file)
        frontmatter = _parse_skill_frontmatter(skill_text)
        if frontmatter.get("name") != skill:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-frontmatter-invalid",
                    path=f"skills/{skill}/SKILL.md",
                    message="Skill frontmatter name must match the skill folder.",
                )
            )
        description = frontmatter.get("description", "")
        if not description.startswith("Use when"):
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-description-invalid",
                    path=f"skills/{skill}/SKILL.md",
                    message='Skill description must start with "Use when" and describe trigger conditions.',
                )
            )
        if "##" not in skill_text:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-missing-sections",
                    path=f"skills/{skill}/SKILL.md",
                    message="Skill body must include scannable Markdown sections.",
                )
            )
        if not any(term in skill_text for term in SKILL_BOUNDARY_TERMS):
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-missing-boundary-guidance",
                    path=f"skills/{skill}/SKILL.md",
                    message="Skill body must include boundary or do-not guidance.",
                )
            )

    if (root / "skills/implementation-plan").exists():
        issues.append(
            ToolkitIssue(
                severity="error",
                code="removed-skill-present",
                path="skills/implementation-plan",
                message="implementation-plan must stay removed to avoid overlapping Superpowers.",
            )
        )

    readme = _read_text(root / "README.md") if (root / "README.md").exists() else ""
    for term in REQUIRED_README_TERMS:
        if term not in readme:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="readme-missing-term",
                    path="README.md",
                    message=f"README.md must document {term}.",
                )
            )

    workflow_review = _read_text(root / "WORKFLOW-REVIEW.md") if (root / "WORKFLOW-REVIEW.md").exists() else ""
    for term in REQUIRED_WORKFLOW_REVIEW_TERMS:
        if workflow_review and term not in workflow_review:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="workflow-review-missing-term",
                    path="WORKFLOW-REVIEW.md",
                    message=f"WORKFLOW-REVIEW.md must include the review term: {term}.",
                )
            )

    quickstart = _read_text(root / "QUICKSTART.md") if (root / "QUICKSTART.md").exists() else ""
    for term in REQUIRED_QUICKSTART_TERMS:
        if quickstart and term not in quickstart:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="quickstart-missing-term",
                    path="QUICKSTART.md",
                    message=f"QUICKSTART.md must document {term}.",
                )
            )

    reverse_readme = _read_text(root / "reverse-skill/README.md") if (root / "reverse-skill/README.md").exists() else ""
    reverse_routing = _read_text(root / "reverse-skill/skills/routing.md") if (root / "reverse-skill/skills/routing.md").exists() else ""
    reverse_router = _read_text(root / "reverse-skill-router/reverse-engineering/SKILL.md") if (root / "reverse-skill-router/reverse-engineering/SKILL.md").exists() else ""
    reverse_aggregate = "\n".join((reverse_readme, reverse_routing, reverse_router))
    for term in REQUIRED_REVERSE_PACK_TERMS:
        if reverse_aggregate and term not in reverse_aggregate:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="reverse-pack-missing-term",
                    path="reverse-skill",
                    message=f"Reverse pack packaging must preserve {term}.",
                )
            )

    v2_plan_path = root / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md"
    v2_plan = _read_text(v2_plan_path) if v2_plan_path.exists() else ""
    for term in REQUIRED_V2_PLAN_TERMS:
        if v2_plan and term not in v2_plan:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v2-plan-missing-term",
                    path="docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md",
                    message=f"V2 adoption plan must document {term}.",
                )
            )

    v2_1_plan_path = root / "docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md"
    v2_1_plan = _read_text(v2_1_plan_path) if v2_1_plan_path.exists() else ""
    for term in REQUIRED_V2_1_PLAN_TERMS:
        if v2_1_plan and term not in v2_1_plan:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v2-1-plan-missing-term",
                    path="docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md",
                    message=f"V2.1 implementation plan must document {term}.",
                )
            )

    v2_evidence_path = root / "docs/V2-ADOPTION-EVIDENCE.md"
    v2_evidence = _read_text(v2_evidence_path) if v2_evidence_path.exists() else ""
    for term in REQUIRED_V2_EVIDENCE_TERMS:
        if v2_evidence and term not in v2_evidence:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v2-evidence-missing-term",
                    path="docs/V2-ADOPTION-EVIDENCE.md",
                    message=f"V2 adoption evidence must document {term}.",
                )
            )

    v3_1_evidence_path = root / "docs/V3.1-ADOPTION-EVIDENCE.md"
    v3_1_evidence = _read_text(v3_1_evidence_path) if v3_1_evidence_path.exists() else ""
    for term in REQUIRED_V3_1_EVIDENCE_TERMS:
        if v3_1_evidence and term not in v3_1_evidence:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v3-1-evidence-missing-term",
                    path="docs/V3.1-ADOPTION-EVIDENCE.md",
                    message=f"V3.1 adoption evidence must document {term}.",
                )
            )

    codex_usage_path = root / "docs/codex-usage.md"
    codex_usage = _read_text(codex_usage_path) if codex_usage_path.exists() else ""
    for term in REQUIRED_CODEX_USAGE_TERMS:
        if codex_usage and term not in codex_usage:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="codex-usage-missing-term",
                    path="docs/codex-usage.md",
                    message=f"Toolkit usage evidence must document {term}.",
                )
            )
    for term in ("Agent Research 20", "docs/V3.1-AGENT-RESEARCH-20.md", "Handoff Envelope", "Return Envelope"):
        if v3_1_evidence and term not in v3_1_evidence:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v3-1-evidence-missing-agent-contract-term",
                    path="docs/V3.1-ADOPTION-EVIDENCE.md",
                    message=f"V3.1 adoption evidence must document agent contract term: {term}.",
                )
            )
    expected_release_evidence = f"codex-workflow-kit-{version_text}.tar.gz: OK" if version_text else ""
    if v3_1_evidence and expected_release_evidence and expected_release_evidence not in v3_1_evidence:
        issues.append(
            ToolkitIssue(
                severity="error",
                code="v3-1-evidence-release-mismatch",
                path="docs/V3.1-ADOPTION-EVIDENCE.md",
                message=f"V3.1 adoption evidence must document {expected_release_evidence}.",
            )
        )

    v3_1_benchmark_path = root / "docs/V3.1-BENCHMARK.md"
    v3_1_benchmark = _read_text(v3_1_benchmark_path) if v3_1_benchmark_path.exists() else ""
    for term in REQUIRED_V3_1_BENCHMARK_TERMS:
        if v3_1_benchmark and term not in v3_1_benchmark:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="v3-1-benchmark-missing-term",
                    path="docs/V3.1-BENCHMARK.md",
                    message=f"V3.1 benchmark must document {term}.",
                )
            )

    skill_polish_benchmark_path = root / "docs/V3.1-SKILL-POLISH-BENCHMARK.md"
    skill_polish_benchmark = _read_text(skill_polish_benchmark_path) if skill_polish_benchmark_path.exists() else ""
    for term in REQUIRED_SKILL_POLISH_BENCHMARK_TERMS:
        if skill_polish_benchmark and term not in skill_polish_benchmark:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-polish-benchmark-missing-term",
                    path="docs/V3.1-SKILL-POLISH-BENCHMARK.md",
                    message=f"Skill polish benchmark must document {term}.",
                )
            )

    agent_research_path = root / "docs/V3.1-AGENT-RESEARCH-20.md"
    agent_research = _read_text(agent_research_path) if agent_research_path.exists() else ""
    for term in REQUIRED_V3_1_AGENT_RESEARCH_TERMS:
        if agent_research and term not in agent_research:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="agent-research-missing-term",
                    path="docs/V3.1-AGENT-RESEARCH-20.md",
                    message=f"Agent research evidence must document {term}.",
                )
            )

    agent_contract_benchmark_path = root / "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md"
    agent_contract_benchmark = _read_text(agent_contract_benchmark_path) if agent_contract_benchmark_path.exists() else ""
    for term in REQUIRED_AGENT_CONTRACT_BENCHMARK_TERMS:
        if agent_contract_benchmark and term not in agent_contract_benchmark:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="agent-contract-benchmark-missing-term",
                    path="docs/V3.1-AGENT-CONTRACT-BENCHMARK.md",
                    message=f"Agent contract benchmark must document {term}.",
                )
            )

    external_intake = (
        _read_text(root / "docs/external-component-intake.md")
        if (root / "docs/external-component-intake.md").exists()
        else ""
    )
    for term in REQUIRED_EXTERNAL_INTAKE_TERMS:
        if external_intake and term not in external_intake:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="external-intake-missing-term",
                    path="docs/external-component-intake.md",
                    message=f"External component intake must document {term}.",
                )
            )

    agent_collaboration_smoke = (
        _read_text(root / "docs/agent-collaboration-smoke.md")
        if (root / "docs/agent-collaboration-smoke.md").exists()
        else ""
    )
    for term in REQUIRED_AGENT_COLLABORATION_SMOKE_TERMS:
        if agent_collaboration_smoke and term not in agent_collaboration_smoke:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="agent-collaboration-smoke-missing-term",
                    path="docs/agent-collaboration-smoke.md",
                    message=f"Agent collaboration smoke checklist must document {term}.",
                )
            )

    global_agents = _read_text(root / "global/AGENTS.md") if (root / "global/AGENTS.md").exists() else ""
    for term in ("Superpowers", "spec-kit-xl", "completion-review", "任务分级"):
        if term not in global_agents:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="global-agents-missing-protocol",
                    path="global/AGENTS.md",
                    message=f"Global AGENTS.md must include the workflow protocol term: {term}.",
                )
            )
    for term in REQUIRED_P0_SKILL_ROUTE_TERMS:
        if global_agents and term not in global_agents:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="global-agents-missing-p0-skill-route",
                    path="global/AGENTS.md",
                    message=f"Global AGENTS.md must route the P0 specialist skill: {term}.",
                )
            )
    if global_agents and not all(term in global_agents for term in ("in-app Browser", "不要静默降级到 Chrome", "用户明确要求 Chrome")):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="global-agents-missing-browser-routing",
                path="global/AGENTS.md",
                message="Global AGENTS.md must route local frontend QA through in-app Browser and prevent silent Chrome fallback.",
            )
        )

    quality_gates = (
        _read_text(root / "repo-template/docs/quality-gates.md")
        if (root / "repo-template/docs/quality-gates.md").exists()
        else ""
    )
    if quality_gates and not all(term in quality_gates for term in ("针对性单元测试", "按受影响范围选择")):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="quality-gates-missing-targeted-guidance",
                path="repo-template/docs/quality-gates.md",
                message="Quality gate template must guide targeted tests by affected scope.",
            )
        )
    if quality_gates and not all(term in quality_gates for term in ("静态文档契约测试", "安装说明", "路径引用")):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="quality-gates-missing-static-doc-contract-guidance",
                path="repo-template/docs/quality-gates.md",
                message="Quality gate template must document static docs/content-contract tests as repo-specific candidates.",
            )
        )
    frontend_qa = _read_text(root / "skills/frontend-qa/SKILL.md") if (root / "skills/frontend-qa/SKILL.md").exists() else ""
    if frontend_qa and not all(term in frontend_qa for term in REQUIRED_FRONTEND_BROWSER_ROUTING_TERMS):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="frontend-qa-missing-browser-routing",
                path="skills/frontend-qa/SKILL.md",
                message="frontend-qa must route local QA through in-app Browser and prevent silent Chrome fallback.",
            )
        )

    usage = (
        _read_text(root / "repo-template/docs/codex-usage.md")
        if (root / "repo-template/docs/codex-usage.md").exists()
        else ""
    )
    if usage and not all(term in usage for term in ("质量门禁", "阶段复盘", "晋升")):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="usage-missing-quality-gate-review",
                path="repo-template/docs/codex-usage.md",
                message="Usage template must include stage review guidance for quality gate promotion.",
            )
        )

    observability = (
        _read_text(root / "repo-template/docs/observability.md")
        if (root / "repo-template/docs/observability.md").exists()
        else ""
    )
    if observability and not all(term in observability for term in REQUIRED_OBSERVABILITY_TERMS):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="observability-missing-guidance",
                path="repo-template/docs/observability.md",
                message="Observability guidance must keep tools optional, local-first, and evidence-recorded.",
            )
        )
    mcp_pilot = (
        _read_text(root / "repo-template/docs/mcp-pilot.md")
        if (root / "repo-template/docs/mcp-pilot.md").exists()
        else ""
    )
    if mcp_pilot and not all(term in mcp_pilot for term in REQUIRED_MCP_PILOT_TERMS):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="mcp-pilot-missing-guidance",
                path="repo-template/docs/mcp-pilot.md",
                message="MCP pilot guidance must keep MCP/code graph optional, baseline-compared, and reversible.",
            )
        )

    for relative in ("global/AGENTS.md", "repo-template/AGENTS.md", "repo-template/docs/subagents.md"):
        text = _read_text(root / relative) if (root / relative).exists() else ""
        if text and not all(term in text for term in REQUIRED_PROACTIVE_SUBAGENT_TERMS):
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="subagents-missing-proactive-guidance",
                    path=relative,
                    message=(
                        "Subagent guidance must require proactive suitability checks, active dispatch for "
                        "2+ independent subtasks, and main-agent integration review."
                    ),
                )
            )
        if text and not all(term in text for term in REQUIRED_AGENT_CONTRACT_TERMS):
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="subagents-missing-agent-contract-guidance",
                    path=relative,
                    message=(
                        "Subagent guidance must document handoff, return, history/input filtering, "
                        "tool risk policy, step budget, lifecycle ledger, and no-dispatch decisions."
                    ),
                )
            )
    if mcp_pilot:
        for term in REQUIRED_V3_1_MCP_PERMISSION_TERMS:
            if term not in mcp_pilot:
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="mcp-pilot-missing-v3-1-permission-term",
                        path="repo-template/docs/mcp-pilot.md",
                        message=f"MCP/plugin pilot guidance must document V3.1 permission term: {term}.",
                    )
                )

    codegraph_pilot = (
        _read_text(root / "repo-template/docs/codegraph-pilot.md")
        if (root / "repo-template/docs/codegraph-pilot.md").exists()
        else ""
    )
    for term in REQUIRED_V3_1_CODEGRAPH_TERMS:
        if codegraph_pilot and term not in codegraph_pilot:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="codegraph-pilot-missing-term",
                    path="repo-template/docs/codegraph-pilot.md",
                    message=f"Code graph pilot guidance must document {term}.",
                )
            )

    memory_recall = (
        _read_text(root / "repo-template/docs/memory-recall-pilot.md")
        if (root / "repo-template/docs/memory-recall-pilot.md").exists()
        else ""
    )
    for term in REQUIRED_V3_1_MEMORY_TERMS:
        if memory_recall and term not in memory_recall:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="memory-recall-pilot-missing-term",
                    path="repo-template/docs/memory-recall-pilot.md",
                    message=f"Memory recall pilot guidance must document {term}.",
                )
            )

    for term in REQUIRED_V3_1_HOOK_TERMS:
        if quality_gates and term not in quality_gates:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="quality-gates-missing-v3-1-hook-term",
                    path="repo-template/docs/quality-gates.md",
                    message=f"Quality gate template must document V3.1 hook discipline term: {term}.",
                )
            )

    subagents = (
        _read_text(root / "repo-template/docs/subagents.md")
        if (root / "repo-template/docs/subagents.md").exists()
        else ""
    )
    if subagents and not all(term in subagents for term in REQUIRED_SUBAGENT_PROMPT_CARDS):
        issues.append(
            ToolkitIssue(
                severity="error",
                code="subagents-missing-prompt-cards",
                path="repo-template/docs/subagents.md",
                message="Subagent guidance must include copy-ready prompt cards for common safe delegation roles.",
            )
        )
    for term in REQUIRED_V3_1_SUBAGENT_TERMS:
        if subagents and term not in subagents:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="subagents-missing-v3-1-contract-term",
                    path="repo-template/docs/subagents.md",
                    message=f"Subagent guidance must include V3.1 prompt contract term: {term}.",
                )
            )

    debug_loop = _read_text(root / "skills/debug-loop/SKILL.md") if (root / "skills/debug-loop/SKILL.md").exists() else ""
    completion_review = (
        _read_text(root / "skills/completion-review/SKILL.md")
        if (root / "skills/completion-review/SKILL.md").exists()
        else ""
    )
    for term in REQUIRED_AGENT_SELF_DIAGNOSIS_TERMS:
        if debug_loop and term not in debug_loop:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="debug-loop-missing-agent-self-diagnosis",
                    path="skills/debug-loop/SKILL.md",
                    message=f"debug-loop must cover agent self-diagnosis term: {term}.",
                )
            )
        if completion_review and term not in completion_review:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="completion-review-missing-agent-self-diagnosis",
                    path="skills/completion-review/SKILL.md",
                    message=f"completion-review must cover final self-diagnosis term: {term}.",
                )
            )

    for term in REQUIRED_DEBUG_LOOP_POLISH_TERMS:
        if debug_loop and term not in debug_loop:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="debug-loop-missing-feedback-loop-polish",
                    path="skills/debug-loop/SKILL.md",
                    message=f"debug-loop must preserve feedback-loop-first polish term: {term}.",
                )
            )
    for term in REQUIRED_COMPLETION_REVIEW_POLISH_TERMS:
        if completion_review and term not in completion_review:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="completion-review-missing-artifact-gate",
                    path="skills/completion-review/SKILL.md",
                    message=f"completion-review must preserve artifact/release evidence term: {term}.",
                )
            )
    for term in REQUIRED_FRONTEND_ACCESSIBILITY_TERMS:
        if frontend_qa and term not in frontend_qa:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="frontend-qa-missing-accessibility-polish",
                    path="skills/frontend-qa/SKILL.md",
                    message=f"frontend-qa must preserve accessibility polish term: {term}.",
                )
            )

    skill_polish_checks = (
        (
            "decision-record",
            "skills/decision-record/SKILL.md",
            REQUIRED_DECISION_RECORD_POLISH_TERMS,
            "decision-record-missing-output-contract",
        ),
        (
            "repo-onboarding",
            "skills/repo-onboarding/SKILL.md",
            REQUIRED_REPO_ONBOARDING_POLISH_TERMS,
            "repo-onboarding-missing-minimal-context-pack",
        ),
        (
            "spec-kit-xl",
            "skills/spec-kit-xl/SKILL.md",
            REQUIRED_SPEC_PROGRESSIVE_DISCLOSURE_TERMS,
            "spec-kit-xl-missing-progressive-disclosure",
        ),
        (
            "release-readiness",
            "skills/release-readiness/SKILL.md",
            REQUIRED_RELEASE_READINESS_TERMS,
            "release-readiness-missing-contract",
        ),
    )
    for _skill_name, relative, required_terms, code in skill_polish_checks:
        text = _read_text(root / relative) if (root / relative).exists() else ""
        for term in required_terms:
            if text and term not in text:
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code=code,
                        path=relative,
                        message=f"{relative} must preserve skill polish term: {term}.",
                    )
                )

    spec_template = root / "skills/spec-kit-xl/references/spec-template.md"
    if spec_template.exists():
        spec_template_text = _read_text(spec_template)
        for term in ("## 1. 背景和问题", "## 6. 验收标准", "## 11. 发布、迁移和回滚"):
            if term not in spec_template_text:
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="spec-template-missing-section",
                        path="skills/spec-kit-xl/references/spec-template.md",
                        message=f"Spec template must keep section: {term}.",
                    )
                )
    if (root / "skills/spec-kit-xl/assets/spec-template.md").exists():
        issues.append(
            ToolkitIssue(
                severity="error",
                code="spec-template-in-assets",
                path="skills/spec-kit-xl/assets/spec-template.md",
                message="Spec template must live in references/ for progressive disclosure, not assets/.",
            )
        )

    if (root / "scripts/audit_external_component.py").exists():
        try:
            audit_module = _load_script_module(
                root,
                "scripts/audit_external_component.py",
                "audit_external_component_template",
            )
            audit_report = audit_module.audit_component(root / "skills/skill-plugin-intake-review")
            if audit_report.get("recommended_decision") == "reject":
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="external-component-auditor-unexpected-decision",
                        path="scripts/audit_external_component.py",
                        message="Auditor should not reject the packaged intake skill.",
                    )
                )
        except Exception as exc:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="external-component-auditor-error",
                    path="scripts/audit_external_component.py",
                    message=str(exc),
                )
            )

    if (root / "scripts/audit_skill_contracts.py").exists():
        try:
            skill_audit_module = _load_script_module(
                root,
                "scripts/audit_skill_contracts.py",
                "audit_skill_contracts_template",
            )
            skill_audit_report = skill_audit_module.build_report(root)
            expected_skill_count = len(EXPECTED_SKILLS)
            totals = skill_audit_report.get("totals", {})
            if not skill_audit_report.get("ok"):
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="skill-contract-audit-failed",
                        path="scripts/audit_skill_contracts.py",
                        message="Packaged skills must pass the skill contract audit.",
                    )
                )
            if totals.get("skills") != expected_skill_count or totals.get("ok") != expected_skill_count:
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="skill-contract-audit-count-mismatch",
                        path="scripts/audit_skill_contracts.py",
                        message=f"Skill contract audit must report {expected_skill_count}/{expected_skill_count} skills OK.",
                    )
                )
        except Exception as exc:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="skill-contract-auditor-error",
                    path="scripts/audit_skill_contracts.py",
                    message=str(exc),
                )
            )

    if (root / "repo-template/scripts/verify_context_pack.py").exists():
        try:
            context_pack = _load_context_pack_module(root)
            for issue in context_pack.check_context_pack(root / "repo-template"):
                issues.append(
                    ToolkitIssue(
                        severity=issue.severity,
                        code=f"context-pack-{issue.code}",
                        path=f"repo-template/{issue.path}",
                        message=issue.message,
                    )
                )
        except Exception as exc:
            issues.append(
                ToolkitIssue(
                    severity="error",
                    code="context-pack-verifier-error",
                    path="repo-template/scripts/verify_context_pack.py",
                    message=str(exc),
                )
            )

    for current_root, dir_names, file_names in os.walk(root):
        current = Path(current_root)
        for dir_name in list(dir_names):
            if dir_name in GENERATED_PATTERNS:
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="generated-cache-present",
                        path=_relative(root, current / dir_name),
                        message="Generated cache directories must not be packaged.",
                    )
                )
        for file_name in file_names:
            if file_name in MANIFEST_EXCLUDED_FILES:
                continue
            path = current / file_name
            relative = _relative(root, path)
            if path.suffix == ".pyc":
                issues.append(
                    ToolkitIssue(
                        severity="error",
                        code="generated-bytecode-present",
                        path=relative,
                        message="Python bytecode must not be packaged.",
                    )
                )
            if path.is_file() and path.stat().st_size <= 1_000_000:
                for line_number, line in enumerate(_read_text(path).splitlines(), start=1):
                    if HARDCODED_BROWSER_PLUGIN_PATH_RE.search(line):
                        issues.append(
                            ToolkitIssue(
                                severity="error",
                                code="hardcoded-browser-plugin-path",
                                path=relative,
                                message=f"Line {line_number} hardcodes a Browser plugin cache path or version.",
                            )
                        )
                    if SECRET_RE.search(line) and not _secret_line_allowed(line):
                        if relative.startswith("reverse-skill/") and _allow_reverse_pack_secret_pattern(relative):
                            continue
                        issues.append(
                            ToolkitIssue(
                                severity="error",
                                code="sensitive-pattern",
                                path=relative,
                                message=f"Line {line_number} looks like it contains a secret.",
                            )
                        )
                    if PRIVATE_HOME_PATH_RE.search(line) and not _private_path_line_allowed(line):
                        if relative.startswith("reverse-skill/") and _allow_reverse_pack_private_path(relative, line):
                            continue
                        issues.append(
                            ToolkitIssue(
                                severity="error",
                                code="private-home-path",
                                path=relative,
                                message=f"Line {line_number} contains a private home path; use a placeholder.",
                            )
                        )

    return sorted(issues)


def build_report(root: str | Path = ".") -> dict[str, object]:
    issues = check_toolkit(root)
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    return {
        "ok": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": [issue.to_dict() for issue in issues],
    }


def _print_report(report: dict[str, object]) -> None:
    if report["ok"]:
        print("Workflow toolkit OK")
        return

    print(f"Workflow toolkit issues: {report['error_count']} error(s), {report['warning_count']} warning(s)")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the Codex workflow toolkit package.")
    parser.add_argument("root", nargs="?", default=".", help="Toolkit root to verify.")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
