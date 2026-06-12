from pathlib import Path

from scripts.benchmark_skill_polish import _metrics, _score_kit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skill(root: Path, name: str, body: str = "") -> None:
    _write(
        root / f"skills/{name}/SKILL.md",
        f"---\nname: {name}\ndescription: Use when testing.\n---\n\n# {name}\n\n{body}\n",
    )


def test_score_kit_counts_skill_polish_contracts(tmp_path):
    kit = tmp_path / "kit"
    for name in (
        "debug-loop",
        "completion-review",
        "frontend-qa",
        "decision-record",
        "repo-onboarding",
        "spec-kit-xl",
        "release-readiness",
    ):
        _skill(kit, name)

    _write(
        kit / "skills/frontend-qa/SKILL.md",
        "Keyboard Focus Contrast ARIA Reduced motion Output Shape\n",
    )
    _write(
        kit / "skills/release-readiness/SKILL.md",
        "artifact quality gate manifest archive checksum install drill rollback Output Shape\n",
    )
    _write(kit / "skills/spec-kit-xl/SKILL.md", "references/spec-template.md Output Shape\n")
    _write(kit / "skills/spec-kit-xl/references/spec-template.md", "# Template\n")

    scores = _score_kit(kit)

    assert scores["Accessibility coverage"] == 5
    assert scores["Release readiness"] == 6
    assert scores["Progressive disclosure"] == 3


def test_metrics_report_positive_delta(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    _skill(pre, "debug-loop", "Feedback Loop First\n")
    _skill(post, "debug-loop", "Feedback Loop First failing test captured trace replay property/fuzz loop regression test deterministic loop Output Shape\n")
    _skill(post, "release-readiness", "artifact quality gate manifest archive checksum install drill rollback Output Shape\n")

    metric_by_name = {metric.name: metric for metric in _metrics(pre, post)}

    assert metric_by_name["Skill count"].delta == 1
    assert metric_by_name["Feedback Loop First"].delta == 5
    assert metric_by_name["Release readiness"].delta == 6
