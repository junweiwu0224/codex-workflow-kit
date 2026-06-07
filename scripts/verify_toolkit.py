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
)

REQUIRED_FILES = (
    "README.md",
    "QUICKSTART.md",
    "WORKFLOW-REVIEW.md",
    "VERSION",
    "MANIFEST.sha256",
    "install.sh",
    "global/AGENTS.md",
    "scripts/audit_repo_adoption.py",
    "scripts/build_release.py",
    "scripts/render_usage_row.py",
    "scripts/verify_live_install.py",
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
    "repo-template/docs/codex-usage.md",
    "repo-template/docs/codex-playbook.md",
    "repo-template/docs/glossary.md",
    "repo-template/docs/decisions/README.md",
    "repo-template/docs/specs/README.md",
    "scripts/verify_toolkit.py",
)

REQUIRED_README_TERMS = (
    "QUICKSTART.md",
    "VERSION",
    "MANIFEST.sha256",
    "scripts/build_release.py",
    "install.sh",
    "--repo-only",
    "scripts/verify_toolkit.py",
    "scripts/audit_repo_adoption.py",
    "scripts/render_usage_row.py",
    "scripts/verify_live_install.py",
    "pilot",
    "--json",
    "--markdown",
    "scripts/verify_context_pack.py",
    "WORKFLOW-REVIEW.md",
    "~/.codex/AGENTS.md",
    "~/.agents/skills/",
)

REQUIRED_WORKFLOW_REVIEW_TERMS = (
    "Workflow Review",
    "工作流复盘",
    "个人 Codex 宪法",
    "repo context pack",
    "MCP/代码图谱/memory",
    "hooks 质量门禁",
    "usage/效果评估",
    "security-review",
    "dependency-upgrade-review",
    "research-brief",
)
REQUIRED_P0_SKILL_ROUTE_TERMS = (
    "security-review",
    "dependency-upgrade-review",
    "research-brief",
)
REQUIRED_QUICKSTART_TERMS = (
    "Quickstart",
    "快速开始",
    "10 分钟流程",
    "python3 scripts/verify_toolkit.py",
    "python3 scripts/verify_live_install.py",
    "scripts/render_usage_row.py baseline",
    "./install.sh --dry-run",
    "./install.sh --repo-only --repo /path/to/repo --backup",
    "python3 scripts/verify_context_pack.py",
    "docs/codex-usage.md",
)
REQUIRED_PROACTIVE_SUBAGENT_TERMS = (
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
}
MANIFEST_EXCLUDED_SUFFIXES = {
    ".pyc",
}
MANIFEST_EXCLUDED_FILES = {
    ".DS_Store",
}

SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{20,}|BEGIN (?:RSA|OPENSSH|PRIVATE) KEY|"
    r"(?:api[_-]?key|secret|password)\s*=",
    re.IGNORECASE,
)
ALLOWED_SECRET_FIXTURES = ("sk-thisisnotarealkeybutshouldbeflagged",)
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
            files.append(path)
    return files


def _expected_manifest(root: Path) -> str:
    lines = []
    for path in _iter_manifest_files(root):
        lines.append(f"{_hash_file(path)}  {_relative(root, path)}")
    return "\n".join(lines) + "\n"


def _load_context_pack_module(root: Path):
    script = root / "repo-template/scripts/verify_context_pack.py"
    spec = importlib.util.spec_from_file_location("verify_context_pack_template", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load repo-template/scripts/verify_context_pack.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode
    return module


def _secret_line_allowed(line: str) -> bool:
    return any(fixture in line for fixture in ALLOWED_SECRET_FIXTURES)


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
        "scripts/audit_repo_adoption.py",
        "scripts/build_release.py",
        "scripts/render_usage_row.py",
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
                    if SECRET_RE.search(line) and not _secret_line_allowed(line):
                        issues.append(
                            ToolkitIssue(
                                severity="error",
                                code="sensitive-pattern",
                                path=relative,
                                message=f"Line {line_number} looks like it contains a secret.",
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
