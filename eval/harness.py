#!/usr/bin/env python3
"""Black-box, paired evaluation harness for the V4.2 workflow.

The harness intentionally treats a runner as an opaque adapter.  It records
what the adapter reported, applies only deterministic assertions, and never
turns a fixture result into evidence about an external Skill.  A runner may be
backed by Codex, a subprocess, or a test double; all runs receive a fresh HOME
and worktree so that state cannot silently leak between pairs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


SCHEMA_VERSION = "4.2"
HARNESS_VERSION = "4.2.0"
_SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_-]{12,}|"
    r"(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+)",
    re.IGNORECASE,
)
_PRIVATE_PATH_RE = re.compile(
    r"/Users/[^\s'\"`]+|/home/[^\s'\"`]+|C:\\Users\\[^\s'\"`]+",
    re.IGNORECASE,
)
_SENSITIVE_ENV_RE = re.compile(
    r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE[_-]?KEY|"
    r"CREDENTIAL|AUTHORIZATION|COOKIE|SESSION)",
    re.IGNORECASE,
)


class EvalError(ValueError):
    """Raised for an invalid suite, runner result, or evaluation operation."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        value = _SECRET_RE.sub("[REDACTED]", value)
        return _PRIVATE_PATH_RE.sub("[PRIVATE_PATH]", value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    return value


def _snapshot_tree(path: Path) -> dict[str, str]:
    """Return a content fingerprint for files below an isolated directory."""
    snapshot: dict[str, str] = {}
    if not path.exists():
        return snapshot
    for item in sorted(path.rglob("*")):
        if item.is_dir() or item.is_symlink():
            continue
        try:
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
        except OSError:
            digest = "unreadable"
        snapshot[item.relative_to(path).as_posix()] = digest
    return snapshot


def _context_changes(context: "CleanContext", before: Mapping[str, Mapping[str, str]]) -> list[str]:
    changes: list[str] = []
    for label, directory in (("home", context.home), ("worktree", context.worktree)):
        after = _snapshot_tree(directory)
        previous = dict(before.get(label, {}))
        for relative in sorted(set(previous) | set(after)):
            if previous.get(relative) != after.get(relative):
                changes.append(f"{label}/{relative}")
    return changes


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _nonnegative_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, number)


def _normalise_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _expected_invocation(case: Mapping[str, Any]) -> bool:
    if "expected_invocation" in case:
        return _as_bool(case["expected_invocation"])
    return bool(case.get("expected_skill"))


def _expected_route(case: Mapping[str, Any], assertion: Mapping[str, Any] | None = None) -> str | None:
    source = assertion or {}
    value = source.get("skill", source.get("route", case.get("expected_route", case.get("expected_skill"))))
    if value is None:
        return "native"
    return value if isinstance(value, str) else None


def validate_suite(suite: Mapping[str, Any]) -> list[str]:
    """Return deterministic validation errors for a suite document."""
    errors: list[str] = []
    if suite.get("schema_version") not in {None, SCHEMA_VERSION}:
        errors.append("schema_version must be 4.2")
    suite_id = suite.get("suite_id")
    if not isinstance(suite_id, str) or not suite_id.strip():
        errors.append("suite_id must be a non-empty string")
    if "promotion_eligible" in suite and not isinstance(suite["promotion_eligible"], bool):
        errors.append("promotion_eligible must be boolean")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        return errors
    seen: set[str] = set()
    held_out = 0
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}.case_id must be a non-empty string")
        elif case_id in seen:
            errors.append(f"duplicate case_id: {case_id}")
        else:
            seen.add(case_id)
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            errors.append(f"{prefix}.prompt must be a non-empty string")
        split = case.get("split", "train")
        if split not in {"train", "held_out"}:
            errors.append(f"{prefix}.split must be train or held_out")
        elif split == "held_out":
            held_out += 1
        family = case.get("family", "general")
        if not isinstance(family, str) or not family.strip():
            errors.append(f"{prefix}.family must be a non-empty string")
        assertions = case.get("assertions", [])
        if not isinstance(assertions, list) or any(not isinstance(item, dict) for item in assertions):
            errors.append(f"{prefix}.assertions must be a list of objects")
        if "expected_skill" in case and case["expected_skill"] is not None and not isinstance(case["expected_skill"], str):
            errors.append(f"{prefix}.expected_skill must be a string or null")
        if "expected_route" in case and case["expected_route"] is not None and not isinstance(case["expected_route"], str):
            errors.append(f"{prefix}.expected_route must be a string or null")
        if "subjective" in case and not isinstance(case["subjective"], bool):
            errors.append(f"{prefix}.subjective must be boolean")
    if held_out == 0:
        errors.append("suite must contain at least one held_out case")
    repetitions = suite.get("repetitions", 3)
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        errors.append("repetitions must be a positive integer")
    return errors


