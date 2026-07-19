import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAPS = (
    ROOT / "reverse-skill/skills/scripts/bootstrap-reverse.sh",
    ROOT / "reverse-skill/kali/scripts/bootstrap-reverse.sh",
)


def _run(command: str, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", command, "bootstrap-test", *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _git(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    ).stdout.strip()


def _locked_git_fixture(tmp_path: Path) -> tuple[Path, Path, str, dict[str, str]]:
    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    checkout = tmp_path / "checkout"
    expected_url = "https://example.invalid/anything-analyzer.git"

    _git("init", "--bare", str(remote))
    _git("symbolic-ref", "HEAD", "refs/heads/main", cwd=remote)
    _git("init", str(source))
    _git("config", "user.email", "test@example.invalid", cwd=source)
    _git("config", "user.name", "Bootstrap Test", cwd=source)
    (source / "package.json").write_text('{"name":"fixture"}\n', encoding="utf-8")
    _git("add", "package.json", cwd=source)
    _git("commit", "-m", "base", cwd=source)
    base_commit = _git("rev-parse", "HEAD", cwd=source)
    _git("remote", "add", "origin", str(remote), cwd=source)
    _git("push", "origin", "HEAD:main", cwd=source)
    (source / "package.json").write_text('{"name":"fixture","version":"2"}\n', encoding="utf-8")
    _git("commit", "-am", "locked", cwd=source)
    locked_commit = _git("rev-parse", "HEAD", cwd=source)
    _git("push", "origin", "HEAD:main", cwd=source)

    _git("clone", str(remote), str(checkout))
    _git("checkout", "--detach", base_commit, cwd=checkout)
    lock = tmp_path / "reverse-dependencies.lock.yaml"
    lock.write_text(
        "schema_version: '4.2'\n"
        "policy: fail-closed\n"
        "dependencies:\n"
        "  - id: anything-analyzer-git\n"
        "    kind: git\n"
        f"    repository: {expected_url}\n"
        f"    commit: {locked_commit}\n"
        "    status: resolved\n",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    git_path = shutil.which("git")
    assert git_path is not None
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"-C\" && \"$3\" == \"remote\" && \"$4\" == \"get-url\" ]]; then\n"
        "  printf '%s\\n' \"$FAKE_ORIGIN_URL\"\n"
        "  exit 0\n"
        "fi\n"
        f"exec {git_path} \"$@\"\n",
        encoding="utf-8",
    )
    (fake_bin / "git").chmod(0o755)
    git_env = os.environ.copy()
    git_env.update(
        {
            "REVERSE_DEPENDENCY_LOCK": str(lock),
            "BOOTSTRAP_REVERSE_LIB_ONLY": "1",
            "FAKE_ORIGIN_URL": expected_url,
            "PATH": f"{fake_bin}{os.pathsep}{git_env['PATH']}",
        }
    )
    return checkout, lock, locked_commit, git_env


@pytest.mark.parametrize("script", BOOTSTRAPS, ids=lambda path: path.parent.parent.name)
def test_locked_checkout_switches_commit_and_rejects_dirty_or_remote_mismatch(tmp_path: Path, script: Path) -> None:
    checkout, _lock, locked_commit, env = _locked_git_fixture(tmp_path)
    command = (
        'source "$1"; log_warn() { :; }; log_err() { :; }; '
        'if fetch_locked_repo anything-analyzer-git "$2"; then exit 0; fi; exit 17'
    )

    switched = _run(command, str(script), str(checkout), env=env)
    assert switched.returncode == 0, switched.stderr
    assert _git("rev-parse", "HEAD", cwd=checkout) == locked_commit

    (checkout / "tampered.txt").write_text("dirty\n", encoding="utf-8")
    dirty = _run(command, str(script), str(checkout), env=env)
    assert dirty.returncode == 17
    (checkout / "tampered.txt").unlink()

    env["FAKE_ORIGIN_URL"] = "https://example.invalid/not-locked.git"
    mismatch = _run(command, str(script), str(checkout), env=env)
    assert mismatch.returncode == 17


@pytest.mark.parametrize("script", BOOTSTRAPS, ids=lambda path: path.parent.parent.name)
def test_pnpm_service_dependencies_require_and_use_frozen_lockfile(tmp_path: Path, script: Path) -> None:
    project = tmp_path / "anything-analyzer"
    project.mkdir()
    env = os.environ.copy()
    env["BOOTSTRAP_REVERSE_LIB_ONLY"] = "1"
    command = (
        'source "$1"; log_err() { :; }; '
        'if install_pnpm_dependencies_frozen "$2"; then exit 0; fi; exit 19'
    )

    missing_lock = _run(command, str(script), str(project), env=env)
    assert missing_lock.returncode == 19

    (project / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    pnpm_log = tmp_path / "pnpm.log"
    (fake_bin / "pnpm").write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > \"$PNPM_LOG\"\n",
        encoding="utf-8",
    )
    (fake_bin / "pnpm").chmod(0o755)
    env.update({"PATH": f"{fake_bin}{os.pathsep}{env['PATH']}", "PNPM_LOG": str(pnpm_log)})

    frozen = _run(command, str(script), str(project), env=env)
    assert frozen.returncode == 0, frozen.stderr
    assert pnpm_log.read_text(encoding="utf-8").strip() == "install --frozen-lockfile"


@pytest.mark.parametrize("script", BOOTSTRAPS, ids=lambda path: path.parent.parent.name)
def test_go_install_stops_when_tag_does_not_resolve_to_locked_commit(tmp_path: Path, script: Path) -> None:
    expected_commit = "a" * 40
    lock = tmp_path / "reverse-dependencies.lock.yaml"
    lock.write_text(
        "schema_version: '4.2'\n"
        "policy: fail-closed\n"
        "dependencies:\n"
        "  - id: example-go\n"
        "    kind: go\n"
        "    module: example.invalid/tool/cmd/tool\n"
        "    repository: https://example.invalid/tool.git\n"
        "    version: v1.2.3\n"
        f"    commit: {expected_commit}\n"
        "    status: resolved\n",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    go_called = tmp_path / "go-called"
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\nprintf '%s\\trefs/tags/v1.2.3\\n' 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'\n",
        encoding="utf-8",
    )
    (fake_bin / "go").write_text(
        "#!/usr/bin/env bash\ntouch \"$GO_CALLED\"\n",
        encoding="utf-8",
    )
    for executable in (fake_bin / "git", fake_bin / "go"):
        executable.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "BOOTSTRAP_REVERSE_LIB_ONLY": "1",
            "REVERSE_DEPENDENCY_LOCK": str(lock),
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "GO_CALLED": str(go_called),
        }
    )
    command = (
        'source "$1"; log_warn() { :; }; log_err() { :; }; '
        'if install_locked_go_package example-go; then exit 0; fi; exit 23'
    )

    result = _run(command, str(script), env=env)
    assert result.returncode == 23
    assert not go_called.exists()


def test_kali_non_service_anything_analyzer_path_verifies_the_checkout() -> None:
    script = BOOTSTRAPS[1].read_text(encoding="utf-8")

    assert "ensure_anything_analyzer_checkout()" in script
    assert "else\n                ensure_anything_analyzer_checkout\n            fi" in script
    assert "ensure_anything_analyzer_checkout || return 1" in script
