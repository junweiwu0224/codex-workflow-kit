"""Real, verifier-backed Codex behavior runner.

This module deliberately separates execution quality from route selection.  A
Codex completion is not a behavior pass: every case supplies a deterministic
``verification_id`` and the workspace is checked after the turn.  The runner
does not infer or report optional Skill invocation; it records only the fixed
profile that was staged for each paired arm.

The adapter reuses the conservative provider, profile, JSONL, and isolation
primitives from :mod:`eval.codex_runner`.  Its only material difference is an
externally enforced ``workspace-write`` boundary so a behavior fixture can be
changed and verified. macOS does not permit nested ``sandbox_apply`` calls, so
Codex's inner sandbox is explicitly bypassed only after the mandatory outer
launcher limits writes to the disposable runtime/worktree and egress to the
selected provider.
"""
from __future__ import annotations

import shutil
import subprocess
import time
import uuid
import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .codex_runner import (
    _BASELINE_VARIANTS,
    _DISABLED_FEATURES,
    _redact_auth_values,
    CodexSubprocessRunner,
    IsolationRequest,
    parse_codex_jsonl,
)
from .harness import EvalError


# A behavior evaluation must let Codex run commands in its disposable
# worktree. All other interactive/external surfaces remain explicitly off.
_BEHAVIOR_DISABLED_FEATURES = tuple(
    feature for feature in _DISABLED_FEATURES if feature not in {"shell_tool", "unified_exec"}
)

# The deterministic verifier validates only one fixture per case.  Keep the
# corresponding write boundary in the runner so a successful verifier cannot
# mask a mutation elsewhere in the copied source tree.
_BEHAVIOR_CASE_SCOPES = {
    "debug-loop-python-bug-v1": "eval/behavior_fixtures/debug-loop",
    "completion-review-no-go-v1": "eval/behavior_fixtures/completion-review",
    "decision-record-event-log-v1": "eval/behavior_fixtures/decision-record",
    "security-review-webhook-v1": "eval/behavior_fixtures/security-review",
    "spec-kit-xl-artifacts-v1": "eval/behavior_fixtures/spec-kit-xl",
}


def _verification_id(case: Mapping[str, Any]) -> str | None:
    value = case.get("verification_id")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _normalise_verification(value: Any, verification_id: str) -> dict[str, Any]:
    """Validate a verifier result before allowing it into an eval report."""
    if not isinstance(value, Mapping):
        return {
            "verification_id": verification_id,
            "passed": False,
            "checks": [],
            "summary": "behavior verifier returned an invalid result",
        }
    checks = value.get("checks")
    summary = value.get("summary")
    if not isinstance(checks, list) or not isinstance(summary, str):
        return {
            "verification_id": verification_id,
            "passed": False,
            "checks": [],
            "summary": "behavior verifier result is missing checks or summary",
        }
    return {
        "verification_id": verification_id,
        "passed": value.get("passed") is True,
        "checks": checks,
        "summary": summary,
    }


def _snapshot_worktree(worktree: Path) -> dict[str, str]:
    """Fingerprint files, symlinks, and directories for write-scope checks."""
    snapshot: dict[str, str] = {}
    for item in sorted(worktree.rglob("*")):
        relative = item.relative_to(worktree).as_posix()
        try:
            if item.is_symlink():
                snapshot[f"symlink:{relative}"] = item.readlink().as_posix()
            elif item.is_dir():
                snapshot[f"directory:{relative}"] = "directory"
            elif item.is_file():
                snapshot[f"file:{relative}"] = hashlib.sha256(item.read_bytes()).hexdigest()
            else:
                snapshot[f"other:{relative}"] = "other"
        except OSError:
            snapshot[f"unreadable:{relative}"] = "unreadable"
    return snapshot


def _changed_paths(before: Mapping[str, str], after: Mapping[str, str]) -> list[str]:
    return sorted(key.split(":", 1)[1] for key in set(before) | set(after) if before.get(key) != after.get(key))


def _append_scope_check(verification: Mapping[str, Any], *, scope: str, changed_paths: Sequence[str]) -> dict[str, Any]:
    allowed = scope.rstrip("/")
    allowed_prefix = f"{allowed}/"
    outside = [path for path in changed_paths if path != allowed and not path.startswith(allowed_prefix)]
    checks = list(verification.get("checks", []))
    checks.append(
        {
            "name": "write_scope",
            "passed": not outside,
            "detail": (
                f"all changed paths stayed inside {allowed}"
                if not outside
                else f"changed paths outside {allowed}: {', '.join(outside)}"
            ),
        }
    )
    passed = verification.get("passed") is True and not outside
    base_summary = str(verification.get("summary", "behavior verification result"))
    summary = base_summary if not outside else f"{base_summary}; write scope violation"
    return {
        "verification_id": verification.get("verification_id"),
        "passed": passed,
        "checks": checks,
        "summary": summary,
        "write_scope": allowed,
        "changed_paths": list(changed_paths),
        "outside_scope_paths": outside,
    }


