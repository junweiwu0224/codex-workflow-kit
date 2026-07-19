import json
import shutil
from pathlib import Path

import pytest

from eval.behavior_verifier import verify_behavior_case
from eval.harness import load_suite


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "eval/behavior_fixtures"
SUITE = ROOT / "eval/suites/v4.2-behavior-pilot.json"
SCHEMA = ROOT / "governance/eval-suite.schema.json"


def _worktree_for(tmp_path: Path, fixture_name: str) -> Path:
    target = tmp_path / "eval/behavior_fixtures" / fixture_name
    target.parent.mkdir(parents=True)
    shutil.copytree(FIXTURES / fixture_name, target)
    return tmp_path


@pytest.mark.parametrize(
    ("verification_id", "fixture_name"),
    [
        ("debug-loop-python-bug-v1", "debug-loop"),
        ("completion-review-no-go-v1", "completion-review"),
        ("decision-record-event-log-v1", "decision-record"),
        ("security-review-webhook-v1", "security-review"),
        ("spec-kit-xl-artifacts-v1", "spec-kit-xl"),
    ],
)
def test_behavior_fixtures_fail_before_a_correct_output_exists(tmp_path, verification_id, fixture_name):
    result = verify_behavior_case(verification_id, _worktree_for(tmp_path, fixture_name))
    assert result["passed"] is False
    assert result["checks"]
    assert "fail" in result["summary"]


def test_debug_loop_passes_only_with_unchanged_tests_and_real_unittest_success(tmp_path):
    worktree = _worktree_for(tmp_path, "debug-loop")
    source = worktree / "eval/behavior_fixtures/debug-loop/src/text_utils.py"
    source.write_text(
        '"""Small text helpers used by the behavior-pilot debugging case."""\n\n\n'
        "def canonical_slug(value: str) -> str:\n"
        '    """Return a lower-case URL slug for a human-entered title."""\n'
        '    return "-".join(value.strip().lower().split())\n',
        encoding="utf-8",
    )

    result = verify_behavior_case("debug-loop-python-bug-v1", worktree)
    assert result["passed"] is True
    assert next(check for check in result["checks"] if check["name"] == "unittest")["passed"] is True

    tests = worktree / "eval/behavior_fixtures/debug-loop/tests/test_text_utils.py"
    tests.write_text("import unittest\n", encoding="utf-8")
    result = verify_behavior_case("debug-loop-python-bug-v1", worktree)
    assert result["passed"] is False
    assert next(check for check in result["checks"] if check["name"] == "tests_unchanged")["passed"] is False


@pytest.mark.parametrize(
    ("verification_id", "fixture_name", "output_paths"),
    [
        (
            "completion-review-no-go-v1",
            "completion-review",
            {
                "review.md": "# Release Review\n\n## Decision\nNO-GO.\n\nThe signature verification is missing. Replay protection is missing. The test output leaves those rejection paths unverified.\n",
            },
        ),
        (
            "decision-record-event-log-v1",
            "decision-record",
            {
                "ADR.md": "# ADR\n\n## Context\nHistory is required.\n\n## Decision\nUse an append-only event log.\n\n## Alternatives\nReject a mutable status row.\n\n## Consequences\nReaders reconstruct state.\n\n## Review\nRevisit after retention requirements change.\n",
            },
        ),
        (
            "security-review-webhook-v1",
            "security-review",
            {
                "security-review.md": "# Security Review\n\nSeverity: High. `callback_url` is untrusted and passed to `urlopen`, creating SSRF risk. The webhook has no HMAC signature verification. Allowlist destination hosts and verify an HMAC signature before processing.\n",
            },
        ),
        (
            "spec-kit-xl-artifacts-v1",
            "spec-kit-xl",
            {
                "artifacts/proposal.md": "# Proposal\n\n## Scope\nAuthorize release notifications.\n\n## Non-goals\nNo delivery UI.\n",
                "artifacts/tasks.md": "# Tasks\n\n- T1 Implement the authorized enqueue transition.\n- T2 Add tests for destination enforcement and retries.\n",
                "artifacts/acceptance.md": "# Acceptance\n\n- An authorized transition is required.\n- The host allowlist rejects unknown destinations.\n- Retry is idempotent for a release identifier.\n",
            },
        ),
    ],
)
def test_behavior_verifier_accepts_correct_simulated_outputs(tmp_path, verification_id, fixture_name, output_paths):
    worktree = _worktree_for(tmp_path, fixture_name)
    root = worktree / "eval/behavior_fixtures" / fixture_name
    for relative, contents in output_paths.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    result = verify_behavior_case(verification_id, worktree)
    assert result["passed"] is True
    assert all(check["passed"] for check in result["checks"])


def test_unknown_behavior_verification_id_fails_closed(tmp_path):
    result = verify_behavior_case("unknown-case", tmp_path)
    assert result == {
        "passed": False,
        "checks": [{"name": "verification_id", "passed": False, "detail": "unknown verification_id: unknown-case"}],
        "summary": "unknown-case: fail (0/1 checks)",
    }


def test_verifiers_accept_equivalent_gap_language_and_numbered_tasks(tmp_path):
    completion = _worktree_for(tmp_path / "completion", "completion-review")
    completion_root = completion / "eval/behavior_fixtures/completion-review"
    (completion_root / "review.md").write_text(
        "# Review\n\nNO-GO. Signature verification is absent. Replay protection is absent. "
        "The tests provide no evidence for either rejection path.\n",
        encoding="utf-8",
    )
    assert verify_behavior_case("completion-review-no-go-v1", completion)["passed"] is True

    specification = _worktree_for(tmp_path / "specification", "spec-kit-xl")
    artifacts = specification / "eval/behavior_fixtures/spec-kit-xl/artifacts"
    artifacts.mkdir()
    (artifacts / "proposal.md").write_text("# Proposal\n\n## Scope\nNotifications.\n\n## Non-goals\nNo UI.\n", encoding="utf-8")
    (artifacts / "tasks.md").write_text("# Tasks\n\n1. Implement authorization.\n2. Add tests for retries.\n", encoding="utf-8")
    (artifacts / "acceptance.md").write_text(
        "# Acceptance\n\nAuthorized releases use an allowlist and retries are idempotent.\n",
        encoding="utf-8",
    )
    assert verify_behavior_case("spec-kit-xl-artifacts-v1", specification)["passed"] is True


def test_behavior_pilot_suite_is_schema_shaped_and_has_train_and_held_out_cases():
    suite = load_suite(SUITE)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    properties = schema["properties"]["cases"]["items"]["properties"]
    assert properties["verification_id"] == {"type": "string", "minLength": 1}
    assert suite["promotion_eligible"] is False
    assert suite["repetitions"] == 1
    assert len(suite["cases"]) == 5
    assert {case["split"] for case in suite["cases"]} == {"train", "held_out"}
    assert all(case["verification_id"] for case in suite["cases"])
    assert all({"success", "no_external_effects"} <= {item["type"] for item in case["assertions"]} for case in suite["cases"])
