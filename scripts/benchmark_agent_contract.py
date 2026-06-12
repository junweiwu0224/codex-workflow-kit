#!/usr/bin/env python3
"""Measure V3.1 agent contract improvements against the previous V3.1 release."""
from __future__ import annotations

import argparse
import json
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PRE_AGENT_CONTRACT_VERSION = "2026.06.12.1"


@dataclass(frozen=True)
class Metric:
    name: str
    pre_agent_contract: int
    post_agent_contract: int
    maximum: int | None = None

    @property
    def delta(self) -> int:
        return self.post_agent_contract - self.pre_agent_contract

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "name": self.name,
            "pre_agent_contract": self.pre_agent_contract,
            "post_agent_contract": self.post_agent_contract,
            "delta": self.delta,
            "maximum": self.maximum,
        }


def _extract_release(release_dir: Path, version: str, target_root: Path) -> Path:
    archive = release_dir / f"codex-workflow-kit-{version}.tar.gz"
    if not archive.exists():
        raise FileNotFoundError(f"Missing release archive: {archive}")
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(target_root, filter="data")
    return target_root / "codex-workflow-kit"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _score_prompt_cards(text: str) -> int:
    cards = (
        "read-only code mapper",
        "implementation worker",
        "test/debug investigator",
        "batch worker",
        "coverage-gap auditor",
        "frontend QA reviewer",
        "docs/content-contract reviewer",
        "architecture/migration reviewer",
    )
    contract_terms = (
        "Handoff Envelope",
        "History/Input Filter",
        "Command/Tool Risk Policy",
        "Step Budget / Stop Condition",
        "Return Envelope",
    )
    score = 0
    for card in cards:
        position = text.find(f"### {card}")
        if position == -1:
            continue
        next_position = text.find("\n### ", position + 1)
        section = text[position:] if next_position == -1 else text[position:next_position]
        score += _count_terms(section, contract_terms)
    return score


def _score_kit(kit: Path) -> dict[str, int]:
    subagents = _read(kit / "repo-template/docs/subagents.md")
    global_agents = _read(kit / "global/AGENTS.md")
    repo_agents = _read(kit / "repo-template/AGENTS.md")
    verifier = _read(kit / "scripts/verify_toolkit.py")
    usage_row = _read(kit / "scripts/render_usage_row.py")
    evidence = _read(kit / "docs/V3.1-ADOPTION-EVIDENCE.md")
    research = _read(kit / "docs/V3.1-AGENT-RESEARCH-20.md")
    benchmark = _read(kit / "docs/V3.1-AGENT-CONTRACT-BENCHMARK.md")

    contract_terms = (
        "Handoff Envelope",
        "Return Envelope",
        "History/Input Filter",
        "Command/Tool Risk Policy",
        "Step Budget / Stop Condition",
        "Lifecycle Ledger",
        "No-Dispatch Decision",
    )
    command_risk_terms = (
        "docs-only",
        "read-only local",
        "local write",
        "dev server/service",
        "network/external read",
        "external write",
        "destructive / production-risk",
    )
    stop_terms = ("NEEDS_CONTEXT", "BLOCKED", "STOPPED_BY_BUDGET")
    ledger_terms = ("id", "role/card", "read/write", "target", "previous_status", "integrated/discarded")
    usage_pilots = ("subagent-contract", "agent-lifecycle-ledger", "agent-eval-evidence")
    source_repos = (
        "langchain-ai/langgraph",
        "microsoft/autogen",
        "crewAIInc/crewAI",
        "openai/openai-agents-python",
        "agno-agi/agno",
        "huggingface/smolagents",
        "lastmile-ai/mcp-agent",
        "modelcontextprotocol/python-sdk",
        "AgentOps-AI/agentops",
        "Arize-ai/phoenix",
        "promptfoo/promptfoo",
        "All-Hands-AI/OpenHands",
        "SWE-agent/SWE-agent",
        "aider-ai/aider",
        "Significant-Gravitas/AutoGPT",
        "geekan/MetaGPT",
        "OpenBMB/ChatDev",
        "camel-ai/camel",
        "browser-use/browser-use",
        "langfuse/langfuse",
    )

    return {
        "Core contract terms in subagents.md": _count_terms(subagents, contract_terms),
        "Prompt card contract coverage": _score_prompt_cards(subagents),
        "Command/tool risk levels": _count_terms(subagents, command_risk_terms),
        "Stop-condition statuses": _count_terms(subagents, stop_terms),
        "Lifecycle ledger fields": _count_terms(subagents, ledger_terms),
        "Global AGENTS contract routing": _count_terms(global_agents, contract_terms),
        "Repo AGENTS contract routing": _count_terms(repo_agents, contract_terms),
        "Verifier contract checks": _count_terms(verifier, contract_terms),
        "Usage pilot defaults": _count_terms(usage_row, usage_pilots),
        "Agent research source coverage": _count_terms(research, source_repos),
        "Evidence contract references": _count_terms(evidence + benchmark, contract_terms),
    }


