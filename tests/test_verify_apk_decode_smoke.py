from pathlib import Path
import subprocess

from scripts.verify_apk_decode_smoke import run_apk_decode_smoke


def test_run_apk_decode_smoke_rejects_missing_fixture(tmp_path):
    issues, report = run_apk_decode_smoke(tmp_path / "missing.apk", codex_home=tmp_path / "codex-home")

    assert report["ok"] is False
    assert any(issue.code == "missing-apk-fixture" for issue in issues)


def test_run_apk_decode_smoke_detects_decode_script_failure(tmp_path, monkeypatch):
    apk = tmp_path / "sample.apk"
    apk.write_bytes(b"fake apk")
    codex_home = tmp_path / "codex-home"
    decode_script = codex_home / "reverse-skill/skills/apk-reverse/scripts/decode.sh"
    decode_script.parent.mkdir(parents=True, exist_ok=True)
    decode_script.write_text("#!/usr/bin/env bash\necho 'apktool_exit_code=1'\n", encoding="utf-8")
    decode_script.chmod(0o755)

    class Result:
        returncode = 0
        stdout = "package=test.app\napktool_exit_code=1\nsmali_dirs=0\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())

    issues, report = run_apk_decode_smoke(apk, codex_home=codex_home, output_root=tmp_path / "out")

    assert report["ok"] is False
    assert any(issue.code == "apktool-decode-failed" for issue in issues)
    assert any(issue.code == "missing-smali-output" for issue in issues)

