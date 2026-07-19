#!/usr/bin/env python3
"""State-transition router for the V4.2 runtime.

There is exactly one authoritative Driver for a state transition.  Domain
Skills may advise or veto, but they cannot silently claim ownership.  This
module only computes a transition decision and can return a next-state
snapshot; it never writes a contract or invokes a Driver.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from scripts.policy_router import ApprovalVerifier, has_granted_approval, route_task
    from scripts.validate_task_contract import DRIVERS, STATES, TRANSITION_RE, validate_contract
except ImportError:  # pragma: no cover - direct script execution
    from policy_router import ApprovalVerifier, has_granted_approval, route_task
    from validate_task_contract import DRIVERS, STATES, TRANSITION_RE, validate_contract


# This is intentionally a single mapping, rather than a set of independent
# skill declarations.  It makes competing Drivers visible and testable.
TRANSITION_OWNERS: dict[tuple[str, str], frozenset[str]] = {
    ("discovered", "scoped"): frozenset({"policy-router", "native"}),
    ("scoped", "approved_spec"): frozenset({"openspec", "spec-kit-xl"}),
    ("scoped", "planned"): frozenset({"native", "superpowers"}),
    ("approved_spec", "planned"): frozenset({"superpowers"}),
    ("planned", "implemented"): frozenset({"native", "superpowers"}),
    ("implemented", "verified"): frozenset({"deterministic-runner", "verifier"}),
    ("implemented", "rework_required"): frozenset({"verifier"}),
    ("rework_required", "implemented"): frozenset({"native", "superpowers"}),
    ("verified", "released"): frozenset({"release-readiness"}),
    ("verified", "closed"): frozenset({"native", "verifier"}),
}
TERMINAL_TRANSITION_DRIVERS = frozenset(DRIVERS)
APPROVAL_TRANSITIONS = {
    ("scoped", "approved_spec"): "approved_spec",
    ("verified", "released"): "release",
}


def transition_owners(source: str, target: str) -> frozenset[str]:
    """Return the authoritative Driver set for a core transition."""
    if target in {"blocked", "cancelled"}:
        return TERMINAL_TRANSITION_DRIVERS
    return TRANSITION_OWNERS.get((source, target), frozenset())


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    from_state: str
    to_state: str
    transition: str
    driver: str | None
    lane: str
    reason: str
    enforcement: str
    handoff: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "transition": self.transition,
            "driver": self.driver,
            "lane": self.lane,
            "reason": self.reason,
            "enforcement": self.enforcement,
            "handoff": self.handoff,
        }


def _decision(
    allowed: bool,
    source: str,
    target: str,
    driver: str | None,
    lane: str,
    reason: str,
    *,
    enforcement: str = "advisory",
    handoff: str = "none",
) -> TransitionDecision:
    return TransitionDecision(
        allowed,
        source,
        target,
        f"{source}_to_{target}",
        driver,
        lane,
        reason,
        enforcement,
        handoff,
    )


def _driver_is_single(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def route_transition(
    contract: Mapping[str, Any],
    target_state: str,
    *,
    driver: str | None = None,
    approval_evidence: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    approval_verifier: ApprovalVerifier | None = None,
) -> TransitionDecision:
    """Return a fail-closed decision for ``contract.state -> target_state``."""
    if not isinstance(contract, Mapping):
        return _decision(False, "unknown", target_state, None, "governed", "contract_is_not_an_object", enforcement="unavailable")

    source = contract.get("state")
    if source not in STATES:
        return _decision(False, str(source), target_state, None, "governed", "source_state_is_unavailable", enforcement="unavailable")
    if target_state not in STATES:
        return _decision(False, str(source), str(target_state), None, "governed", "target_state_is_unavailable", enforcement="unavailable")
    if source == target_state:
        return _decision(False, str(source), target_state, None, str(contract.get("lane", "governed")), "self_transition_not_allowed")

    transition = f"{source}_to_{target_state}"
    declared_transition = contract.get("transition")
    if declared_transition != transition:
        return _decision(False, source, target_state, None, str(contract.get("lane", "governed")), "contract_transition_does_not_match_request")
    if not TRANSITION_RE.match(transition):  # Defensive, in case constants change.
        return _decision(False, source, target_state, None, "governed", "transition_format_is_unavailable", enforcement="unavailable")

    # Check this before the generic Contract validator so malformed lists are
    # reported as the ownership conflict they represent, rather than leaking a
    # type error or an opaque schema failure.
    declared_driver = contract.get("transition_driver")
    if isinstance(declared_driver, (list, tuple, set)):
        return _decision(False, source, target_state, None, "governed", "multiple_transition_drivers_declared", enforcement="unavailable")

    # validate_contract proves the declaration is coherent.  It is not used as
    # an authorization grant, and no fields are filled in on the caller's
    # behalf.
    contract_errors = validate_contract(dict(contract))
    route = route_task(contract)
    lane = route.lane
    if contract_errors or not route.allowed:
        return _decision(False, source, target_state, None, lane, "invalid_or_unavailable_task_policy", enforcement="unavailable")

    if driver is None:
        driver = declared_driver if _driver_is_single(declared_driver) else None
    elif not _driver_is_single(driver):
        driver = None
    # A list such as ["openspec", "superpowers"] is a direct signal that two
    # Drivers are trying to own one transition; reject it rather than choose.
    if not _driver_is_single(driver) or driver not in DRIVERS:
        return _decision(False, source, target_state, None, lane, "exactly_one_valid_transition_driver_required", enforcement="unavailable")

    owners = transition_owners(source, target_state)
    if not owners:
        return _decision(False, source, target_state, driver, lane, "unsupported_core_transition")
    if driver not in owners:
        return _decision(False, source, target_state, driver, lane, "driver_does_not_own_transition")
    if (source, target_state) == ("planned", "implemented") and driver == "native" and lane != "fast":
        return _decision(False, source, target_state, driver, lane, "native_implementation_driver_requires_fast_lane")
    if target_state == "approved_spec" and lane != "governed":
        return _decision(False, source, target_state, driver, lane, "approved_spec_requires_governed_lane")
    if target_state == "released" and lane != "governed":
        return _decision(False, source, target_state, driver, lane, "release_requires_governed_lane")
    if target_state == "verified":
        verification_mode = contract.get("verification_mode")
        if verification_mode == "deterministic" and driver != "deterministic-runner":
            return _decision(False, source, target_state, driver, lane, "deterministic_verification_requires_runner")
        if verification_mode == "fresh_context" and driver != "verifier":
            return _decision(False, source, target_state, driver, lane, "fresh_context_verification_requires_verifier")
        if lane == "governed" and driver != "verifier":
            return _decision(False, source, target_state, driver, lane, "governed_verification_requires_verifier")

    approval_action = APPROVAL_TRANSITIONS.get((source, target_state))
    if approval_action and not has_granted_approval(
        approval_evidence,
        approval_action,
        contract_id=contract.get("contract_id") if isinstance(contract.get("contract_id"), str) else None,
        verifier=approval_verifier,
    ):
        return _decision(False, source, target_state, driver, "governed", "explicit_scoped_approval_required", handoff="approval")

    if target_state == "verified" and contract.get("handoff") not in {"verify", "none"}:
        return _decision(False, source, target_state, driver, lane, "verified_transition_requires_verify_handoff")
    handoff = str(contract.get("handoff", "none"))
    if target_state == "implemented":
        handoff = "verify"
    elif target_state == "approved_spec":
        handoff = "superpowers"
    elif target_state == "verified":
        handoff = "release" if contract.get("handoff") == "release" else "none"

    return _decision(True, source, target_state, driver, lane, "transition_driver_authorized", handoff=handoff)


# Friendly aliases for callers integrating a Policy Router.
route = route_transition
authorize_transition = route_transition


def propose_next_state(
    contract: Mapping[str, Any],
    target_state: str,
    *,
    driver: str | None = None,
    approval_evidence: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    approval_verifier: ApprovalVerifier | None = None,
) -> dict[str, Any]:
    """Return a non-authorizing state snapshot for an allowed transition.

    The snapshot is intentionally not a new Task Contract: the next transition
    and its Driver must be declared and validated separately.
    """
    decision = route_transition(
        contract,
        target_state,
        driver=driver,
        approval_evidence=approval_evidence,
        approval_verifier=approval_verifier,
    )
    if not decision.allowed:
        raise ValueError(decision.reason)
    return {
        "contract_id": contract.get("contract_id"),
        "lane": decision.lane,
        "state": decision.to_state,
        "previous_state": decision.from_state,
        "last_transition": decision.transition,
        "last_transition_driver": decision.driver,
        "handoff": decision.handoff,
        "authorization_granted": False,
    }


# Compatibility name; the return value is a state snapshot, not a permission
# grant or a schema-complete Contract for a future transition.
propose_next_contract = propose_next_state


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authorize one V4.2 Task Contract transition.")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--to", dest="target_state", required=True)
    parser.add_argument("--driver")
    parser.add_argument("--approval-evidence", type=Path)
    parser.add_argument("--propose", action="store_true", help="Print the proposed next contract")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = _load_json(args.contract)
        if not isinstance(contract, Mapping):
            raise ValueError("contract root must be an object")
        approval_evidence = _load_json(args.approval_evidence) if args.approval_evidence else None
        decision = route_transition(
            contract,
            args.target_state,
            driver=args.driver,
            approval_evidence=approval_evidence,
        )
        result: Any = decision.to_dict()
        if args.propose and decision.allowed:
            result = {
                "decision": result,
                "state_snapshot": propose_next_state(
                    contract,
                    args.target_state,
                    driver=args.driver,
                    approval_evidence=approval_evidence,
                ),
            }
    except ValueError as exc:
        print(f"runtime router error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
    return 0 if (result.get("allowed") if isinstance(result, Mapping) and "allowed" in result else result.get("decision", {}).get("allowed", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
