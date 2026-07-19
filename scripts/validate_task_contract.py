#!/usr/bin/env python3
"""Validate a V4.2 Task Contract without third-party dependencies.

The contract describes intent and evidence requirements. It is not a
permission grant; actual tool and network policy must enforce the declared
scope separately.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


LANES = {"fast", "standard", "governed"}
STATES = {
    "discovered",
    "scoped",
    "approved_spec",
    "planned",
    "implemented",
    "rework_required",
    "verified",
    "released",
    "closed",
    "blocked",
    "cancelled",
}
DRIVERS = {
    "native",
    "policy-router",
    "openspec",
    "spec-kit-xl",
    "superpowers",
    "deterministic-runner",
    "verifier",
    "release-readiness",
}
WRITE_SCOPES = {"none", "workspace", "external"}
VERIFICATION_MODES = {"deterministic", "fresh_context", "mixed"}
HANDOFFS = {"none", "verify", "release", "openspec", "superpowers"}
NETWORK_POLICIES = {"none", "allowlist", "unrestricted"}
PACKAGE_INSTALL_MODES = {"none", "project-only", "user", "system"}
ALLOWED_FIELDS = {
    "acceptance_checks",
    "approval",
    "approvals",
    "audit_record",
    "browser_actions",
    "contract_id",
    "created_at",
    "credential_refs",
    "credentials",
    "destructive_actions",
    "escalation_reasons",
    "evidence_paths",
    "external_effects",
    "external_targets",
    "handoff",
    "intent",
    "lane",
    "network",
    "network_allowlist",
    "network_policy",
    "package_install",
    "policy_enforcement",
    "production_access",
    "read_roots",
    "repo_revision",
    "request_provenance",
    "required_artifacts",
    "retention",
    "reversibility",
    "rollback_plan",
    "state",
    "transition",
    "transition_driver",
    "verification_mode",
    "write_roots",
    "write_scope",
}
GOVERNED_POLICY_FIELDS = {
    "external_targets",
    "package_install",
    "production_access",
    "reversibility",
    "policy_enforcement",
}
TRANSITION_RE = re.compile(r"^(?P<source>[a-z][a-z0-9_-]*)_to_(?P<target>[a-z][a-z0-9_-]*)$")

# These are ownership defaults, not a replacement for a project-specific
# workflow. A contract can use a different driver only when the handoff is
# explicit and the transition remains auditable.
ALLOWED_TRANSITION_DRIVERS = {
    ("discovered", "scoped"): {"policy-router", "native"},
    ("scoped", "approved_spec"): {"openspec", "spec-kit-xl"},
    ("scoped", "planned"): {"native", "superpowers"},
    ("approved_spec", "planned"): {"superpowers"},
    ("planned", "implemented"): {"native", "superpowers"},
    ("implemented", "verified"): {"deterministic-runner", "verifier"},
    ("implemented", "rework_required"): {"verifier"},
    ("rework_required", "implemented"): {"native", "superpowers"},
    ("verified", "released"): {"release-readiness"},
    ("verified", "closed"): {"native", "verifier"},
}


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "lane",
        "state",
        "transition",
        "transition_driver",
        "write_scope",
        "external_effects",
        "approvals",
        "required_artifacts",
        "acceptance_checks",
        "verification_mode",
        "handoff",
    }
    missing = sorted(required - contract.keys())
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    unknown = sorted(set(contract) - ALLOWED_FIELDS)
    if unknown:
        errors.append("unknown fields: " + ", ".join(unknown))

    lane = contract.get("lane")
    state = contract.get("state")
    transition = contract.get("transition")
    driver = contract.get("transition_driver")
    write_scope = contract.get("write_scope")
    verification_mode = contract.get("verification_mode")
    handoff = contract.get("handoff")

    if not isinstance(lane, str) or lane not in LANES:
        errors.append(f"lane must be one of {sorted(LANES)}")
    if not isinstance(state, str) or state not in STATES:
        errors.append(f"state must be one of {sorted(STATES)}")
    match = TRANSITION_RE.match(transition) if isinstance(transition, str) else None
    if not match:
        errors.append("transition must use source_to_target form")
    elif state != match.group("source"):
        errors.append("transition source must match state")
    if not isinstance(driver, str) or driver not in DRIVERS:
        errors.append(f"transition_driver must be one of {sorted(DRIVERS)}")
    if not isinstance(write_scope, str) or write_scope not in WRITE_SCOPES:
        errors.append(f"write_scope must be one of {sorted(WRITE_SCOPES)}")
    if not isinstance(verification_mode, str) or verification_mode not in VERIFICATION_MODES:
        errors.append(f"verification_mode must be one of {sorted(VERIFICATION_MODES)}")
    if not isinstance(handoff, str) or handoff not in HANDOFFS:
        errors.append(f"handoff must be one of {sorted(HANDOFFS)}")
    nested_network = contract.get("network", {})
    if nested_network is not None and not isinstance(nested_network, dict):
        errors.append("network must be an object")
        nested_network = {}
    network_policy = contract.get("network_policy", nested_network.get("mode", "none"))
    if not isinstance(network_policy, str) or network_policy not in NETWORK_POLICIES:
        errors.append(f"network_policy must be one of {sorted(NETWORK_POLICIES)}")

    for field in (
        "external_effects",
        "required_artifacts",
        "acceptance_checks",
        "credential_refs",
        "credentials",
        "external_targets",
        "escalation_reasons",
        "read_roots",
        "write_roots",
        "network_allowlist",
        "evidence_paths",
        "browser_actions",
    ):
        if field not in contract:
            continue
        if not _is_string_list(contract.get(field)):
            errors.append(f"{field} must be a list of strings")
    if "package_install" in contract:
        package_install = contract["package_install"]
        if not isinstance(package_install, bool) and (
            not isinstance(package_install, str)
            or package_install not in PACKAGE_INSTALL_MODES
        ):
            # Preserve the original diagnostic for callers while accepting
            # the V4.2 scoped string modes above.
            errors.append("package_install must be boolean")
    for field in ("production_access", "audit_record", "destructive_actions"):
        if field in contract and not isinstance(contract[field], bool):
            errors.append(f"{field} must be boolean")
    if "reversibility" in contract and contract.get("reversibility") not in {
        "reversible",
        "partially-reversible",
        "irreversible",
    }:
        errors.append("reversibility has an unsupported value")
    for field in (
        "contract_id",
        "created_at",
        "intent",
        "repo_revision",
        "request_provenance",
        "retention",
        "rollback_plan",
    ):
        if field in contract and not isinstance(contract.get(field), str):
            errors.append(f"{field} must be a string")
    approvals = contract.get("approvals")
    if not isinstance(approvals, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("actor"), str)
        or item.get("decision") not in {"pending", "granted", "denied"}
        for item in approvals
    ):
        errors.append("approvals must contain actor and pending/granted/denied decision")
    elif any(
        "scope" in item
        and not (
            isinstance(item.get("scope"), str)
            or _is_string_list(item.get("scope"))
        )
        for item in approvals
        if isinstance(item, dict)
    ):
        errors.append("approval scope must be a string or list of strings")

    nested_approval = contract.get("approval")
    if nested_approval is not None and not isinstance(nested_approval, dict):
        errors.append("approval must be an object")
    elif isinstance(nested_approval, dict):
        if not isinstance(nested_approval.get("required"), bool):
            errors.append("approval.required must be boolean")
        if nested_approval.get("status") not in {"pending", "granted", "denied"}:
            errors.append("approval.status is unsupported")
        if not _is_string_list(nested_approval.get("scope", [])):
            errors.append("approval.scope must be a list of strings")

    if isinstance(nested_network, dict):
        if "network" in contract:
            missing_network = {"mode", "allowlist"} - set(nested_network)
            if missing_network:
                errors.append(
                    "network must declare: " + ", ".join(sorted(missing_network))
                )
            unknown_network = set(nested_network) - {"mode", "allowlist"}
            if unknown_network:
                errors.append(
                    "network contains unknown fields: "
                    + ", ".join(sorted(unknown_network))
                )
        nested_allowlist = nested_network.get("allowlist", [])
        if not _is_string_list(nested_allowlist):
            errors.append("network allowlist must be a list of strings")
        if (
            "network_policy" in contract
            and "mode" in nested_network
            and contract.get("network_policy") != nested_network.get("mode")
        ):
            errors.append("network_policy and network.mode must match")

    policy_enforcement = contract.get("policy_enforcement", [])
    if not isinstance(policy_enforcement, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("field"), str)
        or item.get("status") not in {"enforced", "verified", "advisory", "unavailable"}
        for item in policy_enforcement
    ):
        errors.append("policy_enforcement must contain field and a supported status")
    elif len({item["field"] for item in policy_enforcement}) != len(policy_enforcement):
        errors.append("policy_enforcement fields must be unique")

    external_effects = contract.get("external_effects") or []
    package_install_value = contract.get("package_install")
    package_install_dangerous = package_install_value is True or (
        isinstance(package_install_value, str)
        and package_install_value in {"user", "system"}
    )
    project_install = package_install_value == "project-only"
    credential_values = contract.get("credential_refs", contract.get("credentials", []))
    browser_actions = contract.get("browser_actions", [])
    if not isinstance(browser_actions, list):
        browser_actions = []
    elif any(
        not isinstance(action, str)
        or action not in {"inspect-local", "inspect-external", "submit-external"}
        for action in browser_actions
    ):
        errors.append("browser_actions contains an unsupported action")
    dangerous = any(
        (
            bool(external_effects),
            write_scope == "external",
            contract.get("production_access") is True,
            package_install_dangerous,
            bool(credential_values),
            network_policy == "unrestricted",
            contract.get("destructive_actions") is True,
            "submit-external" in browser_actions,
        )
    )
    irreversible = contract.get("reversibility") == "irreversible"
    approval_items = approvals if isinstance(approvals, list) else []
    approval_recorded = any(isinstance(item, dict) for item in approval_items)

    if lane == "fast":
        if contract.get("audit_record") is True:
            errors.append("fast contracts must not require a persistent audit record")
        if dangerous or irreversible or project_install:
            errors.append("fast lane cannot declare external or irreversible effects")
        if verification_mode != "deterministic":
            errors.append("fast lane requires deterministic verification")
    if lane == "governed":
        missing_policy = sorted(GOVERNED_POLICY_FIELDS - contract.keys())
        if "network_policy" not in contract and "network" not in contract:
            missing_policy.append("network_policy|network")
        if "credential_refs" not in contract and "credentials" not in contract:
            missing_policy.append("credential_refs|credentials")
        if missing_policy:
            errors.append("governed contracts must declare: " + ", ".join(missing_policy))
        if contract.get("audit_record") is not True:
            errors.append("governed contracts require audit_record: true")
        if (dangerous or irreversible) and not approval_recorded:
            errors.append("governed external/irreversible work requires an approval record")
        if verification_mode not in {"fresh_context", "mixed"}:
            errors.append("governed contracts require fresh_context or mixed verification")
    writes_outside_none = (
        bool(external_effects)
        or write_scope == "external"
        or package_install_dangerous
        or contract.get("destructive_actions") is True
        or "submit-external" in browser_actions
    )
    if writes_outside_none and write_scope == "none":
        errors.append("declared side effects cannot use write_scope: none")
    if project_install and write_scope == "none":
        errors.append("project-only package installation requires workspace write_scope")
    if match:
        transition_key = (match.group("source"), match.group("target"))
        allowed = ALLOWED_TRANSITION_DRIVERS.get(transition_key)
        if match.group("target") in {"blocked", "cancelled"}:
            allowed = DRIVERS
        if allowed is None:
            errors.append(f"unsupported core transition: {transition}")
        elif not isinstance(driver, str) or driver not in allowed:
            errors.append(
                f"{transition} must use one of {sorted(allowed)}, not {driver}"
            )
    if match and match.group("target") == "verified" and handoff not in {"verify", "none"}:
        errors.append("transitions into verified must hand off to verify or none")

    return errors


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("contract root must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a V4.2 Task Contract JSON file.")
    parser.add_argument("contract", type=Path, help="Path to a JSON Task Contract")
    parser.add_argument("--json", action="store_true", help="Print a JSON report")
    args = parser.parse_args(argv)

    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"invalid contract: {exc}", file=sys.stderr)
        return 2
    errors = validate_contract(contract)
    report = {"ok": not errors, "path": str(args.contract), "errors": errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif errors:
        print("Task Contract invalid")
        for error in errors:
            print(f"- {error}")
    else:
        print("Task Contract valid")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
