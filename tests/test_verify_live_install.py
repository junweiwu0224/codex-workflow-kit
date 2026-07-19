from pathlib import Path
import json

from scripts.verify_live_install import LiveInstallIssue, build_report, check_live_install, main


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
    _write(
        kit / "skills/pilot-example/SKILL.md",
        "---\nname: pilot-example\ndescription: Use when testing pilots.\n---\n\n# pilot-example\n",
    )
    _write(kit / "catalog/profiles/stable.txt", "debug-loop\nrepo-onboarding\n")
    _write(kit / "catalog/profiles/pilot.txt", "pilot-example\n")
    _write(
        kit / "reverse-skill-router/reverse-engineering/SKILL.md",
        "---\nname: reverse-engineering\ndescription: Use when reverse engineering.\n---\n\n# reverse-engineering\n",
    )
    _write(kit / "reverse-skill/README.md", "# Reverse pack\n")
    _write(kit / "reverse-skill/skills/routing.md", "# Routing\n")
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
    for router_file in sorted((kit / "reverse-skill-router").rglob("*")):
        if router_file.is_file():
            target = codex_home / "skills" / router_file.relative_to(kit / "reverse-skill-router")
            _write(target, router_file.read_text(encoding="utf-8"))
    for reverse_file in sorted((kit / "reverse-skill").rglob("*")):
        if reverse_file.is_file():
            target = codex_home / "reverse-skill" / reverse_file.relative_to(kit / "reverse-skill")
            _write(target, reverse_file.read_text(encoding="utf-8"))


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


def test_check_live_install_reports_missing_reverse_router(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    (codex_home / "skills/reverse-engineering/SKILL.md").unlink()

    issues = check_live_install(kit, codex_home, agents_home)

    assert any(
        issue.code == "missing" and issue.path == str(codex_home / "skills/reverse-engineering/SKILL.md")
        for issue in issues
    )


def test_check_live_install_reports_reverse_pack_drift(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    _write(codex_home / "reverse-skill/skills/routing.md", "# Local routing edit\n")

    issues = check_live_install(kit, codex_home, agents_home)

    assert any(
        issue.code == "drift" and issue.path == str(codex_home / "reverse-skill/skills/routing.md")
        for issue in issues
    )


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
    assert report["checked_count"] == 7
    assert report["issues"] == []


def test_check_live_install_allows_default_install_without_reverse_profile(tmp_path, capsys):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    import shutil

    shutil.rmtree(codex_home / "skills/reverse-engineering")
    shutil.rmtree(codex_home / "reverse-skill")

    assert check_live_install(kit, codex_home, agents_home) == []
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
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["reverse_enabled"] is False


def test_check_live_install_allows_default_install_without_pilot_skills(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    import shutil

    shutil.rmtree(agents_home / "skills/pilot-example")

    assert check_live_install(kit, codex_home, agents_home) == []
    report = build_report(kit, codex_home, agents_home)
    assert report["pilots_enabled"] is False


def test_default_verification_ignores_pilot_remnants_after_prune(tmp_path):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    _write(agents_home / "skills/pilot-example/SKILL.md", "# stale pilot remnant\n")

    assert check_live_install(kit, codex_home, agents_home) == []
    report = build_report(kit, codex_home, agents_home)
    assert report["pilots_enabled"] is False
    assert report["checked_count"] == 7

    pilot_issues = check_live_install(kit, codex_home, agents_home, include_pilots=True)
    assert any(
        issue.code == "drift" and issue.path == str(agents_home / "skills/pilot-example/SKILL.md")
        for issue in pilot_issues
    )


def test_with_pilots_requires_pruned_pilot_files(tmp_path, capsys):
    kit = _make_kit(tmp_path)
    codex_home = tmp_path / "codex-home"
    agents_home = tmp_path / "agents-home"
    _install_matching(kit, codex_home, agents_home)
    import shutil

    shutil.rmtree(agents_home / "skills/pilot-example")

    exit_code = main(
        [
            "--root",
            str(kit),
            "--codex-home",
            str(codex_home),
            "--agents-home",
            str(agents_home),
            "--with-pilots",
            "--json",
        ]
    )
    report = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert report["pilots_enabled"] is True
    assert any(
        issue["code"] == "missing"
        and issue["path"] == str(agents_home / "skills/pilot-example/SKILL.md")
        for issue in report["issues"]
    )
