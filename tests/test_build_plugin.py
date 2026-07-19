import json
from pathlib import Path

import pytest

from scripts.build_plugin import main, validate_plugin, verify_profile_lock
from scripts.refresh_local_lock import skill_tree_sha256


def test_build_stable_plugin_is_profile_scoped(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "plugin"
    assert main(["--root", str(root), "--output", str(output), "--profile", "stable"]) == 0
    assert (output / ".codex-plugin/plugin.json").is_file()
    assert (output / "skills/junwei-frontend-design/SKILL.md").is_file()
    assert not (output / "skills/spec-kit-xl/SKILL.md").exists()
    assert validate_plugin(output) == []


def test_plugin_builder_requires_force_for_existing_output(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "plugin"
    output.mkdir()
    try:
        main(["--root", str(root), "--output", str(output)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("existing plugin output should require --force")


def test_plugin_lock_verification_covers_packaged_references(tmp_path):
    root = tmp_path / "kit"
    (root / "catalog/profiles").mkdir(parents=True)
    (root / "catalog/profiles/stable.txt").write_text("example\n", encoding="utf-8")
    skill = root / "skills/example"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: example\n---\n", encoding="utf-8")
    reference = skill / "references/playbook.md"
    reference.write_text("locked", encoding="utf-8")
    lock = {
        "entries": [{
            "name": "example",
            "source": {"kind": "repo-local", "path": "skills/example"},
            "resolution": {"status": "resolved", "kind": "repo-local-content"},
            "content": {
                "status": "resolved",
                "algorithm": "sha256",
                "scope": "skill-tree",
                "value": skill_tree_sha256(skill),
            },
        }],
    }
    (root / "catalog/upstreams.lock.json").write_text(json.dumps(lock), encoding="utf-8")

    verify_profile_lock(root, ["example"])
    reference.write_text("drifted", encoding="utf-8")

    with pytest.raises(RuntimeError, match="content hash mismatch: example"):
        verify_profile_lock(root, ["example"])
