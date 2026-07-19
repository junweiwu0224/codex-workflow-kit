import json
import subprocess
from pathlib import Path

import pytest

from eval.codex_runner import (
    CodexProvider,
    CodexSubprocessRunner,
    CommandIsolationVerifier,
    IsolationRequest,
    MacOSSandboxExecLauncher,
    parse_codex_jsonl,
)
from eval.harness import EvalError, EvalHarness, evaluate_assertions, load_suite
from scripts.run_real_codex_eval import build_parser


def _provider():
    return CodexProvider(
        identifier="test",
        name="test-provider",
        base_url="https://provider.example.test/v1",
        wire_api="responses",
    )


def _skill(path: Path, label: str) -> Path:
    skill = path / label
    skill.mkdir()
    (skill / "SKILL.md").write_text(f"# {label}\n", encoding="utf-8")
    return skill


def _auth(path: Path) -> Path:
    auth = path / "auth.json"
    auth.write_text('{"OPENAI_API_KEY":"private-auth-value"}', encoding="utf-8")
    return auth


class _PrefixLauncher:
    def __init__(self):
        self.commands = []

    def wrap(self, command, request):
        self.commands.append((list(command), request))
        return ["seatbelt-test", *command], {"launcher": "test-seatbelt", "profile_sha256": "a" * 64}


def _events(message: str = "done") -> str:
    return "\n".join(
        json.dumps(item)
        for item in (
            {"type": "thread.started", "thread_id": "thread"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": message}},
            {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 2}},
        )
    )


def test_parse_codex_jsonl_maps_messages_usage_and_tool_events():
    stdout = "\n".join(
        [
            _events("final"),
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "status": "completed"}}),
        ]
    )

    result = parse_codex_jsonl(stdout, returncode=0)

    assert result["success"] is True
    assert result["output"] == "final"
    assert result["tokens"] == 5
    assert result["tool_calls"] == [{"type": "command_execution", "status": "completed"}]
    assert result["runner_audit"]["event_count"] == 5


def test_parse_codex_jsonl_accepts_item_lifecycle_events_without_double_counting_tools():
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "thread"}),
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "item.started", "item": {"type": "command_execution"}}),
            json.dumps({"type": "item.updated", "item": {"type": "command_execution"}}),
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "status": "completed"}}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
            json.dumps({"type": "turn.completed", "usage": {"total_tokens": 5}}),
        ]
    )

    result = parse_codex_jsonl(stdout, returncode=0)

    assert result["success"] is True
    assert result["tool_calls"] == [{"type": "command_execution", "status": "completed"}]
    assert result["runner_audit"]["event_count"] == 7


def test_parse_codex_jsonl_fails_closed_for_unknown_or_malformed_events():
    result = parse_codex_jsonl('{"type":"new.event"}\nnot json', returncode=0)

    assert result["success"] is False
    assert "unrecognized Codex JSONL event" in result["error"]
    assert "malformed JSONL" in result["error"]
    assert "turn.completed" in result["error"]


def test_parse_codex_jsonl_classifies_infrastructure_failure_without_retaining_diagnostic():
    private_diagnostic = "429 Too Many Requests for <private-home>/project with secret-token"
    stdout = "\n".join(
        json.dumps(event)
        for event in (
            {"type": "thread.started", "thread_id": "thread"},
            {"type": "turn.started"},
            {"type": "error", "message": private_diagnostic},
            {"type": "turn.failed", "error": {"message": private_diagnostic}},
        )
    )

    result = parse_codex_jsonl(stdout, returncode=1)

    assert result["success"] is False
    assert result["evaluation_status"] == "inconclusive"
    assert result["failure_categories"] == ["rate_limited"]
    assert result["runner_audit"]["failure_categories"] == ["rate_limited"]
    assert private_diagnostic not in json.dumps(result)


def test_provider_allows_only_https_or_loopback_http():
    CodexProvider("local", "local", "http://127.0.0.1:15721/v1", "responses").validate()
    with pytest.raises(EvalError, match="loopback"):
        CodexProvider("remote", "remote", "http://provider.example.test/v1", "responses").validate()


def test_runner_fails_before_auth_copy_when_isolation_is_not_verified(tmp_path, monkeypatch):
    auth = _auth(tmp_path)
    runner = CodexSubprocessRunner(auth_file=auth, provider=_provider(), model="gpt-5.4-mini")
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("Codex must not start")

    monkeypatch.setattr("eval.codex_runner.subprocess.run", forbidden)
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run("prompt", case={}, variant="with", mode="paired", worktree=worktree, home=home, run_id="run", repetition=0)

    assert called is False
    assert result["success"] is False
    assert result["safety_findings"] == ["trusted external isolation verifier is required"]
    assert not list(tmp_path.glob("codex-runtime-*/.codex/auth.json"))


