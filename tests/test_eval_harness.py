import json
import sys
from pathlib import Path

import pytest

from eval.harness import EvalError, EvalHarness, FixtureRunner, ShadowRunner, SubprocessRunner, load_suite


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "eval/fixtures/routing-demo.json"
SOURCE_COMMIT = "a" * 40


def _verify_isolation(runner, mode):
    return True


def _real_subject():
    return {"kind": "component", "id": "fixture-test-component", "content_sha256": "a" * 64}


def test_fixture_paired_eval_has_independent_held_out_and_stability():
    report = EvalHarness(FixtureRunner(), seed=11).run(load_suite(SUITE))
    assert report["fixture_only"] is True
    assert report["source_commit"] is None
    assert report["verdict"] == "pass"
    assert report["promotion_decision"] == "hold"
    assert report["case_counts"] == {"total": 5, "train": 3, "held_out": 2, "runs": 30, "inconclusive_runs": 0}
    trigger = report["metrics"]["trigger"]
    assert trigger["held_out"]["precision"] == 1.0
    assert trigger["held_out"]["recall"] == 1.0
    assert trigger["stability_rate"] == 1.0
    assert all(len(record["order"]) == 2 for record in report["pair_records"])
    assert all(pair["label_a"] != pair["label_b"] for pair in report["blind_review"]["pairs"])
    assert len(report["blind_review"]["reviewer_packets"]) == len(report["pair_records"])
    assert set(report["blind_review"]["reviewer_packets"][0]) >= {"blind_pair_id", "sample_a", "sample_b"}
    assert report["blind_review"]["required"] is False


def test_fixture_shadow_never_invokes_or_writes():
    report = EvalHarness(FixtureRunner(), seed=2).run(load_suite(SUITE), mode="shadow", repetitions=2)
    assert report["mode"] == "shadow"
    assert report["verdict"] == "pass"
    assert report["metrics"]["safety"]["violations"] == 0
    assert all(run["invoked"] is False for run in report["evidence"]["raw_runs"])
    assert all(run["route_suggestion"] in {None, "fixture-skill"} for run in report["evidence"]["raw_runs"])


def test_shadow_runner_forces_route_only_mode():
    report = EvalHarness(ShadowRunner(FixtureRunner()), seed=2).run(load_suite(SUITE), mode="shadow", repetitions=1)
    assert report["verdict"] == "pass"
    assert all(not run["invoked"] for run in report["evidence"]["raw_runs"])


def test_subprocess_runner_receives_clean_context_and_json_result():
    command = [
        sys.executable,
        "-c",
        "import json,os; print(json.dumps({{'invoked': os.getenv('EVAL_VARIANT') == 'with', 'success': True, 'tool_calls': [], 'writes': [], 'external_effects': [], 'tokens': 10, 'duration_ms': 1}}))",
    ]
    report = EvalHarness(
        SubprocessRunner(command),
        seed=3,
        isolation_verifier=_verify_isolation,
        subject=_real_subject(),
        source_commit=SOURCE_COMMIT,
    ).run(load_suite(SUITE), repetitions=1)
    assert report["fixture_only"] is False
    assert report["source_commit"] == SOURCE_COMMIT
    assert report["evidence"]["clean_context_per_run"] is True
    assert report["metrics"]["safety"]["violations"] == 0


class _LyingShadowRunner:
    fixture_only = False

    def run(self, prompt, *, case, variant, mode, worktree, home, run_id, repetition):
        (worktree / "unexpected.txt").write_text("side effect", encoding="utf-8")
        return {"route_suggestion": case.get("expected_skill"), "invoked": False, "success": True}


def test_shadow_detects_filesystem_write_even_when_runner_omits_it():
    report = EvalHarness(
        _LyingShadowRunner(), isolation_verifier=_verify_isolation, subject=_real_subject(), source_commit=SOURCE_COMMIT
    ).run(load_suite(SUITE), mode="shadow", repetitions=1)
    assert report["verdict"] == "fail"
    assert report["metrics"]["safety"]["violations"] > 0
    assert any(run["filesystem_writes"] for run in report["evidence"]["raw_runs"])


