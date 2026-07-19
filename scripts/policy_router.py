#!/usr/bin/env python3
"""Fail-closed policy routing and action authorization for V4.2.

The Task Contract is an intent/evidence document.  This module is the small
runtime decision layer that turns a task description into a lane and checks a
single requested action against the declared policy.  It deliberately does
not execute tools, install packages, or contact external services.

Missing policy is interpreted as the least privilege.  In particular, a
contract never grants a network, credential, production, or external-write
permission merely by mentioning it in free-form text.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

try:  # Support both ``python scripts/policy_router.py`` and package imports.
    from scripts.validate_task_contract import validate_contract
except ImportError:  # pragma: no cover - exercised by direct script execution
    from validate_task_contract import validate_contract


LANES = ("fast", "standard", "governed")
LANE_RANK = {lane: index for index, lane in enumerate(LANES)}
NETWORK_MODES = {"none", "allowlist", "unrestricted"}
PACKAGE_MODES = {"none", "project-only", "user", "system"}
APPROVAL_DECISIONS = {"pending", "granted", "denied"}
MAX_APPROVAL_TTL = dt.timedelta(minutes=15)
TRUSTED_APPROVAL_SOURCES = {
    "runtime-user",
    "user-confirmation",
    "signed-record",
    "trusted-policy",
}
ACTION_ALIASES = {
    "read": "workspace_read",
    "write": "workspace_write",
    "network": "network_read",
    "network_write": "network_write",
    "external_read": "external_read",
    "external_write": "external_write",
    "credential": "credential_use",
    "use_credential": "credential_use",
    "install": "package_install",
    "production": "production_access",
    "destructive_action": "destructive",
}
CRITICAL_ACTION_KINDS = {
    "external_write",
    "network_write",
    "credential_use",
    "production_access",
    "destructive",
}
ApprovalVerifier = Callable[[Mapping[str, Any], str, str | None], bool]
EnforcementVerifier = Callable[[Mapping[str, Any], Mapping[str, Any], str], bool]

_SENSITIVE_KEY_RE = re.compile(
    r"(?:^|_)(?:api[_-]?key|secret|token|password|private[_-]?key|"
    r"credential[_-]?value|authorization)(?:$|_)",
    re.IGNORECASE,
)
_SENSITIVE_VALUE_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RouteDecision:
    """The router's deterministic, side-effect-free result."""

    lane: str
    reasons: tuple[str, ...]
    transition_driver: str
    persist_contract: bool
    require_approval: bool
    verification_mode: str
    allowed: bool = True
    enforcement: str = "advisory"

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "reasons": list(self.reasons),
            "transition_driver": self.transition_driver,
            "persist_contract": self.persist_contract,
            "require_approval": self.require_approval,
            "verification_mode": self.verification_mode,
            "allowed": self.allowed,
            "enforcement": self.enforcement,
        }


@dataclass(frozen=True)
class ActionDecision:
    """Authorization result for one concrete tool/action request."""

    allowed: bool
    action: str
    lane: str
    reason: str
    enforcement: str
    require_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "lane": self.lane,
            "reason": self.reason,
            "enforcement": self.enforcement,
            "require_approval": self.require_approval,
        }