class CodexBehaviorRunner(CodexSubprocessRunner):
    """Run paired workspace behavior cases through Codex and a verifier."""

    def verify_for_harness(self, runner: object, mode: str) -> bool:
        return super().verify_for_harness(runner, mode) and mode == "paired"

    def _write_config(self, codex_home: Path) -> None:
        provider = self.provider
        content = "\n".join(
            [
                f"model_provider = {self._toml_string(provider.identifier)}",
                f"model = {self._toml_string(self.model)}",
                f"model_reasoning_effort = {self._toml_string(self.reasoning_effort)}",
                'approval_policy = "never"',
                'sandbox_mode = "danger-full-access"',
                "",
                f"[model_providers.{provider.identifier}]",
                f"name = {self._toml_string(provider.name)}",
                f"base_url = {self._toml_string(provider.base_url)}",
                f"wire_api = {self._toml_string(provider.wire_api)}",
                f"requires_openai_auth = {'true' if provider.requires_openai_auth else 'false'}",
                "",
            ]
        )
        (codex_home / "config.toml").write_text(content, encoding="utf-8")

    @staticmethod
    def _toml_string(value: str) -> str:
        # Importing this tiny helper as a static method prevents behavior
        # configuration from silently inheriting a route-only sandbox mode.
        import json

        return json.dumps(value)

    @staticmethod
    def _behavior_prompt(prompt: str, verification_id: str) -> str:
        return (
            "Complete the requested task in the current workspace. Use local "
            "workspace tools only; do not use network, install dependencies, "
            "change approval policy, or access credentials. Make the smallest "
            "correct changes and run relevant local checks when possible. A "
            "deterministic verifier will inspect the resulting workspace, so do "
            "not claim success unless the work is actually complete.\n\n"
            f"Behavior verification id: {verification_id}\n\nTask:\n{prompt}"
        )

    def _command(self, worktree: Path, prompt: str) -> list[str]:
        command = [
            self.codex_binary,
            "exec",
            "--json",
            "--strict-config",
            "--ephemeral",
            "--ignore-rules",
        ]
        for feature in _BEHAVIOR_DISABLED_FEATURES:
            command.extend(["--disable", feature])
        command.extend(
            [
                "--color",
                "never",
                "--dangerously-bypass-approvals-and-sandbox",
                "-m",
                self.model,
                "-C",
                str(worktree),
                "--skip-git-repo-check",
                prompt,
            ]
        )
        return command

    @staticmethod
    def _verify_behavior(verification_id: str, worktree: Path) -> dict[str, Any]:
        try:
            # Delayed import avoids making ordinary route evaluation depend on
            # the behavior-fixture package while keeping the verifier explicit.
            from .behavior_verifier import verify_behavior_case

            return _normalise_verification(verify_behavior_case(verification_id, worktree), verification_id)
        except Exception:
            return {
                "verification_id": verification_id,
                "passed": False,
                "checks": [],
                "summary": "behavior verifier could not complete",
            }

    def _failure_with_verification(
        self,
        message: str,
        *,
        verification: Mapping[str, Any] | None = None,
        safety: bool = False,
        duration_ms: float = 0.0,
    ) -> dict[str, Any]:
        result = self._failure(message, safety=safety, duration_ms=duration_ms)
        if verification is not None:
            result["verification"] = dict(verification)
            result["runner_audit"]["verification"] = dict(verification)
        return result

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
        if mode != "paired":
            return self._failure_with_verification("behavior runner requires paired mode", safety=True)
        verification_id = _verification_id(case)
        if verification_id is None:
            return self._failure_with_verification("behavior case requires a non-empty verification_id", safety=True)
        scope = _BEHAVIOR_CASE_SCOPES.get(verification_id)
        if scope is None:
            return self._failure_with_verification(
                "behavior case verification_id lacks a declared fixture scope",
                safety=True,
            )
        if self.isolation_verifier is None:
            return self._failure_with_verification("trusted external isolation verifier is required", safety=True)
        if self.sandbox_launcher is None:
            return self._failure_with_verification("actual sandbox launcher is required", safety=True)

        runtime_home = home.parent / f"codex-runtime-{uuid.uuid4().hex}"
        codex_home = runtime_home / ".codex"
        codex_home.mkdir(parents=True)
        self._write_config(codex_home)
        selected_profile = self._profile_for_variant(variant)
        staged_profile = self._stage_profile(selected_profile, codex_home)
        expected_profile_sha256 = (
            self.baseline_profile_sha256 if variant in _BASELINE_VARIANTS else self.candidate_profile_sha256
        )
        if staged_profile["sha256"] != expected_profile_sha256:
            return self._failure_with_verification("staged profile changed after runner binding", safety=True)
        request = IsolationRequest(
            runtime_home=runtime_home,
            worktree=worktree,
            provider_base_url=self.provider.base_url,
            mode=mode,
            sandbox="workspace-write",
        )
        try:
            isolated = bool(self.isolation_verifier(request))
        except Exception:
            isolated = False
        if not isolated:
            return self._failure_with_verification("trusted external isolation verification failed", safety=True)

        # The external verifier has accepted the runtime layout. Only now may
        # the Codex client receive even a test/placeholder auth document.
        auth_target = codex_home / "auth.json"
        shutil.copyfile(self.auth_file, auth_target)
        auth_target.chmod(0o600)
        before_workspace = _snapshot_worktree(worktree)
        started = time.perf_counter()
        command = self._command(worktree, self._behavior_prompt(prompt, verification_id))
        try:
            wrapped_command, launcher_audit = self.sandbox_launcher.wrap(command, request)
        except (EvalError, OSError):
            return self._failure_with_verification("sandbox launcher could not prepare the Codex process", safety=True)
        try:
            completed = subprocess.run(
                wrapped_command,
                cwd=worktree,
                env=self._environment(
                    runtime_home,
                    codex_home,
                    mode=mode,
                    variant=variant,
                    run_id=run_id,
                    repetition=repetition,
                ),
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            verification = _append_scope_check(
                self._verify_behavior(verification_id, worktree),
                scope=scope,
                changed_paths=_changed_paths(before_workspace, _snapshot_worktree(worktree)),
            )
            return self._failure_with_verification(
                "Codex runner timed out",
                verification=verification,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except OSError:
            verification = _append_scope_check(
                self._verify_behavior(verification_id, worktree),
                scope=scope,
                changed_paths=_changed_paths(before_workspace, _snapshot_worktree(worktree)),
            )
            return self._failure_with_verification(
                "Codex runner could not start",
                verification=verification,
                duration_ms=(time.perf_counter() - started) * 1000,
            )

        result = parse_codex_jsonl(completed.stdout, returncode=completed.returncode)
        verification = _append_scope_check(
            self._verify_behavior(verification_id, worktree),
            scope=scope,
            changed_paths=_changed_paths(before_workspace, _snapshot_worktree(worktree)),
        )
        codex_completed = bool(result["success"])
        result["success"] = codex_completed and bool(verification["passed"])
        if not verification["passed"]:
            reason = str(verification["summary"])
            previous = result.get("error")
            result["error"] = f"{previous}; behavior verification failed: {reason}" if previous else f"behavior verification failed: {reason}"
        if result.get("evaluation_status") != "inconclusive":
            result["evaluation_status"] = (
                "completed" if result["success"] else ("task_failed" if codex_completed else "runner_failed")
            )
        # Do not manufacture Skill-use evidence from a staged profile or from
        # a successful workspace mutation.
        result["invoked"] = False
        result["invoked_skill"] = None
        result["route_suggestion"] = None
        result["output"] = _redact_auth_values(str(result["output"]), self._auth_values)
        result["duration_ms"] = (time.perf_counter() - started) * 1000
        audit = dict(result["runner_audit"])
        audit.update(
            {
                "runner_kind": "behavior",
                "runtime_home_separate": runtime_home != home,
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "provider": self.provider.identifier,
                "wire_api": self.provider.wire_api,
                "disabled_features": list(_BEHAVIOR_DISABLED_FEATURES),
                "staged_profile": staged_profile,
                "sandbox": "external-workspace-write",
                "codex_inner_sandbox": "bypassed-for-external-seatbelt",
                "sandbox_launcher": dict(launcher_audit),
                "verification": verification,
                "system_skill_surface": "fresh-runtime; built-in Codex Skills are not treated as profile members",
                "stderr_discarded": bool(completed.stderr),
            }
        )
        result["runner_audit"] = audit
        result["verification"] = verification
        return result
