import datetime as dt
import json
from pathlib import Path

from scripts.event_log import validate_log
from scripts.runtime_policy import (
    authorize_runtime_action,
    authorize_runtime_transition,
    main,
    route_runtime,
)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _approval(*scope, contract_id="contract-1"):
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "source": "user-confirmation",
        "contract_id": contract_id,
        "approvals": [
            {
                "actor": "user",
                "decision": "granted",
                "scope": list(scope),
                "at": _iso(now - dt.timedelta(minutes=1)),
                "expires_at": _iso(now + dt.timedelta(minutes=5)),
            }
        ],
    }


def _verify_approval(record, action, target):
    return record.get("source") == "user-confirmation"


def _verify_enforcement(contract, operation, kind):
    return True


def _governed(**overrides):
    value = {
        "contract_id": "contract-1",
        "lane": "governed",
        "state": "verified",
        "transition": "verified_to_released",
        "transition_driver": "release-readiness",
        "write_scope": "external",
        "external_effects": ["publish"],
        "approvals": [{"actor": "user", "decision": "granted", "scope": ["release", "external_write"]}],
        "required_artifacts": [],
        "acceptance_checks": ["release smoke"],
        "verification_mode": "mixed",
        "handoff": "release",
        "audit_record": True,
        "reversibility": "reversible",
        "network_policy": "allowlist",
        "network_allowlist": ["releases.example"],
        "credential_refs": [],
        "external_targets": ["releases.example"],
        "package_install": False,
        "production_access": False,
        "policy_enforcement": [
            {"field": "external_write", "status": "enforced"},
            {"field": "credential_use", "status": "enforced"},
            {"field": "network", "status": "enforced"},
        ],
    }
    value.update(overrides)
    return value


def test_governed_allow_fails_closed_without_event_log():
    result = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert result["allowed"] is False
    assert result["reason"] == "governed_event_log_required"
    assert result["enforcement"] == "unavailable"


def test_governed_action_is_allowed_only_after_durable_audit(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    result = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        event_log=path,
        event_anchor=anchor,
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert result["allowed"] is True
    assert result["audit_event_id"]
    assert validate_log(path, anchor_path=anchor)["ok"] is True


def test_governed_allow_fails_closed_without_external_anchor(tmp_path: Path):
    result = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        event_log=tmp_path / "events.jsonl",
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert result["allowed"] is False
    assert result["reason"] == "governed_event_anchor_required"
    assert result["enforcement"] == "unavailable"


def test_governed_transition_requires_external_approval_and_audit(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    denied = authorize_runtime_transition(_governed(), "released", event_log=path, event_anchor=anchor)
    assert denied["allowed"] is False
    allowed = authorize_runtime_transition(
        _governed(),
        "released",
        approval_evidence=_approval("release"),
        event_log=path,
        event_anchor=anchor,
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert allowed["allowed"] is True
    assert validate_log(path, anchor_path=anchor)["events"] == 2


def test_governed_transition_rejects_approval_bound_to_another_contract(tmp_path: Path):
    result = authorize_runtime_transition(
        _governed(),
        "released",
        approval_evidence=_approval("release", contract_id="another-contract"),
        event_log=tmp_path / "events.jsonl",
        event_anchor=tmp_path / "events.anchor.json",
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert result["allowed"] is False
    assert result["reason"] == "explicit_scoped_approval_required"


def test_governed_runtime_append_rejects_tail_truncation(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    allowed = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        event_log=path,
        event_anchor=anchor,
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert allowed["allowed"] is True
    path.write_text("", encoding="utf-8")
    rejected = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        event_log=path,
        event_anchor=anchor,
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert rejected["allowed"] is False
    assert rejected["reason"] == "governed_event_log_unavailable"
    assert "anchor" in rejected["audit_error"]


def test_denial_reason_is_preserved_when_anchor_is_unavailable(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    anchor.write_text(json.dumps({"version": 1, "events": 0, "last_hash": ""}), encoding="utf-8")
    denied = authorize_runtime_transition(
        _governed(),
        "released",
        event_log=path,
        event_anchor=anchor,
    )
    assert denied["allowed"] is False
    assert denied["reason"] == "explicit_scoped_approval_required"
    assert "audit_error" in denied


def test_governed_route_requires_contract_id_and_log(tmp_path: Path):
    result = route_runtime(
        {**_governed(), "contract_id": ""},
        event_log=tmp_path / "events.jsonl",
        enforcement_verifier=_verify_enforcement,
    )
    assert result["allowed"] is False
    assert result["reason"] == "governed_contract_id_required"


def test_standard_runtime_does_not_create_persistent_log(tmp_path: Path):
    contract = {
        "lane": "standard",
        "state": "planned",
        "transition": "planned_to_implemented",
        "transition_driver": "superpowers",
        "write_scope": "workspace",
        "write_roots": ["/workspace"],
        "external_effects": [],
        "approvals": [],
        "required_artifacts": [],
        "acceptance_checks": ["pytest"],
        "verification_mode": "mixed",
        "handoff": "verify",
        "audit_record": False,
        "reversibility": "reversible",
    }
    path = tmp_path / "events.jsonl"
    result = authorize_runtime_action(contract, {"kind": "workspace_write", "path": "/workspace/a.py"}, event_log=path)
    assert result["allowed"] is True
    assert not path.exists()


def test_governed_noncritical_action_requires_trusted_runtime_enforcement(tmp_path: Path):
    contract = _governed(
        write_scope="workspace",
        write_roots=["/workspace"],
        external_effects=[],
        external_targets=[],
        network_policy="none",
        network_allowlist=[],
    )
    action = {"kind": "workspace_write", "path": "/workspace/a.py"}
    denied = authorize_runtime_action(contract, action)
    assert denied["allowed"] is False
    assert denied["reason"] == "trusted_enforcement_verifier_required"

    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    allowed = authorize_runtime_action(
        contract,
        action,
        event_log=path,
        event_anchor=anchor,
        enforcement_verifier=_verify_enforcement,
    )
    assert allowed["allowed"] is True
    assert allowed["enforcement"] == "verified"
    assert validate_log(path, anchor_path=anchor)["events"] == 1


def test_runtime_policy_cli(tmp_path: Path, capsys):
    contract_path = tmp_path / "contract.json"
    action_path = tmp_path / "action.json"
    approval_path = tmp_path / "approval.json"
    event_path = tmp_path / "events.jsonl"
    contract_path.write_text(json.dumps(_governed()), encoding="utf-8")
    action_path.write_text(json.dumps({"kind": "external_write", "target": "releases.example"}), encoding="utf-8")
    approval_path.write_text(json.dumps(_approval("external_write", "releases.example")), encoding="utf-8")
    assert main(
        [
            "action",
            str(contract_path),
            "--action",
            str(action_path),
            "--approval-evidence",
            str(approval_path),
            "--event-log",
            str(event_path),
            "--json",
        ]
    ) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["allowed"] is False
    assert output["reason"] == "trusted_enforcement_verifier_required"


def test_standalone_approval_json_cannot_authorize_governed_action(tmp_path: Path):
    result = authorize_runtime_action(
        _governed(),
        {"kind": "external_write", "target": "releases.example"},
        approval_evidence=_approval("external_write", "releases.example"),
        event_log=tmp_path / "events.jsonl",
    )
    assert result["allowed"] is False
    assert result["reason"] == "trusted_enforcement_verifier_required"
