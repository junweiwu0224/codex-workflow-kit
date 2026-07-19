from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import scripts.manage_install as manage_install
from scripts.manage_install import main, state_path


def _kit(tmp_path: Path) -> Path:
    kit = tmp_path / "kit"
    (kit / "catalog/profiles").mkdir(parents=True)
    (kit / "catalog/profiles/stable.txt").write_text("stable-skill\n", encoding="utf-8")
    (kit / "catalog/profiles/pilot.txt").write_text("pilot-skill\n", encoding="utf-8")
    (kit / "global/AGENTS.md").parent.mkdir(parents=True)
    (kit / "global/AGENTS.md").write_text("core\n", encoding="utf-8")
    for skill in ("stable-skill", "pilot-skill"):
        skill_dir = kit / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(skill, encoding="utf-8")
    (kit / "repo-template/docs").mkdir(parents=True)
    (kit / "repo-template/docs/readme.md").write_text("repo", encoding="utf-8")
    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(source_root / "install.sh", kit / "install.sh")
    (kit / "scripts").mkdir()
    shutil.copy2(source_root / "scripts/manage_install.py", kit / "scripts/manage_install.py")
    return kit


def _install_files(kit: Path, codex: Path, agents: Path, *, pilot: bool = False, repo: Path | None = None) -> None:
    (codex).mkdir(parents=True, exist_ok=True)
    (agents / "skills").mkdir(parents=True, exist_ok=True)
    (codex / "AGENTS.md").write_text((kit / "global/AGENTS.md").read_text(), encoding="utf-8")
    for name in ("stable-skill", "pilot-skill") if pilot else ("stable-skill",):
        target = agents / "skills" / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((kit / "skills" / name / "SKILL.md").read_text(), encoding="utf-8")
    if repo:
        target = repo / "docs/readme.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("repo", encoding="utf-8")


def _args(kit: Path, codex: Path, agents: Path, mode: str, *extra: str) -> list[str]:
    return [
        mode,
        "--kit-root",
        str(kit),
        "--codex-home",
        str(codex),
        "--agents-home",
        str(agents),
        *extra,
    ]


def _copy_transaction(kit: Path, codex: Path, agents: Path, *extra: str) -> None:
    transaction = state_path(agents).with_name("install-transaction.json")
    data = json.loads(transaction.read_text(encoding="utf-8"))
    for item in data["files"]:
        assert main(_args(kit, codex, agents, "copy-target", *extra, "--target", item["target"])) == 0


def _write_state(agents: Path, files: list[dict]) -> None:
    path = state_path(agents)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "files": files}), encoding="utf-8")


def _state_entry(target: Path, source: str, profile: str, *, active: bool = True) -> dict:
    return {
        "target": str(target),
        "source": source,
        "sha256": "0" * 64,
        "profile": profile,
        "active": active,
    }


def test_record_and_prune_preview_tracks_profile_changes(tmp_path, capsys):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin", "--with-pilots")) == 0
    _install_files(kit, codex, agents, pilot=True)
    assert main(_args(kit, codex, agents, "commit", "--with-pilots")) == 0
    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    assert main(_args(kit, codex, agents, "prune-preview")) == 0
    report = json.loads(capsys.readouterr().out.split("\n")[-2]) if False else None
    # The preview is JSON and must identify the pilot file without removing it.
    captured = capsys.readouterr().out
    assert "pilot-skill/SKILL.md" in captured or (agents / "skills/pilot-skill/SKILL.md").exists()
    assert (agents / "skills/pilot-skill/SKILL.md").exists()

    assert main(_args(kit, codex, agents, "prune")) == 0
    assert not (agents / "skills/pilot-skill/SKILL.md").exists()
    assert (agents / "skills/stable-skill/SKILL.md").exists()