def load_suite(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"cannot load suite {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvalError("suite root must be a JSON object")
    errors = validate_suite(value)
    if errors:
        raise EvalError("invalid suite: " + "; ".join(errors))
    return value


class RunnerAdapter(Protocol):
    """Opaque runner contract used by :class:`EvalHarness`."""

    def run(
        self,
        prompt: str,
        *,
        case: Mapping[str, Any],
        variant: str,
        mode: str,
        worktree: Path,
        home: Path,
        run_id: str,
        repetition: int,
    ) -> Mapping[str, Any]:
        ...


IsolationVerifier = Callable[[RunnerAdapter, str], bool]


def _normalise_subject(value: Mapping[str, Any] | None, *, fixture_only: bool, runner: RunnerAdapter) -> dict[str, str]:
    if fixture_only:
        fixture_id = str(getattr(runner, "skill_name", runner.__class__.__name__))
        return {
            "kind": "fixture",
            "id": fixture_id,
            "content_sha256": _sha256(f"fixture:{fixture_id}:{HARNESS_VERSION}"),
        }
    if not isinstance(value, Mapping):
        raise EvalError("non-fixture evaluation requires a locked subject binding")
    kind = value.get("kind")
    subject_id = value.get("id")
    content_sha256 = value.get("content_sha256")
    if kind not in {"component", "profile"}:
        raise EvalError("evaluation subject kind must be component or profile")
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise EvalError("evaluation subject id must be non-empty")
    if not isinstance(content_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
        raise EvalError("evaluation subject content_sha256 must be a lowercase SHA-256 digest")
    return {"kind": str(kind), "id": subject_id, "content_sha256": content_sha256}


def _normalise_source_commit(value: str | None, *, fixture_only: bool) -> str | None:
    if fixture_only:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise EvalError("non-fixture evaluation requires a full source commit binding")
    return value


@dataclass(frozen=True)
class CleanContext:
    """Paths and metadata for one isolated evaluation attempt."""

    root: Path
    home: Path
    worktree: Path

    @classmethod
    def create(cls, template: Path | None = None) -> tuple["CleanContext", tempfile.TemporaryDirectory[str]]:
        temporary = tempfile.TemporaryDirectory(prefix="codex-eval-")
        root = Path(temporary.name)
        home = root / "home"
        worktree = root / "worktree"
        home.mkdir()
        if template is not None:
            if not template.is_dir():
                temporary.cleanup()
                raise EvalError(f"workspace template is not a directory: {template}")
            shutil.copytree(template, worktree, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        else:
            worktree.mkdir()
        (home / ".codex").mkdir()
        return cls(root=root, home=home, worktree=worktree), temporary


def _normalise_result(raw: Mapping[str, Any], *, case: Mapping[str, Any], variant: str, mode: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise EvalError("runner result must be an object")
    invoked_skill = raw.get("invoked_skill")
    route_suggestion = raw.get("route_suggestion")
    invoked = _as_bool(raw.get("invoked", invoked_skill is not None))
    tool_calls = _normalise_list(raw.get("tool_calls"))
    writes = _normalise_list(raw.get("writes", raw.get("write_paths")))
    external_effects = _normalise_list(raw.get("external_effects"))
    success = _as_bool(raw.get("success", True))
    evaluation_status = raw.get("evaluation_status")
    if evaluation_status not in {"completed", "task_failed", "runner_failed", "inconclusive"}:
        evaluation_status = "completed" if success else "runner_failed"
    return {
        "variant": variant,
        "mode": mode,
        "case_id": case.get("case_id"),
        "invoked": invoked,
        "invoked_skill": invoked_skill if isinstance(invoked_skill, str) else None,
        "route_suggestion": _redact(route_suggestion) if isinstance(route_suggestion, str) else None,
        "output": _redact(str(raw.get("output", ""))),
        "success": success,
        "evaluation_status": evaluation_status,
        "failure_categories": _redact(_normalise_list(raw.get("failure_categories"))),
        "exit_code": raw.get("exit_code", 0),
        "tool_calls": _redact(tool_calls),
        "writes": _redact(writes),
        "filesystem_writes": _redact(_normalise_list(raw.get("filesystem_writes"))),
        "external_effects": _redact(external_effects),
        "credentials_exposed": _as_bool(raw.get("credentials_exposed", False)),
        "unauthorized_install": _as_bool(raw.get("unauthorized_install", False)),
        "unauthorized_external_write": _as_bool(raw.get("unauthorized_external_write", False)),
        "prompt_injection_succeeded": _as_bool(raw.get("prompt_injection_succeeded", raw.get("prompt_injection_success", False))),
        "approval_forged": _as_bool(raw.get("approval_forged", False)),
        "destructive_data_loss": _as_bool(raw.get("destructive_data_loss", False)),
        "reported_safety_findings": _redact(_normalise_list(raw.get("safety_findings"))),
        "runner_audit": _redact(_normalise_list(raw.get("runner_audit"))),
        "driver_changed": _as_bool(raw.get("driver_changed", False)),
        "tokens": int(_nonnegative_number(raw.get("tokens"), 0)),
        "duration_ms": _nonnegative_number(raw.get("duration_ms"), 0),
        "corrections": int(_nonnegative_number(raw.get("corrections"), 0)),
        "rework": int(_nonnegative_number(raw.get("rework"), 0)),
        "error": _redact(raw.get("error")),
        "environment": {
            "clean_context": True,
            "home_basename": "home",
            "worktree_basename": "worktree",
        },
    }


class FixtureRunner:
    """Deterministic demo adapter; never evidence for an external Skill."""

    fixture_only = True

    def __init__(self, skill_name: str = "fixture-skill") -> None:
        self.skill_name = skill_name

    def run(
        self,
        prompt: str,
        *,
        case: Mapping[str, Any],
        variant: str,
        mode: str,
        worktree: Path,
        home: Path,
        run_id: str,
        repetition: int,
    ) -> Mapping[str, Any]:
        expected = case.get("expected_skill") or self.skill_name
        eligible = bool(case.get("expected_skill"))
        candidate_enabled = variant in {"with", "candidate", "new"}
        suggestion = self.skill_name if eligible else None
        if mode == "shadow":
            return {
                "invoked": False,
                "invoked_skill": None,
                "route_suggestion": suggestion,
                "output": f"shadow suggestion: {suggestion or 'native'}",
                "success": True,
                "tool_calls": [],
                "writes": [],
                "external_effects": [],
                "tokens": 18,
                "duration_ms": 1,
            }
        invoked = candidate_enabled and eligible
        return {
            "invoked": invoked,
            "invoked_skill": expected if invoked else None,
            "output": f"fixture {'enabled' if invoked else 'native'} response for {prompt}",
            "success": True,
            "tool_calls": [],
            "writes": [],
            "external_effects": [],
            "tokens": 20 if invoked else 28,
            "duration_ms": 1 if invoked else 2,
            "corrections": 0,
            "rework": 0,
        }


class ShadowRunner:
    """Capability-reducing adapter that gives a runner route-only authority.

    The wrapped runner still executes in the harness's clean context, but it
    receives ``mode=shadow`` and the standard no-tools/no-writes/no-network
    environment when it is a :class:`SubprocessRunner`.  Any self-reported
    side effect is preserved as a safety finding for the harness to fail
    closed; this wrapper never silently clears it.
    """

    fixture_only = False

    def __init__(self, delegate: RunnerAdapter) -> None:
        self.delegate = delegate
        self.fixture_only = bool(getattr(delegate, "fixture_only", False))

    def run(
        self,
        prompt: str,
        *,
        case: Mapping[str, Any],
        variant: str,
        mode: str,
        worktree: Path,
        home: Path,
        run_id: str,
        repetition: int,
    ) -> Mapping[str, Any]:
        raw = dict(
            self.delegate.run(
                prompt,
                case=case,
                variant="shadow",
                mode="shadow",
                worktree=worktree,
                home=home,
                run_id=run_id,
                repetition=repetition,
            )
        )
        violations: list[str] = []
        for key, label in (("tool_calls", "tool calls"), ("writes", "writes"), ("external_effects", "external effects")):
            if _normalise_list(raw.get(key)):
                violations.append(label)
        if _as_bool(raw.get("invoked")) or _as_bool(raw.get("driver_changed")):
            violations.append("execution authority")
        if violations:
            raw.setdefault("safety_findings", []).extend([f"Shadow attempted {item}" for item in violations])
        raw["invoked"] = False
        raw["invoked_skill"] = None
        return raw


class SubprocessRunner:
    """Run an explicit command adapter without invoking a shell.

    The command may contain placeholders ``{prompt}``, ``{case_id}``,
    ``{variant}``, ``{mode}``, ``{home}``, and ``{worktree}``.  JSON stdout is
    consumed as a runner result; non-JSON stdout is retained as ``output``.
    """

    fixture_only = False

    def __init__(self, command: Sequence[str], timeout: float = 120.0, env: Mapping[str, str] | None = None) -> None:
        if not command:
            raise EvalError("subprocess runner command cannot be empty")
        self.command = tuple(command)
        self.timeout = timeout
        self.extra_env = dict(env or {})

    def run(
        self,
        prompt: str,
        *,
        case: Mapping[str, Any],
        variant: str,
        mode: str,
        worktree: Path,
        home: Path,
        run_id: str,
        repetition: int,
    ) -> Mapping[str, Any]:
        values = {
            "prompt": prompt,
            "case_id": str(case.get("case_id", "")),
            "variant": variant,
            "mode": mode,
            "home": str(home),
            "worktree": str(worktree),
        }
        try:
            command = [item.format(**values) for item in self.command]
        except (KeyError, ValueError) as exc:
            raise EvalError(f"invalid runner command placeholder: {exc}") from exc
        # A clean HOME is not sufficient if inherited API keys remain in the
        # process environment.  Keep ordinary runtime variables, but remove
        # ambient credentials unless the caller explicitly supplies an env
        # override for this adapter.
        environment = {
            key: value
            for key, value in os.environ.items()
            if not _SENSITIVE_ENV_RE.search(key)
        }
        environment.update(self.extra_env)
        environment.update(
            {
                "HOME": str(home),
                "CODEX_HOME": str(home / ".codex"),
                "EVAL_MODE": mode,
                "EVAL_VARIANT": variant,
                "EVAL_RUN_ID": run_id,
                "EVAL_REPETITION": str(repetition),
                "EVAL_NO_TOOLS": "1" if mode == "shadow" else "0",
                "EVAL_NO_WRITES": "1" if mode == "shadow" else "0",
                "EVAL_NO_NETWORK": "1" if mode == "shadow" else "0",
            }
        )
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=worktree,
                env=environment,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "exit_code": None,
                "output": str(exc),
                "error": "timeout",
                "duration_ms": (time.perf_counter() - started) * 1000,
            }
        duration_ms = (time.perf_counter() - started) * 1000
        stdout = completed.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            parsed = {"output": stdout}
        if not isinstance(parsed, dict):
            parsed = {"output": stdout}
        parsed.setdefault("success", completed.returncode == 0)
        parsed.setdefault("exit_code", completed.returncode)
        parsed.setdefault("duration_ms", duration_ms)
        if completed.stderr.strip():
            parsed.setdefault("error", completed.stderr.strip())
        return parsed


def _assertion_result(assertion: Mapping[str, Any], result: Mapping[str, Any], case: Mapping[str, Any]) -> tuple[bool, str]:
    kind = str(assertion.get("type", "")).strip()
    if kind == "skill_invoked":
        expected = assertion.get("skill", case.get("expected_skill"))
        ok = _as_bool(result.get("invoked")) and (expected is None or result.get("invoked_skill") == expected)
        return ok, f"skill_invoked={result.get('invoked_skill')!r}, expected={expected!r}"
    if kind == "skill_not_invoked":
        ok = not _as_bool(result.get("invoked"))
        return ok, f"invoked={result.get('invoked')!r}, expected=false"
    if kind == "route_suggested":
        expected = _expected_route(case, assertion)
        actual = result.get("route_suggestion")
        ok = expected is not None and actual == expected
        return ok, f"route_suggestion={actual!r}, expected={expected!r}"
    if kind == "route_not_suggested":
        expected = _expected_route(case, assertion)
        actual = result.get("route_suggestion")
        ok = actual == "native" if expected is None else actual != expected
        return ok, f"route_suggestion={actual!r}, excluded={expected!r}"
    if kind in {"contains", "output_contains"}:
        needle = str(assertion.get("value", assertion.get("text", "")))
        ok = needle in str(result.get("output", ""))
        return ok, f"output contains {needle!r}={ok}"
    if kind in {"not_contains", "output_not_contains"}:
        needle = str(assertion.get("value", assertion.get("text", "")))
        ok = needle not in str(result.get("output", ""))
        return ok, f"output excludes {needle!r}={ok}"
    if kind == "output_regex":
        pattern = str(assertion.get("pattern", ""))
        ok = re.search(pattern, str(result.get("output", ""))) is not None
        return ok, f"output regex {pattern!r}={ok}"
    if kind in {"no_tool_calls", "shadow_no_tools"}:
        ok = not result.get("tool_calls")
        return ok, f"tool_calls={len(_normalise_list(result.get('tool_calls')))}"
    if kind in {"no_writes", "shadow_no_writes"}:
        ok = not result.get("writes")
        return ok, f"writes={len(_normalise_list(result.get('writes')))}"
    if kind in {"no_external_effects", "shadow_no_external_effects"}:
        ok = not result.get("external_effects")
        return ok, f"external_effects={len(_normalise_list(result.get('external_effects')))}"
    if kind == "success":
        ok = _as_bool(result.get("success"))
        return ok, f"success={ok}"
    if kind == "exit_code":
        expected = assertion.get("value", 0)
        ok = result.get("exit_code") == expected
        return ok, f"exit_code={result.get('exit_code')!r}, expected={expected!r}"
    if kind == "max_tool_calls":
        try:
            expected = int(assertion.get("value", 0))
        except (TypeError, ValueError):
            return False, "max_tool_calls assertion value is not an integer"
        actual = len(_normalise_list(result.get("tool_calls")))
        return actual <= expected, f"tool_calls={actual}, max={expected}"
    if kind == "no_credentials":
        ok = not _as_bool(result.get("credentials_exposed"))
        return ok, f"credentials_exposed={result.get('credentials_exposed')!r}"
    return False, f"unknown assertion type: {kind or '<empty>'}"


def evaluate_assertions(case: Mapping[str, Any], result: Mapping[str, Any], mode: str, variant: str = "with") -> tuple[list[dict[str, Any]], list[str]]:
    assertions = list(case.get("assertions", []))
    if mode == "shadow":
        assertions.extend(
            [
                {"type": "shadow_no_tools"},
                {"type": "shadow_no_writes"},
                {"type": "shadow_no_external_effects"},
            ]
        )
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for assertion in assertions:
        # A paired baseline can stage a different fixed profile. Candidate
        # invocation and candidate-only route requirements therefore do not
        # fail that arm; safety and negative assertions still run for both.
        candidate_only_route = (
            assertion.get("type") == "route_suggested"
            and _expected_route(case, assertion) not in {None, "native"}
        )
        if variant in {"without", "baseline", "old", "shadow"} and (
            assertion.get("type") == "skill_invoked" or candidate_only_route
        ):
            checks.append({"type": assertion.get("type"), "ok": True, "detail": "baseline arm: candidate-only assertion skipped"})
            continue
        ok, detail = _assertion_result(assertion, result, case)
        item = {"type": assertion.get("type"), "ok": ok, "detail": detail}
        checks.append(item)
        if not ok:
            failures.append(detail)
    return checks, failures


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 4) if values else 0.0


def _median(values: Iterable[float]) -> float:
    values = list(values)
    return round(float(statistics.median(values)), 4) if values else 0.0


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


class EvalHarness:
    """Execute paired/Shadow runs and produce a machine-readable report."""

    def __init__(
        self,
        runner: RunnerAdapter,
        *,
        seed: int = 42,
        workspace_template: str | Path | None = None,
        isolation_verifier: IsolationVerifier | None = None,
        subject: Mapping[str, Any] | None = None,
        source_commit: str | None = None,
    ) -> None:
        self.runner = runner
        self.seed = seed
        self.workspace_template = Path(workspace_template).resolve() if workspace_template else None
        self.isolation_verifier = isolation_verifier
        self.subject = subject
        self.source_commit = source_commit

    def run(
        self,
        suite: Mapping[str, Any],
        *,
        repetitions: int | None = None,
        mode: str = "paired",
        human_reviews: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        errors = validate_suite(suite)
        if errors:
            raise EvalError("invalid suite: " + "; ".join(errors))
        if mode not in {"paired", "shadow"}:
            raise EvalError("mode must be paired or shadow")
        fixture_only = bool(getattr(self.runner, "fixture_only", False))
        if not fixture_only:
            try:
                isolation_verified = bool(
                    self.isolation_verifier
                    and self.isolation_verifier(self.runner, mode)
                )
            except Exception:
                isolation_verified = False
            if not isolation_verified:
                raise EvalError(
                    "trusted isolation verifier required before running a non-fixture adapter"
                )
        subject = _normalise_subject(self.subject, fixture_only=fixture_only, runner=self.runner)
        source_commit = _normalise_source_commit(self.source_commit, fixture_only=fixture_only)
        repetitions = repetitions if repetitions is not None else int(suite.get("repetitions", 3))
        if repetitions < 1:
            raise EvalError("repetitions must be positive")
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        rng = random.Random(self.seed)
        cases = list(suite["cases"])
        rng.shuffle(cases)
        raw_runs: list[dict[str, Any]] = []
        pair_orders: dict[str, list[str]] = {}
        for case in cases:
            variants = ["with", "without"] if mode == "paired" else ["shadow"]
            rng.shuffle(variants)
            pair_orders[str(case["case_id"])] = list(variants)
            for variant in variants:
                for repetition in range(repetitions):
                    context, temporary = CleanContext.create(self.workspace_template)
                    before = {
                        "home": _snapshot_tree(context.home),
                        "worktree": _snapshot_tree(context.worktree),
                    }
                    try:
                        raw = self.runner.run(
                            str(case["prompt"]),
                            case=case,
                            variant=variant,
                            mode=mode,
                            worktree=context.worktree,
                            home=context.home,
                            run_id=run_id,
                            repetition=repetition,
                        )
                        changes = _context_changes(context, before)
                        if changes:
                            raw = dict(raw)
                            claimed = _normalise_list(raw.get("writes", raw.get("write_paths")))
                            raw["writes"] = sorted({str(item) for item in claimed} | set(changes))
                            raw["filesystem_writes"] = changes
                        result = _normalise_result(raw, case=case, variant=variant, mode=mode)
                        checks, failures = evaluate_assertions(case, result, mode, variant)
                        result["assertions"] = checks
                        result["assertion_failures"] = failures
                        result["run_index"] = len(raw_runs)
                        result["repetition"] = repetition
                        result["case_family"] = case.get("family", "general")
                        result["split"] = case.get("split", "train")
                        result["subjective"] = bool(case.get("subjective", False))
                        raw_runs.append(result)
                    finally:
                        temporary.cleanup()

        report = self._build_report(
            suite,
            run_id,
            mode,
            repetitions,
            raw_runs,
            pair_orders,
            human_reviews or [],
            subject,
            source_commit,
        )
        return report

    def _build_report(
        self,
        suite: Mapping[str, Any],
        run_id: str,
        mode: str,
        repetitions: int,
        runs: list[dict[str, Any]],
        pair_orders: Mapping[str, list[str]],
        human_reviews: Sequence[Mapping[str, Any]],
        subject: Mapping[str, str],
        source_commit: str | None,
    ) -> dict[str, Any]:
        by_case_variant: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for run in runs:
            by_case_variant.setdefault((str(run["case_id"]), str(run["variant"])), []).append(run)
        cases_by_id = {str(case["case_id"]): case for case in suite["cases"]}

        candidates = [run for run in runs if run["variant"] in {"with", "candidate", "new"}]
        if mode == "shadow":
            candidates = runs

        def predicted_invocation(run: Mapping[str, Any]) -> bool:
            # Shadow has no execution authority; its route suggestion is the
            # prediction to score, while actual invocation must remain false.
            if mode == "shadow":
                return bool(run.get("route_suggestion"))
            return bool(run.get("invoked"))

        objective_cases = [case for case in suite["cases"] if not bool(case.get("subjective", False))]
        route_cases = [
            case
            for case in objective_cases
            if any(
                isinstance(assertion, Mapping) and str(assertion.get("type", "")).startswith("route_")
                for assertion in case.get("assertions", [])
            )
        ]
        route_case_ids = {str(case["case_id"]) for case in route_cases}
        trigger_cases = [
            case
            for case in objective_cases
            if str(case["case_id"]) not in route_case_ids
            and (
                "expected_invocation" in case
                or "expected_skill" in case
                or any(
                    isinstance(assertion, Mapping)
                    and assertion.get("type") in {"skill_invoked", "skill_not_invoked"}
                    for assertion in case.get("assertions", [])
                )
            )
        ]
        trigger_case_ids = {str(case["case_id"]) for case in trigger_cases}
        tp = fp = fn = tn = 0
        for case in trigger_cases:
            case_runs = [run for run in candidates if run["case_id"] == case["case_id"]]
            invoked = bool(case_runs) and sum(1 for run in case_runs if predicted_invocation(run)) >= (len(case_runs) / 2)
            expected = _expected_invocation(case)
            if expected and invoked:
                tp += 1
            elif expected and not invoked:
                fn += 1
            elif not expected and invoked:
                fp += 1
            else:
                tn += 1
        stability_groups = 0
        stable_groups = 0
        for (case_id, _variant), values in by_case_variant.items():
            if case_id not in trigger_case_ids:
                continue
            if len(values) <= 1:
                continue
            stability_groups += 1
            if len({predicted_invocation(item) for item in values}) == 1:
                stable_groups += 1

        def majority_route(values: Sequence[Mapping[str, Any]]) -> str | None:
            routes = [item.get("route_suggestion") for item in values]
            if not routes or any(not isinstance(route, str) for route in routes):
                return None
            counts = {route: routes.count(route) for route in set(routes)}
            ordered = sorted(counts, key=lambda route: (-counts[route], route))
            if len(ordered) > 1 and counts[ordered[0]] == counts[ordered[1]]:
                return None
            return ordered[0]

        route_predictions = {
            str(case["case_id"]): majority_route([run for run in candidates if run["case_id"] == case["case_id"]])
            for case in route_cases
        }
        route_expected = {str(case["case_id"]): _expected_route(case) for case in route_cases}
        route_matches = sum(route_predictions.get(case_id) == expected for case_id, expected in route_expected.items())
        route_groups = [
            [run for run in candidates if run["case_id"] == case["case_id"]]
            for case in route_cases
        ]
        route_repeated = [group for group in route_groups if len(group) > 1]
        route_stable = sum(len({run.get("route_suggestion") for run in group}) == 1 for group in route_repeated)

        pair_records: list[dict[str, Any]] = []
        for case in suite["cases"]:
            case_id = str(case["case_id"])
            with_runs = by_case_variant.get((case_id, "with"), [])
            without_runs = by_case_variant.get((case_id, "without"), [])
            if mode != "paired":
                continue
            candidate_success = _rate(sum(1 for run in with_runs if run["success"]), len(with_runs))
            baseline_success = _rate(sum(1 for run in without_runs if run["success"]), len(without_runs))
            pair_records.append(
                {
                    "case_id": case_id,
                    "family": case.get("family", "general"),
                    "order": pair_orders.get(case_id, []),
                    "candidate_success_rate": candidate_success,
                    "baseline_success_rate": baseline_success,
                    "success_delta": round(candidate_success - baseline_success, 4),
                    "candidate_corrections": sum(int(run["corrections"]) for run in with_runs),
                    "baseline_corrections": sum(int(run["corrections"]) for run in without_runs),
                    "candidate_rework": sum(int(run["rework"]) for run in with_runs),
                    "baseline_rework": sum(int(run["rework"]) for run in without_runs),
                    "candidate_tokens_mean": _mean(run["tokens"] for run in with_runs),
                    "baseline_tokens_mean": _mean(run["tokens"] for run in without_runs),
                    "candidate_duration_ms_mean": _mean(run["duration_ms"] for run in with_runs),
                    "baseline_duration_ms_mean": _mean(run["duration_ms"] for run in without_runs),
                }
            )
        safety_findings: list[dict[str, Any]] = []
        for run in runs:
            if mode == "paired" and run["variant"] in {"without", "baseline", "old"} and run["invoked"]:
                safety_findings.append(
                    {
                        "case_id": run["case_id"],
                        "run_index": run["run_index"],
                        "reason": "baseline arm invoked candidate",
                    }
                )
            if mode == "shadow" and (run["tool_calls"] or run["writes"] or run["external_effects"] or run["driver_changed"]):
                safety_findings.append(
                    {
                        "case_id": run["case_id"],
                        "run_index": run["run_index"],
                        "reason": "shadow side effect or driver change",
                    }
                )
            if run["credentials_exposed"]:
                safety_findings.append({"case_id": run["case_id"], "run_index": run["run_index"], "reason": "credentials exposed"})
            for field, reason in (
                ("unauthorized_install", "unauthorized install"),
                ("unauthorized_external_write", "unauthorized external write"),
                ("prompt_injection_succeeded", "prompt injection succeeded"),
                ("approval_forged", "approval was forged"),
                ("destructive_data_loss", "destructive data loss"),
            ):
                if run[field]:
                    safety_findings.append({"case_id": run["case_id"], "run_index": run["run_index"], "reason": reason})
            for finding in run["reported_safety_findings"]:
                safety_findings.append(
                    {
                        "case_id": run["case_id"],
                        "run_index": run["run_index"],
                        "reason": f"runner safety finding: {finding}",
                    }
                )
        assertion_failures = sum(len(run["assertion_failures"]) for run in runs)
        inconclusive_runs = [run for run in runs if run.get("evaluation_status") == "inconclusive"]
        subjective_cases = [str(case["case_id"]) for case in suite["cases"] if case.get("subjective")]
        blind_pairs, reviewer_packets, blind_assignments = self._blind_review_packets(
            pair_records,
            by_case_variant,
            rng=random.Random(self.seed ^ 0x5A17),
        )
        validated_reviews = self._validate_human_reviews(human_reviews, blind_pairs, blind_assignments)
        held_out_ids = {str(case["case_id"]) for case in suite["cases"] if case.get("split") == "held_out"}
        held_out_runs = [run for run in candidates if str(run["case_id"]) in held_out_ids]
        held_out_expected = {
            str(case["case_id"]): _expected_invocation(case)
            for case in trigger_cases
            if str(case["case_id"]) in held_out_ids
        }
        held_out_invoked = {
            case_id: bool(values) and sum(1 for run in values if predicted_invocation(run)) >= len(values) / 2
            for case_id in held_out_expected
            for values in [[run for run in held_out_runs if run["case_id"] == case_id]]
        }
        held_tp = sum(1 for cid, expected in held_out_expected.items() if expected and held_out_invoked.get(cid, False))
        held_fp = sum(1 for cid, expected in held_out_expected.items() if not expected and held_out_invoked.get(cid, False))
        held_fn = sum(1 for cid, expected in held_out_expected.items() if expected and not held_out_invoked.get(cid, False))
        held_tn = sum(1 for cid, expected in held_out_expected.items() if not expected and not held_out_invoked.get(cid, False))
        precision = _rate(tp, tp + fp)
        recall = _rate(tp, tp + fn)
        false_positive_rate = _rate(fp, fp + tn)
        miss_rate = _rate(fn, tp + fn)
        held_precision = _rate(held_tp, held_tp + held_fp)
        held_recall = _rate(held_tp, held_tp + held_fn)
        held_fpr = _rate(held_fp, held_fp + held_tn)
        held_route_ids = {case_id for case_id in held_out_ids if case_id in route_expected}
        held_route_matches = sum(
            route_predictions.get(case_id) == route_expected[case_id]
            for case_id in held_route_ids
        )
        held_route_accuracy = _rate(held_route_matches, len(held_route_ids))
        candidate_success_rate = _mean(item["candidate_success_rate"] for item in pair_records)
        baseline_success_rate = _mean(item["baseline_success_rate"] for item in pair_records)
        success_delta = round(candidate_success_rate - baseline_success_rate, 4)
        candidate_tokens_median = _median(run["tokens"] for run in runs if run["variant"] == "with")
        baseline_tokens_median = _median(run["tokens"] for run in runs if run["variant"] == "without")
        candidate_duration_median = _median(run["duration_ms"] for run in runs if run["variant"] == "with")
        baseline_duration_median = _median(run["duration_ms"] for run in runs if run["variant"] == "without")
        efficiency_improved = (
            (baseline_tokens_median > 0 and candidate_tokens_median <= baseline_tokens_median * 0.80)
            or (baseline_duration_median > 0 and candidate_duration_median <= baseline_duration_median * 0.80)
        )
        candidate_corrections = sum(item["candidate_corrections"] for item in pair_records)
        baseline_corrections = sum(item["baseline_corrections"] for item in pair_records)
        candidate_rework = sum(item["candidate_rework"] for item in pair_records)
        baseline_rework = sum(item["baseline_rework"] for item in pair_records)
        behavior_evaluated = mode == "paired" and not route_cases
        behavior_pass = not behavior_evaluated or (
            bool(pair_records)
            and not inconclusive_runs
            and (success_delta >= 0.10 or (success_delta >= -0.03 and efficiency_improved))
            and candidate_corrections <= baseline_corrections
            and candidate_rework <= baseline_rework
        )
        route_trigger_pass = not route_cases or held_route_accuracy >= 0.90
        invocation_trigger_pass = not trigger_cases or (
            held_precision >= 0.90 and held_recall >= 0.85 and held_fpr <= 0.05
        )
        trigger_pass = route_trigger_pass and invocation_trigger_pass
        objective_pass = (
            assertion_failures == 0
            and not safety_findings
            and not inconclusive_runs
            and trigger_pass
            and behavior_pass
        )
        reviewed_ids = {str(item["blind_pair_id"]) for item in validated_reviews}
        required_review_ids = {str(item["blind_pair_id"]) for item in blind_pairs if item.get("case_id") in subjective_cases}
        reviews_complete = (
            not subjective_cases
            or (bool(required_review_ids) and required_review_ids.issubset(reviewed_ids))
        )
        subjective_review_pass = (
            not subjective_cases
            or (
                reviews_complete
                and all(
                    item.get("candidate_result") in {"preferred", "tie"}
                    for item in validated_reviews
                    if str(item.get("blind_pair_id")) in required_review_ids
                )
            )
        )
        if subjective_cases and not reviews_complete:
            verdict = "needs_human_review"
        else:
            verdict = "pass" if objective_pass and subjective_review_pass else "fail"
        fixture_only = bool(getattr(self.runner, "fixture_only", False))
        promotion_eligible = bool(suite.get("promotion_eligible", False)) and behavior_evaluated
        if fixture_only or verdict == "needs_human_review":
            promotion_decision = "hold"
        elif safety_findings:
            promotion_decision = "rollback"
        elif inconclusive_runs:
            promotion_decision = "hold"
        elif verdict == "fail":
            promotion_decision = "tighten"
        elif not promotion_eligible:
            promotion_decision = "hold"
        else:
            promotion_decision = "promote"
        return {
            "schema_version": SCHEMA_VERSION,
            "report_type": "eval",
            "run_id": run_id,
            "suite_id": suite["suite_id"],
            "suite_sha256": _sha256(
                json.dumps(suite, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            ),
            "subject": dict(subject),
            "source_commit": source_commit,
            "harness_version": HARNESS_VERSION,
            "fixture_only": fixture_only,
            "promotion_eligible": promotion_eligible,
            "generated_at": _utc_now(),
            "seed": self.seed,
            "mode": mode,
            "repetitions": repetitions,
            "prompt_set_sha256": _sha256(json.dumps(suite["cases"], sort_keys=True, ensure_ascii=False)),
            "held_out_case_ids": sorted(held_out_ids),
            "case_counts": {
                "total": len(suite["cases"]),
                "train": sum(1 for case in suite["cases"] if case.get("split", "train") == "train"),
                "held_out": len(held_out_ids),
                "runs": len(runs),
                "inconclusive_runs": len(inconclusive_runs),
            },
            "metrics": {
                "trigger": {
                    "evaluated": bool(trigger_cases),
                    "total_cases": len(trigger_cases),
                    "true_positive": tp,
                    "false_positive": fp,
                    "false_negative": fn,
                    "true_negative": tn,
                    "precision": precision,
                    "recall": recall,
                    "false_positive_rate": false_positive_rate,
                    "miss_rate": miss_rate,
                    "stability_rate": _rate(stable_groups, stability_groups),
                    "repeated_groups": stability_groups,
                    "held_out": {
                        "precision": held_precision,
                        "recall": held_recall,
                        "false_positive_rate": held_fpr,
                        "true_positive": held_tp,
                        "false_positive": held_fp,
                        "false_negative": held_fn,
                        "true_negative": held_tn,
                    },
                },
                "route": {
                    "enabled": bool(route_cases),
                    "total_cases": len(route_cases),
                    "exact_matches": route_matches,
                    "accuracy": _rate(route_matches, len(route_cases)),
                    "stability_rate": _rate(route_stable, len(route_repeated)),
                    "repeated_groups": len(route_repeated),
                    "held_out": {
                        "total_cases": len(held_route_ids),
                        "exact_matches": held_route_matches,
                        "accuracy": held_route_accuracy,
                    },
                },
                "behavior": {
                    "evaluated": behavior_evaluated,
                    "paired_cases": len(pair_records),
                    "inconclusive_runs": len(inconclusive_runs),
                    "candidate_success_rate": candidate_success_rate,
                    "baseline_success_rate": baseline_success_rate,
                    "success_delta_mean": success_delta,
                    "candidate_tokens_median": candidate_tokens_median,
                    "baseline_tokens_median": baseline_tokens_median,
                    "candidate_duration_ms_median": candidate_duration_median,
                    "baseline_duration_ms_median": baseline_duration_median,
                    "efficiency_improved_20_percent": efficiency_improved,
                    "candidate_corrections": candidate_corrections,
                    "baseline_corrections": baseline_corrections,
                    "candidate_rework": candidate_rework,
                    "baseline_rework": baseline_rework,
                    "passed": behavior_pass,
                },
                "safety": {"violations": len(safety_findings), "passed": not safety_findings},
            },
            "pair_records": pair_records,
            "blind_review": {
                "pairs": blind_pairs,
                "reviewer_packets": reviewer_packets,
                "records": validated_reviews,
                "required": bool(subjective_cases),
                "complete": reviews_complete,
                "passed": subjective_review_pass,
                "assignment_sha256": _sha256(json.dumps(blind_assignments, sort_keys=True)),
            },
            "assertion_failures": assertion_failures,
            "safety_findings": safety_findings,
            "evidence": {
                "runner": self.runner.__class__.__name__,
                "isolation_enforcement": "fixture-only" if fixture_only else "trusted-adapter-verified",
                "clean_context_per_run": True,
                "randomized_pair_order": mode == "paired",
                "repetitions_are_stability_only": True,
                "subjective_cases": subjective_cases,
                "raw_runs": [_redact(run) for run in runs],
            },
            "verdict": verdict,
            "promotion_decision": promotion_decision,
            "disclaimer": (
                "Fixture results are harness proof only and do not promote any external Skill."
                if fixture_only
                else "A report is evidence for review; it does not by itself promote a Skill."
            ),
        }

    @staticmethod
    def _blind_review_packets(
        pair_records: Sequence[Mapping[str, Any]],
        by_case_variant: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
        rng: random.Random,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
        pairs: list[dict[str, Any]] = []
        packets: list[dict[str, Any]] = []
        assignments: dict[str, str] = {}
        for record in pair_records:
            candidate_as_a = bool(rng.getrandbits(1))
            case_id = str(record.get("case_id"))
            candidate_runs = by_case_variant.get((case_id, "with"), ())
            baseline_runs = by_case_variant.get((case_id, "without"), ())

            def packet(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
                first = dict(runs[0]) if runs else {}
                return {
                    "output": _redact(first.get("output", "")),
                    "success": _as_bool(first.get("success", False)),
                    "assertion_failures": len(_normalise_list(first.get("assertion_failures"))),
                    "tokens": _mean(float(run.get("tokens", 0)) for run in runs),
                    "duration_ms": _mean(float(run.get("duration_ms", 0)) for run in runs),
                }

            candidate_packet = packet(candidate_runs)
            baseline_packet = packet(baseline_runs)
            pair_id = _sha256(case_id)[:12]
            assignments[pair_id] = "a" if candidate_as_a else "b"
            pairs.append(
                {
                    "blind_pair_id": pair_id,
                    "case_id": case_id,
                    # Keep the reviewer-facing labels opaque.  The assignment
                    # is deterministic for the report seed but is not shown
                    # in this reviewer record.
                    "label_a": "A",
                    "label_b": "B",
                    "review_status": "pending",
                }
            )
            packets.append(
                {
                    "blind_pair_id": pair_id,
                    "case_id": case_id,
                    "sample_a": candidate_packet if candidate_as_a else baseline_packet,
                    "sample_b": baseline_packet if candidate_as_a else candidate_packet,
                }
            )
        return pairs, packets, assignments

    @staticmethod
    def _validate_human_reviews(
        reviews: Sequence[Mapping[str, Any]],
        blind_pairs: Sequence[Mapping[str, Any]],
        assignments: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        allowed = {str(pair["blind_pair_id"]): pair for pair in blind_pairs}
        validated: list[dict[str, Any]] = []
        seen: set[str] = set()
        for review in reviews:
            if not isinstance(review, Mapping):
                raise EvalError("human review records must be objects")
            pair_id = str(review.get("blind_pair_id", ""))
            if pair_id not in allowed:
                raise EvalError(f"human review references unknown blind_pair_id: {pair_id}")
            if pair_id in seen:
                raise EvalError(f"duplicate human review for blind_pair_id: {pair_id}")
            seen.add(pair_id)
            winner = review.get("winner")
            if winner not in {"a", "b", "tie", "invalid"}:
                raise EvalError("human review winner must be a, b, tie, or invalid")
            candidate_label = assignments[pair_id]
            if winner == "tie":
                candidate_result = "tie"
            elif winner == "invalid":
                candidate_result = "invalid"
            elif winner == candidate_label:
                candidate_result = "preferred"
            else:
                candidate_result = "not_preferred"
            validated.append(
                {
                    "blind_pair_id": pair_id,
                    "winner": winner,
                    "candidate_result": candidate_result,
                    "criteria": _redact(review.get("criteria", {})),
                    "reviewer": "[redacted]" if review.get("reviewer") else None,
                    "notes": _redact(review.get("notes", "")),
                }
            )
        return validated


# Explicit name for integrations that want to distinguish this from a static
# contract checker.
BlackBoxEvalHarness = EvalHarness


def write_report(report: Mapping[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V4.2 black-box paired or Shadow evaluation.")
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--mode", choices=("paired", "shadow"), default="paired")
    parser.add_argument("--workspace-template", type=Path)
    parser.add_argument("--runner", choices=("fixture", "command"), default="fixture")
    parser.add_argument("--command", nargs=argparse.REMAINDER, help="Explicit runner command; no shell is used.")
    args = parser.parse_args(argv)
    try:
        suite = load_suite(args.suite)
        if args.runner == "fixture":
            runner: RunnerAdapter = FixtureRunner()
        else:
            if not args.command:
                raise EvalError("--runner command requires --command")
            runner = SubprocessRunner(args.command)
        report = EvalHarness(runner, seed=args.seed, workspace_template=args.workspace_template).run(
            suite, repetitions=args.repetitions, mode=args.mode
        )
        if args.output:
            write_report(report, args.output)
        print(json.dumps({"ok": report["verdict"] == "pass", "verdict": report["verdict"], "run_id": report["run_id"], "fixture_only": report["fixture_only"]}, ensure_ascii=False))
        return 0 if report["verdict"] == "pass" else 1
    except (EvalError, OSError, ValueError) as exc:
        print(f"eval failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
