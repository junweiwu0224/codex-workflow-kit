import datetime as dt
import json
from pathlib import Path

from scripts.policy_router import authorize_action, main, route_task


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def _approval(*scope, contract_id="contract-1", at=None, expires_at=None):
    now = dt.datetime.now(dt.timezone.utc)
    at = at or now - dt.timedelta(minutes=1)
    expires_at = expires_at or now + dt.timedelta(minutes=5)
    return {
        "source": "user-confirmation",
        "contract_id": contract_id,
        "approvals": [
            {
                "actor": "user",
                "decision": "granted",
                "scope": list(scope),
                "at": _iso(at),
                "expires_at": _iso(expires_at),
            }
        ],
    }


def _verify_approval(record, action, target):
    return record.get("source") == "user-confirmation"


def _verify_enforcement(contract, action, kind):
    return True


def _contract(**overrides):
    value = {
        "contract_id": "contract-1",
        "lane": "fast",
        "state": "scoped",
        "transition": "scoped_to_planned",
        "transition_driver": "native",
        "write_scope": "none",
        "external_effects": [],
        "approvals": [],
        "required_artifacts": [],
        "acceptance_checks": ["pytest"],
        "verification_mode": "deterministic",
        "handoff": "none",
        "audit_record": False,
        "reversibility": "reversible",
        "read_roots": ["/workspace"],
        "write_roots": ["/workspace"],
        "policy_enforcement": [
            {"field": "external_write", "status": "enforced"},
            {"field": "credential_use", "status": "enforced"},
            {"field": "production_access", "status": "enforced"},
            {"field": "network_write", "status": "enforced"},
            {"field": "package_install", "status": "enforced"},
            {"field": "destructive", "status": "enforced"},
        ],
    }
    value.update(overrides)
    return value


def test_clear_reversible_task_uses_fast_lane():
    decision = route_task(
        _contract(
            requirement_clear=True,
            strong_verifier=True,
        )
    )
    assert decision.allowed is True
    assert decision.lane == "fast"
    assert decision.persist_contract is False
    assert decision.require_approval is False


def test_external_write_upgrades_to_governed_even_when_fast_requested():
    decision = route_task(
        _contract(
            write_scope="external",
            external_effects=["publish"],
            external_targets=["example.invalid"],
            requirement_clear=True,
            strong_verifier=True,
        )
    )
    assert decision.lane == "governed"
    assert "external_write_or_effect" in decision.reasons
    assert decision.persist_contract is True
    assert decision.require_approval is True


def test_malformed_policy_fails_closed():
    decision = route_task(_contract(network_policy="not-a-policy"))
    assert decision.allowed is False
    assert decision.lane == "governed"
    assert decision.enforcement == "unavailable"


def test_workspace_write_requires_declared_root():
    contract = _contract(lane="standard", write_scope="workspace")
    assert authorize_action(contract, {"kind": "workspace_write", "path": "/workspace/src/a.py"}).allowed
    denied = authorize_action(contract, {"kind": "workspace_write", "path": "/tmp/a.py"})
    assert denied.allowed is False
    assert denied.reason == "write_path_not_declared"


def test_workspace_root_does_not_allow_symlink_escape(tmp_path: Path):
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    contract = _contract(
        lane="standard",
        write_scope="workspace",
        write_roots=[str(root)],
    )
    decision = authorize_action(
        contract,
        {"kind": "workspace_write", "path": str(root / "link" / "a.py")},
    )
    assert decision.allowed is False
    assert decision.reason == "write_path_not_declared"