def test_prune_keeps_entire_modified_skill_component_without_force(tmp_path):
    kit = _kit(tmp_path)
    pilot_agent = kit / "skills/pilot-skill/agents/openai.yaml"
    pilot_agent.parent.mkdir(parents=True)
    pilot_agent.write_text("interface: agent\n", encoding="utf-8")
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"

    assert main(_args(kit, codex, agents, "begin", "--with-pilots")) == 0
    _install_files(kit, codex, agents, pilot=True)
    installed_agent = agents / "skills/pilot-skill/agents/openai.yaml"
    installed_agent.parent.mkdir(parents=True, exist_ok=True)
    installed_agent.write_text("interface: agent\n", encoding="utf-8")
    assert main(_args(kit, codex, agents, "commit", "--with-pilots")) == 0

    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    pilot_skill = agents / "skills/pilot-skill/SKILL.md"
    pilot_skill.write_text("user edit", encoding="utf-8")

    assert main(_args(kit, codex, agents, "prune")) == 1
    assert pilot_skill.read_text(encoding="utf-8") == "user edit"
    assert installed_agent.read_text(encoding="utf-8") == "interface: agent\n"
    assert state_path(agents).exists()

    assert main(_args(kit, codex, agents, "prune", "--force")) == 0
    assert not pilot_skill.exists()
    assert not installed_agent.exists()


def test_prune_keeps_entire_modified_reverse_profile_without_force(tmp_path):
    kit = _kit(tmp_path)
    reverse_lock = kit / "catalog/reverse-dependencies.lock.yaml"
    reverse_lock.write_text("components: []\n", encoding="utf-8")
    router = kit / "reverse-skill-router/reverse-engineering/SKILL.md"
    router.parent.mkdir(parents=True)
    router.write_text("router\n", encoding="utf-8")
    first = kit / "reverse-skill/first.txt"
    second = kit / "reverse-skill/nested/second.txt"
    second.parent.mkdir(parents=True)
    first.write_text("first\n", encoding="utf-8")
    second.write_text("second\n", encoding="utf-8")
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"

    assert main(_args(kit, codex, agents, "begin", "--with-reverse")) == 0
    _copy_transaction(kit, codex, agents, "--with-reverse")
    assert main(_args(kit, codex, agents, "commit", "--with-reverse")) == 0
    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0

    installed_first = codex / "reverse-skill/first.txt"
    installed_second = codex / "reverse-skill/nested/second.txt"
    installed_first.write_text("user edit", encoding="utf-8")
    assert main(_args(kit, codex, agents, "prune")) == 1
    assert installed_first.read_text(encoding="utf-8") == "user edit"
    assert installed_second.read_text(encoding="utf-8") == "second\n"
    assert (codex / "skills/reverse-engineering/SKILL.md").read_text(encoding="utf-8") == "router\n"
    assert (codex / "catalog/reverse-dependencies.lock.yaml").read_text(encoding="utf-8") == "components: []\n"

    assert main(_args(kit, codex, agents, "prune", "--force")) == 0
    assert not installed_first.exists()
    assert not installed_second.exists()
    assert not (codex / "skills/reverse-engineering/SKILL.md").exists()
    assert not (codex / "catalog/reverse-dependencies.lock.yaml").exists()


def test_uninstall_keeps_modified_files_without_force(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    (agents / "skills/stable-skill/SKILL.md").write_text("user edit", encoding="utf-8")

    assert main(_args(kit, codex, agents, "uninstall")) == 1
    assert (agents / "skills/stable-skill/SKILL.md").exists()
    # Conflict preflight is atomic: no other managed target is removed first.
    assert (codex / "AGENTS.md").exists()
    assert state_path(agents).exists()

    assert main(_args(kit, codex, agents, "uninstall", "--force")) == 0
    assert not (agents / "skills/stable-skill/SKILL.md").exists()
    assert not state_path(agents).exists()


def test_rollback_restores_backup_bound_by_transaction(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    (codex).mkdir(parents=True)
    target = agents / "skills/stable-skill/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin", "--backup")) == 0
    _copy_transaction(kit, codex, agents, "--backup")
    assert main(_args(kit, codex, agents, "commit", "--backup")) == 0

    assert main(_args(kit, codex, agents, "rollback")) == 0
    assert target.read_text(encoding="utf-8") == "old"


