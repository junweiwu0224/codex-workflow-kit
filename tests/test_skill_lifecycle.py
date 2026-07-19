import json
from pathlib import Path

import pytest

from eval.lifecycle import LifecycleError, LifecycleManager, LifecycleState


def _promote_to_stable(manager: LifecycleManager, component: str = "fixture"):
    manager.register(component, version="sha-v1", last_known_good="sha-v1")
    manager.transition(component, LifecycleState.AUDITED, evidence={"audit_pass": True})
    manager.transition(
        component,
        LifecycleState.SHADOW,
        evidence={"shadow_pass": True, "tool_calls": 0, "writes": 0, "external_effects": 0},
    )
    manager.transition(
        component,
        LifecycleState.REPO_PILOT,
        evidence={"exact_commit": True, "explicit_only": True, "paired_pass": True},
    )
    manager.transition(
        component,
        LifecycleState.STABLE,
        evidence={"trigger_pass": True, "behavior_pass": True, "safety_pass": True, "safety_violations": 0, "rollback_tested": True},
    )


def test_lifecycle_requires_evidence_for_each_promotion():
    manager = LifecycleManager()
    manager.register("candidate", version="v1", last_known_good="v1")
    with pytest.raises(LifecycleError, match="audit_pass"):
        manager.transition("candidate", LifecycleState.AUDITED)
    manager.transition("candidate", LifecycleState.AUDITED, evidence={"audit_pass": True})
    with pytest.raises(LifecycleError, match="Shadow evidence"):
        manager.transition("candidate", LifecycleState.SHADOW, evidence={"shadow_pass": True, "tool_calls": 1})


def test_canary_scope_and_kill_switch_are_fail_closed():
    manager = LifecycleManager()
    _promote_to_stable(manager)
    manager.configure_canary("fixture", projects=["repo-a"], task_families=["ui"])
    assert manager.canary_allowed("fixture", project="repo-a", task_family="ui")
    assert not manager.canary_allowed("fixture", project="repo-b", task_family="ui")
    manager.activate_kill_switch("fixture", reason="safety regression")
    assert manager.get("fixture").state == LifecycleState.SUSPENDED
    assert not manager.canary_allowed("fixture", project="repo-a", task_family="ui")


def test_rollback_restores_last_known_good_and_persists(tmp_path: Path):
    path = tmp_path / "lifecycle.json"
    manager = LifecycleManager(path)
    _promote_to_stable(manager)
    manager.get("fixture").version = "sha-bad"
    manager.activate_kill_switch("fixture", reason="bad candidate")
    record = manager.rollback("fixture", reason="restore known good")
    assert record.state == LifecycleState.ROLLED_BACK
    assert record.version == "sha-v1"
    loaded = LifecycleManager(path)
    assert loaded.get("fixture").version == "sha-v1"
    assert loaded.get("fixture").state == LifecycleState.ROLLED_BACK
    assert any(event.action == "rollback" for event in loaded.get("fixture").history)


def test_retirement_requires_removal_evidence():
    manager = LifecycleManager()
    _promote_to_stable(manager)
    manager.transition("fixture", LifecycleState.DEPRECATED, evidence={"replacement": "native"})
    with pytest.raises(LifecycleError, match="removed_from_runtime"):
        manager.transition("fixture", LifecycleState.RETIRED)
    manager.transition("fixture", LifecycleState.RETIRED, evidence={"removed_from_runtime": True})
    assert manager.get("fixture").state == LifecycleState.RETIRED


def test_durable_state_is_json_object(tmp_path: Path):
    path = tmp_path / "state.json"
    manager = LifecycleManager(path)
    manager.register("fixture")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == "4.2"
    assert parsed["components"]["fixture"]["state"] == "discovered"
