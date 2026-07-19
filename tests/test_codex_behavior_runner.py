import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from eval.codex_behavior_runner import CodexBehaviorRunner
from eval.codex_runner import CodexProvider, IsolationRequest, MacOSSandboxExecLauncher
from scripts.run_real_codex_behavior_eval import _tracked_workspace_directory, build_parser, main


def _provider():
    return CodexProvider("local", "local", "http://127.0.0.1:15721/v1", "responses")


def _auth(path: Path) -> Path:
    auth = path / "auth.json"
    auth.write_text('{"OPENAI_API_KEY":"placeholder-token"}', encoding="utf-8")
    return auth


def _skill(path: Path, label: str) -> Path:
    skill = path / label
    skill.mkdir()
    (skill / "SKILL.md").write_text(f"# {label}\n", encoding="utf-8")
    return skill


def _events(message: str = "completed") -> str:
    return "\n".join(
        json.dumps(event)
        for event in (
            {"type": "thread.started", "thread_id": "thread"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": message}},
            {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 2}},
        )
    )


class _PrefixLauncher:
    def __init__(self):
        self.requests = []

    def wrap(self, command, request):
        self.requests.append(request)
        return ["seatbelt-test", *command], {"launcher": "test-seatbelt", "profile_sha256": "a" * 64}


def _install_verifier(monkeypatch, callback):
    module = types.ModuleType("eval.behavior_verifier")
    module.verify_behavior_case = callback
    monkeypatch.setitem(sys.modules, "eval.behavior_verifier", module)