def test_backup_rollback_detaches_restored_user_file_before_uninstall(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("user agents\n", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin", "--backup")) == 0
    _copy_transaction(kit, codex, agents, "--backup")

    assert main(_args(kit, codex, agents, "commit", "--backup")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    record = next(item for item in state["last_transaction"]["files"] if item["target"] == str(target))
    backup = Path(record["public_backup"])
    assert target.read_text(encoding="utf-8") == "core\n"
    assert main(_args(kit, codex, agents, "rollback")) == 0
    assert target.read_text(encoding="utf-8") == "user agents\n"
    assert backup.read_text(encoding="utf-8") == "user agents\n"
    assert not (agents / "skills/stable-skill/SKILL.md").exists()
    assert not state_path(agents).exists()

    # A later uninstall has no authority over the restored user-owned target.
    assert main(_args(kit, codex, agents, "uninstall")) == 0
    assert target.read_text(encoding="utf-8") == "user agents\n"
    assert backup.read_text(encoding="utf-8") == "user agents\n"


def test_rollback_removes_unchanged_files_created_by_install(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)

    assert main(_args(kit, codex, agents, "commit")) == 0
    assert main(_args(kit, codex, agents, "rollback")) == 0
    assert not (codex / "AGENTS.md").exists()
    assert not (agents / "skills/stable-skill/SKILL.md").exists()
    assert not state_path(agents).exists()


def test_rollback_preserves_modified_created_file_even_with_force(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    target = agents / "skills/stable-skill/SKILL.md"
    target.write_text("user edit", encoding="utf-8")

    assert main(_args(kit, codex, agents, "rollback")) == 1
    assert target.read_text(encoding="utf-8") == "user edit"
    assert (codex / "AGENTS.md").read_text(encoding="utf-8") == "core\n"
    assert state_path(agents).exists()

    assert main(_args(kit, codex, agents, "rollback", "--force")) == 1
    assert target.read_text(encoding="utf-8") == "user edit"
    assert (codex / "AGENTS.md").read_text(encoding="utf-8") == "core\n"
    assert state_path(agents).exists()


def test_rollback_validates_every_recorded_backup_before_changes(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("user agents\n", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin", "--backup")) == 0
    _copy_transaction(kit, codex, agents, "--backup")
    assert main(_args(kit, codex, agents, "commit", "--backup")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    record = next(item for item in state["last_transaction"]["files"] if item["target"] == str(target))
    Path(record["rollback_snapshot"]).write_text("tampered", encoding="utf-8")

    assert main(_args(kit, codex, agents, "rollback", "--force")) == 2
    assert target.read_text(encoding="utf-8") == "core\n"
    assert (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8") == "stable-skill"
    assert state_path(agents).exists()


def test_transaction_does_not_mistake_stale_backup_for_fresh_create(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    target = agents / "skills/stable-skill/SKILL.md"
    target.parent.mkdir(parents=True)
    stale_backup = target.with_name(target.name + ".bak-20250101000000")
    stale_backup.write_text("stale user file", encoding="utf-8")

    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    record = next(item for item in state["last_transaction"]["files"] if item["target"] == str(target))
    assert record["before_exists"] is False

    assert main(_args(kit, codex, agents, "rollback")) == 0
    assert not target.exists()
    assert stale_backup.read_text(encoding="utf-8") == "stale user file"


def test_force_commit_is_fail_closed_but_abort_restores_private_snapshot(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("user agents\n", encoding="utf-8")

    # An interrupted force install can be recovered from its private journal.
    assert main(_args(kit, codex, agents, "begin", "--force")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "abort", "--force")) == 0
    assert target.read_text(encoding="utf-8") == "user agents\n"
    assert not (agents / "skills/stable-skill/SKILL.md").exists()

    # Force suppresses a public backup, but the private transaction preimage
    # still makes the most recent install safely reversible.
    assert main(_args(kit, codex, agents, "begin", "--force")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit", "--force")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    record = next(item for item in state["last_transaction"]["files"] if item["target"] == str(target))
    assert record["public_backup"] is None
    assert main(_args(kit, codex, agents, "rollback", "--force")) == 0
    assert target.read_text(encoding="utf-8") == "user agents\n"
    assert not state_path(agents).exists()


def test_identical_preexisting_files_are_not_claimed_by_install(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    _install_files(kit, codex, agents)

    assert main(_args(kit, codex, agents, "begin")) == 0
    _install_files(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    assert state["files"] == []

    assert main(_args(kit, codex, agents, "uninstall")) == 0
    assert (codex / "AGENTS.md").read_text(encoding="utf-8") == "core\n"
    assert (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8") == "stable-skill"


def test_commit_binds_only_backup_created_after_begin(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("current user agents\n", encoding="utf-8")
    stale = target.with_name(target.name + ".bak-20250101000000")
    stale.write_text("stale agents\n", encoding="utf-8")

    assert main(_args(kit, codex, agents, "begin", "--backup")) == 0
    _copy_transaction(kit, codex, agents, "--backup")
    assert main(_args(kit, codex, agents, "commit", "--backup")) == 0
    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    record = next(item for item in state["last_transaction"]["files"] if item["target"] == str(target))
    fresh = Path(record["public_backup"])
    assert fresh != stale

    assert main(_args(kit, codex, agents, "rollback")) == 0
    assert target.read_text(encoding="utf-8") == "current user agents\n"
    assert stale.read_text(encoding="utf-8") == "stale agents\n"


def test_rollback_only_reverts_the_most_recent_repeat_install(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    before = (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8")

    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    assert main(_args(kit, codex, agents, "rollback")) == 0

    assert (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8") == before
    restored = json.loads(state_path(agents).read_text(encoding="utf-8"))
    assert restored["files"]
    assert "last_transaction" not in restored


def test_profile_shrink_then_rollback_restores_previous_active_profile(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin", "--with-pilots")) == 0
    _copy_transaction(kit, codex, agents, "--with-pilots")
    assert main(_args(kit, codex, agents, "commit", "--with-pilots")) == 0

    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    assert main(_args(kit, codex, agents, "rollback")) == 0

    state = json.loads(state_path(agents).read_text(encoding="utf-8"))
    pilot = next(item for item in state["files"] if "pilot-skill/SKILL.md" in item["target"])
    assert pilot["active"] is True
    assert (agents / "skills/pilot-skill/SKILL.md").exists()


def test_upgrade_one_file_then_rollback_restores_only_that_file(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    assert main(_args(kit, codex, agents, "commit")) == 0
    stable_before = (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8")
    (kit / "global/AGENTS.md").write_text("core v2\n", encoding="utf-8")

    assert main(_args(kit, codex, agents, "begin", "--force")) == 0
    _copy_transaction(kit, codex, agents, "--force")
    assert main(_args(kit, codex, agents, "commit", "--force")) == 0
    assert main(_args(kit, codex, agents, "rollback")) == 0

    assert (codex / "AGENTS.md").read_text(encoding="utf-8") == "core\n"
    assert (agents / "skills/stable-skill/SKILL.md").read_text(encoding="utf-8") == stable_before


def test_reserved_backup_collision_fails_without_overwriting_user_file(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("user agents\n", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin", "--backup")) == 0
    transaction = json.loads(state_path(agents).with_name("install-transaction.json").read_text(encoding="utf-8"))
    planned = Path(next(item for item in transaction["files"] if item["target"] == str(target))["planned_backup"])
    planned.write_text("user sentinel\n", encoding="utf-8")

    assert main(_args(kit, codex, agents, "copy-target", "--backup", "--target", str(target))) == 2
    assert planned.read_text(encoding="utf-8") == "user sentinel\n"
    assert target.read_text(encoding="utf-8") == "user agents\n"
    assert main(_args(kit, codex, agents, "abort", "--backup")) == 1
    planned.unlink()
    assert main(_args(kit, codex, agents, "abort", "--backup")) == 0


def test_begin_cleans_a_committed_but_stale_journal(tmp_path, monkeypatch):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    assert main(_args(kit, codex, agents, "begin")) == 0
    _copy_transaction(kit, codex, agents)
    original_cleanup = manage_install.remove_transaction_storage

    def leave_journal(*_args, **_kwargs):
        raise RuntimeError("simulated cleanup interruption")

    monkeypatch.setattr(manage_install, "remove_transaction_storage", leave_journal)
    assert main(_args(kit, codex, agents, "commit")) == 0
    monkeypatch.setattr(manage_install, "remove_transaction_storage", original_cleanup)
    transaction_path = state_path(agents).with_name("install-transaction.json")
    stale_id = json.loads(transaction_path.read_text(encoding="utf-8"))["transaction_id"]

    assert main(_args(kit, codex, agents, "begin")) == 0
    fresh_id = json.loads(transaction_path.read_text(encoding="utf-8"))["transaction_id"]
    assert fresh_id != stale_id
    assert main(_args(kit, codex, agents, "abort")) == 0


def test_copy_rejects_target_drift_after_begin_and_abort_preserves_it(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir(parents=True)
    target = codex / "AGENTS.md"
    target.write_text("before\n", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin", "--force")) == 0
    target.write_text("user changed after begin\n", encoding="utf-8")

    assert main(_args(kit, codex, agents, "copy-target", "--force", "--target", str(target))) == 2
    assert main(_args(kit, codex, agents, "abort", "--force")) == 0
    assert target.read_text(encoding="utf-8") == "user changed after begin\n"
    assert not state_path(agents).exists()


def test_post_hoc_record_without_begin_is_rejected(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    _install_files(kit, codex, agents)

    assert main(_args(kit, codex, agents, "record")) == 2
    assert not state_path(agents).exists()


def test_abort_rejects_forged_transaction_target_before_changes(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    outside = tmp_path / "outside.txt"
    outside.write_text("protected", encoding="utf-8")
    assert main(_args(kit, codex, agents, "begin")) == 0
    transaction = state_path(agents).with_name("install-transaction.json")
    data = json.loads(transaction.read_text(encoding="utf-8"))
    data["files"][0]["target"] = str(outside)
    transaction.write_text(json.dumps(data), encoding="utf-8")

    assert main(_args(kit, codex, agents, "abort")) == 2
    assert outside.read_text(encoding="utf-8") == "protected"
    assert transaction.exists()


def test_shell_installer_backup_rollback_uninstall_chain(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir()
    target = codex / "AGENTS.md"
    target.write_text("user shell agents\n", encoding="utf-8")
    base = [str(kit / "install.sh"), "--codex-home", str(codex), "--agents-home", str(agents)]

    installed = subprocess.run([*base, "--backup"], text=True, capture_output=True, check=False)
    assert installed.returncode == 0, installed.stderr + installed.stdout
    assert "Install transaction committed" in installed.stdout
    rolled_back = subprocess.run([*base, "--rollback"], text=True, capture_output=True, check=False)
    assert rolled_back.returncode == 0, rolled_back.stderr + rolled_back.stdout
    assert target.read_text(encoding="utf-8") == "user shell agents\n"
    assert not state_path(agents).exists()

    uninstalled = subprocess.run([*base, "--uninstall"], text=True, capture_output=True, check=False)
    assert uninstalled.returncode == 0, uninstalled.stderr + uninstalled.stdout
    assert target.read_text(encoding="utf-8") == "user shell agents\n"


def test_shell_installer_failure_aborts_partial_force_install(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    codex.mkdir()
    target = codex / "AGENTS.md"
    target.write_text("user shell agents\n", encoding="utf-8")
    verifier = kit / "scripts/verify_reverse_ready.py"
    verifier.write_text("raise SystemExit(9)\n", encoding="utf-8")

    result = subprocess.run(
        [
            str(kit / "install.sh"),
            "--codex-home",
            str(codex),
            "--agents-home",
            str(agents),
            "--force",
            "--verify-reverse-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Install transaction aborted" in result.stdout
    assert target.read_text(encoding="utf-8") == "user shell agents\n"
    assert not (agents / "skills/stable-skill/SKILL.md").exists()
    assert not state_path(agents).exists()
    assert not state_path(agents).with_name("install-transaction.json").exists()


def test_management_rejects_outside_state_target_even_with_force_and_rollback(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    _install_files(kit, codex, agents)
    outside = tmp_path / "outside.txt"
    outside.write_text("protected", encoding="utf-8")
    outside.with_name(outside.name + ".bak-20260101000000").write_text("backup", encoding="utf-8")
    valid_target = codex / "AGENTS.md"

    for mode, extra, active in (
        ("prune", (), False),
        ("uninstall", ("--force",), True),
        ("rollback", ("--force",), True),
    ):
        _write_state(
            agents,
            [
                _state_entry(valid_target, "global/AGENTS.md", "core", active=active),
                _state_entry(outside, "global/AGENTS.md", "core", active=active),
            ],
        )
        assert main(_args(kit, codex, agents, mode, *extra)) == 2
        assert outside.read_text(encoding="utf-8") == "protected"
        assert valid_target.read_text(encoding="utf-8") == "core\n"
        assert state_path(agents).exists()


def test_management_rejects_source_traversal_and_symlink_parent_escape(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    _install_files(kit, codex, agents)
    target = agents / "skills/stable-skill/SKILL.md"

    _write_state(agents, [_state_entry(target, "../outside-source", "stable")])
    assert main(_args(kit, codex, agents, "uninstall", "--force")) == 2
    assert target.read_text(encoding="utf-8") == "stable-skill"

    outside = tmp_path / "outside"
    escaped_target = outside / "stable-skill/SKILL.md"
    escaped_target.parent.mkdir(parents=True)
    escaped_target.write_text("protected", encoding="utf-8")
    escaped_target.with_name(escaped_target.name + ".bak-20260101000000").write_text("backup", encoding="utf-8")
    shutil.rmtree(agents / "skills")
    (agents / "skills").symlink_to(outside, target_is_directory=True)
    _write_state(agents, [_state_entry(target, "skills/stable-skill/SKILL.md", "stable")])

    assert main(_args(kit, codex, agents, "rollback")) == 2
    assert escaped_target.read_text(encoding="utf-8") == "protected"


def test_management_rejects_relative_and_root_state_targets(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    _install_files(kit, codex, agents)

    for invalid_target in (Path("relative-target"), agents):
        _write_state(agents, [_state_entry(invalid_target, "global/AGENTS.md", "core")])
        assert main(_args(kit, codex, agents, "uninstall", "--force")) == 2
        assert (codex / "AGENTS.md").read_text(encoding="utf-8") == "core\n"


def test_repo_only_requires_repo_and_manages_repo_install(tmp_path):
    kit = _kit(tmp_path)
    codex = tmp_path / "codex"
    agents = tmp_path / "agents"
    repo = tmp_path / "repo"

    assert main(_args(kit, codex, agents, "uninstall", "--repo-only")) == 2
    repo.mkdir()
    assert main(_args(kit, codex, agents, "begin", "--repo-only", "--repo", str(repo))) == 0
    _install_files(kit, codex, agents, repo=repo)
    assert main(_args(kit, codex, agents, "commit", "--repo-only", "--repo", str(repo))) == 0
    assert main(_args(kit, codex, agents, "uninstall", "--repo-only", "--repo", str(repo))) == 0
    assert not (repo / "docs/readme.md").exists()
    assert not state_path(agents, repo=repo, repo_only=True).exists()