class _UnsafeRunner(FixtureRunner):
    fixture_only = False

    def run(self, *args, **kwargs):
        result = dict(super().run(*args, **kwargs))
        result["approval_forged"] = True
        return result


def test_safety_violation_forces_rollback_decision():
    report = EvalHarness(
        _UnsafeRunner(), isolation_verifier=_verify_isolation, subject=_real_subject(), source_commit=SOURCE_COMMIT
    ).run(load_suite(SUITE), repetitions=1)
    assert report["verdict"] == "fail"
    assert report["promotion_decision"] == "rollback"
    assert any(finding["reason"] == "approval was forged" for finding in report["safety_findings"])


class _NoBenefitRunner(FixtureRunner):
    fixture_only = False

    def run(self, *args, **kwargs):
        result = dict(super().run(*args, **kwargs))
        result["tokens"] = 28
        result["duration_ms"] = 2
        return result


def test_paired_pass_requires_behavior_benefit_for_real_runner():
    report = EvalHarness(
        _NoBenefitRunner(), isolation_verifier=_verify_isolation, subject=_real_subject(), source_commit=SOURCE_COMMIT
    ).run(load_suite(SUITE), repetitions=1)
    assert report["metrics"]["behavior"]["passed"] is False
    assert report["verdict"] == "fail"
    assert report["promotion_decision"] == "tighten"


def test_inconclusive_infrastructure_run_holds_instead_of_tightening_candidate():
    suite = {
        "schema_version": "4.2",
        "suite_id": "inconclusive-behavior",
        "promotion_eligible": True,
        "repetitions": 1,
        "cases": [
            {"case_id": "train", "prompt": "x", "family": "behavior", "split": "train", "assertions": [{"type": "success"}]},
            {"case_id": "held", "prompt": "y", "family": "behavior", "split": "held_out", "assertions": [{"type": "success"}]},
        ],
    }

    class InfrastructureFailureRunner:
        fixture_only = False

        def run(self, prompt, *, variant, **kwargs):
            if variant == "with":
                return {
                    "success": False,
                    "evaluation_status": "inconclusive",
                    "failure_categories": ["rate_limited"],
                }
            return {"success": True, "tokens": 10, "duration_ms": 1}

    report = EvalHarness(
        InfrastructureFailureRunner(),
        isolation_verifier=_verify_isolation,
        subject=_real_subject(),
        source_commit=SOURCE_COMMIT,
    ).run(suite, repetitions=1)

    assert report["verdict"] == "fail"
    assert report["promotion_decision"] == "hold"
    assert report["case_counts"]["inconclusive_runs"] == 2
    assert report["metrics"]["behavior"]["inconclusive_runs"] == 2
    assert all(
        run["failure_categories"] == ["rate_limited"]
        for run in report["evidence"]["raw_runs"]
        if run["variant"] == "with"
    )


def test_only_explicit_behavior_suite_can_recommend_promotion():
    class BenefitRunner(FixtureRunner):
        fixture_only = False

    suite = load_suite(SUITE)
    suite["promotion_eligible"] = True
    report = EvalHarness(
        BenefitRunner(),
        isolation_verifier=_verify_isolation,
        subject=_real_subject(),
        source_commit=SOURCE_COMMIT,
    ).run(suite, repetitions=1)

    assert report["verdict"] == "pass"
    assert report["metrics"]["behavior"]["evaluated"] is True
    assert report["promotion_eligible"] is True
    assert report["promotion_decision"] == "promote"


def test_behavior_only_suite_does_not_report_invocation_metrics():
    suite = {
        "schema_version": "4.2",
        "suite_id": "behavior-only",
        "promotion_eligible": False,
        "repetitions": 1,
        "cases": [
            {"case_id": "train", "prompt": "x", "family": "behavior", "split": "train", "assertions": [{"type": "success"}]},
            {"case_id": "held", "prompt": "y", "family": "behavior", "split": "held_out", "assertions": [{"type": "success"}]},
        ],
    }

    class BehaviorRunner:
        fixture_only = False

        def run(self, prompt, **kwargs):
            return {"success": True, "tokens": 10, "duration_ms": 1}

    report = EvalHarness(
        BehaviorRunner(), isolation_verifier=_verify_isolation, subject=_real_subject(), source_commit=SOURCE_COMMIT
    ).run(suite, repetitions=1)

    assert report["metrics"]["trigger"]["evaluated"] is False
    assert report["metrics"]["trigger"]["total_cases"] == 0
    assert report["metrics"]["behavior"]["evaluated"] is True