def test_external_write_requires_scoped_approval():
    contract = _contract(
        lane="governed",
        write_scope="external",
        external_effects=["publish"],
        external_targets=["deploy.example"],
        credential_refs=[],
        package_install=False,
        production_access=False,
        reversibility="reversible",
        approvals=[{"actor": "user", "decision": "granted", "scope": ["external_write", "deploy.example"]}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        network_allowlist=["deploy.example"],
    )
    # A granted value inside the Contract is intent, not runtime authority.
    assert not authorize_action(contract, {"kind": "external_write", "target": "deploy.example"}).allowed
    allowed = authorize_action(
        contract,
        {"kind": "external_write", "target": "deploy.example"},
        approval_evidence=_approval("external_write", "deploy.example"),
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    )
    assert allowed.allowed is True
    denied = authorize_action(
        {**contract, "approvals": [{"actor": "user", "decision": "granted", "scope": ["other"]}]},
        {"kind": "external_write", "target": "deploy.example"},
    )
    assert denied.allowed is False
    assert denied.require_approval is True


def test_credentials_production_and_unknown_actions_are_denied_without_approval():
    contract = _contract(
        lane="governed",
        credential_refs=["deploy-token"],
        production_access=True,
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        network_allowlist=["deploy.example"],
        external_effects=[],
        external_targets=[],
        package_install=False,
        reversibility="reversible",
    )
    assert not authorize_action(contract, {"kind": "credential_use", "credential_ref": "deploy-token"}).allowed
    assert not authorize_action(contract, {"kind": "production_access", "target": "prod"}).allowed
    assert not authorize_action(contract, {"kind": "run-arbitrary-tool"}).allowed


def test_contract_grant_and_unavailable_enforcement_cannot_authorize_dangerous_action():
    contract = _contract(
        lane="governed",
        write_scope="external",
        external_effects=["publish"],
        external_targets=["deploy.example"],
        credential_refs=[],
        package_install=False,
        production_access=False,
        approvals=[{"actor": "user", "decision": "granted", "scope": ["external_write"]}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        policy_enforcement=[{"field": "external_write", "status": "unavailable"}],
    )
    route = route_task(contract)
    assert route.allowed is False
    assert route.lane == "governed"
    decision = authorize_action(
        contract,
        {"kind": "external_write", "target": "deploy.example"},
        approval_evidence=_approval("external_write", "deploy.example"),
    )
    assert decision.allowed is False
    assert decision.enforcement == "unavailable"
    assert decision.reason == "critical_policy_enforcement_not_available"


def test_untrusted_or_undated_approval_evidence_is_rejected():
    contract = _contract(
        lane="governed",
        credential_refs=["deploy-token"],
        external_targets=[],
        package_install=False,
        production_access=False,
        approvals=[{"actor": "user", "decision": "granted", "scope": ["credential_use"]}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="none",
    )
    untrusted = {"approvals": [{"actor": "user", "decision": "granted", "scope": ["credential_use", "deploy-token"]}]}
    assert not authorize_action(
        contract,
        {"kind": "credential_use", "credential_ref": "deploy-token"},
        approval_evidence=untrusted,
    ).allowed
    raw_material_check = authorize_action(
        contract,
        {
            "kind": "credential_use",
            "credential_ref": "deploy-token",
            "".join(("to", "ken")): "".join(("raw", "-credential-material")),
        },
        approval_evidence=_approval("credential_use", "deploy-token"),
    )
    assert raw_material_check.allowed is False
    assert raw_material_check.reason == "raw_secret_material_is_forbidden"


def test_approval_must_be_fresh_contract_bound_and_short_lived():
    contract = _contract(
        lane="governed",
        write_scope="external",
        external_effects=["publish"],
        external_targets=["deploy.example"],
        credential_refs=[],
        package_install=False,
        production_access=False,
        approvals=[{"actor": "user", "decision": "granted", "scope": ["external_write"]}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        network_allowlist=["deploy.example"],
    )
    action = {"kind": "external_write", "target": "deploy.example"}
    kwargs = {
        "approval_verifier": _verify_approval,
        "enforcement_verifier": _verify_enforcement,
    }
    assert authorize_action(
        contract,
        action,
        approval_evidence=_approval("external_write", "deploy.example"),
        **kwargs,
    ).allowed

    missing_expiry = _approval("external_write", "deploy.example")
    del missing_expiry["approvals"][0]["expires_at"]
    now = dt.datetime.now(dt.timezone.utc)
    invalid_evidence = [
        missing_expiry,
        _approval("external_write", "deploy.example", contract_id="another-contract"),
        _approval(
            "external_write",
            "deploy.example",
            at=dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc),
            expires_at=dt.datetime(2000, 1, 1, 0, 5, tzinfo=dt.timezone.utc),
        ),
        _approval(
            "external_write",
            "deploy.example",
            at=now - dt.timedelta(minutes=1),
            expires_at=now + dt.timedelta(minutes=15),
        ),
    ]
    for evidence in invalid_evidence:
        decision = authorize_action(contract, action, approval_evidence=evidence, **kwargs)
        assert decision.allowed is False
        assert decision.reason == "explicit_scoped_approval_required"


def test_project_install_is_allowed_only_when_explicitly_declared():
    contract = _contract(lane="standard", write_scope="workspace", package_install="project-only")
    assert authorize_action(
        contract,
        {"kind": "package_install", "scope": "project-only", "path": "/workspace"},
    ).allowed
    assert not authorize_action(
        contract,
        {"kind": "package_install", "scope": "user", "path": "/workspace"},
    ).allowed


def test_production_access_requires_declared_target_network_and_scoped_evidence():
    contract = _contract(
        lane="governed",
        production_access=True,
        credential_refs=[],
        external_targets=["prod.example"],
        package_install=False,
        approvals=[{"actor": "user", "decision": "granted", "scope": ["production_access"]}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        network_allowlist=["prod.example"],
    )
    action = {"kind": "production_access", "target": "prod.example"}
    assert not authorize_action(contract, action).allowed
    assert authorize_action(
        contract,
        action,
        approval_evidence=_approval("production_access", "prod.example"),
        approval_verifier=_verify_approval,
        enforcement_verifier=_verify_enforcement,
    ).allowed
    assert not authorize_action(
        contract,
        {"kind": "production_access", "target": "other.example"},
        approval_evidence=_approval("production_access", "other.example"),
    ).allowed


def test_network_allowlist_and_unrestricted_network_rules():
    contract = _contract(lane="standard", network_policy="allowlist", network_allowlist=["docs.example"])
    assert authorize_action(contract, {"kind": "network_read", "target": "https://docs.example/a"}).allowed
    assert not authorize_action(contract, {"kind": "network_read", "target": "https://evil.example/a"}).allowed
    unrestricted = _contract(lane="standard", network_policy="unrestricted")
    denied = authorize_action(unrestricted, {"kind": "network_read", "target": "https://docs.example"})
    assert denied.allowed is False
    assert denied.require_approval is True


def test_policy_router_cli(tmp_path: Path, capsys):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(_contract(requirement_clear=True, strong_verifier=True)), encoding="utf-8")
    assert main([str(path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["lane"] == "fast"


def test_policy_router_cli_cannot_trust_caller_authored_approval(tmp_path: Path, capsys):
    contract = _contract(
        lane="governed",
        write_scope="external",
        external_effects=["publish"],
        approvals=[{"actor": "owner", "decision": "pending"}],
        audit_record=True,
        verification_mode="mixed",
        network_policy="allowlist",
        network_allowlist=["deploy.example"],
        credential_refs=[],
        external_targets=["deploy.example"],
        package_install=False,
        production_access=False,
    )
    contract_path = tmp_path / "contract.json"
    action_path = tmp_path / "action.json"
    approval_path = tmp_path / "approval.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    action_path.write_text(json.dumps({"kind": "external_write", "target": "deploy.example"}), encoding="utf-8")
    approval_path.write_text(json.dumps(_approval("external_write", "deploy.example")), encoding="utf-8")

    assert main([
        str(contract_path),
        "--action",
        str(action_path),
        "--approval-evidence",
        str(approval_path),
        "--json",
    ]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["allowed"] is False
    assert output["reason"] == "trusted_enforcement_verifier_required"