def test_behavior_runner_requires_verification_id_before_auth_or_launch(tmp_path, monkeypatch):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("Codex must not start")

    monkeypatch.setattr("eval.codex_behavior_runner.subprocess.run", forbidden)
    runner = CodexBehaviorRunner(
        auth_file=_auth(tmp_path),
        provider=_provider(),
        model="gpt-5.6-sol",
        isolation_verifier=lambda request: True,
        sandbox_launcher=_PrefixLauncher(),
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()
    (worktree / "eval/behavior_fixtures/debug-loop").mkdir(parents=True)

    result = runner.run("task", case={}, variant="with", mode="paired", worktree=worktree, home=home, run_id="run", repetition=0)

    assert called is False
    assert result["success"] is False
    assert result["safety_findings"] == ["behavior case requires a non-empty verification_id"]
    assert not list(tmp_path.glob("codex-runtime-*/.codex/auth.json"))


def test_behavior_runner_requires_both_completed_turn_and_verifier_pass(tmp_path, monkeypatch):
    candidate = _skill(tmp_path, "candidate")
    baseline = _skill(tmp_path, "baseline")
    launcher = _PrefixLauncher()
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["environment"] = kwargs["env"]
        observed["worktree"] = Path(kwargs["cwd"])
        assert (Path(kwargs["env"]["CODEX_HOME"]) / "auth.json").is_file()
        fixture_root = Path(kwargs["cwd"]) / "eval/behavior_fixtures/debug-loop"
        fixture_root.mkdir(parents=True, exist_ok=True)
        (fixture_root / "result.txt").write_text("done\n", encoding="utf-8")
        config = (Path(kwargs["env"]["CODEX_HOME"]) / "config.toml").read_text(encoding="utf-8")
        assert 'approval_policy = "never"' in config
        assert 'sandbox_mode = "danger-full-access"' in config
        return subprocess.CompletedProcess(command, 0, _events("placeholder-token"), "private diagnostic")

    monkeypatch.setattr("eval.codex_behavior_runner.subprocess.run", fake_run)
    _install_verifier(
        monkeypatch,
        lambda verification_id, worktree: {
            "passed": verification_id == "debug-loop-python-bug-v1" and (worktree / "eval/behavior_fixtures/debug-loop/result.txt").read_text(encoding="utf-8") == "done\n",
            "checks": [{"name": "result", "passed": True}],
            "summary": "workspace verified",
        },
    )
    runner = CodexBehaviorRunner(
        auth_file=_auth(tmp_path),
        provider=_provider(),
        model="gpt-5.6-sol",
        reasoning_effort="xhigh",
        candidate_skills=[candidate],
        baseline_skills=[baseline],
        codex_binary="codex-test",
        isolation_verifier=lambda request: request.sandbox == "workspace-write",
        sandbox_launcher=launcher,
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()
    (worktree / "eval/behavior_fixtures/debug-loop").mkdir(parents=True)

    result = runner.run(
        "implement fixture",
        case={"verification_id": "debug-loop-python-bug-v1"},
        variant="with",
        mode="paired",
        worktree=worktree,
        home=home,
        run_id="run",
        repetition=0,
    )

    command = observed["command"]
    disabled = {command[index + 1] for index, value in enumerate(command[:-1]) if value == "--disable"}
    assert "--dangerously-bypass-approvals-and-sandbox" in command
    assert "shell_tool" not in disabled
    assert "unified_exec" not in disabled
    assert {"plugins", "apps", "browser_use", "multi_agent", "network_proxy"}.issubset(disabled)
    assert launcher.requests[0].sandbox == "workspace-write"
    assert result["success"] is True
    assert result["evaluation_status"] == "completed"
    assert result["invoked"] is False
    assert result["invoked_skill"] is None
    assert result["route_suggestion"] is None
    assert result["verification"]["passed"] is True
    assert result["runner_audit"]["model"] == "gpt-5.6-sol"
    assert result["runner_audit"]["reasoning_effort"] == "xhigh"
    assert result["runner_audit"]["sandbox"] == "external-workspace-write"
    assert result["runner_audit"]["codex_inner_sandbox"] == "bypassed-for-external-seatbelt"
    assert result["runner_audit"]["staged_profile"]["sha256"] == runner.candidate_profile_sha256
    assert "placeholder-token" not in json.dumps(result)


def test_behavior_runner_fails_closed_when_deterministic_verifier_fails(tmp_path, monkeypatch):
    _install_verifier(
        monkeypatch,
        lambda verification_id, worktree: {"passed": False, "checks": [], "summary": "expected artifact missing"},
    )
    monkeypatch.setattr(
        "eval.codex_behavior_runner.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, _events(), ""),
    )
    runner = CodexBehaviorRunner(
        auth_file=_auth(tmp_path),
        provider=_provider(),
        model="gpt-5.6-sol",
        isolation_verifier=lambda request: True,
        sandbox_launcher=_PrefixLauncher(),
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()

    result = runner.run(
        "task",
        case={"verification_id": "debug-loop-python-bug-v1"},
        variant="with",
        mode="paired",
        worktree=worktree,
        home=home,
        run_id="run",
        repetition=0,
    )

    assert result["success"] is False
    assert result["evaluation_status"] == "task_failed"
    assert "behavior verification failed" in result["error"]
    assert result["verification"]["passed"] is False
    assert result["runner_audit"]["turn_completed"] is True


def test_macos_launcher_workspace_write_profile_limits_writes_to_runtime_and_worktree(tmp_path):
    runtime = tmp_path / "runtime"
    worktree = tmp_path / "worktree"
    runtime.mkdir()
    worktree.mkdir()

    command, audit = MacOSSandboxExecLauncher().wrap(
        ["/bin/echo", "codex", "exec"],
        IsolationRequest(runtime, worktree, "http://127.0.0.1:15721/v1", "paired", sandbox="workspace-write"),
    )

    profile = (runtime / "codex-eval.sb").read_text(encoding="utf-8")
    assert command[:4] == ["/usr/bin/sandbox-exec", "-f", str(runtime / "codex-eval.sb"), "/bin/echo"]
    assert "(allow default)" in profile
    assert "(deny network-outbound)" in profile
    assert "(deny file-write*)" in profile
    assert f'(subpath "{runtime.resolve()}")' in profile
    assert f'(subpath "{worktree.resolve()}")' in profile
    assert '(remote tcp "localhost:15721")' in profile
    assert '(remote tcp "127.0.0.1:15721")' not in profile
    assert audit["sandbox"] == "workspace-write"


def test_behavior_runner_fails_verification_for_writes_outside_case_scope(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        worktree = Path(kwargs["cwd"])
        target = worktree / "eval/behavior_fixtures/debug-loop"
        target.mkdir(parents=True, exist_ok=True)
        (target / "result.txt").write_text("allowed\n", encoding="utf-8")
        (worktree / "outside.txt").write_text("forbidden\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, _events(), "")

    monkeypatch.setattr("eval.codex_behavior_runner.subprocess.run", fake_run)
    _install_verifier(
        monkeypatch,
        lambda verification_id, worktree: {"passed": True, "checks": [], "summary": "target fixture verified"},
    )
    runner = CodexBehaviorRunner(
        auth_file=_auth(tmp_path),
        provider=_provider(),
        model="gpt-5.6-sol",
        isolation_verifier=lambda request: True,
        sandbox_launcher=_PrefixLauncher(),
    )
    home = tmp_path / "home"
    worktree = tmp_path / "worktree"
    home.mkdir()
    worktree.mkdir()
    (worktree / "eval/behavior_fixtures/debug-loop").mkdir(parents=True)

    result = runner.run(
        "task",
        case={"verification_id": "debug-loop-python-bug-v1"},
        variant="with",
        mode="paired",
        worktree=worktree,
        home=home,
        run_id="run",
        repetition=0,
    )

    assert result["success"] is False
    assert result["verification"]["outside_scope_paths"] == ["outside.txt"]
    assert result["verification"]["checks"][-1]["name"] == "write_scope"
    assert result["verification"]["checks"][-1]["passed"] is False


def test_behavior_cli_defaults_to_sol_xhigh_and_accepts_multiple_profiles(tmp_path):
    args = build_parser().parse_args(
        [
            "--suite", str(tmp_path / "suite.json"),
            "--output", str(tmp_path / "report.json"),
            "--auth-file", str(tmp_path / "auth.json"),
            "--model-provider", "custom", "--provider-name", "local",
            "--provider-base-url", "http://127.0.0.1:15721/v1", "--provider-wire-api", "responses",
            "--isolation-verifier", str(tmp_path / "verify"), "--sandbox-wrapper", "macos-seatbelt",
            "--subject-id", "behavior-profile", "--subject-sha256", "a" * 64,
            "--candidate-skill", str(tmp_path / "candidate-one"),
            "--candidate-skill", str(tmp_path / "candidate-two"),
            "--baseline-skill", str(tmp_path / "baseline"),
        ]
    )

    assert args.model == "gpt-5.6-sol"
    assert args.reasoning_effort == "xhigh"
    assert args.candidate_skill == [tmp_path / "candidate-one", tmp_path / "candidate-two"]
    assert args.baseline_skill == [tmp_path / "baseline"]


def test_workspace_template_must_be_a_tracked_directory_inside_clean_source_root(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    tracked = source / "fixture"
    tracked.mkdir()
    (tracked / "input.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=source, check=True)

    assert _tracked_workspace_directory(source, tracked) == tracked
    untracked = source / "untracked"
    untracked.mkdir()
    with pytest.raises(Exception, match="tracked directory"):
        _tracked_workspace_directory(source, untracked)
    with pytest.raises(Exception, match="inside source root"):
        _tracked_workspace_directory(source, tmp_path)


def _commit_fixture_source(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Eval", "-c", "user.email=eval@example.test", "commit", "-m", "fixture"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _behavior_cli_arguments(source: Path, auth: Path, candidate: Path) -> list[str]:
    return [
        "--suite", str(source / "suite.json"), "--output", str(source / "report.json"),
        "--source-root", str(source), "--workspace-template", str(source),
        "--candidate-skill", str(candidate), "--auth-file", str(auth),
        "--model-provider", "custom", "--provider-name", "local",
        "--provider-base-url", "http://127.0.0.1:15721/v1", "--provider-wire-api", "responses",
        "--isolation-verifier", str(source / "verify"), "--sandbox-wrapper", "macos-seatbelt",
        "--subject-id", "profile", "--subject-sha256", "a" * 64,
    ]


def test_behavior_cli_rejects_dirty_source_before_auth_or_model_setup(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    (source / "suite.json").write_text("{}\n", encoding="utf-8")
    candidate = _skill(source, "candidate")
    auth = _auth(source)
    _commit_fixture_source(source)
    (source / "dirty.txt").write_text("not bound\n", encoding="utf-8")

    assert main(_behavior_cli_arguments(source, auth, candidate)) == 2
    assert "clean Git checkout" in capsys.readouterr().err


def test_behavior_cli_rejects_mismatched_candidate_profile_hash_before_run(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    (source / "suite.json").write_text("{}\n", encoding="utf-8")
    candidate = _skill(source, "candidate")
    auth = _auth(source)
    _commit_fixture_source(source)

    assert main(_behavior_cli_arguments(source, auth, candidate)) == 2
    assert "profile subject SHA-256" in capsys.readouterr().err
