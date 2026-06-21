#!/usr/bin/env python3
"""Verify a Codex repo context pack without starting app services."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_FILES = (
    "AGENTS.md",
    "docs/commands.md",
    "docs/architecture.md",
    "docs/testing.md",
    "docs/quality-gates.md",
    "docs/subagents.md",
    "docs/observability.md",
    "docs/mcp-pilot.md",
    "docs/codegraph-pilot.md",
    "docs/memory-recall-pilot.md",
    "docs/codex-usage.md",
    "docs/codex-playbook.md",
    "docs/glossary.md",
    "docs/decisions/README.md",
    "docs/specs/README.md",
)

TEXT_FILES = (
    "AGENTS.md",
    "docs/commands.md",
    "docs/testing.md",
    "docs/quality-gates.md",
    "docs/subagents.md",
    "docs/observability.md",
    "docs/mcp-pilot.md",
    "docs/codegraph-pilot.md",
    "docs/memory-recall-pilot.md",
    "docs/codex-usage.md",
    "docs/codex-playbook.md",
    "docs/glossary.md",
    "docs/decisions/README.md",
    "docs/specs/README.md",
)

BARE_PYTHON_RE = re.compile(r"(^|[`>\s])python( -m| scripts/)")
SECRET_RE = re.compile(
    r"sk-[A-Za-z0-9]{20,}|BEGIN (?:RSA|OPENSSH|PRIVATE) KEY|"
    r"(?:api[_-]?key|secret|password)\s*=",
    re.IGNORECASE,
)
PRIVATE_HOME_PATH_RE = re.compile(r"/(?:Users|home)/(?!\[|\<|path/to/)([A-Za-z0-9._-]+)(?:/|$)")
REQUIRED_QUALITY_GATE_TERMS = (
    "Hook Review Checklist",
    "advisory",
    "fail-open",
    "blocking",
    "External Component Gate",
    "curl-to-shell",
    "自动 memory 写入",
)
REQUIRED_MCP_PERMISSION_TERMS = (
    "docs-only",
    "read-only local",
    "local write",
    "external read",
    "external write",
    "destructive / production-risk",
    "allowed tools",
    "denied tools",
    "rollback/fallback",
)
REQUIRED_SUBAGENT_CONTRACT_TERMS = (
    "V3.1 Prompt Contract",
    "subagent suitability check",
    "subagent 工具实际可用且未被平台权限阻止",
    "AGENTS.override",
    "长期授权即视为显式授权",
    "本轮重复授权不是必要条件",
    "不包括已加载长期授权后缺少本轮重复授权",
    "No-Dispatch Decision",
    "tool permission constraint",
    "allowed write set",
    "off-limits",
    "lifecycle close",
    "implementation worker",
    "batch worker",
)
FORBIDDEN_UNCONDITIONAL_SUBAGENT_DISPATCH_PHRASES = (
    "不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或 dispatch",
    "不要因为当前对话没有再次要求并行就跳过 suitability check 或安全 dispatch",
    "不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或安全 dispatch",
)
FORBIDDEN_REPEAT_AUTH_SUBAGENT_PHRASES = (
    "当前工具层仍要求本轮显式授权",
    "当前工具要求本轮显式授权",
    "工具要求本轮显式授权",
    "长期授权需要本轮确认",
    "已加载长期授权但仍记录 No-Dispatch: tool permission constraint",
)
REQUIRED_CODEGRAPH_TERMS = (
    "Code Graph Pilot",
    "不是真相源",
    "不默认安装",
    "不默认启用",
    "python3 scripts/render_usage_row.py pilot --pilot codegraph",
)
REQUIRED_MEMORY_RECALL_TERMS = (
    "Memory Recall Pilot",
    "不是真相源",
    "不默认启用 memory hook",
    "不默认启用 MCP memory writer",
    "raw transcript",
    "provenance",
)


@dataclass(frozen=True, order=True)
class ContextPackIssue:
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


def _existing_text_files(root: Path) -> Iterable[tuple[str, str]]:
    for relative in TEXT_FILES:
        path = root / relative
        if path.exists() and path.is_file():
            yield relative, _read_text(path)


def _line_has_bare_python(line: str) -> bool:
    if ".venv/bin/python" in line or "python3" in line:
        return False
    return bool(BARE_PYTHON_RE.search(line))


def _is_usage_history(path: str) -> bool:
    return path == "docs/codex-usage.md"


def _architecture_docs(root: Path) -> list[str]:
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return []
    return sorted(path.name for path in docs_dir.iterdir() if path.name.lower() == "architecture.md")


def _has_usage_review_mechanism(text: str) -> bool:
    return "周期复盘" in text or "阶段复盘" in text


def _require_terms(
    issues: list[ContextPackIssue],
    root: Path,
    relative: str,
    terms: tuple[str, ...],
    code: str,
) -> None:
    path = root / relative
    if not path.exists():
        return
    text = _read_text(path)
    for term in terms:
        if term not in text:
            issues.append(
                ContextPackIssue(
                    severity="error",
                    code=code,
                    path=relative,
                    message=f"{relative} must include V3.1 guidance term: {term}.",
                )
            )


def check_context_pack(root: str | Path = ".") -> list[ContextPackIssue]:
    root = Path(root)
    issues: list[ContextPackIssue] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).exists():
            issues.append(
                ContextPackIssue(
                    severity="error",
                    code="missing-required-file",
                    path=relative,
                    message="Required context pack file is missing.",
                )
            )

    architecture_docs = _architecture_docs(root)
    if len(architecture_docs) > 1:
        issues.append(
            ContextPackIssue(
                severity="error",
                code="architecture-case-duplicate",
                path="docs/",
                message=f"Multiple architecture docs differ only by case: {', '.join(architecture_docs)}.",
            )
        )

    agents_text = _read_text(root / "AGENTS.md") if (root / "AGENTS.md").exists() else ""
    if architecture_docs and not any(f"docs/{name}" in agents_text for name in architecture_docs):
        issues.append(
            ContextPackIssue(
                severity="error",
                code="missing-architecture-reference",
                path="AGENTS.md",
                message="AGENTS.md must reference the repo architecture document.",
            )
        )

    usage_path = root / "docs/codex-usage.md"
    if usage_path.exists() and not _has_usage_review_mechanism(_read_text(usage_path)):
        issues.append(
            ContextPackIssue(
                severity="error",
                code="missing-usage-review",
                path="docs/codex-usage.md",
                message="docs/codex-usage.md must include periodic or stage review guidance.",
            )
        )

    _require_terms(issues, root, "docs/quality-gates.md", REQUIRED_QUALITY_GATE_TERMS, "missing-v3-1-hook-guidance")
    _require_terms(issues, root, "docs/mcp-pilot.md", REQUIRED_MCP_PERMISSION_TERMS, "missing-v3-1-mcp-permission-guidance")
    _require_terms(issues, root, "docs/subagents.md", REQUIRED_SUBAGENT_CONTRACT_TERMS, "missing-v3-1-subagent-contract")
    subagents_path = root / "docs/subagents.md"
    if subagents_path.exists():
        subagents_text = _read_text(subagents_path)
        forbidden_phrase = next(
            (
                phrase
                for phrase in FORBIDDEN_UNCONDITIONAL_SUBAGENT_DISPATCH_PHRASES
                if phrase in subagents_text
            ),
            None,
        )
        if forbidden_phrase:
            issues.append(
                ContextPackIssue(
                    severity="error",
                    code="subagents-unconditional-dispatch-guidance",
                    path="docs/subagents.md",
                    message=(
                        "docs/subagents.md must not treat long-term suitability-check authorization as permission "
                        f"to bypass current runtime/tool dispatch gates: {forbidden_phrase}"
                    ),
                )
            )
        repeat_auth_phrase = next(
            (
                phrase
                for phrase in FORBIDDEN_REPEAT_AUTH_SUBAGENT_PHRASES
                if phrase in subagents_text
            ),
            None,
        )
        if repeat_auth_phrase:
            issues.append(
                ContextPackIssue(
                    severity="error",
                    code="subagents-repeat-authorization-regression",
                    path="docs/subagents.md",
                    message=(
                        "docs/subagents.md must not require current-turn repeated authorization once loaded "
                        f"AGENTS/AGENTS.override long-term authorization is present: {repeat_auth_phrase}"
                    ),
                )
            )
    _require_terms(issues, root, "docs/codegraph-pilot.md", REQUIRED_CODEGRAPH_TERMS, "missing-codegraph-pilot-guidance")
    _require_terms(issues, root, "docs/memory-recall-pilot.md", REQUIRED_MEMORY_RECALL_TERMS, "missing-memory-recall-guidance")

    for relative, text in _existing_text_files(root):
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _line_has_bare_python(line) and not _is_usage_history(relative):
                issues.append(
                    ContextPackIssue(
                        severity="error",
                        code="bare-python-command",
                        path=relative,
                        message=f"Line {line_number} uses an unverified python command: {line.strip()}",
                    )
                )
            if SECRET_RE.search(line):
                issues.append(
                    ContextPackIssue(
                        severity="error",
                        code="sensitive-pattern",
                        path=relative,
                        message=f"Line {line_number} looks like it contains a secret or endpoint value.",
                    )
                )
            if PRIVATE_HOME_PATH_RE.search(line) and "/path/to/" not in line:
                issues.append(
                    ContextPackIssue(
                        severity="error",
                        code="private-home-path",
                        path=relative,
                        message=f"Line {line_number} contains a private home path; use a placeholder.",
                    )
                )

    return sorted(issues)


def build_report(root: str | Path = ".") -> dict[str, object]:
    issues = check_context_pack(root)
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
        print("Context pack OK")
        return

    print(f"Context pack issues: {report['error_count']} error(s), {report['warning_count']} warning(s)")
    for issue in report["issues"]:
        print(f"[{issue['severity']}] {issue['code']} {issue['path']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Codex context pack files.")
    parser.add_argument("root", nargs="?", default=".", help="Repository root to verify.")
    args = parser.parse_args(argv)

    report = build_report(args.root)
    _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
