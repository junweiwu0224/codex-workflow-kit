import json
from pathlib import Path
import subprocess

from scripts.codex_doctor import build_report, main
from tests.test_verify_live_install import _install_matching, _make_kit


def test_codex_doctor_reports_live_install_and_plugin_paths(tmp_path):
    kit = _make_kit(tmp_path)
    user_home = tmp_path / "Users" / "junwei"
    codex_home = user_home / ".codex"
    agents_home = user_home / ".agents"
    _install_matching(kit, codex_home, agents_home)

    report = build_report(kit, codex_home=codex_home, agents_home=agents_home, user_home=user_home)

    assert report["ok"] is True
    assert report["checks"]["live_install"]["ok"] is True
    assert report["checks"]["active_plugin_paths"]["ok"] is True
    assert report["checks"]["active_plugin_paths"]["user_home"] == str(user_home)


def test_codex_doctor_json_output(tmp_path, capsys):
    kit = _make_kit(tmp_path)
    user_home = tmp_path / "Users" / "junwei"
    codex_home = user_home / ".codex"
    agents_home = user_home / ".agents"
    _install_matching(kit, codex_home, agents_home)

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
    assert set(report["checks"]) == {
        "live_install",
        "active_plugin_paths",
    }


def test_codex_doctor_cli_does_not_write_bytecode(tmp_path):
    kit = _make_kit(tmp_path)
    user_home = tmp_path / "Users" / "junwei"
    codex_home = user_home / ".codex"
    agents_home = user_home / ".agents"
    _install_matching(kit, codex_home, agents_home)

    scripts_dir = kit / "scripts"
    scripts_dir.mkdir()
    source_root = Path(__file__).resolve().parents[1]
    (scripts_dir / "codex_doctor.py").write_text(
        (source_root / "scripts/codex_doctor.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "verify_live_install.py").write_text(
        (source_root / "scripts/verify_live_install.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python3",
            str(scripts_dir / "codex_doctor.py"),
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
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not (scripts_dir / "__pycache__").exists()
