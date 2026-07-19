"""Deterministic verifiers for the V4.2 behavior-pilot fixtures.

These checks inspect artifacts left in an isolated evaluation worktree. They
never use a model response as evidence and never contact the network.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


FIXTURE_ROOT = Path("eval/behavior_fixtures")

# Every supplied task input is immutable evidence. Outputs are deliberately
# absent from this map, so the verifier distinguishes doing the task from
# rewriting its premise.
_EXPECTED_INPUT_HASHES: dict[str, dict[str, str]] = {
    "debug-loop": {
        "task.md": "d14a4d660ce1bed399ee16adaa131a67628d54503178ab7bd4cff1bf85839fbd",
        "tests/test_text_utils.py": "21e5d1f829802e0837627b4c89a4ca1c069ed9378799af592ee659f3f500e331",
    },
    "completion-review": {
        "requirements.md": "ad98d8088700c02ce7f36d2d40bad477b94bebed3e2bb58231d0d0a9ce4523f2",
        "changes.diff": "f464065c23c0100901c296879a76a1682363ee9e2717aa58cd8ea43d4d47445b",
        "test-output.txt": "9c4fb65da1d543bbf1a0561f987a01e6e1f5834323d9e1d75601fc7198022693",
        "task.md": "df9af8e8204b99a925ff9ecf9d126bba5d4b1be46b1304d50ae8e5bd626e36df",
    },
    "decision-record": {
        "constraints.md": "21729e384c6612594799b0fd079c5c7536c0df2b76e7d6d6ddedbb8a69ffaf84",
        "task.md": "e00c9ea8ffb0c6eec8a6ba5fb2e80d7c29dce1420e83da770d9504ebefda300b",
    },
    "security-review": {
        "webhook.py": "58ef96e5ba1aa30a6c474ee9080b06ac8c6dc0f2fd5d2f629f6aa10e3025cfb5",
        "task.md": "5903df037bc9c75ff36d83f77c158460f20128df352b68e948e2b627130c46f6",
    },
    "spec-kit-xl": {
        "requirements.md": "c295a3d7c2d29d555ca213291cb1678d091989e12db0d5136ea4bd00906a9219",
        "task.md": "38fdb4feb773b35ecc3fdbf176c08d14104f29c7bfa335e6b1794e89e3f55ffe",
    },
}


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _contains_all(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return all(term.casefold() in lowered for term in terms)


def _mentions_gap(text: str, subject: str) -> bool:
    lowered = text.casefold()
    gap_terms = ("missing", "absent", "unverified", "not verified", "no evidence", "without")
    return subject.casefold() in lowered and any(term in lowered for term in gap_terms)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _case_root(worktree: Path, name: str) -> Path:
    return worktree / FIXTURE_ROOT / name


def _inputs_unchanged(root: Path, fixture_name: str) -> dict[str, Any]:
    altered = [
        relative
        for relative, expected_hash in _EXPECTED_INPUT_HASHES[fixture_name].items()
        if _sha256(root / relative) != expected_hash
    ]
    detail = "all supplied inputs are unchanged" if not altered else f"altered or missing supplied inputs: {', '.join(altered)}"
    return _check("inputs_unchanged", not altered, detail)


def _verify_debug_loop(worktree: Path) -> list[dict[str, Any]]:
    root = _case_root(worktree, "debug-loop")
    source = root / "src/text_utils.py"
    tests = root / "tests/test_text_utils.py"
    source_text = _read(source)
    expected_test_hash = "21e5d1f829802e0837627b4c89a4ca1c069ed9378799af592ee659f3f500e331"
    checks = [
        _inputs_unchanged(root, "debug-loop"),
        _check("source_changed", bool(source_text) and "replace(\" \", \"-\")" not in source_text, "buggy implementation is not retained"),
        _check("tests_unchanged", _sha256(tests) == expected_test_hash, "stdlib regression tests remain intact"),
    ]
    if source.exists() and tests.exists():
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests")],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        output = completed.stdout[-1200:]
        checks.append(_check("unittest", completed.returncode == 0, f"unittest exit_code={completed.returncode}: {output}"))
    else:
        checks.append(_check("unittest", False, "source or stdlib test file is missing"))
    return checks


def _verify_completion_review(worktree: Path) -> list[dict[str, Any]]:
    root = _case_root(worktree, "completion-review")
    review = _read(root / "review.md")
    return [
        _inputs_unchanged(root, "completion-review"),
        _check("review_exists", bool(review.strip()), "review.md exists and is non-empty"),
        _check("no_go_decision", "no-go" in review.casefold() or "no go" in review.casefold(), "review explicitly blocks release"),
        _check("signature_gap", _mentions_gap(review, "signature"), "review identifies missing signature verification"),
        _check("replay_gap", _mentions_gap(review, "replay"), "review identifies missing replay protection"),
        _check("test_evidence_gap", _mentions_gap(review, "test"), "review identifies absent rejection-path evidence"),
    ]


def _verify_decision_record(worktree: Path) -> list[dict[str, Any]]:
    root = _case_root(worktree, "decision-record")
    record = _read(root / "ADR.md")
    headings = ("context", "decision", "alternatives", "consequences", "review")
    return [
        _inputs_unchanged(root, "decision-record"),
        _check("adr_exists", bool(record.strip()), "ADR.md exists and is non-empty"),
        _check("adr_sections", all(re.search(rf"^#+\s+{heading}\b", record, re.IGNORECASE | re.MULTILINE) for heading in headings), "ADR includes required decision sections"),
        _check("event_log_selected", _contains_all(record, ("append-only", "event log")), "ADR selects append-only event log"),
        _check("mutable_row_rejected", _contains_all(record, ("mutable", "status row")), "ADR records mutable status rows as an alternative"),
    ]


def _verify_security_review(worktree: Path) -> list[dict[str, Any]]:
    root = _case_root(worktree, "security-review")
    report = _read(root / "security-review.md")
    return [
        _inputs_unchanged(root, "security-review"),
        _check("report_exists", bool(report.strip()), "security-review.md exists and is non-empty"),
        _check("severity", any(level in report.casefold() for level in ("critical", "high", "medium")), "report assigns a severity"),
        _check("ssrf_finding", "ssrf" in report.casefold() or _contains_all(report, ("callback_url", "untrusted")), "report identifies untrusted callback URL risk"),
        _check("code_evidence", "urlopen" in report.casefold() and "callback_url" in report.casefold(), "report cites the vulnerable code path"),
        _check("authentication_gap", "hmac" in report.casefold() or "signature" in report.casefold(), "report identifies missing webhook authentication"),
        _check("remediation", any(term in report.casefold() for term in ("allowlist", "allow-list", "validate host")) and any(term in report.casefold() for term in ("hmac", "signature")), "report prescribes allowlisting and signature verification"),
    ]


def _verify_spec_kit_xl(worktree: Path) -> list[dict[str, Any]]:
    root = _case_root(worktree, "spec-kit-xl")
    artifacts = root / "artifacts"
    proposal = _read(artifacts / "proposal.md")
    tasks = _read(artifacts / "tasks.md")
    acceptance = _read(artifacts / "acceptance.md")
    task_lines = re.findall(
        r"^\s*(?:[-*]\s+(?:\[[ xX]\]\s*)?|(?:\d+|T\d+)[.)\s:-]+)\S.*$",
        tasks,
        re.IGNORECASE | re.MULTILINE,
    )
    return [
        _inputs_unchanged(root, "spec-kit-xl"),
        _check("proposal_exists", bool(proposal.strip()), "proposal.md exists and is non-empty"),
        _check("proposal_scope", _contains_all(proposal, ("scope", "non-goal")), "proposal defines scope and non-goals"),
        _check("tasks_exists", bool(tasks.strip()), "tasks.md exists and is non-empty"),
        _check("task_breakdown", len(task_lines) >= 2 and "test" in tasks.casefold(), "tasks include an ordered implementation and test breakdown"),
        _check("acceptance_exists", bool(acceptance.strip()), "acceptance.md exists and is non-empty"),
        _check("acceptance_constraints", _contains_all(acceptance, ("authorized", "allowlist", "idempotent")), "acceptance makes authorization, destination allowlist, and idempotency testable"),
    ]


_VERIFIERS: dict[str, Callable[[Path], list[dict[str, Any]]]] = {
    "debug-loop-python-bug-v1": _verify_debug_loop,
    "completion-review-no-go-v1": _verify_completion_review,
    "decision-record-event-log-v1": _verify_decision_record,
    "security-review-webhook-v1": _verify_security_review,
    "spec-kit-xl-artifacts-v1": _verify_spec_kit_xl,
}


def verify_behavior_case(verification_id: str, worktree: Path) -> dict[str, Any]:
    """Verify a single behavior fixture without trusting runner/model output."""
    verifier = _VERIFIERS.get(verification_id)
    if verifier is None:
        checks = [_check("verification_id", False, f"unknown verification_id: {verification_id}")]
    else:
        try:
            checks = verifier(Path(worktree))
        except (OSError, subprocess.SubprocessError) as exc:
            checks = [_check("verifier_execution", False, f"verifier failed: {exc}")]
    passed = all(bool(check["passed"]) for check in checks)
    summary = f"{verification_id}: {'pass' if passed else 'fail'} ({sum(bool(check['passed']) for check in checks)}/{len(checks)} checks)"
    return {"passed": passed, "checks": checks, "summary": summary}
