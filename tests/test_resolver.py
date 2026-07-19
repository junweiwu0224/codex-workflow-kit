import json
from pathlib import Path

from eval.resolver import resolve_catalog
from scripts.refresh_local_lock import skill_tree_sha256


ROOT = Path(__file__).resolve().parents[1]


def test_current_repo_local_lock_is_fully_content_addressed():
    result = resolve_catalog(ROOT / "catalog/components.yaml", ROOT / "catalog/upstreams.lock.json", repository_root=ROOT)
    assert result["summary"]["total"] == 14
    assert result["summary"]["resolved"] == 14
    assert result["summary"]["unresolved"] == 0
    assert result["summary"]["release_eligible"] is True
    spec = next(item for item in result["entries"] if item["name"] == "spec-kit-xl")
    assert spec["issues"] == []
    assert spec["resolution"] == {"status": "resolved", "kind": "repo-local-content"}
    assert spec["content"]["scope"] == "skill-tree"
    assert spec["observed_content_sha256"] == spec["content"]["value"]


def test_resolver_accepts_fully_resolved_fixture(tmp_path: Path):
    catalog = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit_policy": "release-manifest"},
        "skills": [{
            "name": "fixture-skill", "status": "stable", "implicit": True,
        }],
    }
    lock = {
        "schema_version": "4.2",
        "repository": {"name": "fixture"},
        "entries": [{
            "name": "fixture-skill",
            "catalog_ref": "fixture-skill",
            "source": {"kind": "git", "url": "https://example.invalid/x"},
            "resolution": {"status": "resolved", "kind": "commit", "commit": "a" * 40},
            "content": {"status": "resolved", "algorithm": "sha256", "value": "b" * 64},
            "compatibility": {"status": "resolved", "codex": ">=4.2"},
            "license": {"status": "resolved", "spdx": "MIT"},
        }],
    }
    catalog_path = tmp_path / "components.yaml"
    # The repository's standard-library fallback supports this small mapping.
    catalog_path.write_text("schema_version: '4.2'\nrepository:\n  name: fixture\nskills:\n  - name: fixture-skill\n    status: stable\n    implicit: true\n", encoding="utf-8")
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    result = resolve_catalog(catalog_path, lock_path)
    assert result["summary"]["release_eligible"] is True
    assert result["entries"][0]["stable_eligible"] is True


def test_floating_lock_reference_is_never_eligible(tmp_path: Path):
    catalog_path = tmp_path / "components.yaml"
    catalog_path.write_text("schema_version: '4.2'\nrepository:\n  name: fixture\nskills:\n  - name: fixture-skill\n    status: stable\n    implicit: true\n", encoding="utf-8")
    lock = {
        "schema_version": "4.2", "entries": [{
            "name": "fixture-skill", "resolution": {"status": "resolved", "commit": "main"},
            "content": {"status": "resolved", "algorithm": "sha256", "value": "b" * 64},
            "compatibility": {"status": "resolved"}, "license": {"status": "resolved"},
            "source": {"ref": "main"},
        }]
    }
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    result = resolve_catalog(catalog_path, lock_path)
    assert result["summary"]["release_eligible"] is False
    assert "external resolution is not pinned to an immutable commit or digest" in result["entries"][0]["issues"]
    assert "lock contains a floating reference" in result["entries"][0]["issues"]


def test_external_digest_is_accepted_as_immutable_pin(tmp_path: Path):
    catalog_path = tmp_path / "components.yaml"
    catalog_path.write_text(
        "schema_version: '4.2'\nrepository:\n  name: fixture\n  commit_policy: release-manifest\n"
        "skills:\n  - name: fixture-skill\n    status: stable\n    implicit: false\n",
        encoding="utf-8",
    )
    lock = {
        "schema_version": "4.2",
        "entries": [{
            "name": "fixture-skill",
            "source": {"kind": "container", "repository": "registry.example.invalid/tool"},
            "resolution": {"status": "resolved", "kind": "digest", "digest": f"sha256:{'a' * 64}"},
            "content": {"status": "resolved", "algorithm": "sha256", "value": "b" * 64},
            "compatibility": {"status": "resolved"},
            "license": {"status": "resolved", "spdx": "MIT"},
        }],
    }
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    result = resolve_catalog(catalog_path, lock_path)
    assert result["summary"]["release_eligible"] is True
    assert result["entries"][0]["issues"] == []


def test_repo_local_hash_drift_blocks_release(tmp_path: Path):
    skill = tmp_path / "skills/fixture-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("locked skill", encoding="utf-8")
    reference = skill / "references/playbook.md"
    reference.write_text("locked reference", encoding="utf-8")
    catalog_path = tmp_path / "components.yaml"
    catalog_path.write_text(
        "schema_version: '4.2'\nrepository:\n  name: fixture\n  commit_policy: release-manifest\n"
        "skills:\n  - name: fixture-skill\n    status: stable\n    implicit: false\n",
        encoding="utf-8",
    )
    lock = {
        "schema_version": "4.2",
        "entries": [{
            "name": "fixture-skill",
            "source": {"kind": "repo-local", "path": "skills/fixture-skill"},
            "resolution": {"status": "resolved", "kind": "repo-local-content"},
            "content": {
                "status": "resolved",
                "algorithm": "sha256",
                "scope": "skill-tree",
                "value": skill_tree_sha256(skill),
            },
            "compatibility": {"status": "resolved"},
            "license": {"status": "resolved"},
        }],
    }
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    reference.write_text("changed after lock", encoding="utf-8")
    result = resolve_catalog(catalog_path, lock_path, repository_root=tmp_path)
    assert result["summary"]["release_eligible"] is False
    assert result["entries"][0]["resolution_status"] == "unresolved"
    assert "local content hash does not match lock" in result["entries"][0]["issues"]
