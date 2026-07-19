import builtins
import json
from pathlib import Path

from scripts.validate_governance import (
    GovernanceValidationError,
    load_catalog,
    main,
    validate_catalog_data,
    validate_eval_trust_policy,
    validate_governance,
    validate_lock_data,
)
from scripts.refresh_local_lock import skill_tree_sha256


ROOT = Path(__file__).resolve().parents[1]
def test_missing_pyyaml_uses_standard_library_fallback(monkeypatch, tmp_path):
    catalog = tmp_path / "components.yaml"
    catalog.write_text("schema_version: '4.2'\n", encoding="utf-8")
    original_import = builtins.__import__

    def block_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ModuleNotFoundError("No module named 'yaml'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_yaml)
    assert load_catalog(catalog) == {"schema_version": "4.2"}


def test_current_catalog_and_lock_validate():
    result = validate_governance(ROOT)
    catalog = load_catalog(ROOT / "catalog/components.yaml")
    assert result["ok"] is True
    assert result["skills"] == 14
    assert result["implicit"] == 7
    assert result["profiles"] == {"pilot": 4, "stable": 10}
    assert {item["owner"] for item in catalog["skills"]} == {"junweiwu0224"}


def test_eval_trust_policy_rejects_duplicate_or_unpinned_keys(tmp_path):
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    (catalog / "eval-trust-policy.json").write_text(
        json.dumps({
            "schema_version": "4.2",
            "policy_id": "test",
            "keys": [
                {"key_id": "owner", "algorithm": "hmac-sha256", "key_sha256": "x", "status": "active"},
                {"key_id": "owner", "algorithm": "hmac-sha256", "key_sha256": "a" * 64, "status": "active"},
            ],
        }),
        encoding="utf-8",
    )

    issues = validate_eval_trust_policy(tmp_path)
    assert any("invalid key_sha256" in issue for issue in issues)
    assert any("duplicate key_id" in issue for issue in issues)


def test_catalog_and_skill_directory_mismatch_is_reported(tmp_path):
    catalog = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit_policy": "release-manifest"},
        "skills": [],
    }
    root = tmp_path / "kit"
    (root / "skills/example").mkdir(parents=True)
    (root / "skills/example/SKILL.md").write_text("---\nname: example\n---\n", encoding="utf-8")
    issues = validate_catalog_data(root, catalog)
    assert any("missing from catalog: example" in issue for issue in issues)


def test_pilot_cannot_be_implicit_and_budget_is_bounded(tmp_path):
    catalog = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit_policy": "release-manifest"},
        "skills": [
            {
                "name": f"skill-{index}",
                "role": "overlay",
                "stage": "implementation",
                "status": "pilot" if index == 0 else "stable",
                "implicit": True,
                "network": "none",
                "write_scope": "none",
                "license": "unresolved",
                "eval_suite": "fixture",
            }
            for index in range(9)
        ],
    }
    root = tmp_path / "kit"
    for index in range(9):
        path = root / f"skills/skill-{index}/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nname: fixture\n---\n", encoding="utf-8")
    issues = validate_catalog_data(root, catalog)
    assert any("pilot/lab skills cannot be implicit" in issue for issue in issues)
    assert any("maximum is 8" in issue for issue in issues)


def test_main_returns_nonzero_for_invalid_governance(tmp_path, capsys):
    root = tmp_path / "kit"
    (root / "catalog").mkdir(parents=True)
    (root / "skills").mkdir()
    (root / "catalog/components.yaml").write_text("schema_version: '3.0'\n", encoding="utf-8")
    (root / "catalog/upstreams.lock.json").write_text(json.dumps({}), encoding="utf-8")
    assert main(["--root", str(root)]) == 1
    assert "Governance validation failed" in capsys.readouterr().out


def test_catalog_rejects_self_referential_repository_commit(tmp_path):
    catalog = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit": "a" * 40},
        "skills": [],
    }
    issues = validate_catalog_data(tmp_path, catalog)
    assert "catalog.repository.commit_policy must be release-manifest" in issues
    assert "catalog.repository must not embed a self-referential commit" in issues


def test_external_lock_resolution_requires_immutable_pin(tmp_path):
    lock = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit_policy": "release-manifest"},
        "license_policy": "catalog/license-policy.yaml",
        "entries": [{
            "name": "external-skill",
            "catalog_ref": "external-skill",
            "source": {"kind": "git", "repository": "https://example.invalid/external.git"},
            "resolution": {"status": "resolved", "kind": "commit", "commit": "main"},
            "content": {"status": "resolved", "algorithm": "sha256", "value": "b" * 64},
            "compatibility": {
                "status": "resolved",
                "codex": "agentskills-standard-v1",
                "evidence": "scripts/validate_governance.py",
            },
            "license": {"status": "resolved", "spdx": "MIT"},
        }],
    }
    policy = tmp_path / "catalog/license-policy.yaml"
    policy.parent.mkdir(parents=True)
    policy.write_text("fail_closed: true\n", encoding="utf-8")
    issues = validate_lock_data(tmp_path, lock, {"external-skill"})
    assert "external-skill: external commit must be a full 40-character lowercase SHA" in issues


def test_repo_local_lock_hash_covers_agents_and_requires_tree_scope(tmp_path):
    skill = tmp_path / "skills/example"
    (skill / "agents").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: example\ndescription: example\n---\n", encoding="utf-8")
    policy = skill / "agents/openai.yaml"
    policy.write_text("allow_implicit_invocation: false\n", encoding="utf-8")
    license_policy = tmp_path / "catalog/license-policy.yaml"
    license_policy.parent.mkdir(parents=True)
    license_policy.write_text("fail_closed: true\n", encoding="utf-8")
    lock = {
        "schema_version": "4.2",
        "repository": {"name": "fixture", "commit_policy": "release-manifest"},
        "license_policy": "catalog/license-policy.yaml",
        "entries": [{
            "name": "example",
            "catalog_ref": "example",
            "source": {"kind": "repo-local", "repository": "fixture", "path": "skills/example"},
            "resolution": {"status": "resolved", "kind": "repo-local-content"},
            "content": {
                "status": "resolved",
                "algorithm": "sha256",
                "scope": "skill-tree",
                "value": skill_tree_sha256(skill),
            },
            "compatibility": {
                "status": "resolved",
                "codex": "agentskills-standard-v1",
                "evidence": "scripts/validate_governance.py",
            },
            "license": {
                "status": "resolved",
                "spdx": "LicenseRef-Proprietary",
                "policy_ref": "catalog/license-policy.yaml",
            },
        }],
    }

    assert validate_lock_data(tmp_path, lock, {"example"}) == []
    policy.write_text("allow_implicit_invocation: true\n", encoding="utf-8")
    issues = validate_lock_data(tmp_path, lock, {"example"})

    assert any(issue.startswith("example.content.value does not match") for issue in issues)
