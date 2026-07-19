import datetime as dt
import json
from pathlib import Path

from scripts.runtime_router import main, propose_next_contract, route_transition


def _approval(*scope):
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "source": "user-confirmation",
        "contract_id": "contract-1",
        "approvals": [
            {
                "actor": "user",
                "decision": "granted",
                "scope": list(scope),
                "at": (now - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                "expires_at": (now + dt.timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            }
        ],
    }


def _verify_approval(record, action, target):
    return record.get("source") == "user-confirmation"


def _contract(**overrides):
    value = {
        "contract_id": "contract-1",
        "lane": "standard",
        "state": "planned",
        "transition": "planned_to_implemented",
        "transition_driver": "superpowers",
        "write_scope": "workspace",
        "external_effects": [],
        "approvals": [],
        "required_artifacts": [],
        "acceptance_checks": ["pytest"],
        "verification_mode": "mixed",
        "handoff": "verify",
        "audit_record": False,
        "reversibility": "reversible",
        "write_roots": ["/workspace"],
        "policy_enforcement": [],
    }
    value.update(overrides)
    return value


def test_single_driver_owns_planned_to_implemented():
    decision = route_transition(_contract(), "implemented")
    assert decision.allowed is True
    assert decision.driver == "superpowers"
    assert decision.handoff == "verify"


def test_wrong_driver_cannot_claim_transition():
    decision = route_transition(_contract(), "implemented", driver="openspec")
    assert decision.allowed is False
    assert decision.reason == "driver_does_not_own_transition"


def test_native_implementation_driver_is_fast_only():
    decision = route_transition(
        _contract(transition_driver="native"),
        "implemented",
    )
    assert decision.allowed is False
    assert decision.reason == "native_implementation_driver_requires_fast_lane"


def test_governed_verification_requires_independent_verifier():
    contract = _contract(
        lane="governed",
        state="implemented",
        transition="implemented_to_verified",
        transition_driver="deterministic-runner",
        verification_mode="mixed",
        audit_record=True,
        network_policy="none",
        credential_refs=[],
        external_targets=[],
        package_install=False,
        production_access=False,
    )
    decision = route_transition(contract, "verified")
    assert decision.allowed is False
    assert decision.reason == "governed_verification_requires_verifier"


def test_multiple_drivers_fail_closed():
    decision = route_transition(
        _contract(transition_driver=["openspec", "superpowers"]),
        "implemented",
    )
    assert decision.allowed is False
    assert decision.enforcement == "unavailable"


def test_open_spec_transition_requires_scoped_approval():
    contract = _contract(
        lane="governed",
        state="scoped",
        transition="scoped_to_approved_spec",
        transition_driver="openspec",
        audit_record=True,
        verification_mode="fresh_context",
        handoff="superpowers",
        network_policy="none",
        credential_refs=[],
        external_targets=[],
        package_install=False,
        production_access=False,
        reversibility="reversible",
    )
    denied = route_transition(contract, "approved_spec")
    assert denied.allowed is False
    assert denied.reason == "explicit_scoped_approval_required"
    contract["approvals"] = [{"actor": "user", "decision": "granted", "scope": ["approved_spec"]}]
    # Contract approval state alone is not runtime approval evidence.
    assert not route_transition(contract, "approved_spec").allowed
    assert route_transition(
        contract,
        "approved_spec",
        approval_evidence=_approval("approved_spec"),
        approval_verifier=_verify_approval,
    ).allowed is True


def test_contract_transition_must_match_requested_target():
    decision = route_transition(_contract(transition="implemented_to_verified"), "implemented")
    assert decision.allowed is False
    assert decision.reason == "contract_transition_does_not_match_request"


def test_unsupported_skip_transition_is_denied():
    contract = _contract(transition="planned_to_released")
    decision = route_transition(contract, "released")
    assert decision.allowed is False
    assert decision.reason in {"invalid_or_unavailable_task_policy", "unsupported_core_transition"}


def test_propose_returns_a_copy_without_mutating_input():
    contract = _contract()
    proposed = propose_next_contract(contract, "implemented")
    assert contract["state"] == "planned"
    assert proposed["state"] == "implemented"
    assert proposed["previous_state"] == "planned"
    assert proposed["authorization_granted"] is False


def test_runtime_router_cli(tmp_path: Path, capsys):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(_contract()), encoding="utf-8")
    assert main([str(path), "--to", "implemented", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["allowed"] is True
