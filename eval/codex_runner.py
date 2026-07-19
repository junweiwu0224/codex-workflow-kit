"""Conservative Codex CLI adapter for :mod:`eval.harness`.

This adapter deliberately does not reuse the caller's Codex home.  The CLI
needs a credential and a minimal provider configuration, but its runtime
database, bundled-skill synchronisation, and logs must not be mistaken for
task writes.  They live below a sibling runtime directory that the harness
removes with its per-attempt temporary root.

``codex --sandbox read-only`` constrains model-issued commands.  It is not an
isolation boundary for the Codex client itself, its credentials, or its
network traffic.  A caller must supply a trusted external verifier; the
adapter fails closed before copying credentials or launching Codex otherwise.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import urlparse

from .harness import EvalError


_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_PROVIDER_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_BASELINE_VARIANTS = frozenset({"without", "baseline", "old"})
_KNOWN_EVENT_TYPES = frozenset(
    {
        "error",
        "item.completed",
        "item.started",
        "item.updated",
        "thread.started",
        "turn.completed",
        "turn.failed",
        "turn.started",
    }
)
_EXTERNAL_ITEM_TYPES = frozenset({"mcp_tool_call", "web_search"})
_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh", "max", "ultra"})
_INFRASTRUCTURE_FAILURE_CATEGORIES = frozenset(
    {"authentication", "provider_timeout", "provider_unavailable", "rate_limited", "transport"}
)
_ERROR_CATEGORY_PATTERNS = (
    ("rate_limited", re.compile(r"(?:\b429\b|rate[\s_-]*limit|too many requests|throttl)", re.IGNORECASE)),
    (
        "provider_unavailable",
        re.compile(r"(?:\b50[234]\b|service unavailable|provider unavailable|overloaded|server busy)", re.IGNORECASE),
    ),
    ("provider_timeout", re.compile(r"(?:timed?\s*out|timeout)", re.IGNORECASE)),
    (
        "transport",
        re.compile(r"(?:connection (?:refused|reset|closed)|dns|network error|socket error|econn(?:refused|reset))", re.IGNORECASE),
    ),
    ("authentication", re.compile(r"(?:\b40[13]\b|unauthori[sz]ed|authentication failed|invalid api key)", re.IGNORECASE)),
)
_DISABLED_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "enable_mcp_apps",
    "hooks",
    "goals",
    "guardian_approval",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "network_proxy",
    "plugins",
    "remote_plugin",
    "shell_tool",
    "shell_snapshot",
    "skill_mcp_dependency_install",
    "skill_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "unified_exec",
    "workspace_dependencies",
)


@dataclass(frozen=True)
class CodexProvider:
    """The minimal provider fields required by the current Codex CLI."""

    identifier: str
    name: str
    base_url: str
    wire_api: str
    requires_openai_auth: bool = True

    def validate(self) -> None:
        if not _PROVIDER_ID_RE.fullmatch(self.identifier):
            raise EvalError("Codex provider identifier is invalid")
        if not self.name.strip():
            raise EvalError("Codex provider name must be non-empty")
        parsed = urlparse(self.base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise EvalError("Codex provider base URL must not contain credentials, query, or fragment")
        if parsed.scheme == "https" and parsed.hostname:
            pass
        elif parsed.scheme == "http" and parsed.hostname:
            try:
                is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
            except ValueError:
                is_loopback = False
            if not is_loopback:
                raise EvalError("HTTP Codex provider base URL must use a loopback IP address")
        else:
            raise EvalError("Codex provider base URL must use https or loopback http")
        try:
            parsed.port
        except ValueError as exc:
            raise EvalError("Codex provider base URL has an invalid port") from exc
        if not _IDENTIFIER_RE.fullmatch(self.wire_api):
            raise EvalError("Codex provider wire_api is invalid")


@dataclass(frozen=True)
class IsolationRequest:
    """Non-secret facts an external isolation verifier may inspect."""

    runtime_home: Path
    worktree: Path
    provider_base_url: str
    mode: str
    sandbox: str = "read-only"
    approval_policy: str = "never"


TrustedIsolationVerifier = Callable[[IsolationRequest], bool]


class SandboxLauncher(Protocol):
    """An actual process wrapper around the Codex child process."""

    def wrap(self, command: Sequence[str], request: IsolationRequest) -> tuple[list[str], Mapping[str, Any]]:
        ...


def _loopback_host(base_url: str) -> str | None:
    host = urlparse(base_url).hostname
    if not host:
        return None
    try:
        return host if ipaddress.ip_address(host).is_loopback else None
    except ValueError:
        return None


def _loopback_endpoint(base_url: str) -> tuple[str, int] | None:
    host = _loopback_host(base_url)
    if host is None:
        return None
    parsed = urlparse(base_url)
    try:
        port = parsed.port
    except ValueError:
        return None
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return host, port


class MacOSSandboxExecLauncher:
    """Wrap Codex in a fresh macOS Seatbelt profile for loopback providers.

    Read-only route mode is deny-by-default and permits only the selected Codex
    binary to execute. Workspace-write behavior mode must allow Codex to apply
    its nested tool sandbox, so the outer profile instead uses explicit denies:
    writes remain limited to the isolated runtime and disposable worktree, and
    network egress remains limited to the loopback provider. Credential
    isolation still needs the separately required external verifier because
    Seatbelt cannot distinguish the Codex client from its tool children.
    """

    name = "macos-seatbelt"

    def __init__(self, sandbox_exec: str | Path = "/usr/bin/sandbox-exec") -> None:
        self.sandbox_exec = str(sandbox_exec)

    @staticmethod
    def _seatbelt_path(path: Path | str) -> str:
        return json.dumps(str(path))

    def _profile(
        self,
        *,
        runtime_home: Path,
        worktree: Path,
        codex_binary: Path,
        provider_port: int,
        sandbox: str,
    ) -> str:
        if sandbox not in {"read-only", "workspace-write"}:
            raise EvalError("macOS Seatbelt launcher received an unsupported sandbox mode")
        runtime_paths = sorted({str(runtime_home), str(runtime_home.resolve())})
        writable_paths = list(runtime_paths)
        if sandbox == "workspace-write":
            writable_paths.extend(sorted({str(worktree), str(worktree.resolve())}))
        runtime_write_rules = [
            f"  (subpath {self._seatbelt_path(path)})" for path in writable_paths
        ]
        # Seatbelt's `remote tcp` grammar accepts localhost (or `*`) as the
        # host token, not a literal 127.0.0.1. The localhost rule also matches
        # a client connecting to the validated loopback IP.
        network_rule = f"(allow network-outbound (remote tcp {json.dumps(f'localhost:{provider_port}')}))"
        if sandbox == "workspace-write":
            # Codex applies its own workspace sandbox to model-issued tools.
            # A deny-default outer profile prevents that nested sandbox from
            # calling sandbox_apply, so the outer layer uses explicit deny
            # overrides for the two boundaries it owns: network and writes.
            return "\n".join(
                [
                    "(version 1)",
                    "(allow default)",
                    "(deny network-outbound)",
                    network_rule,
                    "(deny file-write*)",
                    "(allow file-write*",
                    *runtime_write_rules,
                    '  (literal "/dev/null"))',
                    "",
                ]
            )
        return "\n".join(
            [
                "(version 1)",
                "(deny default)",
                # The client needs broad read access for its signed bundle and
                # system runtime. Agent-issued tools are disabled separately;
                # no child executable other than the already selected Codex
                # binary can be launched from this profile.
                "(allow file-read*)",
                "(allow file-read-metadata)",
                f"(allow process-exec (literal {self._seatbelt_path(codex_binary)}))",
                "(allow process-fork)",
                "(allow sysctl-read)",
                "(allow mach-lookup)",
                "(allow ipc-posix-shm*)",
                "(allow file-write*",
                *runtime_write_rules,
                '  (literal "/dev/null"))',
                network_rule,
                "",
            ]
        )

    def wrap(self, command: Sequence[str], request: IsolationRequest) -> tuple[list[str], Mapping[str, Any]]:
        endpoint = _loopback_endpoint(request.provider_base_url)
        if endpoint is None:
            raise EvalError("macOS Seatbelt launcher requires a loopback provider URL")
        provider_host, provider_port = endpoint
        if not command:
            raise EvalError("Codex command cannot be empty")
        binary = Path(command[0])
        if not binary.is_absolute():
            resolved = shutil.which(command[0])
            if resolved is None:
                raise EvalError("Codex binary cannot be resolved for macOS Seatbelt")
            binary = Path(resolved)
        binary = _regular_file(binary, "Codex binary")
        sandbox_exec = _regular_file(Path(self.sandbox_exec), "sandbox-exec binary")
        profile_path = request.runtime_home / "codex-eval.sb"
        profile = self._profile(
            runtime_home=request.runtime_home,
            worktree=request.worktree,
            codex_binary=binary,
            provider_port=provider_port,
            sandbox=request.sandbox,
        )
        profile_path.write_text(profile, encoding="utf-8")
        audit = {
            "launcher": self.name,
            "profile_sha256": hashlib.sha256(profile.encode("utf-8")).hexdigest(),
            "network": f"tcp:localhost:{provider_port}",
            "provider_endpoint": f"{provider_host}:{provider_port}",
            "sandbox": request.sandbox,
        }
        return [str(sandbox_exec), "-f", str(profile_path), str(binary), *command[1:]], audit


class CommandIsolationVerifier:
    """Adapter for a separately managed container, VM, or OS-sandbox check.

    The command must emit one JSON object with all required fields.  The
    verifier runs before auth material exists in the runtime directory.
    """

    _REQUIRED = {
        "trusted": True,
        "enforcement": "external-sandbox",
        "network": "provider-only",
        "filesystem": "runtime-and-worktree-only",
        "credentials": "not-readable-by-agent-tools",
    }

    def __init__(self, command: Sequence[str], timeout: float = 15.0) -> None:
        if not command:
            raise EvalError("isolation verifier command cannot be empty")
        self.command = tuple(str(item) for item in command)
        self.timeout = timeout

    def __call__(self, request: IsolationRequest) -> bool:
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C",
            "LC_ALL": "C",
            "EVAL_ISOLATION_RUNTIME_HOME": str(request.runtime_home),
            "EVAL_ISOLATION_WORKTREE": str(request.worktree),
            "EVAL_ISOLATION_PROVIDER_BASE_URL": request.provider_base_url,
            "EVAL_ISOLATION_MODE": request.mode,
            "EVAL_ISOLATION_SANDBOX": request.sandbox,
            "EVAL_ISOLATION_APPROVAL_POLICY": request.approval_policy,
        }
        try:
            completed = subprocess.run(
                self.command,
                env=environment,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if completed.returncode != 0:
            return False
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return False
        return isinstance(value, dict) and all(value.get(key) == expected for key, expected in self._REQUIRED.items())


def _toml_string(value: str) -> str:
    """JSON escaping is valid for the TOML basic-string subset used here."""
    return json.dumps(value)


def _regular_file(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise EvalError(f"{label} does not exist") from exc
    if path.is_symlink() or not resolved.is_file():
        raise EvalError(f"{label} must be a regular file, not a symlink")
    return resolved


def _auth_values(path: Path) -> tuple[str, ...]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError("Codex auth file must be valid JSON") from exc

    values: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, str) and len(item) >= 4:
            values.append(item)
        elif isinstance(item, Mapping):
            for child in item.values():
                collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)

    collect(value)
    return tuple(sorted(set(values), key=len, reverse=True))


def _redact_auth_values(value: str, auth_values: Sequence[str]) -> str:
    for secret in auth_values:
        value = value.replace(secret, "[REDACTED]")
    return value


def _skill_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(directory.rglob("*")):
        if item.is_dir():
            continue
        digest.update(item.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_skill_directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise EvalError(f"{label} does not exist") from exc
    if path.is_symlink() or not resolved.is_dir():
        raise EvalError(f"{label} must be a directory, not a symlink")
    if not (resolved / "SKILL.md").is_file():
        raise EvalError(f"{label} must contain SKILL.md")
    for item in resolved.rglob("*"):
        if item.is_symlink():
            raise EvalError(f"{label} must not contain symlinks")
    return resolved


def _validate_profile(paths: Sequence[str | Path], label: str) -> tuple[Path, ...]:
    profile = tuple(_validate_skill_directory(Path(path), label) for path in paths)
    names = [path.name for path in profile]
    if len(names) != len(set(names)):
        raise EvalError(f"{label} contains duplicate Skill directory names")
    if ".system" in names:
        raise EvalError(f"{label} must not replace Codex built-in system Skills")
    return profile


def _profile_digest(sources: Sequence[Path]) -> str:
    skills = [{"name": source.name, "sha256": _skill_digest(source)} for source in sources]
    encoded = json.dumps(skills, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _item_text(item: Mapping[str, Any]) -> str:
    text = item.get("text")
    if isinstance(text, str):
        return text
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for entry in content:
        if not isinstance(entry, Mapping):
            continue
        value = entry.get("text")
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def _usage_tokens(value: Any) -> int:
    if not isinstance(value, Mapping):
        return 0
    total = value.get("total_tokens")
    if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
        return total
    return sum(
        item
        for key in ("input_tokens", "output_tokens", "cached_input_tokens")
        if isinstance((item := value.get(key)), int) and not isinstance(item, bool) and item >= 0
    )


def _error_event_category(event: Mapping[str, Any]) -> str:
    """Return a non-secret error class without retaining provider diagnostics."""
    encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for category, pattern in _ERROR_CATEGORY_PATTERNS:
        if pattern.search(encoded):
            return category
    return "codex_error"


def parse_codex_jsonl(stdout: str, *, returncode: int) -> dict[str, Any]:
    """Convert Codex ``exec --json`` output into the harness result contract.

    Stderr intentionally is not accepted here.  Codex may include diagnostic
    paths or provider details there, and neither belongs in an evaluation
    report.  Unknown event types and malformed lines fail closed so an alpha
    CLI upgrade cannot silently change the evidence contract.
    """
    event_types: list[str] = []
    messages: list[str] = []
    tool_calls: list[dict[str, str]] = []
    writes: list[str] = []
    external_effects: list[str] = []
    errors: list[str] = []
    failure_categories: list[str] = []
    tokens = 0
    turn_completed = False
    event_count = 0

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append("Codex emitted malformed JSONL")
            continue
        if not isinstance(event, Mapping) or not isinstance(event.get("type"), str):
            errors.append("Codex emitted an invalid JSONL event")
            continue
        event_count += 1
        event_type = event["type"]
        event_types.append(event_type)
        if event_type not in _KNOWN_EVENT_TYPES:
            errors.append(f"unrecognized Codex JSONL event: {event_type}")
            continue
        if event_type in {"error", "turn.failed"}:
            errors.append(f"Codex reported {event_type}")
            failure_categories.append(_error_event_category(event))
            continue
        if event_type == "turn.completed":
            turn_completed = True
            tokens = max(tokens, _usage_tokens(event.get("usage")))
            continue
        if event_type != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, Mapping) or not isinstance(item.get("type"), str):
            errors.append("Codex completed an invalid item")
            continue
        item_type = item["type"]
        status = item.get("status")
        status_text = status if isinstance(status, str) else "unknown"
        if item_type == "agent_message":
            messages.append(_item_text(item))
        elif item_type == "file_change":
            writes.append("reported:file_change")
        elif item_type != "reasoning":
            tool_calls.append({"type": item_type, "status": status_text})
            if item_type in _EXTERNAL_ITEM_TYPES:
                external_effects.append(f"reported:{item_type}")

    if returncode != 0:
        errors.append(f"Codex exited with status {returncode}")
    if not turn_completed:
        errors.append("Codex did not emit turn.completed")
    if event_count == 0:
        errors.append("Codex did not emit JSONL events")
    error = "; ".join(dict.fromkeys(errors)) or None
    categories = sorted(set(failure_categories))
    infrastructure_failure = bool(set(categories) & _INFRASTRUCTURE_FAILURE_CATEGORIES)
    return {
        # Codex JSONL does not attest which optional Skill was selected.
        "invoked": False,
        "invoked_skill": None,
        "route_suggestion": None,
        "output": "\n".join(part for part in messages if part),
        "success": error is None,
        "exit_code": returncode,
        "tool_calls": tool_calls,
        "writes": sorted(set(writes)),
        "external_effects": sorted(set(external_effects)),
        "tokens": tokens,
        "error": error,
        "failure_categories": categories,
        "evaluation_status": "inconclusive" if infrastructure_failure else ("completed" if error is None else "runner_failed"),
        "runner_audit": {
            "event_count": event_count,
            "event_types": event_types,
            "turn_completed": turn_completed,
            "failure_categories": categories,
        },
    }


def _route_decision(result: dict[str, Any], allowed_routes: Sequence[str]) -> None:
    if not result["success"]:
        return
    try:
        decision = json.loads(str(result["output"]))
    except json.JSONDecodeError:
        decision = None
    if (
        not isinstance(decision, Mapping)
        or set(decision) != {"selected_skill", "output"}
        or not isinstance(decision.get("selected_skill"), str)
        or decision["selected_skill"] not in allowed_routes
        or not isinstance(decision.get("output"), str)
    ):
        result["success"] = False
        result["error"] = "Codex did not return a valid structured route decision"
        result["route_suggestion"] = None
        return
    result["route_suggestion"] = decision["selected_skill"]
    result["output"] = decision["output"]


class CodexSubprocessRunner:
    """Run a fixed-policy Codex ``exec`` process in a private runtime HOME."""

    fixture_only = False

    def __init__(
        self,
        *,
        auth_file: str | Path,
        provider: CodexProvider,
        model: str,
        reasoning_effort: str = "low",
        candidate_skills: Sequence[str | Path] = (),
        baseline_skills: Sequence[str | Path] = (),
        candidate_skill: str | Path | None = None,
        baseline_skill: str | Path | None = None,
        codex_binary: str | Path = "codex",
        timeout: float = 120.0,
        isolation_verifier: TrustedIsolationVerifier | None = None,
        sandbox_launcher: SandboxLauncher | None = None,
    ) -> None:
        provider.validate()
        if not _IDENTIFIER_RE.fullmatch(model):
            raise EvalError("Codex model identifier is invalid")
        if reasoning_effort not in _REASONING_EFFORTS:
            raise EvalError("Codex reasoning effort is invalid")
        if timeout <= 0:
            raise EvalError("Codex runner timeout must be positive")
        self.auth_file = _regular_file(Path(auth_file), "Codex auth file")
        self._auth_values = _auth_values(self.auth_file)
        self.provider = provider
        self.model = model
        self.reasoning_effort = reasoning_effort
        if candidate_skill is not None:
            candidate_skills = (*candidate_skills, candidate_skill)
        if baseline_skill is not None:
            baseline_skills = (*baseline_skills, baseline_skill)
        self.candidate_skills = _validate_profile(candidate_skills, "candidate profile")
        self.baseline_skills = _validate_profile(baseline_skills, "baseline profile")
        self.candidate_profile_sha256 = _profile_digest(self.candidate_skills)
        self.baseline_profile_sha256 = _profile_digest(self.baseline_skills)
        self.codex_binary = str(codex_binary)
        self.timeout = timeout
        self.isolation_verifier = isolation_verifier
        self.sandbox_launcher = sandbox_launcher

    def verify_for_harness(self, runner: object, mode: str) -> bool:
        """Supply this to ``EvalHarness`` as its early, fail-closed gate.

        The verifier executes once per materialised runtime in :meth:`run`.
        This early check ensures the harness never starts a non-fixture run
        when no external enforcement mechanism was provided at all.
        """
        return (
            runner is self
            and mode in {"paired", "shadow"}
            and self.isolation_verifier is not None
            and self.sandbox_launcher is not None
        )

    def _profile_for_variant(self, variant: str) -> tuple[Path, ...]:
        return self.baseline_skills if variant in _BASELINE_VARIANTS else self.candidate_skills

    def _write_config(self, codex_home: Path) -> None:
        provider = self.provider
        content = "\n".join(
            [
                f"model_provider = {_toml_string(provider.identifier)}",
                f"model = {_toml_string(self.model)}",
                f"model_reasoning_effort = {_toml_string(self.reasoning_effort)}",
                'approval_policy = "never"',
                'sandbox_mode = "read-only"',
                "",
                f"[model_providers.{provider.identifier}]",
                f"name = {_toml_string(provider.name)}",
                f"base_url = {_toml_string(provider.base_url)}",
                f"wire_api = {_toml_string(provider.wire_api)}",
                f"requires_openai_auth = {'true' if provider.requires_openai_auth else 'false'}",
                "",
            ]
        )
        (codex_home / "config.toml").write_text(content, encoding="utf-8")

    def _stage_profile(self, sources: Sequence[Path], codex_home: Path) -> dict[str, Any]:
        skills: list[dict[str, str]] = []
        for source in sources:
            destination = codex_home / "skills" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
            skills.append({"name": source.name, "sha256": _skill_digest(destination)})
        encoded = json.dumps(skills, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {"skills": skills, "sha256": hashlib.sha256(encoded).hexdigest()}

    def _write_route_schema(self, runtime_home: Path, profile: Mapping[str, Any]) -> tuple[Path, tuple[str, ...]]:
        routes = tuple(["native", *(skill["name"] for skill in profile["skills"])])
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["selected_skill", "output"],
            "properties": {
                "selected_skill": {"type": "string", "enum": list(routes)},
                "output": {"type": "string"},
            },
        }
        path = runtime_home / "route-decision.schema.json"
        path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
        return path, routes

    @staticmethod
    def _routing_prompt(prompt: str, routes: Sequence[str]) -> str:
        options = ", ".join(routes)
        return (
            "Act only as a route classifier. Select exactly one route from: "
            f"{options}. Do not invoke tools, write files, or access any network. "
            "Your decision is a route suggestion, not evidence that a Skill ran. "
            "The output schema requires selected_skill and output.\n\nTask:\n"
            f"{prompt}"
        )

    def _environment(
        self,
        runtime_home: Path,
        codex_home: Path,
        *,
        mode: str,
        variant: str,
        run_id: str,
        repetition: int,
    ) -> dict[str, str]:
        loopback_host = _loopback_host(self.provider.base_url)
        no_proxy = loopback_host or ""
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C",
            "LC_ALL": "C",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "HOME": str(runtime_home),
            "CODEX_HOME": str(codex_home),
            "EVAL_MODE": mode,
            "EVAL_VARIANT": variant,
            "EVAL_RUN_ID": run_id,
            "EVAL_REPETITION": str(repetition),
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
            "http_proxy": "",
            "https_proxy": "",
            "all_proxy": "",
            "NO_PROXY": no_proxy,
            "no_proxy": no_proxy,
        }

    def _command(self, worktree: Path, schema_path: Path, prompt: str) -> list[str]:
        command = [
            self.codex_binary,
            "exec",
            "--json",
            "--strict-config",
            "--ephemeral",
            "--ignore-rules",
        ]
        for feature in _DISABLED_FEATURES:
            command.extend(["--disable", feature])
        command.extend(
            [
                "--output-schema",
                str(schema_path),
                "--color",
                "never",
                "--sandbox",
                "read-only",
                "-c",
                'approval_policy="never"',
                "-m",
                self.model,
                "-C",
                str(worktree),
                "--skip-git-repo-check",
                prompt,
            ]
        )
        return command

    def _failure(self, message: str, *, safety: bool = False, duration_ms: float = 0.0) -> dict[str, Any]:
        result: dict[str, Any] = {
            "invoked": False,
            "invoked_skill": None,
            "output": "",
            "success": False,
            "exit_code": None,
            "tool_calls": [],
            "writes": [],
            "external_effects": [],
            "duration_ms": duration_ms,
            "error": message,
            "failure_categories": [],
            "evaluation_status": "runner_failed",
            "runner_audit": {"event_count": 0, "event_types": [], "turn_completed": False},
        }
        if safety:
            result["safety_findings"] = [message]
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
        if any(
            isinstance(assertion, Mapping) and assertion.get("type") == "skill_invoked"
            for assertion in case.get("assertions", [])
        ):
            return self._failure("Codex JSONL does not attest optional Skill invocation; use route_suggested")
        if self.isolation_verifier is None:
            return self._failure("trusted external isolation verifier is required", safety=True)
        if self.sandbox_launcher is None:
            return self._failure("actual sandbox launcher is required", safety=True)

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
            return self._failure("staged profile changed after runner binding", safety=True)
        schema_path, routes = self._write_route_schema(runtime_home, staged_profile)
        request = IsolationRequest(
            runtime_home=runtime_home,
            worktree=worktree,
            provider_base_url=self.provider.base_url,
            mode=mode,
        )
        try:
            isolated = bool(self.isolation_verifier(request))
        except Exception:
            isolated = False
        if not isolated:
            return self._failure("trusted external isolation verification failed", safety=True)

        # Copy only the credential material needed by the Codex client after
        # the external verifier has accepted the runtime layout.
        auth_target = codex_home / "auth.json"
        shutil.copyfile(self.auth_file, auth_target)
        os.chmod(auth_target, 0o600)
        started = time.perf_counter()
        command = self._command(worktree, schema_path, self._routing_prompt(prompt, routes))
        try:
            wrapped_command, launcher_audit = self.sandbox_launcher.wrap(command, request)
        except (EvalError, OSError):
            return self._failure("sandbox launcher could not prepare the Codex process", safety=True)
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
            return self._failure("Codex runner timed out", duration_ms=(time.perf_counter() - started) * 1000)
        except OSError:
            return self._failure("Codex runner could not start", duration_ms=(time.perf_counter() - started) * 1000)

        result = parse_codex_jsonl(completed.stdout, returncode=completed.returncode)
        _route_decision(result, routes)
        result["output"] = _redact_auth_values(str(result["output"]), self._auth_values)
        result["duration_ms"] = (time.perf_counter() - started) * 1000
        audit = dict(result["runner_audit"])
        audit.update(
            {
                "runtime_home_separate": runtime_home != home,
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "provider": self.provider.identifier,
                "wire_api": self.provider.wire_api,
                "disabled_features": list(_DISABLED_FEATURES),
                "staged_profile": staged_profile,
                "system_skill_surface": "fresh-runtime; built-in Codex Skills are not treated as profile members",
                "stderr_discarded": bool(completed.stderr),
                "sandbox_launcher": dict(launcher_audit),
            }
        )
        result["runner_audit"] = audit
        return result