def test_runner_requires_an_actual_launcher_before_auth_copy(tmp_path, monkeypatch):
    auth = _auth(tmp_path)
    runner = CodexSubprocessRunner(
        auth_file=auth,
        provider=_provider(),
        model="gpt-5.4-mini",
        isolation_verifier=lambda request: True,
    )
    monkeypatch.setattr("eval.codex_runner.subprocess.run", lambda *args, **kwargs: pytest.fail("must not run"))
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run("prompt", case={}, variant="with", mode="paired", worktree=worktree, home=home, run_id="run", repetition=0)

    assert result["safety_findings"] == ["actual sandbox launcher is required"]
    assert not list(tmp_path.glob("codex-runtime-*/.codex/auth.json"))


def test_runner_stages_selected_profile_and_discards_auth_from_result(tmp_path, monkeypatch):
    auth = _auth(tmp_path)
    candidate = _skill(tmp_path, "candidate-skill")
    candidate_second = _skill(tmp_path, "candidate-second")
    baseline = _skill(tmp_path, "baseline-skill")
    observations = []
    launcher = _PrefixLauncher()

    def verifier(request):
        observations.append(("verified", request.runtime_home, request.worktree))
        assert not (request.runtime_home / ".codex" / "auth.json").exists()
        return True

    def fake_run(command, **kwargs):
        runtime_home = Path(kwargs["env"]["HOME"])
        codex_home = Path(kwargs["env"]["CODEX_HOME"])
        observations.append(("run", command, kwargs["env"], runtime_home, codex_home))
        assert (codex_home / "auth.json").read_text(encoding="utf-8") == auth.read_text(encoding="utf-8")
        schema = json.loads(Path(command[command.index("--output-schema") + 1]).read_text(encoding="utf-8"))
        routes = schema["properties"]["selected_skill"]["enum"]
        if "candidate-skill" in routes:
            assert (codex_home / "skills" / "candidate-skill" / "SKILL.md").is_file()
            assert (codex_home / "skills" / "candidate-second" / "SKILL.md").is_file()
            assert not (codex_home / "skills" / "baseline-skill").exists()
            selected = "candidate-skill"
        else:
            assert routes == ["native", "baseline-skill"]
            assert (codex_home / "skills" / "baseline-skill" / "SKILL.md").is_file()
            assert not (codex_home / "skills" / "candidate-skill").exists()
            selected = "baseline-skill"
        return subprocess.CompletedProcess(
            command,
            0,
            _events(json.dumps({"selected_skill": selected, "output": "private-auth-value"})),
            "provider diagnostic hidden",
        )

    monkeypatch.setattr("eval.codex_runner.subprocess.run", fake_run)
    runner = CodexSubprocessRunner(
        auth_file=auth,
        provider=_provider(),
        model="gpt-5.4-mini",
        candidate_skills=[candidate, candidate_second],
        baseline_skills=[baseline],
        codex_binary="codex-test",
        isolation_verifier=verifier,
        sandbox_launcher=launcher,
    )
    home = tmp_path / "task-home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run("prompt", case={}, variant="with", mode="paired", worktree=worktree, home=home, run_id="run", repetition=0)

    command = observations[1][1]
    environment = observations[1][2]
    assert command[:5] == ["seatbelt-test", "codex-test", "exec", "--json", "--strict-config"]
    assert "read-only" in command
    assert 'approval_policy="never"' in command
    disabled = {command[index + 1] for index, value in enumerate(command[:-1]) if value == "--disable"}
    assert {"apps", "goals", "plugins", "shell_snapshot", "shell_tool", "unified_exec"}.issubset(disabled)
    assert environment["HOME"] != str(home)
    assert environment["CODEX_HOME"].startswith(environment["HOME"])
    assert all(environment[name] == "" for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"))
    assert environment["NO_PROXY"] == ""
    assert result["success"] is True
    assert result["runner_audit"]["runtime_home_separate"] is True
    assert result["runner_audit"]["model"] == "gpt-5.4-mini"
    assert result["runner_audit"]["reasoning_effort"] == "low"
    assert result["route_suggestion"] == "candidate-skill"
    assert [item["name"] for item in result["runner_audit"]["staged_profile"]["skills"]] == [
        "candidate-skill",
        "candidate-second",
    ]
    assert result["runner_audit"]["staged_profile"]["sha256"] == runner.candidate_profile_sha256
    assert result["runner_audit"]["stderr_discarded"] is True
    assert result["runner_audit"]["sandbox_launcher"]["launcher"] == "test-seatbelt"
    assert "private-auth-value" not in json.dumps(result)
    assert result["output"] == "[REDACTED]"

    baseline_result = runner.run(
        "prompt",
        case={},
        variant="without",
        mode="paired",
        worktree=worktree,
        home=home,
        run_id="run",
        repetition=0,
    )

    assert baseline_result["route_suggestion"] == "baseline-skill"
    assert [item["name"] for item in baseline_result["runner_audit"]["staged_profile"]["skills"]] == ["baseline-skill"]


def test_runner_rejects_expected_skill_claim_without_starting_codex(tmp_path, monkeypatch):
    auth = _auth(tmp_path)
    monkeypatch.setattr("eval.codex_runner.subprocess.run", lambda *args, **kwargs: pytest.fail("must not run"))
    runner = CodexSubprocessRunner(
        auth_file=auth,
        provider=_provider(),
        model="gpt-5.4-mini",
        isolation_verifier=lambda request: True,
        sandbox_launcher=_PrefixLauncher(),
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run(
        "prompt",
        case={"assertions": [{"type": "skill_invoked", "skill": "candidate-skill"}]},
        variant="with",
        mode="paired",
        worktree=worktree,
        home=home,
        run_id="run",
        repetition=0,
    )

    assert result["success"] is False
    assert "does not attest optional Skill invocation" in result["error"]


def test_runner_rejects_invalid_structured_route_decision(tmp_path, monkeypatch):
    auth = _auth(tmp_path)
    monkeypatch.setattr(
        "eval.codex_runner.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, _events('{"selected_skill":"not-staged","output":"x"}'), ""),
    )
    runner = CodexSubprocessRunner(
        auth_file=auth,
        provider=_provider(),
        model="gpt-5.4-mini",
        isolation_verifier=lambda request: True,
        sandbox_launcher=_PrefixLauncher(),
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run("prompt", case={}, variant="with", mode="paired", worktree=worktree, home=home, run_id="run", repetition=0)

    assert result["success"] is False
    assert result["route_suggestion"] is None
    assert "valid structured route decision" in result["error"]


def test_command_isolation_verifier_requires_full_external_contract(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        assert kwargs["env"]["EVAL_ISOLATION_RUNTIME_HOME"].endswith("runtime")
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "trusted": True,
            "enforcement": "external-sandbox",
            "network": "provider-only",
            "filesystem": "runtime-and-worktree-only",
            "credentials": "not-readable-by-agent-tools",
        }), "")

    monkeypatch.setattr("eval.codex_runner.subprocess.run", fake_run)
    verifier = CommandIsolationVerifier(["verify-isolation"])
    assert verifier(IsolationRequest(tmp_path / "runtime", tmp_path / "worktree", "https://provider.example.test/v1", "paired"))


def test_macos_launcher_writes_a_loopback_profile_and_wraps_the_command(tmp_path):
    runtime_home = tmp_path / "runtime"
    worktree = tmp_path / "worktree"
    runtime_home.mkdir()
    worktree.mkdir()
    launcher = MacOSSandboxExecLauncher()

    command, audit = launcher.wrap(
        ["/bin/echo", "codex", "exec"],
        IsolationRequest(runtime_home, worktree, "http://127.0.0.1:15721/v1", "paired"),
    )

    profile_path = runtime_home / "codex-eval.sb"
    profile = profile_path.read_text(encoding="utf-8")
    assert command[:4] == ["/usr/bin/sandbox-exec", "-f", str(profile_path), "/bin/echo"]
    assert "(deny default)" in profile
    assert "(allow file-read*)" in profile
    assert '(allow process-exec (literal "/bin/echo"))' in profile
    assert f'(subpath "{runtime_home.resolve()}")' in profile
    assert '(remote tcp "localhost:15721")' in profile
    assert audit["launcher"] == "macos-seatbelt"


def test_runner_config_contains_only_current_strict_fields(tmp_path):
    runner = CodexSubprocessRunner(
        auth_file=_auth(tmp_path),
        provider=CodexProvider("local", "local", "http://127.0.0.1:15721/v1", "responses"),
        model="gpt-5.6-sol",
    )
    codex_home = tmp_path / "runtime/.codex"
    codex_home.mkdir(parents=True)

    runner._write_config(codex_home)

    config = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert 'approval_policy = "never"' in config
    assert 'sandbox_mode = "read-only"' in config
    assert 'model_reasoning_effort = "low"' in config
    assert "disable_response_storage" not in config


def test_loopback_provider_clears_proxies_and_sets_no_proxy(tmp_path):
    runner = CodexSubprocessRunner(
        auth_file=_auth(tmp_path),
        provider=CodexProvider("local", "local", "http://127.0.0.1:15721/v1", "responses"),
        model="gpt-5.4-mini",
    )

    environment = runner._environment(
        tmp_path / "runtime",
        tmp_path / "runtime/.codex",
        mode="paired",
        variant="with",
        run_id="run",
        repetition=0,
    )

    assert environment["NO_PROXY"] == "127.0.0.1"
    assert environment["no_proxy"] == "127.0.0.1"
    assert all(environment[key] == "" for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"))


def test_harness_preserves_non_secret_runner_audit():
    class Runner:
        fixture_only = False

        def run(self, prompt, **kwargs):
            return {"success": True, "runner_audit": {"event_types": ["turn.completed"]}}

    report = EvalHarness(
        Runner(),
        isolation_verifier=lambda runner, mode: True,
        subject={"kind": "component", "id": "subject", "content_sha256": "a" * 64},
        source_commit="a" * 40,
    ).run(load_suite(Path(__file__).resolve().parents[1] / "eval/fixtures/routing-demo.json"), repetitions=1)

    assert all(run["runner_audit"] == [{"event_types": ["turn.completed"]}] for run in report["evidence"]["raw_runs"])


def test_harness_scores_route_suggestions_without_claiming_invocation():
    suite = {
        "schema_version": "4.2",
        "suite_id": "route-only",
        "repetitions": 1,
        "cases": [
            {
                "case_id": "train",
                "prompt": "x",
                "family": "route",
                "split": "train",
                "expected_route": "review",
                "assertions": [{"type": "route_suggested", "skill": "review"}],
            },
            {
                "case_id": "held",
                "prompt": "y",
                "family": "route",
                "split": "held_out",
                "expected_route": "native",
                "assertions": [{"type": "route_suggested", "skill": "native"}],
            },
        ],
    }

    class Runner:
        fixture_only = False

        def run(self, prompt, *, case, **kwargs):
            return {"success": True, "invoked": False, "route_suggestion": case["expected_route"]}

    report = EvalHarness(
        Runner(),
        isolation_verifier=lambda runner, mode: True,
        subject={"kind": "component", "id": "subject", "content_sha256": "a" * 64},
        source_commit="a" * 40,
    ).run(suite, repetitions=1)

    assert report["verdict"] == "pass"
    assert report["promotion_decision"] == "hold"
    assert report["promotion_eligible"] is False
    assert report["metrics"]["behavior"]["evaluated"] is False
    assert report["metrics"]["trigger"]["evaluated"] is False
    assert report["metrics"]["trigger"]["total_cases"] == 0
    assert report["metrics"]["trigger"]["repeated_groups"] == 0
    assert report["metrics"]["route"]["held_out"]["accuracy"] == 1.0
    assert all(run["invoked"] is False for run in report["evidence"]["raw_runs"])


def test_route_not_suggested_assertion_uses_the_structured_route():
    checks, failures = evaluate_assertions(
        {"assertions": [{"type": "route_not_suggested", "skill": "review"}]},
        {"route_suggestion": "native"},
        "paired",
    )

    assert failures == []
    assert checks == [{"type": "route_not_suggested", "ok": True, "detail": "route_suggestion='native', excluded='review'"}]


def test_real_codex_cli_defaults_to_sol_and_accepts_multiple_profile_members(tmp_path):
    args = build_parser().parse_args(
        [
            "--suite",
            str(tmp_path / "suite.json"),
            "--output",
            str(tmp_path / "report.json"),
            "--auth-file",
            str(tmp_path / "auth.json"),
            "--model-provider",
            "custom",
            "--provider-name",
            "local",
            "--provider-base-url",
            "http://127.0.0.1:15721/v1",
            "--provider-wire-api",
            "responses",
            "--isolation-verifier",
            str(tmp_path / "verify"),
            "--sandbox-wrapper",
            "macos-seatbelt",
            "--subject-kind",
            "profile",
            "--subject-id",
            "stable",
            "--subject-sha256",
            "a" * 64,
            "--candidate-skill",
            str(tmp_path / "one"),
            "--candidate-skill",
            str(tmp_path / "two"),
        ]
    )

    assert args.model == "gpt-5.6-sol"
    assert args.reasoning_effort == "low"
    assert args.candidate_skill == [tmp_path / "one", tmp_path / "two"]
