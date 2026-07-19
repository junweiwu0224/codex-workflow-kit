#!/usr/bin/env python3
"""Skill lifecycle, Canary, kill-switch, and rollback state machine."""
from __future__ import annotations

import argparse
import json
import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class LifecycleError(ValueError):
    """Raised when a lifecycle transition or control operation is unsafe."""


class LifecycleState:
    DISCOVERED = "discovered"
    AUDITED = "audited"
    SHADOW = "shadow"
    REPO_PILOT = "repo_pilot"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    ROLLED_BACK = "rolled_back"

    ALL = frozenset(
        {
            DISCOVERED,
            AUDITED,
            SHADOW,
            REPO_PILOT,
            STABLE,
            DEPRECATED,
            RETIRED,
            REJECTED,
            SUSPENDED,
            ROLLED_BACK,
        }
    )


# Public alias used by callers that model the state field as a status.
LifecycleStatus = LifecycleState


TRANSITIONS: dict[str, frozenset[str]] = {
    LifecycleState.DISCOVERED: frozenset({LifecycleState.AUDITED, LifecycleState.REJECTED}),
    LifecycleState.AUDITED: frozenset({LifecycleState.SHADOW, LifecycleState.REJECTED}),
    LifecycleState.SHADOW: frozenset({LifecycleState.REPO_PILOT, LifecycleState.REJECTED}),
    LifecycleState.REPO_PILOT: frozenset({LifecycleState.STABLE, LifecycleState.REJECTED}),
    LifecycleState.STABLE: frozenset({LifecycleState.DEPRECATED, LifecycleState.SUSPENDED, LifecycleState.REJECTED}),
    LifecycleState.SUSPENDED: frozenset({LifecycleState.ROLLED_BACK, LifecycleState.RETIRED, LifecycleState.REJECTED}),
    LifecycleState.ROLLED_BACK: frozenset({LifecycleState.REPO_PILOT, LifecycleState.STABLE, LifecycleState.RETIRED, LifecycleState.REJECTED}),
    LifecycleState.DEPRECATED: frozenset({LifecycleState.RETIRED, LifecycleState.REJECTED}),
    LifecycleState.RETIRED: frozenset(),
    LifecycleState.REJECTED: frozenset(),
}

