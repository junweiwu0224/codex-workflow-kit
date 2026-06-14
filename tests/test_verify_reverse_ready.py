from pathlib import Path
import shutil

from scripts.verify_reverse_ready import check_reverse_ready, main


def test_check_reverse_ready_reports_missing_core_tools(tmp_path, monkeypatch):
    user_home = tmp_path / "home"
    user_home.mkdir()

    def fake_which(name: str) -> str | None:
        if name in {"jadx", "apktool", "frida"}:
            return f"/tmp/{name}"
        return None

    monkeypatch.setattr(shutil, "which", fake_which)

    issues, report = check_reverse_ready(user_home=user_home)

    assert report["ok"] is False
    assert any(issue.code == "missing-core-tool" and issue.path == "r2" for issue in issues)
    assert any(issue.code == "missing-mcp-config" for issue in issues)


def test_check_reverse_ready_accepts_fully_ready_machine(tmp_path, monkeypatch):
    user_home = tmp_path / "home"
    config = user_home / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text("[mcp_servers]\n", encoding="utf-8")

    available = {
        "jadx",
        "apktool",
        "frida",
        "r2",
        "nmap",
        "sqlmap",
        "ffuf",
        "nuclei",
        "binwalk",
        "dot",
        "apksigner",
        "zipalign",
        "adb",
        "plantuml",
    }

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/local/bin/{name}" if name in available else None)

    issues, report = check_reverse_ready(user_home=user_home)

    assert issues == []
    assert report["ok"] is True
    assert report["mcp_config"] == str(config)
    assert report["codex_mcp_config"] == str(config)
    assert report["claude_mcp_config"] is None


def test_check_reverse_ready_warns_when_only_claude_mcp_exists(tmp_path, monkeypatch):
    user_home = tmp_path / "home"
    claude_config = user_home / ".claude/mcp.json"
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text('{"mcpServers": {}}\n', encoding="utf-8")

    available = {
        "jadx",
        "apktool",
        "frida",
        "r2",
        "nmap",
        "sqlmap",
        "ffuf",
        "nuclei",
        "binwalk",
        "dot",
    }

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/local/bin/{name}" if name in available else None)

    issues, report = check_reverse_ready(user_home=user_home)

    assert report["ok"] is True
    assert report["codex_mcp_config"] is None
    assert report["claude_mcp_config"] == str(claude_config)
    assert any(issue.code == "missing-codex-mcp-config" for issue in issues)


def test_check_reverse_ready_respects_explicit_codex_config(tmp_path, monkeypatch):
    user_home = tmp_path / "home"
    custom_codex_config = tmp_path / "custom-codex/config.toml"
    custom_codex_config.parent.mkdir(parents=True)
    custom_codex_config.write_text("[mcp_servers.demo]\ncommand = \"echo\"\n", encoding="utf-8")

    available = {
        "jadx",
        "apktool",
        "frida",
        "r2",
        "nmap",
        "sqlmap",
        "ffuf",
        "nuclei",
        "binwalk",
        "dot",
    }

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/local/bin/{name}" if name in available else None)

    issues, report = check_reverse_ready(user_home=user_home, codex_config=custom_codex_config)

    assert report["ok"] is True
    assert issues == [
        issue for issue in issues if issue.code == "missing-optional-tool"
    ]
    assert report["codex_mcp_config"] == str(custom_codex_config.resolve())


def test_main_prints_json_report(tmp_path, monkeypatch, capsys):
    user_home = tmp_path / "home"
    user_home.mkdir()
    monkeypatch.setattr(shutil, "which", lambda name: None)

    exit_code = main(["--user-home", str(user_home), "--json"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert '"ok": false' in output.lower()
