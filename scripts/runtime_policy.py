#!/usr/bin/env python3
"""Integrated V4.2 runtime policy gate.

This is the entry point tool adapters should call before a governed action or
state transition.  It combines pure routing/authorization decisions with the
append-only audit requirement.  A Governed allow decision is downgraded to a
denial when the contract has no ID, no audit log, no independently retained
anchor, or the log cannot be validated/appended.

The gate still does not execute the requested operation.  Its exit status and
JSON result are intended to be consumed by the actual tool broker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.event_log import EventLogError, append_event
    from scripts.policy_router import EnforcementVerifier, ApprovalVerifier, authorize_action, route_task
    from scripts.runtime_router import route_transition
except ImportError:  # pragma: no cover - direct script execution
    from event_log import EventLogError, append_event
    from policy_router import EnforcementVerifier, ApprovalVerifier, authorize_action, route_task
    from runtime_router import route_transition


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def _evidence_fingerprint(evidence: Any) -> str | None:
    if evidence is None:
        return None
    try:
        encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _audit_or_fail(
    contract: Mapping[str, Any],
    result: dict[str, Any],
    *,
    event_log: str | Path | None,
    event_anchor: str | Path | None,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    governed = result.get("lane") == "governed"
    if not governed:
        return result

    contract_id = contract.get("contract_id")
    # Denials remain denials even when audit infrastructure is unavailable.
    # An allow decision, however, cannot leave the gate without durable audit.
    if not isinstance(contract_id, str) or not contract_id.strip():
        if result.get("allowed"):
            return {
                **result,
                "allowed": False,
                "reason": "governed_contract_id_required",
                "enforcement": "unavailable",
            }
        return result
    if event_log is None:
        if result.get("allowed"):
            return {
                **result,
                "allowed": False,
                "reason": "governed_event_log_required",
                "enforcement": "unavailable",
            }
        return result
    if event_anchor is None:
        if result.get("allowed"):
            return {
                **result,
                "allowed": False,
                "reason": "governed_event_anchor_required",
                "enforcement": "unavailable",
            }
        return result
    try:
        event = append_event(
            event_log,
            anchor_path=event_anchor,
            contract_id=contract_id,
            event_type=event_type,
            actor=actor,
            payload=dict(payload),
        )
    except EventLogError as exc:
        if not result.get("allowed"):
            return {**result, "audit_error": str(exc)}
        return {
            **result,
            "allowed": False,
            "reason": "governed_event_log_unavailable",
            "enforcement": "unavailable",
            "audit_error": str(exc),
        }
    return {**result, "audit_event_id": event["event_id"], "audit_event_hash": event["hash"]}


def _require_runtime_enforcement(
    contract: Mapping[str, Any],
    result: dict[str, Any],
    operation: Mapping[str, Any],
    verifier: EnforcementVerifier | None,
) -> dict[str, Any]:
    """Require a trusted tool-broker capability before allowing Governed work."""
    if result.get("lane") != "governed" or not result.get("allowed"):
        return result
    # Critical actions were already checked by ``authorize_action`` using the
    # same trusted callback.  Avoid invoking a stateful broker verifier twice.
    if result.get("enforcement") == "verified":
        return result
    try:
        available = bool(verifier and verifier(contract, operation, str(operation.get("kind", "governed"))))
    except Exception:
        available = False
    if not available:
        return {
            **result,
            "allowed": False,
            "reason": "trusted_enforcement_verifier_required",
            "enforcement": "unavailable",
        }
    return {**result, "enforcement": "verified"}


def route_runtime(
    contract: Mapping[str, Any],
    *,
    event_log: str | Path | None = None,
    event_anchor: str | Path | None = None,
    actor: str = "policy-router",
    enforcement_verifier: EnforcementVerifier | None = None,
) -> dict[str, Any]:
    decision = route_task(contract).to_dict()
    decision = _require_runtime_enforcement(
        contract,
        decision,
        {"kind": "route", "transition": contract.get("transition", "")},
        enforcement_verifier,
    )
    payload = {
        "decision": "allow" if decision["allowed"] else "deny",
        "lane": decision["lane"],
        "reasons": decision["reasons"],
        "transition_driver": decision["transition_driver"],
    }
    return _audit_or_fail(
        contract,
        decision,
        event_log=event_log,
        event_anchor=event_anchor,
        event_type="policy.route",
        actor=actor,
        payload=payload,
    )


def authorize_runtime_action(
    contract: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    approval_evidence: Any = None,
    event_log: str | Path | None = None,
    event_anchor: str | Path | None = None,
    actor: str = "runtime-policy",
    approval_verifier: ApprovalVerifier | None = None,
    enforcement_verifier: EnforcementVerifier | None = None,
) -> dict[str, Any]:
    decision = authorize_action(
        contract,
        action,
        approval_evidence=approval_evidence,
        approval_verifier=approval_verifier,
        enforcement_verifier=enforcement_verifier,
    ).to_dict()
    decision = _require_runtime_enforcement(
        contract,
        decision,
        action,
        enforcement_verifier,
    )
    payload = {
        "decision": "allow" if decision["allowed"] else "deny",
        "action": decision["action"],
        "reason": decision["reason"],
        "enforcement": decision["enforcement"],
        "approval_evidence_hash": _evidence_fingerprint(approval_evidence),
    }
    return _audit_or_fail(
        contract,
        decision,
        event_log=event_log,
        event_anchor=event_anchor,
        event_type="policy.action",
        actor=actor,
        payload=payload,
    )


def authorize_runtime_transition(
    contract: Mapping[str, Any],
    target_state: str,
    *,
    driver: str | None = None,
    approval_evidence: Any = None,
    event_log: str | Path | None = None,
    event_anchor: str | Path | None = None,
    actor: str = "runtime-policy",
    approval_verifier: ApprovalVerifier | None = None,
    enforcement_verifier: EnforcementVerifier | None = None,
) -> dict[str, Any]:
    decision = route_transition(
        contract,
        target_state,
        driver=driver,
        approval_evidence=approval_evidence,
        approval_verifier=approval_verifier,
    ).to_dict()
    decision = _require_runtime_enforcement(
        contract,
        decision,
        {"kind": "transition", "transition": decision.get("transition", "")},
        enforcement_verifier,
    )
    payload = {
        "decision": "allow" if decision["allowed"] else "deny",
        "transition": decision["transition"],
        "driver": decision["driver"],
        "reason": decision["reason"],
        "approval_evidence_hash": _evidence_fingerprint(approval_evidence),
    }
    return _audit_or_fail(
        contract,
        decision,
        event_log=event_log,
        event_anchor=event_anchor,
        event_type="policy.transition",
        actor=actor,
        payload=payload,
    )


class RuntimePolicy:
    """Object facade around the integrated gate's pure functions."""

    route = staticmethod(route_runtime)
    authorize_action = staticmethod(authorize_runtime_action)
    authorize_transition = staticmethod(authorize_runtime_transition)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fail-closed V4.2 runtime policy gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("route", "action", "transition"):
        child = subparsers.add_parser(name)
        child.add_argument("contract", type=Path)
        child.add_argument("--event-log", type=Path)
        child.add_argument("--event-anchor", type=Path)
        child.add_argument("--actor", default="runtime-policy")
        child.add_argument("--approval-evidence", type=Path)
        child.add_argument("--json", action="store_true")
        if name == "action":
            child.add_argument("--action", type=Path, required=True)
        if name == "transition":
            child.add_argument("--to", required=True)
            child.add_argument("--driver")
    args = parser.parse_args(argv)
    try:
        contract = _load_json(args.contract)
        if not isinstance(contract, Mapping):
            raise ValueError("contract root must be an object")
        evidence = _load_json(args.approval_evidence) if args.approval_evidence else None
        if args.command == "route":
            result = route_runtime(
                contract,
                event_log=args.event_log,
                event_anchor=args.event_anchor,
                actor=args.actor,
            )
        elif args.command == "action":
            action = _load_json(args.action)
            if not isinstance(action, Mapping):
                raise ValueError("action root must be an object")
            result = authorize_runtime_action(
                contract,
                action,
                approval_evidence=evidence,
                event_log=args.event_log,
                event_anchor=args.event_anchor,
                actor=args.actor,
            )
        else:
            result = authorize_runtime_transition(
                contract,
                args.to,
                driver=args.driver,
                approval_evidence=evidence,
                event_log=args.event_log,
                event_anchor=args.event_anchor,
                actor=args.actor,
            )
    except ValueError as exc:
        print(f"runtime policy error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
    return 0 if result.get("allowed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
