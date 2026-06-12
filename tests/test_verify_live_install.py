from pathlib import Path
import json

from scripts.verify_live_install import LiveInstallIssue, check_live_install, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_kit(tmp_path: Path) -> Path:
    kit = tmp_path / "kit"
    _write(kit / "global/AGENTS.md", "# Global rules\n")
    _write(
        kit / "skills/repo-onboarding/SKILL.md",
        "---\nname: repo-onboarding\ndescription: Use when onboarding repos.\n---\n\n# repo-onboarding\n",
    )
    _write(
        kit / "skills/debug-loop/SKILL.md",
        "---\nname: debug-loop\ndescription: Use when debugging failures.\n---\n\n# debug-loop\n",
    )
    _write(kit / "skills/debug-loop/assets/debug-template.md", "# Debug template\n")
    return kit


def _install_matching(kit: Path, codex_home: Path, agents_home: Path) -> None:
    _write(codex_home / "AGENTS.md", (kit / "global/AGENTS.md").read_text(encoding="utf-8"))
    for skill_file in sorted((kit / "skills").glob("*/SKILL.md")):
        target = agents_home / "skills" / skill_file.parent.name / "SKILL.md"
        _write(target, skill_file.read_text(encoding="utf-8"))
    for asset_file in sorted((kit / "skills").glob("*/*/*")):
        if asset_file.is_file():
            target = agents_home / "skills" / asset_file.relative_to(kit / "skills")
            _write(target, asset_file.read_text(encoding="utf-8"))


def test_check_live_install_accepts_matching_install(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)

    assert check_live_install(kit, codex_home, agents_home) == []


def test_check_live_install_reports_global_agents_drift(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    _write(codex_home / "AGENTS.md", "# Local edit\n")

    issues = check_live_install(kit, codex_home, agents_home)

    assert LiveInstallIssue(
        severity="error",
        code="drift",
        path=str(codex_home / "AGENTS.md"),
        message="Installed global AGENTS.md differs from toolkit global/AGENTS.md.",
    ) in issues


def test_check_live_install_reports_missing_skill(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    (agents_home / "skills/debug-loop/SKILL.md").unlink()

    issues = check_live_install(kit, codex_home, agents_home)

    assert any(
        issue.code == "missing" and issue.path == str(agents_home / "skills/debug-loop/SKILL.md")
        for issue in issues
    )


def test_check_live_install_reports_skill_asset_drift(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    _write(agents_home / "skills/debug-loop/assets/debug-template.md", "# Local edit\n")

    issues = check_live_install(kit, codex_home, agents_home)

    assert any(
        issue.code == "drift" and issue.path == str(agents_home / "skills/debug-loop/assets/debug-template.md")
        for issue in issues
    )


def test_check_live_install_reports_foreign_user_plugin_paths(tmp_path):
    kit = _make_kit(tmp_path)
    user_home = tmp_path / "Users" / "junwei"
    codex_home = user_home / ".codex"
    agents_home = user_home / ".agents"
    _install_matching(kit, codex_home, agents_home)
    _write(
        codex_home / "chrome-native-hosts-v2.json",
        json.dumps(
            {
                "entries": [
                    {
                        "paths": {
                            "browserClientPath": (
                                "/" + "Users" + "/" + "otheruser" + "/" + ".codex/plugins/cache/openai-bundled/"
                                "chrome/latest/scripts/browser-client.mjs"
                            ),
                            "codexHome": str(codex_home),
                        }
                    }
                ]
            }
        ),
    )

    issues = check_live_install(kit, codex_home, agents_home, user_home=user_home)

    assert any(issue.code == "foreign-user-plugin-path" for issue in issues)


def test_main_prints_json_report(tmp_path, capsys):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)

    exit_code = main(
        [
            "--root",
            str(kit),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--json",
        ]
    )
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["checked_count"] == 4
    assert report["issues"] == []