def test_baseline_positive_assertions_are_not_counted_as_failures():
    report = EvalHarness(FixtureRunner()).run(load_suite(SUITE), repetitions=1)
    assert report["assertion_failures"] == 0
    baseline_checks = [
        check
        for run in report["evidence"]["raw_runs"]
        if run["variant"] == "without"
        for check in run["assertions"]
        if check["type"] == "skill_invoked"
    ]
    assert baseline_checks and all(check["ok"] for check in baseline_checks)


def test_unknown_assertion_fails_closed(tmp_path):
    suite = {
        "schema_version": "4.2",
        "suite_id": "unknown-assertion",
        "repetitions": 1,
        "cases": [
            {"case_id": "train", "prompt": "x", "family": "x", "split": "train", "assertions": [{"type": "made-up"}]},
            {"case_id": "held", "prompt": "y", "family": "x", "split": "held_out", "assertions": []},
        ],
    }
    report = EvalHarness(FixtureRunner()).run(suite, repetitions=1)
    assert report["verdict"] == "fail"
    assert report["assertion_failures"] > 0


def test_subjective_suite_requires_blind_review():
    suite = load_suite(SUITE)
    suite["cases"][0]["subjective"] = True
    report = EvalHarness(FixtureRunner()).run(suite, repetitions=1)
    assert report["verdict"] == "needs_human_review"
    assert report["blind_review"]["required"] is True


def test_completed_blind_review_affects_subjective_verdict():
    suite = load_suite(SUITE)
    suite["cases"][0]["subjective"] = True
    pending = EvalHarness(FixtureRunner(), seed=8).run(suite, repetitions=1)
    subjective_id = suite["cases"][0]["case_id"]
    packet = next(item for item in pending["blind_review"]["reviewer_packets"] if item["case_id"] == subjective_id)
    winner = "a" if "enabled" in packet["sample_a"]["output"] else "b"
    review = [{"blind_pair_id": packet["blind_pair_id"], "winner": winner, "criteria": {"quality": "pass"}}]
    reviewed = EvalHarness(FixtureRunner(), seed=8).run(suite, repetitions=1, human_reviews=review)
    assert reviewed["verdict"] == "pass"
    assert reviewed["blind_review"]["passed"] is True
    assert reviewed["blind_review"]["records"][0]["candidate_result"] == "preferred"


def test_suite_requires_held_out_case():
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    suite["cases"] = [case for case in suite["cases"] if case["split"] != "held_out"]
    with pytest.raises(EvalError, match="held_out"):
        EvalHarness(FixtureRunner()).run(suite)


def test_non_fixture_runner_is_rejected_before_execution_without_trusted_isolation():
    runner = _LyingShadowRunner()
    with pytest.raises(EvalError, match="trusted isolation verifier required"):
        EvalHarness(runner).run(load_suite(SUITE), mode="shadow", repetitions=1)


def test_non_fixture_runner_requires_locked_subject_after_isolation_is_verified():
    runner = _LyingShadowRunner()
    with pytest.raises(EvalError, match="locked subject binding"):
        EvalHarness(runner, isolation_verifier=_verify_isolation, source_commit=SOURCE_COMMIT).run(
            load_suite(SUITE), mode="shadow", repetitions=1
        )


def test_non_fixture_runner_requires_source_commit_after_subject_is_bound():
    runner = _LyingShadowRunner()
    with pytest.raises(EvalError, match="source commit binding"):
        EvalHarness(
            runner,
            isolation_verifier=_verify_isolation,
            subject=_real_subject(),
        ).run(load_suite(SUITE), mode="shadow", repetitions=1)
