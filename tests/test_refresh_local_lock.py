import json
from pathlib import Path

import pytest

from scripts.refresh_local_lock import expected_lock, main


def test_expected_lock_uses_content_address_not_self_referential_commit(tmp_path: Path):
    root = tmp_path / "kit"
    skill = root / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("example", encoding="utf-8")
    data = {
        "repository": {"name": "kit", "commit": "a" * 40},
        "entries": [{
            "name": "example",
            "source": {"kind": "repo-local", "path": "skills/example/SKILL.md"},
            "resolution": {"status": "resolved", "kind": "repo-commit", "commit": "a" * 40},
            "content": {"status": "unresolved"},
        }],
    }
    result = expected_lock(root, data)
    assert result["repository"] == {"name": "kit", "commit_policy": "release-manifest"}
    assert result["entries"][0]["resolution"] == {"status": "resolved", "kind": "repo-local-content"}
    assert result["entries"][0]["content"]["scope"] == "skill-tree"
    assert len(result["entries"][0]["content"]["value"]) == 64


def test_cli_check_and_write(tmp_path: Path):
    root = tmp_path / "kit"
    skill = root / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("example", encoding="utf-8")
    lock = root / "catalog/upstreams.lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps({
        "repository": {"name": "kit", "commit": "a" * 40},
        "entries": [{"name": "example", "source": {"kind": "repo-local", "path": "skills/example/SKILL.md"}}],
    }), encoding="utf-8")
    assert main(["--root", str(root)]) == 1
    assert main(["--root", str(root), "--write"]) == 0
    assert main(["--root", str(root)]) == 0


def test_expected_lock_does_not_rewrite_external_immutable_pin(tmp_path: Path):
    external = {
        "name": "external",
        "source": {"kind": "git", "repository": "https://example.invalid/external.git"},
        "resolution": {"status": "resolved", "kind": "commit", "commit": "a" * 40},
        "content": {"status": "resolved", "algorithm": "sha256", "value": "b" * 64},
    }
    data = {"repository": {"name": "kit"}, "entries": [external]}
    result = expected_lock(tmp_path, data)
    assert result["entries"][0] == external


def test_expected_lock_hashes_all_packaged_skill_files(tmp_path: Path):
    root = tmp_path / "kit"
    skill = root / "skills/example"
    (skill / "agents").mkdir(parents=True)
    (skill / "references").mkdir()
    (skill / "assets").mkdir()
    (skill / "SKILL.md").write_text("example", encoding="utf-8")
    (skill / "agents/openai.yaml").write_text("allow_implicit_invocation: false\n", encoding="utf-8")
    reference = skill / "references/playbook.md"
    reference.write_text("first", encoding="utf-8")
    asset = skill / "assets/run.sh"
    asset.write_text("#!/bin/sh\n", encoding="utf-8")
    asset.chmod(0o644)
    data = {"entries": [{"name": "example", "source": {"kind": "repo-local", "path": "skills/example/SKILL.md"}}]}

    first = expected_lock(root, data)["entries"][0]["content"]["value"]
    reference.write_text("changed", encoding="utf-8")
    second = expected_lock(root, data)["entries"][0]["content"]["value"]
    asset.chmod(0o744)
    third = expected_lock(root, data)["entries"][0]["content"]["value"]

    assert first != second
    assert second != third


def test_expected_lock_rejects_symlinked_skill_content(tmp_path: Path):
    root = tmp_path / "kit"
    target = tmp_path / "outside-SKILL.md"
    target.write_text("outside", encoding="utf-8")
    skill = root / "skills/example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").symlink_to(target)
    data = {"entries": [{"name": "example", "source": {"kind": "repo-local", "path": "skills/example/SKILL.md"}}]}

    with pytest.raises(ValueError, match="symlinks"):
        expected_lock(root, data)


def test_expected_lock_rejects_source_path_escape(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("outside", encoding="utf-8")
    data = {"entries": [{"name": "example", "source": {"kind": "repo-local", "path": "../outside"}}]}

    with pytest.raises(ValueError, match="escape"):
        expected_lock(tmp_path / "kit", data)