def _metrics(pre: Path, post: Path) -> list[Metric]:
    pre_scores = _score_kit(pre)
    post_scores = _score_kit(post)
    maximums = {
        "Core contract terms in subagents.md": 7,
        "Command/tool risk levels": 7,
        "Stop-condition statuses": 3,
        "Lifecycle ledger fields": 6,
        "Global AGENTS contract routing": 7,
        "Repo AGENTS contract routing": 7,
        "Usage pilot defaults": 3,
        "Agent research source coverage": 20,
    }
    return [
        Metric(
            name=name,
            pre_agent_contract=pre_scores[name],
            post_agent_contract=post_scores[name],
            maximum=maximums.get(name),
        )
        for name in sorted(post_scores)
    ]


def build_report(root: Path, pre_agent_contract_version: str, post_root: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    post = post_root.resolve() if post_root else root
    with tempfile.TemporaryDirectory() as temp_name:
        pre = _extract_release(root / "releases", pre_agent_contract_version, Path(temp_name) / "pre-agent-contract")
        metrics = _metrics(pre, post)

    totals = {
        "pre_agent_contract": sum(metric.pre_agent_contract for metric in metrics),
        "post_agent_contract": sum(metric.post_agent_contract for metric in metrics),
    }
    totals["delta"] = totals["post_agent_contract"] - totals["pre_agent_contract"]
    totals["delta_percent"] = round(
        (totals["delta"] / totals["pre_agent_contract"] * 100) if totals["pre_agent_contract"] else 0.0,
        2,
    )
    return {
        "versions": {
            "pre-agent-contract": pre_agent_contract_version,
            "post-agent-contract": _read(post / "VERSION").strip() or "working-tree",
        },
        "method": (
            "Compare the archived pre-agent-contract release with the current toolkit tree and count explicit "
            "subagent handoff, return, context-filtering, command-risk, stop-condition, ledger, usage, "
            "and research-evidence coverage."
        ),
        "metrics": [metric.to_dict() for metric in metrics],
        "totals": totals,
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# V3.1 Agent Contract Benchmark",
        "",
        f"- pre-agent-contract: `{report['versions']['pre-agent-contract']}`",
        f"- post-agent-contract: `{report['versions']['post-agent-contract']}`",
        "- Method: unpack the pre-agent-contract release archive, compare it with the post-agent-contract toolkit tree, and count explicit agent contract coverage.",
        "",
        "## Results",
        "",
        "| Metric | pre-agent-contract | post-agent-contract | Delta | Maximum |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in report["metrics"]:
        maximum = "" if metric["maximum"] is None else metric["maximum"]
        lines.append(
            f"| {metric['name']} | {metric['pre_agent_contract']} | "
            f"{metric['post_agent_contract']} | {metric['delta']} | {maximum} |"
        )
    totals = report["totals"]
    lines.extend(
        [
            "",
            "## Measured improvement",
            "",
            f"- Total explicit agent contract points: `{totals['pre_agent_contract']}` -> `{totals['post_agent_contract']}` (`+{totals['delta']}`, `{totals['delta_percent']}%`).",
            "- Handoff Envelope and Return Envelope coverage measures whether dispatch and result review fields are explicit.",
            "- Lifecycle Ledger coverage measures whether close evidence and integrated/discarded decisions are tracked.",
            "- History/Input Filter and Command/Tool Risk Policy coverage measures whether subagents receive bounded context and command permissions.",
            "- Step Budget / Stop Condition coverage measures whether subagents can stop with NEEDS_CONTEXT, BLOCKED, or STOPPED_BY_BUDGET instead of drifting.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark V3.1 agent contract improvements.")
    parser.add_argument("--root", default=".", help="Toolkit root containing releases/.")
    parser.add_argument("--pre-agent-contract-version", default=DEFAULT_PRE_AGENT_CONTRACT_VERSION)
    parser.add_argument("--post-root", default=None, help="Optional post-agent-contract toolkit root. Default: --root.")
    parser.add_argument("--json-out", default="docs/V3.1-AGENT-CONTRACT-BENCHMARK.json")
    parser.add_argument("--markdown-out", default="docs/V3.1-AGENT-CONTRACT-BENCHMARK.md")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    post_root = Path(args.post_root).resolve() if args.post_root else None
    report = build_report(root, args.pre_agent_contract_version, post_root)

    json_path = root / args.json_out
    markdown_path = root / args.markdown_out
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")

    print(f"Agent contract benchmark JSON: {json_path}")
    print(f"Agent contract benchmark report: {markdown_path}")
    print(json.dumps(report["totals"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
