#!/usr/bin/env python3
"""Audit whether a repo is ready for repo-only context pack adoption."""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


CONTEXT_FILES = (
    "AGENTS.md",
    "docs/architecture.md",
    "docs/commands.md",
    "docs/testing.md",
    "docs/quality-gates.md",
    "docs/subagents.md",
    "docs/observability.md",
    "docs/mcp-pilot.md",
    "docs/codex-usage.md",
    "docs/codex-playbook.md",
    "docs/glossary.md",
    "docs/decisions/README.md",
    "docs/specs/README.md",
    "scripts/verify_context_pack.py",
    "tests/test_verify_context_pack.py",
)


@dataclass(frozen=True, order=True)
class AdoptionFinding:
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


def _architecture_case_matches(repo: Path) -> list[Path]:
    docs_dir = repo / "docs"
    if not docs_dir.exists():
        return []
    return sorted(
        path
        for path in docs_dir.iterdir()
        if path.is_file() and path.name.lower() == "architecture.md" and path.name != "architecture.md"
    )


def _git_status(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--short"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def audit_repo(repo: str | Path) -> dict[str, object]:
    repo = Path(repo).resolve()
    findings: list[AdoptionFinding] = []

    if not repo.exists() or not repo.is_dir():
        findings.append(
            AdoptionFinding(
                severity="error",
                code="repo-missing",
                path=str(repo),
                message="Target repository directory does not exist.",
            )
        )
    else:
        git_status = _git_status(repo)
        if git_status:
            findings.append(
                AdoptionFinding(
                    severity="warning",
                    code="dirty-worktree",
                    path=".",
                    message="Git worktree has uncommitted changes; review before installing context pack files.",
                )
            )

        if (repo / "AGENTS.md").exists():
            findings.append(
                AdoptionFinding(
                    severity="warning",
                    code="existing-agents",
                    path="AGENTS.md",
                    message="Existing AGENTS.md should be merged manually instead of overwritten.",
                )
            )

        for architecture_doc in _architecture_case_matches(repo):
            findings.append(
                AdoptionFinding(
                    severity="warning",
                    code="architecture-case-match",
                    path=architecture_doc.relative_to(repo).as_posix(),
                    message="Existing architecture doc differs by case; update references manually.",
                )
            )

        for relative in CONTEXT_FILES:
            if relative == "AGENTS.md":
                continue
            if (repo / relative).exists():
                findings.append(
                    AdoptionFinding(
                        severity="info",
                        code="existing-context-file",
                        path=relative,
                        message="Context pack target already exists; review before copying template.",
                    )
                )

    recommendation = "repo-only-install"
    if any(finding.severity in {"error", "warning"} for finding in findings):
        recommendation = "manual-merge"
    elif any(finding.code == "existing-context-file" for finding in findings):
        recommendation = "manual-merge"

    command = f"./install.sh --repo-only --repo {repo} --backup"
    return {
        "repo": str(repo),
        "recommendation": recommendation,
        "command": command,
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in sorted(findings)],
    }


def _print_report(report: dict[str, object]) -> None:
    print(f"Repo: {report['repo']}")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Command: {report['command']}")
    print(f"Findings: {report['finding_count']}")
    for finding in report["findings"]:
        print(f"[{finding['severity']}] {finding['code']} {finding['path']}: {finding['message']}")


def _markdown_cell(text: object) -> str:
    return str(text).replace("|", r"\|").replace("\n", " ")


def _markdown_code(text: object) -> str:
    escaped = _markdown_cell(text).replace("`", r"\`")
    return f"`{escaped}`"


def _markdown_findings(report: dict[str, object]) -> str:
    findings = report["findings"]
    if not findings:
        return "0"
    counts = Counter(finding["code"] for finding in findings)
    summaries = []
    for code, count in sorted(counts.items()):
        summary = _markdown_code(code)
        if count > 1:
            summary = f"{summary} x{count}"
        summaries.append(summary)
    return ", ".join(summaries)


def _print_markdown(reports: list[dict[str, object]]) -> None:
    print("| Repo | Recommendation | Findings | Command |")
    print("|---|---|---|---|")
    for report in reports:
        print(
            "| "
            f"{_markdown_code(report['repo'])} | "
            f"{_markdown_code(report['recommendation'])} | "
            f"{_markdown_findings(report)} | "
            f"{_markdown_code(report['command'])} |"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a repo before installing the Codex context pack.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    output_group.add_argument("--markdown", action="store_true", help="Print a Markdown table for adoption evidence.")
    parser.add_argument("repos", nargs="+", help="Repository root(s) to audit.")
    args = parser.parse_args(argv)

    exit_code = 0
    reports = [audit_repo(repo) for repo in args.repos]

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    elif args.markdown:
        _print_markdown(reports)
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            _print_report(report)

    for report in reports:
        if any(finding["severity"] == "error" for finding in report["findings"]):
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