STATE_ALIASES = {
    "repo-pilot": LifecycleState.REPO_PILOT,
    "repo pilot": LifecycleState.REPO_PILOT,
    "repo_pilot": LifecycleState.REPO_PILOT,
    "last-known-good": LifecycleState.ROLLED_BACK,
    "rolled-back": LifecycleState.ROLLED_BACK,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truth(evidence: Mapping[str, Any], key: str) -> bool:
    value = evidence.get(key)
    return value is True or (isinstance(value, str) and value.lower() in {"true", "yes", "pass", "passed"})


_SENSITIVE_KEY_RE = re.compile(r"(?:token|secret|password|api[_-]?key|private[_-]?key|credential|authorization)", re.IGNORECASE)


def _safe_evidence(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY_RE.search(str(key)) else _safe_evidence(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_safe_evidence(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_evidence(item) for item in value]
    if isinstance(value, str) and ("BEGIN " in value or value.startswith("sk-")):
        return "[REDACTED]"
    return value


@dataclass
class LifecycleEvent:
    event_id: str
    at: str
    component_id: str
    action: str
    from_state: str | None
    to_state: str | None
    actor: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "at": self.at,
            "component_id": self.component_id,
            "action": self.action,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor": self.actor,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class CanaryScope:
    enabled: bool = False
    projects: list[str] = field(default_factory=list)
    task_families: list[str] = field(default_factory=list)

    def allows(self, project: str | None, task_family: str | None) -> bool:
        if not self.enabled:
            return False
        project_ok = not self.projects or project in self.projects
        family_ok = not self.task_families or task_family in self.task_families
        return project_ok and family_ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "projects": list(self.projects),
            "task_families": list(self.task_families),
        }


@dataclass
class ComponentRecord:
    component_id: str
    state: str = LifecycleState.DISCOVERED
    version: str | None = None
    last_known_good: str | None = None
    kill_switch: bool = True
    kill_switch_active: bool = False
    canary: CanaryScope = field(default_factory=CanaryScope)
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[LifecycleEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "state": self.state,
            "version": self.version,
            "last_known_good": self.last_known_good,
            "kill_switch": self.kill_switch,
            "kill_switch_active": self.kill_switch_active,
            "canary": self.canary.to_dict(),
            "metadata": self.metadata,
            "history": [event.to_dict() for event in self.history],
        }


class LifecycleManager:
    """In-memory state machine with optional durable JSON state.

    The manager is deliberately conservative: a state change cannot be used
    as evidence by itself.  Each promotion requires the named evidence gates,
    and the caller can preserve the event log for an independent reviewer.
    """

    schema_version = "4.2"

    def __init__(self, state_path: str | Path | None = None) -> None:
        self.state_path = Path(state_path) if state_path else None
        self.components: dict[str, ComponentRecord] = {}
        if self.state_path and self.state_path.exists():
            self._load(self.state_path)

    def register(
        self,
        component_id: str,
        *,
        version: str | None = None,
        state: str = LifecycleState.DISCOVERED,
        last_known_good: str | None = None,
        kill_switch: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> ComponentRecord:
        component_id = self._component_id(component_id)
        state = self._state(state)
        if state not in LifecycleState.ALL:
            raise LifecycleError(f"unknown lifecycle state: {state}")
        if component_id in self.components:
            raise LifecycleError(f"component already registered: {component_id}")
        if state == LifecycleState.STABLE and (not kill_switch or not last_known_good):
            raise LifecycleError("Stable components require kill_switch and last_known_good")
        record = ComponentRecord(
            component_id=component_id,
            state=state,
            version=version,
            last_known_good=last_known_good,
            kill_switch=kill_switch,
            metadata=dict(metadata or {}),
        )
        self.components[component_id] = record
        self._event(record, "register", None, state, "system", "initial registration", {})
        self.save()
        return record

    def get(self, component_id: str) -> ComponentRecord:
        try:
            return self.components[self._component_id(component_id)]
        except KeyError as exc:
            raise LifecycleError(f"unknown component: {component_id}") from exc

    def transition(
        self,
        component_id: str,
        target: str,
        *,
        evidence: Mapping[str, Any] | None = None,
        actor: str = "harness",
        reason: str = "",
    ) -> ComponentRecord:
        record = self.get(component_id)
        target = self._state(target)
        if target not in LifecycleState.ALL:
            raise LifecycleError(f"unknown lifecycle state: {target}")
        if target not in TRANSITIONS[record.state]:
            raise LifecycleError(f"invalid transition: {record.state} -> {target}")
        if target in {LifecycleState.REJECTED, LifecycleState.SUSPENDED} and not reason.strip():
            raise LifecycleError(f"{target} transition requires a non-empty reason")
        evidence = dict(evidence or {})
        errors = self._gate_errors(record, target, evidence)
        if errors:
            raise LifecycleError("; ".join(errors))
        old = record.state
        record.state = target
        if target == LifecycleState.STABLE:
            record.kill_switch_active = False
            record.last_known_good = record.version or record.last_known_good
        if target == LifecycleState.SUSPENDED:
            record.kill_switch_active = True
            record.canary.enabled = False
        if target in {LifecycleState.DEPRECATED, LifecycleState.RETIRED, LifecycleState.REJECTED}:
            record.canary.enabled = False
        self._event(record, "transition", old, target, actor, reason or f"promote {old} to {target}", evidence)
        self.save()
        return record

    def configure_canary(
        self,
        component_id: str,
        *,
        projects: list[str] | None = None,
        task_families: list[str] | None = None,
        enabled: bool = True,
        actor: str = "harness",
    ) -> ComponentRecord:
        record = self.get(component_id)
        if record.state not in {LifecycleState.REPO_PILOT, LifecycleState.STABLE}:
            raise LifecycleError("Canary is only available for Repo Pilot or Stable components")
        if record.kill_switch_active:
            raise LifecycleError("kill switch is active")
        project_scope = list(projects or [])
        family_scope = list(task_families or [])
        if enabled and not project_scope and not family_scope:
            raise LifecycleError("enabled Canary requires a project or task-family scope")
        record.canary = CanaryScope(bool(enabled), project_scope, family_scope)
        self._event(record, "configure_canary", record.state, record.state, actor, "update Canary scope", record.canary.to_dict())
        self.save()
        return record

    def canary_allowed(self, component_id: str, *, project: str | None = None, task_family: str | None = None) -> bool:
        record = self.get(component_id)
        return (
            record.state in {LifecycleState.REPO_PILOT, LifecycleState.STABLE}
            and not record.kill_switch_active
            and record.canary.allows(project, task_family)
        )

    def activate_kill_switch(self, component_id: str, *, reason: str, actor: str = "system") -> ComponentRecord:
        record = self.get(component_id)
        if not reason.strip():
            raise LifecycleError("kill switch requires a non-empty reason")
        if not record.kill_switch:
            raise LifecycleError("component has no kill switch capability")
        record.kill_switch_active = True
        record.canary.enabled = False
        old = record.state
        if record.state == LifecycleState.STABLE:
            record.state = LifecycleState.SUSPENDED
        self._event(record, "kill_switch", old, record.state, actor, reason, {"reason": reason})
        self.save()
        return record

    def rollback(self, component_id: str, *, reason: str, actor: str = "system") -> ComponentRecord:
        record = self.get(component_id)
        if record.state != LifecycleState.SUSPENDED:
            raise LifecycleError("rollback requires a suspended component")
        if not record.last_known_good:
            raise LifecycleError("rollback requires last_known_good")
        if not reason.strip():
            raise LifecycleError("rollback requires a non-empty reason")
        old_version = record.version
        record.version = record.last_known_good
        record.state = LifecycleState.ROLLED_BACK
        record.kill_switch_active = False
        record.canary.enabled = False
        self._event(
            record,
            "rollback",
            LifecycleState.SUSPENDED,
            LifecycleState.ROLLED_BACK,
            actor,
            reason,
            {"from_version": old_version, "to_version": record.last_known_good},
        )
        self.save()
        return record

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": _now(),
            "components": {key: value.to_dict() for key, value in sorted(self.components.items())},
        }

    def save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.export(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)

    def _load(self, path: Path) -> None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LifecycleError(f"cannot load lifecycle state: {exc}") from exc
        if not isinstance(value, dict) or not isinstance(value.get("components"), dict):
            raise LifecycleError("lifecycle state must contain components object")
        for component_id, raw in value["components"].items():
            if not isinstance(raw, dict):
                raise LifecycleError(f"invalid component record: {component_id}")
            canary_raw = raw.get("canary", {})
            record = ComponentRecord(
                component_id=str(raw.get("component_id", component_id)),
                state=str(raw.get("state", LifecycleState.DISCOVERED)),
                version=raw.get("version"),
                last_known_good=raw.get("last_known_good"),
                kill_switch=bool(raw.get("kill_switch", True)),
                kill_switch_active=bool(raw.get("kill_switch_active", False)),
                canary=CanaryScope(
                    bool(canary_raw.get("enabled", False)),
                    list(canary_raw.get("projects", [])),
                    list(canary_raw.get("task_families", [])),
                ),
                metadata=dict(raw.get("metadata", {})),
            )
            if record.state not in LifecycleState.ALL:
                raise LifecycleError(f"unknown lifecycle state for component: {component_id}")
            if record.canary.enabled and not (record.canary.projects or record.canary.task_families):
                raise LifecycleError(f"enabled Canary has no scope for component: {component_id}")
            history = raw.get("history", [])
            if not isinstance(history, list):
                raise LifecycleError(f"invalid history for component: {component_id}")
            for event_raw in history:
                if not isinstance(event_raw, dict):
                    raise LifecycleError(f"invalid lifecycle event for component: {component_id}")
                if not isinstance(event_raw.get("evidence", {}), dict):
                    raise LifecycleError(f"invalid lifecycle evidence for component: {component_id}")
                record.history.append(
                    LifecycleEvent(
                        event_id=str(event_raw.get("event_id", "")),
                        at=str(event_raw.get("at", "")),
                        component_id=str(event_raw.get("component_id", record.component_id)),
                        action=str(event_raw.get("action", "")),
                        from_state=event_raw.get("from_state"),
                        to_state=event_raw.get("to_state"),
                        actor=str(event_raw.get("actor", "")),
                        reason=str(event_raw.get("reason", "")),
                        evidence=dict(event_raw.get("evidence", {})),
                    )
                )
            self.components[record.component_id] = record

    @staticmethod
    def _component_id(component_id: str) -> str:
        if not isinstance(component_id, str) or not component_id.strip():
            raise LifecycleError("component_id must be non-empty")
        return component_id.strip()

    @staticmethod
    def _state(value: str) -> str:
        if not isinstance(value, str):
            raise LifecycleError("lifecycle state must be a string")
        normalized = STATE_ALIASES.get(value.strip().lower(), value.strip().lower())
        if normalized not in LifecycleState.ALL:
            raise LifecycleError(f"unknown lifecycle state: {value}")
        return normalized

    @staticmethod
    def _event(record: ComponentRecord, action: str, from_state: str | None, to_state: str | None, actor: str, reason: str, evidence: Mapping[str, Any]) -> None:
        safe_reason = _safe_evidence(reason)
        record.history.append(
            LifecycleEvent(
                event_id=uuid.uuid4().hex,
                at=_now(),
                component_id=record.component_id,
                action=action,
                from_state=from_state,
                to_state=to_state,
                actor=actor,
                reason=safe_reason if isinstance(safe_reason, str) else str(safe_reason),
                evidence=_safe_evidence(dict(evidence)),
            )
        )

    @staticmethod
    def _gate_errors(record: ComponentRecord, target: str, evidence: Mapping[str, Any]) -> list[str]:
        required: dict[str, tuple[str, ...]] = {
            LifecycleState.AUDITED: ("audit_pass",),
            LifecycleState.SHADOW: ("shadow_pass",),
            LifecycleState.REPO_PILOT: ("exact_commit", "explicit_only", "paired_pass"),
            LifecycleState.STABLE: ("trigger_pass", "behavior_pass", "safety_pass", "rollback_tested"),
            LifecycleState.DEPRECATED: ("replacement",),
            LifecycleState.RETIRED: ("removed_from_runtime",),
            LifecycleState.ROLLED_BACK: ("rollback_tested",),
        }
        errors: list[str] = []
        for key in required.get(target, ()):
            if key == "replacement":
                if not isinstance(evidence.get(key), str) or not str(evidence[key]).strip():
                    errors.append("deprecated transition requires replacement")
            elif not _truth(evidence, key):
                errors.append(f"{target} transition requires evidence: {key}")
        if target == LifecycleState.SHADOW:
            for key in ("tool_calls", "writes", "external_effects"):
                if key not in evidence:
                    errors.append(f"Shadow evidence must explicitly report zero {key}")
                    continue
                value = evidence[key]
                is_empty = value in (0, None, False, "", ()) or value == []
                if not is_empty:
                    errors.append(f"Shadow evidence must have zero {key}")
        if target == LifecycleState.STABLE:
            if not record.kill_switch:
                errors.append("Stable component must have kill_switch")
            if not record.last_known_good:
                errors.append("Stable component requires last_known_good")
            if "safety_violations" not in evidence:
                errors.append("Stable transition requires explicit safety_violations count")
            elif _truth(evidence, "safety_pass") and evidence.get("safety_violations") not in {0, None}:
                errors.append("safety_pass cannot coexist with safety violations")
        return errors


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage V4.2 Skill lifecycle state.")
    parser.add_argument("--state", type=Path, required=True, help="Durable JSON state path")
    sub = parser.add_subparsers(dest="action", required=True)
    register = sub.add_parser("register")
    register.add_argument("component")
    register.add_argument("--version")
    register.add_argument("--last-known-good")
    register.add_argument("--state-name", default=LifecycleState.DISCOVERED, choices=sorted(LifecycleState.ALL))
    register.add_argument("--no-kill-switch", action="store_true")
    transition = sub.add_parser("transition")
    transition.add_argument("component")
    transition.add_argument("target", choices=sorted(LifecycleState.ALL))
    transition.add_argument("--evidence", default="{}", help="Evidence JSON object")
    transition.add_argument("--reason", default="")
    kill = sub.add_parser("kill")
    kill.add_argument("component")
    kill.add_argument("--reason", required=True)
    rollback = sub.add_parser("rollback")
    rollback.add_argument("component")
    rollback.add_argument("--reason", required=True)
    canary = sub.add_parser("canary")
    canary.add_argument("component")
    canary.add_argument("--project", action="append", default=[])
    canary.add_argument("--task-family", action="append", default=[])
    canary.add_argument("--disable", action="store_true")
    sub.add_parser("show")
    args = parser.parse_args(argv)
    try:
        manager = LifecycleManager(args.state)
        if args.action == "register":
            record = manager.register(
                args.component,
                version=args.version,
                state=args.state_name,
                last_known_good=args.last_known_good,
                kill_switch=not args.no_kill_switch,
            )
        elif args.action == "transition":
            evidence = json.loads(args.evidence)
            if not isinstance(evidence, dict):
                raise LifecycleError("--evidence must decode to an object")
            record = manager.transition(args.component, args.target, evidence=evidence, reason=args.reason)
        elif args.action == "kill":
            record = manager.activate_kill_switch(args.component, reason=args.reason)
        elif args.action == "rollback":
            record = manager.rollback(args.component, reason=args.reason)
        elif args.action == "canary":
            record = manager.configure_canary(args.component, projects=args.project, task_families=args.task_family, enabled=not args.disable)
        else:
            print(json.dumps(manager.export(), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LifecycleError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"lifecycle failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
