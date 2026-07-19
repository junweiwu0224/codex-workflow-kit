import json
from pathlib import Path
import subprocess

from scripts import codex_runtime_smoke
from scripts.codex_runtime_smoke import SUPERPOWERS_SKILLS, build_report, expected_prompt_skills, main
from tests.test_verify_live_install import _install_matching, _make_kit


def _matching_runtime(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    kit = _make_kit(tmp_path)
    user_home = tmp_path / "Users" / "junwei"
    codex_home = user_home / ".codex"
    agents_home = user_home / ".agents"
    _install_matching(kit, codex_home, agents_home)
    return kit, user_home, codex_home, agents_home


def test_build_report_skips_prompt_input_by_default(tmp_path, monkeypatch):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    monkeypatch.setattr(codex_runtime_smoke.shutil, "which", lambda command: "/usr/local/bin/codex")
    monkeypatch.setattr(
        codex_runtime_smoke,
        "_run",
        lambda command, cwd, timeout=30: {
            "ok": True,
            "command": command,
            "returncode": 0,
            "stdout": "codex-cli test",
            "stderr": "",
        },
    )

    report = build_report(kit, codex_home, agents_home, user_home)

    assert report["ok"] is True
    assert report["checks"]["live_install"]["ok"] is True
    assert report["checks"]["local_doctor"]["ok"] is True
    assert report["checks"]["codex_cli"]["version"] == "codex-cli test"
    assert report["checks"]["prompt_input"]["skipped"] is True
    assert report["checks"]["manual_agent_smoke"]["checklist"] == "docs/agent-collaboration-smoke.md"


def test_build_report_checks_prompt_input_when_requested(tmp_path, monkeypatch):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    expected = expected_prompt_skills(kit, include_pilots=True, require_superpowers=False)
    prompt_input = "\n".join(expected)

    def fake_run(command, cwd, timeout=30):
        stdout = prompt_input if command[:3] == ["codex", "debug", "prompt-input"] else "codex-cli test"
        return {"ok": True, "command": command, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(codex_runtime_smoke.shutil, "which", lambda command: "/usr/local/bin/codex")
    monkeypatch.setattr(codex_runtime_smoke, "_run", fake_run)

    report = build_report(kit, codex_home, agents_home, user_home, check_prompt_input=True, include_pilots=True)

    assert report["ok"] is True
    assert report["checks"]["prompt_input"]["skipped"] is False
    assert report["checks"]["prompt_input"]["skills"]["visible"] == list(expected)
    assert report["checks"]["prompt_input"]["skills"]["missing"] == []


def test_build_report_reports_missing_prompt_skill(tmp_path, monkeypatch):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    expected = expected_prompt_skills(kit, include_pilots=True, require_superpowers=False)
    prompt_input = "\n".join(expected[:-1])

    def fake_run(command, cwd, timeout=30):
        stdout = prompt_input if command[:3] == ["codex", "debug", "prompt-input"] else "codex-cli test"
        return {"ok": True, "command": command, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(codex_runtime_smoke.shutil, "which", lambda command: "/usr/local/bin/codex")
    monkeypatch.setattr(codex_runtime_smoke, "_run", fake_run)

    report = build_report(kit, codex_home, agents_home, user_home, check_prompt_input=True, include_pilots=True)

    assert report["ok"] is False
    assert report["checks"]["prompt_input"]["skills"]["missing"] == [expected[-1]]


def test_build_report_reports_missing_superpowers_prompt_skill(tmp_path, monkeypatch):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    expected = expected_prompt_skills(kit, include_pilots=True, require_superpowers=True)
    prompt_input = "\n".join(expected[:-1])

    def fake_run(command, cwd, timeout=30):
        stdout = prompt_input if command[:3] == ["codex", "debug", "prompt-input"] else "codex-cli test"
        return {"ok": True, "command": command, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(codex_runtime_smoke.shutil, "which", lambda command: "/usr/local/bin/codex")
    monkeypatch.setattr(codex_runtime_smoke, "_run", fake_run)

    report = build_report(
        kit,
        codex_home,
        agents_home,
        user_home,
        check_prompt_input=True,
        require_superpowers=True,
        include_pilots=True,
    )

    assert report["ok"] is False
    assert report["checks"]["prompt_input"]["skills"]["missing"] == [SUPERPOWERS_SKILLS[-1]]


def test_main_prints_json_report(tmp_path, monkeypatch, capsys):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    monkeypatch.setattr(codex_runtime_smoke.shutil, "which", lambda command: "/usr/local/bin/codex")
    monkeypatch.setattr(
        codex_runtime_smoke,
        "_run",
        lambda command, cwd, timeout=30: {
            "ok": True,
            "command": command,
            "returncode": 0,
            "stdout": "codex-cli test",
            "stderr": "",
        },
    )

    exit_code = main(
        [
            "--root",
            str(kit),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--user-home",
            str(user_home),
            "--json",
        ]
    )
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["checks"]["prompt_input"]["skipped"] is True


def test_codex_runtime_smoke_cli_does_not_write_bytecode(tmp_path):
    kit, user_home, codex_home, agents_home = _matching_runtime(tmp_path)
    scripts_dir = kit / "scripts"
    scripts_dir.mkdir()
    source_root = Path(__file__).resolve().parents[1]
    for name in ("codex_runtime_smoke.py", "codex_doctor.py", "verify_live_install.py"):
        (scripts_dir / name).write_text((source_root / "scripts" / name).read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [
            "python3",
            str(scripts_dir / "codex_runtime_smoke.py"),
            "--root",
            str(kit),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--user-home",
            str(user_home),
        ],
        cwd=kit,
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode in {0, 1}
    assert not (scripts_dir / "__pycache__").exists()
