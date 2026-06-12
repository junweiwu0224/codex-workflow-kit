#!/usr/bin/env python3
"""Measure V3.1 skill polish improvements against a pre-polish release."""
from __future__ import annotations

import argparse
import json
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PRE_POLISH_VERSION = "2026.06.12"


@dataclass(frozen=True)
class Metric:
    name: str
    pre_polish: int
    post_polish: int
    maximum: int | None = None

    @property
    def delta(self) -> int:
        return self.post_polish - self.pre_polish

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "name": self.name,
            "pre_polish": self.pre_polish,
            "post_polish": self.post_polish,
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


def _skill_files(kit: Path) -> list[Path]:
    skills = kit / "skills"
    if not skills.exists():
        return []
    return sorted(path for path in skills.glob("*/SKILL.md") if path.is_file())


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _count_skills_with_term(kit: Path, term: str) -> int:
    return sum(1 for path in _skill_files(kit) if term in _read(path))


def _score_kit(kit: Path) -> dict[str, int]:
    debug_loop = _read(kit / "skills/debug-loop/SKILL.md")
    completion_review = _read(kit / "skills/completion-review/SKILL.md")
    frontend_qa = _read(kit / "skills/frontend-qa/SKILL.md")
    decision_record = _read(kit / "skills/decision-record/SKILL.md")
    repo_onboarding = _read(kit / "skills/repo-onboarding/SKILL.md")
    spec_kit = _read(kit / "skills/spec-kit-xl/SKILL.md")
    release_readiness = _read(kit / "skills/release-readiness/SKILL.md")

    feedback_loop_terms = (
        "Feedback Loop First",
        "failing test",
        "captured trace replay",
        "property/fuzz loop",
        "regression test",
        "deterministic loop",
    )
    accessibility_terms = ("Keyboard", "Focus", "Contrast", "ARIA", "Reduced motion")
    artifact_terms = ("Artifact / Release Evidence Gate", "archive listing", "checksum", "install docs")
    adr_terms = ("Output Shape", "Completion Conditions", "Superseded", "Consequences")
    onboarding_terms = ("minimal context pack", "Core context pack", "Optional context pack")
    release_terms = ("artifact quality gate", "manifest", "archive", "checksum", "install drill", "rollback")

    spec_reference = kit / "skills/spec-kit-xl/references/spec-template.md"
    old_spec_asset = kit / "skills/spec-kit-xl/assets/spec-template.md"

    scores = {
        "Skill count": len(_skill_files(kit)),
        "Output Shape": _count_skills_with_term(kit, "Output Shape"),
        "Feedback Loop First": _count_terms(debug_loop, feedback_loop_terms),
        "Accessibility coverage": _count_terms(frontend_qa, accessibility_terms),
        "Artifact gate coverage": _count_terms(completion_review, artifact_terms),
        "ADR completion contract": _count_terms(decision_record, adr_terms),
        "Repo onboarding scope control": _count_terms(repo_onboarding, onboarding_terms),
        "Release readiness": _count_terms(release_readiness, release_terms),
        "Progressive disclosure": int(spec_reference.exists())
        + int("references/spec-template.md" in spec_kit)
        + int(not old_spec_asset.exists()),
    }
    return scores


def _metrics(pre: Path, post: Path) -> list[Metric]:
    pre_scores = _score_kit(pre)
    post_scores = _score_kit(post)
    maximums = {
        "Accessibility coverage": 5,
        "Artifact gate coverage": 4,
        "ADR completion contract": 4,
        "Feedback Loop First": 6,
        "Progressive disclosure": 3,
        "Release readiness": 6,
        "Repo onboarding scope control": 3,
    }
    return [
        Metric(name=name, pre_polish=pre_scores[name], post_polish=post_scores[name], maximum=maximums.get(name))
        for name in sorted(post_scores)
    ]


def build_report(root: Path, pre_polish_version: str, post_root: Path | None = None) -> dict[str, object]:
    root = root.resolve()
    post = post_root.resolve() if post_root else root
    with tempfile.TemporaryDirectory() as temp_name:
        pre = _extract_release(root / "releases", pre_polish_version, Path(temp_name) / "pre-polish")
        metrics = _metrics(pre, post)

    totals = {
        "pre_polish": sum(metric.pre_polish for metric in metrics),
        "post_polish": sum(metric.post_polish for metric in metrics),
    }
    totals["delta"] = totals["post_polish"] - totals["pre_polish"]
    totals["delta_percent"] = round((totals["delta"] / totals["pre_polish"] * 100) if totals["pre_polish"] else 0.0, 2)
    return {
        "versions": {
            "pre-polish": pre_polish_version,
            "post-polish": _read(post / "VERSION").strip() or "working-tree",
        },
        "method": "Compare the archived pre-polish release with the current post-polish toolkit tree.",
        "metrics": [metric.to_dict() for metric in metrics],
        "totals": totals,
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# V3.1 Skill Polish Benchmark",
        "",
        f"- pre-polish: `{report['versions']['pre-polish']}`",
        f"- post-polish: `{report['versions']['post-polish']}`",
        "- Method: unpack the pre-polish release archive, compare it with the post-polish toolkit tree, and count explicit skill contract coverage.",
        "",
        "## Results",
        "",
        "| Metric | pre-polish | post-polish | Delta | Maximum |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric in report["metrics"]:
        maximum = "" if metric["maximum"] is None else metric["maximum"]
        lines.append(
            f"| {metric['name']} | {metric['pre_polish']} | {metric['post_polish']} | {metric['delta']} | {maximum} |"
        )
    totals = report["totals"]
    lines.extend(
        [
            "",
            "## Measured improvement",
            "",
            f"- Total explicit contract points: `{totals['pre_polish']}` -> `{totals['post_polish']}` (`+{totals['delta']}`, `{totals['delta_percent']}%`).",
            "- Skill count increased through one pilot skill: `release-readiness`.",
            "- Output Shape coverage measures how many packaged skills now provide a concrete result contract.",
            "- Accessibility coverage measures Keyboard, Focus, Contrast, ARIA, and Reduced motion checks in `frontend-qa`.",
            "- Release readiness measures manifest/archive/checksum/install drill/rollback coverage for reusable artifacts.",
            "- Progressive disclosure measures the `spec-kit-xl` template moving from inline or asset placement into `references/spec-template.md`.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark V3.1 skill polish improvements.")
    parser.add_argument("--root", default=".", help="Toolkit root containing releases/.")
    parser.add_argument("--pre-polish-version", default=DEFAULT_PRE_POLISH_VERSION)
    parser.add_argument("--post-root", default=None, help="Optional post-polish toolkit root. Default: --root.")
    parser.add_argument("--json-out", default="docs/V3.1-SKILL-POLISH-BENCHMARK.json")
    parser.add_argument("--markdown-out", default="docs/V3.1-SKILL-POLISH-BENCHMARK.md")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    post_root = Path(args.post_root).resolve() if args.post_root else None
    report = build_report(root, args.pre_polish_version, post_root)

    json_path = root / args.json_out
    markdown_path = root / args.markdown_out
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")

    print(f"Skill polish benchmark JSON: {json_path}")
    print(f"Skill polish benchmark report: {markdown_path}")
    print(json.dumps(report["totals"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