def _as_string_list(value: Any) -> tuple[list[str] | None, str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None, "must be a list of strings"
    return list(value), None


def _contains_secret_material(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and _SENSITIVE_KEY_RE.search(key):
                return True
            if _contains_secret_material(child):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_material(item) for item in value)
    elif isinstance(value, str):
        return bool(_SENSITIVE_VALUE_RE.search(value))
    return False


def _network_values(policy: Mapping[str, Any]) -> tuple[str, list[str], str | None]:
    nested = policy.get("network")
    if nested is not None and not isinstance(nested, Mapping):
        return "none", [], "network must be an object"
    nested = nested if isinstance(nested, Mapping) else {}
    mode = policy.get("network_policy", nested.get("mode", "none"))
    allowlist = policy.get("network_allowlist", nested.get("allowlist", []))
    hosts, error = _as_string_list(allowlist)
    if mode not in NETWORK_MODES:
        return "none", [], "network mode is unavailable"
    if error:
        return str(mode), [], f"network allowlist {error}"
    return str(mode), hosts or [], None


def _credentials(policy: Mapping[str, Any]) -> tuple[list[str], str | None]:
    values = policy.get("credential_refs", policy.get("credentials", []))
    refs, error = _as_string_list(values)
    return refs or [], error


def _package_mode(policy: Mapping[str, Any]) -> tuple[str, str | None]:
    value = policy.get("package_install", "none")
    # A boolean is the legacy schema form.  ``True`` is intentionally
    # ambiguous: the runtime cannot know whether it means project or system.
    if isinstance(value, bool):
        return ("unavailable", "boolean package_install is ambiguous") if value else ("none", None)
    if value not in PACKAGE_MODES:
        return "unavailable", "package_install mode is unavailable"
    return str(value), None


def _effects(policy: Mapping[str, Any]) -> tuple[list[str], str | None]:
    effects, error = _as_string_list(policy.get("external_effects", []))
    return effects or [], error


def _targets(policy: Mapping[str, Any]) -> tuple[list[str], str | None]:
    targets, error = _as_string_list(policy.get("external_targets", []))
    return targets or [], error


def _requested_lane(task: Mapping[str, Any]) -> tuple[str | None, str | None]:
    value = task.get("lane")
    if value is None:
        return None, None
    if value not in LANE_RANK:
        return None, "lane is unavailable"
    return str(value), None


def _max_lane(*lanes: str) -> str:
    return max(lanes, key=lambda lane: LANE_RANK[lane])


def route_task(task: Mapping[str, Any]) -> RouteDecision:
    """Choose a lane from risk and side-effect declarations.

    This function accepts either a compact Fast/Standard request or a full
    Task Contract.  It never lowers an explicitly requested lane.  A malformed
    dangerous field produces a blocked Governed result instead of silently
    treating the field as absent.
    """
    if not isinstance(task, Mapping):
        return RouteDecision(
            lane="governed",
            reasons=("task_is_not_an_object",),
            transition_driver="policy-router",
            persist_contract=True,
            require_approval=True,
            verification_mode="fresh_context",
            allowed=False,
            enforcement="unavailable",
        )

    requested, lane_error = _requested_lane(task)
    reasons: list[str] = []
    errors: list[str] = []
    if lane_error:
        errors.append(lane_error)

    write_scope = task.get("write_scope", "none")
    if write_scope not in {"none", "workspace", "external"}:
        errors.append("write_scope is unavailable")
        write_scope = "external"

    effects, error = _effects(task)
    if error:
        errors.append(f"external_effects {error}")
    targets, error = _targets(task)
    if error:
        errors.append(f"external_targets {error}")
    credentials, error = _credentials(task)
    if error:
        errors.append(f"credentials {error}")
    network_mode, allowlist, error = _network_values(task)
    if error:
        errors.append(error)
    package_mode, error = _package_mode(task)
    if error:
        errors.append(error)

    production = task.get("production_access", False)
    destructive = task.get("destructive_actions", False)
    if not isinstance(production, bool):
        errors.append("production_access is unavailable")
        production = True
    if not isinstance(destructive, bool):
        errors.append("destructive_actions is unavailable")
        destructive = True
    irreversible = task.get("reversibility") == "irreversible"
    if task.get("reversibility") is not None and task.get("reversibility") not in {
        "reversible",
        "partially-reversible",
        "irreversible",
    }:
        errors.append("reversibility is unavailable")
        irreversible = True

    # Explicit external effects are dangerous even when a caller forgot to
    # set write_scope.  External *read* targets remain Standard unless another
    # boundary (credentials, production, write, or unrestricted network) is
    # present.
    external_write = write_scope == "external" or bool(effects)
    governed_reasons: list[str] = []
    if external_write:
        governed_reasons.append("external_write_or_effect")
    if credentials:
        governed_reasons.append("credential_use")
    if production:
        governed_reasons.append("production_access")
    if destructive or irreversible:
        governed_reasons.append("destructive_or_irreversible")
    if package_mode in {"user", "system", "unavailable"}:
        governed_reasons.append("privileged_or_ambiguous_install")
    if network_mode == "unrestricted":
        governed_reasons.append("unrestricted_network")
    if task.get("public_api") is True or task.get("data_migration") is True:
        governed_reasons.append("public_or_data_boundary")
    if task.get("permission_change") is True or task.get("security_boundary") is True:
        governed_reasons.append("security_boundary")

    standard_reasons: list[str] = []
    if write_scope == "workspace":
        standard_reasons.append("workspace_write")
    if network_mode == "allowlist":
        standard_reasons.append("allowlisted_network")
    if targets:
        standard_reasons.append("external_read_target")
    if package_mode == "project-only":
        standard_reasons.append("project_dependency_install")
    if task.get("subjective") is True or task.get("weak_verifier") is True:
        standard_reasons.append("weak_or_subjective_verifier")
    if task.get("design_choices") is True or task.get("multi_module") is True or task.get("requires_tdd") is True:
        standard_reasons.append("design_or_multi_module_work")

    if governed_reasons:
        derived = "governed"
        reasons.extend(governed_reasons)
    else:
        declared_fast_evidence = (
            requested == "fast"
            and task.get("verification_mode") == "deterministic"
            and isinstance(task.get("acceptance_checks"), list)
            and bool(task.get("acceptance_checks"))
        )
        non_workspace_standard = [
            reason for reason in standard_reasons if reason != "workspace_write"
        ]
        fast_eligible = (
            (
                (
                    bool(task.get("requirement_clear", task.get("clear_requirement", False)))
                    and bool(task.get("strong_verifier", task.get("has_strong_verifier", False)))
                )
                or declared_fast_evidence
            )
            and task.get("reversibility", "reversible") == "reversible"
            and not non_workspace_standard
            and write_scope in {"none", "workspace"}
            and network_mode == "none"
            and package_mode == "none"
        )
        if fast_eligible:
            derived = "fast"
            reasons.append("clear_reversible_strongly_verified")
        else:
            derived = "standard"
            reasons.extend(standard_reasons or ["explicit_reviewable_work"])

    if requested:
        lane = _max_lane(derived, requested)
        if LANE_RANK[requested] < LANE_RANK[derived]:
            reasons.append("requested_lane_upgraded")
    else:
        lane = derived

    # Any unavailable declaration is a hard stop.  The result is still
    # Governed so callers cannot accidentally proceed down a Fast path.
    if errors:
        lane = "governed"
        reasons.extend(f"policy_unavailable:{item}" for item in errors)

    declared_enforcement = task.get("policy_enforcement")
    if declared_enforcement is not None:
        if not isinstance(declared_enforcement, list):
            errors.append("policy_enforcement is unavailable")
        else:
            critical_fields = {
                "external_write",
                "network_write",
                "credential_use",
                "production_access",
                "destructive",
                "package_install",
            }
            for entry in declared_enforcement:
                if not isinstance(entry, Mapping):
                    errors.append("policy_enforcement entry is unavailable")
                    continue
                field = entry.get("field")
                status = entry.get("status")
                if field in critical_fields and status != "enforced":
                    errors.append(f"critical_enforcement:{field}:{status or 'missing'}")

    if errors:
        reasons.extend(
            f"policy_unavailable:{item}"
            for item in errors
            if f"policy_unavailable:{item}" not in reasons
        )
        lane = "governed"

    transition = str(task.get("transition", ""))
    if transition.startswith("discovered_to_scoped"):
        driver = "policy-router"
    elif transition.startswith("scoped_to_approved_spec"):
        driver = str(task.get("transition_driver", "openspec"))
    elif transition.startswith("approved_spec_to_planned") or transition.startswith("planned_to_implemented"):
        driver = str(task.get("transition_driver", "superpowers" if lane != "fast" else "native"))
    elif transition.startswith("implemented_to_verified"):
        driver = str(task.get("transition_driver", "verifier" if lane == "governed" else "deterministic-runner"))
    else:
        driver = str(task.get("transition_driver", "native" if lane == "fast" else "policy-router"))

    return RouteDecision(
        lane=lane,
        reasons=tuple(dict.fromkeys(reasons)),
        transition_driver=driver,
        persist_contract=lane == "governed",
        require_approval=lane == "governed",
        verification_mode="deterministic" if lane == "fast" else ("fresh_context" if lane == "governed" else "mixed"),
        allowed=not errors,
        enforcement="advisory" if not errors else "unavailable",
    )


# Alias used by callers that prefer the policy vocabulary.
classify_task = route_task
route = route_task


def _approval_records(evidence: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    """Read approval evidence supplied outside the Task Contract.

    Contract ``approvals`` describe expected state only.  Runtime callers must
    pass an independent evidence object to this function; no Contract is used
    as an implicit fallback.
    """
    records: list[Mapping[str, Any]] = []
    if evidence is None:
        return records
    if isinstance(evidence, Mapping):
        inherited_source = evidence.get("source")
        inherited_contract_id = evidence.get("contract_id")
        values = evidence.get("approvals")
        if isinstance(values, list):
            for item in values:
                if isinstance(item, Mapping):
                    record = dict(item)
                    record.setdefault("source", inherited_source)
                    record.setdefault("contract_id", inherited_contract_id)
                    records.append(record)
        elif "decision" in evidence or "status" in evidence:
            records.append(evidence)
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        records.extend(item for item in evidence if isinstance(item, Mapping))
    return records


def _scope_matches(scope: Any, action: str, target: str | None) -> bool:
    if isinstance(scope, str):
        values = [scope]
    elif isinstance(scope, list) and all(isinstance(item, str) for item in scope):
        values = scope
    else:
        return False
    normalized = {value.strip().lower() for value in values}
    if "*" in normalized:
        return True
    action_matches = action.lower() in normalized
    if action.startswith("external_"):
        action_matches = action_matches or "external" in normalized
    if not action_matches:
        return False
    return not target or target.lower() in normalized


def has_granted_approval(
    evidence: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    action: str,
    target: str | None = None,
    *,
    contract_id: str | None = None,
    verifier: ApprovalVerifier | None = None,
) -> bool:
    """Return true only for fresh, contract-bound, authenticated evidence."""
    if verifier is None or not isinstance(contract_id, str) or not contract_id.strip():
        return False
    for record in _approval_records(evidence):
        if record.get("decision", record.get("status")) != "granted":
            continue
        if not isinstance(record.get("actor"), str) or not record.get("actor", "").strip():
            continue
        if record.get("source") not in TRUSTED_APPROVAL_SOURCES:
            continue
        if record.get("contract_id") != contract_id:
            continue
        try:
            at = record.get("at", record.get("granted_at"))
            parsed = dt.datetime.fromisoformat(str(at).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                continue
            now = dt.datetime.now(dt.timezone.utc)
            if parsed > now + dt.timedelta(minutes=5):
                continue
            expires_at = record.get("expires_at")
            if expires_at is None:
                continue
            expires = dt.datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expires.tzinfo is None or expires < parsed or expires < now:
                continue
            if expires - parsed > MAX_APPROVAL_TTL:
                continue
        except (TypeError, ValueError):
            continue
        if not _scope_matches(record.get("scope"), action, target):
            continue
        try:
            if verifier(record, action, target):
                return True
        except Exception:
            continue
    return False


def _path_matches(path: Any, roots: Sequence[str]) -> bool:
    if not isinstance(path, str) or not path or not roots:
        return False
    try:
        candidate = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
        for root in roots:
            if not isinstance(root, str) or not root:
                continue
            root_abs = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
            if os.path.commonpath([candidate, root_abs]) == root_abs:
                return True
    except (OSError, ValueError):
        return False
    return False


def _host(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").lower().rstrip(".") or None


def _host_matches(host: str | None, allowlist: Sequence[str]) -> bool:
    if not host:
        return False
    for raw in allowlist:
        allowed = _host(raw) or raw.lower().strip().rstrip(".")
        if allowed.startswith("*."):
            if host.endswith(allowed[1:]) and host != allowed[2:]:
                return True
        elif host == allowed:
            return True
    return False


def _deny(action: str, lane: str, reason: str, *, approval: bool = False, enforcement: str = "advisory") -> ActionDecision:
    return ActionDecision(False, action, lane, reason, enforcement, approval)


def _declared_enforcement(contract: Mapping[str, Any], capability: str) -> str:
    entries = contract.get("policy_enforcement")
    if entries is None:
        return "unavailable"
    if not isinstance(entries, list):
        return "unavailable"
    aliases = {capability}
    if capability.startswith("network_"):
        aliases.add("network")
    if capability.startswith("external_"):
        aliases.add("external")
    for item in entries:
        if isinstance(item, Mapping) and item.get("field") in aliases:
            status = item.get("status")
            return str(status) if status in {"enforced", "verified", "advisory", "unavailable"} else "unavailable"
    return "unavailable"


def authorize_action(
    contract: Mapping[str, Any],
    action: Mapping[str, Any],
    *,
    approval_evidence: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    approval_verifier: ApprovalVerifier | None = None,
    enforcement_verifier: EnforcementVerifier | None = None,
) -> ActionDecision:
    """Authorize one action; unknown or under-specified actions are denied."""
    if not isinstance(contract, Mapping):
        return _deny("unknown", "governed", "contract_is_not_an_object", enforcement="unavailable")
    if not isinstance(action, Mapping):
        return _deny("unknown", "governed", "action_is_not_an_object", enforcement="unavailable")
    if _contains_secret_material(contract) or _contains_secret_material(action):
        return _deny("unknown", "governed", "raw_secret_material_is_forbidden", enforcement="unavailable")

    raw_kind = action.get("kind", action.get("action", ""))
    kind = ACTION_ALIASES.get(raw_kind, raw_kind)
    if not isinstance(kind, str) or not kind:
        return _deny("unknown", "governed", "action_kind_missing", enforcement="unavailable")

    contract_errors = validate_contract(dict(contract))
    route = route_task(contract)
    lane = route.lane
    if contract_errors or not route.allowed:
        enforcement_status = _declared_enforcement(contract, kind)
        if kind in CRITICAL_ACTION_KINDS and enforcement_status != "enforced":
            return _deny(
                kind,
                lane,
                "critical_policy_enforcement_not_available",
                approval=True,
                enforcement=enforcement_status,
            )
        return _deny("unknown", lane, "invalid_or_unavailable_task_policy", enforcement="unavailable")
    if lane not in LANE_RANK:
        return _deny("unknown", "governed", "lane_is_unavailable", enforcement="unavailable")

    target = action.get("target", action.get("domain"))
    if target is not None and not isinstance(target, str):
        return _deny(kind, lane, "action_target_is_unavailable", enforcement="unavailable")

    mode, allowlist, network_error = _network_values(contract)
    package_mode, package_error = _package_mode(contract)
    refs, credentials_error = _credentials(contract)
    effects, effects_error = _effects(contract)
    targets, targets_error = _targets(contract)
    policy_errors = [error for error in (network_error, package_error, credentials_error, effects_error, targets_error) if error]
    if policy_errors:
        return _deny(kind, lane, "policy_unavailable", enforcement="unavailable")

    critical = kind in CRITICAL_ACTION_KINDS or (kind == "network_read" and mode == "unrestricted") or (
        kind == "package_install" and package_mode in {"user", "system", "unavailable"}
    )
    enforcement_status = _declared_enforcement(contract, kind)
    if critical and enforcement_status not in {"enforced", "verified"}:
        return _deny(
            kind,
            lane,
            "critical_policy_enforcement_not_available",
            approval=True,
            enforcement=enforcement_status,
        )
    if critical:
        try:
            enforcement_available = bool(
                enforcement_verifier
                and enforcement_verifier(contract, action, kind)
            )
        except Exception:
            enforcement_available = False
        if not enforcement_available:
            return _deny(
                kind,
                lane,
                "trusted_enforcement_verifier_required",
                approval=True,
                enforcement="unavailable",
            )

    decision_enforcement = "verified" if critical else "advisory"

    approvals_required = False
    approval_target = target if isinstance(target, str) else None
    contract_id = contract.get("contract_id")
    trusted_contract_id = contract_id if isinstance(contract_id, str) else None

    if kind == "workspace_read":
        roots, error = _as_string_list(contract.get("read_roots", []))
        if error or not _path_matches(action.get("path"), roots or []):
            return _deny(kind, lane, "read_path_not_declared")
        return ActionDecision(True, kind, lane, "declared_read_root", decision_enforcement)

    if kind == "workspace_write":
        if contract.get("write_scope") != "workspace":
            return _deny(kind, lane, "workspace_write_not_declared")
        roots, error = _as_string_list(contract.get("write_roots", []))
        if error or not _path_matches(action.get("path"), roots or []):
            return _deny(kind, lane, "write_path_not_declared")
        return ActionDecision(True, kind, lane, "declared_workspace_write_root", decision_enforcement)

    if kind in {"network_read", "network_write"}:
        if mode == "none":
            return _deny(kind, lane, "network_not_declared")
        if kind == "network_write":
            approvals_required = True
            if not isinstance(target, str) or target not in targets:
                return _deny(kind, lane, "network_write_target_not_declared", approval=True)
        if mode == "allowlist" and not _host_matches(_host(target), allowlist):
            return _deny(kind, lane, "network_target_not_allowlisted")
        if mode == "unrestricted":
            approvals_required = True
        if approvals_required:
            if lane != "governed":
                return _deny(kind, lane, "network_action_requires_governed_lane", approval=True)
            if not has_granted_approval(approval_evidence, kind, approval_target, contract_id=trusted_contract_id, verifier=approval_verifier):
                return _deny(kind, lane, "explicit_scoped_approval_required", approval=True)
        return ActionDecision(True, kind, lane, "declared_network_policy", decision_enforcement, approvals_required)

    if kind == "external_read":
        if not isinstance(target, str) or target not in targets:
            return _deny(kind, lane, "external_read_target_not_declared")
        if mode == "none":
            return _deny(kind, lane, "network_not_declared")
        if mode == "allowlist" and not _host_matches(_host(target), allowlist):
            return _deny(kind, lane, "external_read_target_not_allowlisted")
        return ActionDecision(True, kind, lane, "declared_external_read", decision_enforcement)

    if kind == "external_write":
        if contract.get("write_scope") != "external":
            return _deny(kind, lane, "external_write_scope_not_declared", approval=True)
        if not isinstance(target, str) or target not in targets:
            return _deny(kind, lane, "external_write_target_not_declared", approval=True)
        if not effects:
            return _deny(kind, lane, "external_effect_not_declared", approval=True)
        if mode == "none":
            return _deny(kind, lane, "network_not_declared", approval=True)
        if mode == "allowlist" and not _host_matches(_host(target), allowlist):
            return _deny(kind, lane, "external_write_target_not_allowlisted", approval=True)
        if lane != "governed":
            return _deny(kind, lane, "external_write_requires_governed_lane", approval=True)
        if not has_granted_approval(approval_evidence, kind, approval_target, contract_id=trusted_contract_id, verifier=approval_verifier) and not has_granted_approval(approval_evidence, "external", approval_target, contract_id=trusted_contract_id, verifier=approval_verifier):
            return _deny(kind, lane, "explicit_scoped_approval_required", approval=True)
        return ActionDecision(True, kind, lane, "approved_external_write", decision_enforcement, True)

    if kind == "credential_use":
        ref = action.get("credential_ref", target)
        if not isinstance(ref, str) or ref not in refs:
            return _deny(kind, lane, "credential_reference_not_declared", approval=True)
        if lane != "governed" or not has_granted_approval(approval_evidence, kind, ref, contract_id=trusted_contract_id, verifier=approval_verifier):
            return _deny(kind, lane, "explicit_scoped_approval_required", approval=True)
        return ActionDecision(True, kind, lane, "approved_named_credential", decision_enforcement, True)

    if kind == "package_install":
        requested_scope = action.get("scope", "project-only")
        if package_mode == "none" or package_mode == "unavailable":
            return _deny(kind, lane, "package_install_not_declared", approval=True)
        if requested_scope != package_mode:
            return _deny(kind, lane, "package_install_scope_mismatch", approval=package_mode != "project-only")
        if package_mode == "project-only":
            roots, error = _as_string_list(contract.get("write_roots", []))
            if error or not _path_matches(action.get("path"), roots or []):
                return _deny(kind, lane, "project_install_path_not_declared")
        if package_mode in {"user", "system"}:
            if lane != "governed" or not has_granted_approval(approval_evidence, kind, package_mode, contract_id=trusted_contract_id, verifier=approval_verifier):
                return _deny(kind, lane, "privileged_install_requires_scoped_approval", approval=True)
            return ActionDecision(True, kind, lane, "approved_privileged_install", decision_enforcement, True)
        return ActionDecision(True, kind, lane, "approved_project_install", decision_enforcement)

    if kind == "production_access":
        if contract.get("production_access") is not True:
            return _deny(kind, lane, "production_access_not_declared", approval=True)
        if not isinstance(target, str) or target not in targets:
            return _deny(kind, lane, "production_target_not_declared", approval=True)
        if mode == "none":
            return _deny(kind, lane, "network_not_declared", approval=True)
        if mode == "allowlist" and not _host_matches(_host(target), allowlist):
            return _deny(kind, lane, "production_target_not_allowlisted", approval=True)
        if lane != "governed" or not has_granted_approval(approval_evidence, kind, approval_target, contract_id=trusted_contract_id, verifier=approval_verifier):
            return _deny(kind, lane, "explicit_scoped_approval_required", approval=True)
        return ActionDecision(True, kind, lane, "approved_production_access", decision_enforcement, True)

    if kind == "destructive":
        if contract.get("destructive_actions") is not True and contract.get("reversibility") != "irreversible":
            return _deny(kind, lane, "destructive_action_not_declared", approval=True)
        path = action.get("path")
        if path is not None:
            roots, error = _as_string_list(contract.get("write_roots", []))
            if error or not _path_matches(path, roots or []):
                return _deny(kind, lane, "destructive_path_not_declared", approval=True)
            approval_target = str(path)
        elif not isinstance(target, str) or target not in targets:
            return _deny(kind, lane, "destructive_target_not_declared", approval=True)
        if lane != "governed" or not has_granted_approval(approval_evidence, kind, approval_target, contract_id=trusted_contract_id, verifier=approval_verifier):
            return _deny(kind, lane, "explicit_scoped_approval_required", approval=True)
        return ActionDecision(True, kind, lane, "approved_destructive_action", decision_enforcement, True)

    return _deny(kind, lane, "unknown_action_kind", enforcement="unavailable")


# Common spelling for callers and tests.
evaluate_action = authorize_action
enforce_action = authorize_action


class PolicyRouter:
    """Small object facade for adapters that prefer dependency injection."""

    route = staticmethod(route_task)
    authorize = staticmethod(authorize_action)
    enforce = staticmethod(authorize_action)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route a V4.2 task or authorize one action.")
    parser.add_argument("contract", type=Path, help="Task/request JSON")
    parser.add_argument("--action", type=Path, help="Action JSON; authorize instead of route")
    parser.add_argument("--approval-evidence", type=Path, help="Independent runtime approval evidence JSON")
    parser.add_argument("--json", action="store_true", help="Print a JSON decision")
    args = parser.parse_args(argv)
    try:
        contract = _load_json(args.contract)
        approval_evidence = _load_json(args.approval_evidence) if args.approval_evidence else None
        if args.action:
            action = _load_json(args.action)
            result: Mapping[str, Any] = authorize_action(
                contract,
                action,
                approval_evidence=approval_evidence,
            ).to_dict()
            ok = bool(result.get("allowed"))
        else:
            if not isinstance(contract, Mapping):
                raise ValueError("task JSON root must be an object")
            result = route_task(contract).to_dict()
            ok = bool(result.get("allowed"))
    except ValueError as exc:
        print(f"policy router error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
