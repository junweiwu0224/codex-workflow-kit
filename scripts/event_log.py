#!/usr/bin/env python3
"""Append-only, hash-chained runtime event log for V4.2.

The log records decisions and evidence metadata, never secrets.  It is a
small JSONL format so it can be inspected with ordinary tools while retaining
integrity evidence.  Existing entries are validated before every append.
Modification/reordering is detected by the chain; tail truncation is detected
when the caller supplies an independently retained event-count/last-hash
anchor path.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping


EVENT_VERSION = 1
ANCHOR_VERSION = 2
HEX_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,80}$")
SENSITIVE_KEY_RE = re.compile(
    r"(?:^|_)(?:api[_-]?key|secret|token|password|private[_-]?key|"
    r"credential[_-]?value|authorization)(?:$|_)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY|"
    r"authorization:\s*bearer\s+[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


class EventLogError(ValueError):
    """Raised when an event would violate append-only or redaction rules."""


def _anchor_error(message: str) -> EventLogError:
    return EventLogError(f"invalid event log anchor: {message}")


def _lock_path(target: Path) -> Path:
    return target.with_name(f".{target.name}.lock")


def log_identity(path: str | Path) -> str:
    """Bind a local anchor to one canonical log path."""
    canonical = str(Path(path).resolve(strict=False)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@contextmanager
def _exclusive_lock(target: Path) -> Iterator[None]:
    """Take a process-wide lock for a log and fail closed when unavailable."""
    lock_path = _lock_path(target)
    descriptor: int | None = None
    unlock: Any = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        if os.name == "posix":
            try:
                import fcntl
            except ImportError as exc:  # pragma: no cover - unusual POSIX runtime
                raise EventLogError("cross-process event log locking is unavailable") from exc
            deadline = time.monotonic() + 10.0
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise EventLogError("cannot acquire cross-process event log lock") from exc
                    time.sleep(0.025)

            def unlock() -> None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)

        elif os.name == "nt":
            try:
                import msvcrt
            except ImportError as exc:  # pragma: no cover - Windows always provides msvcrt
                raise EventLogError("cross-process event log locking is unavailable") from exc
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.read(descriptor, 1) == b"":
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            deadline = time.monotonic() + 10.0
            while True:
                try:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise EventLogError("cannot acquire cross-process event log lock") from exc
                    time.sleep(0.025)

            def unlock() -> None:
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)

        else:  # pragma: no cover - Python currently has no other supported OS family
            raise EventLogError("cross-process event log locking is unavailable")
        yield
    except EventLogError:
        raise
    except OSError as exc:
        raise EventLogError(f"cannot acquire cross-process event log lock: {exc}") from exc
    finally:
        if descriptor is not None:
            if unlock is not None:
                try:
                    unlock()
                except OSError as exc:
                    raise EventLogError(f"cannot release cross-process event log lock: {exc}") from exc
            try:
                os.close(descriptor)
            except OSError as exc:
                raise EventLogError(f"cannot close cross-process event log lock: {exc}") from exc


@contextmanager
def _exclusive_locks(*targets: Path) -> Iterator[None]:
    """Lock every shared log/anchor resource in a stable global order."""
    canonical = sorted({target.resolve(strict=False) for target in targets}, key=str)
    with ExitStack() as stack:
        for target in canonical:
            stack.enter_context(_exclusive_lock(target))
        yield


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def event_hash(event: Mapping[str, Any]) -> str:
    """Hash an event excluding its stored ``hash`` field."""
    payload = {key: value for key, value in event.items() if key != "hash"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _contains_secret(value: Any, path: str = "payload") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                return f"{path}.<non-string-key>"
            child_path = f"{path}.{key}"
            if SENSITIVE_KEY_RE.search(key):
                return child_path
            found = _contains_secret(child, child_path)
            if found:
                return found
        return None
    if isinstance(value, list):
        for index, child in enumerate(value):
            found = _contains_secret(child, f"{path}[{index}]")
            if found:
                return found
        return None
    if isinstance(value, str) and SENSITIVE_VALUE_RE.search(value):
        return path
    return None


def _timestamp(value: str | None = None) -> str:
    if value is None:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if not isinstance(value, str) or not value:
        raise EventLogError("timestamp must be a non-empty ISO-8601 string")
    candidate = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise EventLogError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise EventLogError("timestamp must include a timezone")
    return value


def _read_raw(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if not path.is_file():
        raise EventLogError("event log path is not a file")
    events: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise EventLogError(f"blank line at event {line_number}")
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EventLogError(f"invalid JSON at event {line_number}: {exc.msg}") from exc
                if not isinstance(value, dict):
                    raise EventLogError(f"event {line_number} must be an object")
                events.append(value)
    except OSError as exc:
        raise EventLogError(f"cannot read event log: {exc}") from exc
    return events


def _read_anchor(path: Path, *, expected_log_identity: str | None = None) -> dict[str, Any]:
    if not path.exists():
        raise _anchor_error("does not exist")
    if not path.is_file():
        raise _anchor_error("path is not a file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _anchor_error(f"cannot read JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise _anchor_error("must be an object")
    if value.get("version") != ANCHOR_VERSION:
        raise _anchor_error("unsupported version")
    events = value.get("events")
    last_hash = value.get("last_hash")
    bound_log = value.get("log_identity")
    if not isinstance(bound_log, str) or not HEX_HASH_RE.fullmatch(bound_log):
        raise _anchor_error("log_identity must be a lowercase SHA-256 hex digest")
    if expected_log_identity is not None and bound_log != expected_log_identity:
        raise _anchor_error("is bound to a different event log")
    if not isinstance(events, int) or isinstance(events, bool) or events < 0:
        raise _anchor_error("events must be a non-negative integer")
    if events == 0:
        if last_hash != "":
            raise _anchor_error("empty log anchor must have an empty last_hash")
    elif not isinstance(last_hash, str) or not HEX_HASH_RE.fullmatch(last_hash):
        raise _anchor_error("last_hash must be a lowercase SHA-256 hex digest")
    return {
        "version": ANCHOR_VERSION,
        "log_identity": bound_log,
        "events": events,
        "last_hash": last_hash,
    }


def _fsync_parent(path: Path) -> None:
    """Persist a rename on platforms where directory fsync is supported."""
    if os.name != "posix":
        return
    try:
        descriptor = os.open(str(path.parent), os.O_RDONLY)
    except OSError as exc:
        raise EventLogError(f"cannot open event log parent directory: {exc}") from exc
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise EventLogError(f"cannot sync event log parent directory: {exc}") from exc
    finally:
        os.close(descriptor)


def _write_anchor_atomically(
    path: Path,
    *,
    bound_log_identity: str,
    events: int,
    last_hash: str,
) -> None:
    """Atomically replace the anchor only after the log itself is durable."""
    anchor = {
        "version": ANCHOR_VERSION,
        "log_identity": bound_log_identity,
        "events": events,
        "last_hash": last_hash,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(anchor, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            _fsync_parent(path)
        finally:
            if temporary.exists():
                temporary.unlink()
    except OSError as exc:
        raise EventLogError(f"cannot atomically update event log anchor: {exc}") from exc


def validate_event(
    event: Mapping[str, Any],
    *,
    previous_hash: str = "",
    expected_sequence: int = 1,
    known_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    required = {"version", "sequence", "event_id", "timestamp", "contract_id", "event_type", "actor", "payload", "prev_hash", "hash"}
    missing = sorted(required - set(event))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
        return errors
    if event.get("version") != EVENT_VERSION:
        errors.append("unsupported event version")
    if event.get("sequence") != expected_sequence:
        errors.append("sequence is not contiguous")
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id:
        errors.append("event_id must be non-empty")
    elif known_ids is not None and event_id in known_ids:
        errors.append("event_id is duplicated")
    try:
        _timestamp(event.get("timestamp"))
    except EventLogError as exc:
        errors.append(str(exc))
    for field in ("contract_id", "actor"):
        if not isinstance(event.get(field), str) or not event.get(field, "").strip():
            errors.append(f"{field} must be non-empty")
    if not isinstance(event.get("event_type"), str) or not EVENT_TYPE_RE.fullmatch(event.get("event_type", "")):
        errors.append("event_type has invalid format")
    if not isinstance(event.get("payload"), dict):
        errors.append("payload must be an object")
    secret_path = _contains_secret(event.get("payload"))
    if secret_path:
        errors.append(f"secret-like payload field: {secret_path}")
    if event.get("prev_hash") != previous_hash:
        errors.append("prev_hash does not match previous event")
    stored_hash = event.get("hash")
    if not isinstance(stored_hash, str) or not HEX_HASH_RE.fullmatch(stored_hash):
        errors.append("hash must be a lowercase SHA-256 hex digest")
    elif stored_hash != event_hash(event):
        errors.append("event hash mismatch")
    return errors


def validate_log(
    path: str | Path,
    *,
    allow_missing: bool = False,
    anchor_path: str | Path | None = None,
    expected_last_hash: str | None = None,
    expected_events: int | None = None,
) -> dict[str, Any]:
    """Validate every line and return a machine-readable report."""
    target = Path(path)
    anchor_target = Path(anchor_path) if anchor_path is not None else None
    anchored = anchor_target is not None or expected_last_hash is not None or expected_events is not None
    unsafe_paths = []
    if target.is_symlink():
        unsafe_paths.append("event log path must not be a symlink")
    if anchor_target is not None and anchor_target.is_symlink():
        unsafe_paths.append("event log anchor path must not be a symlink")
    if unsafe_paths:
        return {
            "ok": False,
            "path": str(target),
            "events": 0,
            "last_hash": "",
            "anchored": anchored,
            **({"anchor_path": str(anchor_target)} if anchor_target is not None else {}),
            "errors": unsafe_paths,
        }
    if anchor_target is not None and anchor_target.resolve() == target.resolve():
        return {
            "ok": False,
            "path": str(target),
            "events": 0,
            "last_hash": "",
            "anchored": anchored,
            "anchor_path": str(anchor_target),
            "errors": ["event log anchor must be a separate path"],
        }
    log_exists = target.exists()
    anchor_exists = anchor_target.exists() if anchor_target is not None else False
    if not log_exists and not allow_missing:
        errors = ["event log does not exist"]
        if anchor_target is not None and anchor_exists:
            errors.append("event log anchor exists but event log is missing")
        return {
            "ok": False,
            "path": str(target),
            "events": 0,
            "last_hash": "",
            "anchored": anchored,
            **({"anchor_path": str(anchor_target)} if anchor_target is not None else {}),
            "errors": errors,
        }
    try:
        events = _read_raw(target)
    except EventLogError as exc:
        return {
            "ok": False,
            "path": str(target),
            "events": 0,
            "last_hash": "",
            "anchored": anchored,
            **({"anchor_path": str(anchor_target)} if anchor_target is not None else {}),
            "errors": [str(exc)],
        }
    errors: list[str] = []
    anchor: dict[str, Any] | None = None
    if anchor_target is not None:
        if log_exists and not anchor_exists:
            errors.append("event log exists but anchor is missing")
        elif anchor_exists and not log_exists:
            errors.append("event log anchor exists but event log is missing")
            try:
                _read_anchor(
                    anchor_target,
                    expected_log_identity=log_identity(target),
                )
            except EventLogError as exc:
                errors.append(str(exc))
        elif anchor_exists:
            try:
                anchor = _read_anchor(
                    anchor_target,
                    expected_log_identity=log_identity(target),
                )
            except EventLogError as exc:
                errors.append(str(exc))
    previous = ""
    known_ids: set[str] = set()
    for sequence, event in enumerate(events, start=1):
        event_errors = validate_event(event, previous_hash=previous, expected_sequence=sequence, known_ids=known_ids)
        errors.extend(f"event {sequence}: {error}" for error in event_errors)
        if not event_errors:
            previous = str(event["hash"])
            known_ids.add(str(event["event_id"]))
        else:
            # Continue checking later entries against the last trustworthy
            # hash, so the report identifies all corruption in one pass.
            if isinstance(event.get("hash"), str) and HEX_HASH_RE.fullmatch(event["hash"]):
                previous = str(event["hash"])
    if expected_events is not None and len(events) != expected_events:
        errors.append(
            f"event count does not match anchor: expected {expected_events}, got {len(events)}"
        )
    if expected_last_hash is not None and previous != expected_last_hash:
        errors.append("last hash does not match anchor")
    if anchor is not None:
        if len(events) != anchor["events"]:
            errors.append(
                f"event count does not match anchor: expected {anchor['events']}, got {len(events)}"
            )
        if previous != anchor["last_hash"]:
            errors.append("last hash does not match anchor")
    return {
        "ok": not errors,
        "path": str(target),
        "events": len(events),
        "last_hash": previous,
        "anchored": anchored,
        **({"anchor_path": str(anchor_target), "anchor": anchor} if anchor_target is not None else {}),
        "errors": errors,
    }


def _new_event(
    *,
    sequence: int,
    previous_hash: str,
    contract_id: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any] | None,
    timestamp: str | None,
) -> dict[str, Any]:
    if not isinstance(contract_id, str) or not contract_id.strip():
        raise EventLogError("contract_id must be non-empty")
    if not isinstance(actor, str) or not actor.strip():
        raise EventLogError("actor must be non-empty")
    if not isinstance(event_type, str) or not EVENT_TYPE_RE.fullmatch(event_type):
        raise EventLogError("event_type has invalid format")
    if payload is not None and not isinstance(payload, Mapping):
        raise EventLogError("event payload must be an object")
    body = dict(payload or {})
    if _contains_secret(body):
        raise EventLogError("event payload contains secret-like data")
    event = {
        "version": EVENT_VERSION,
        "sequence": sequence,
        "event_id": str(uuid.uuid4()),
        "timestamp": _timestamp(timestamp),
        "contract_id": contract_id,
        "event_type": event_type,
        "actor": actor,
        "payload": body,
        "prev_hash": previous_hash,
    }
    try:
        event["hash"] = event_hash(event)
    except (TypeError, ValueError) as exc:
        raise EventLogError("event payload must be JSON serializable") from exc
    return event


def append_event(
    path: str | Path,
    event: Mapping[str, Any] | None = None,
    *,
    contract_id: str | None = None,
    event_type: str | None = None,
    actor: str | None = None,
    payload: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
    anchor_path: str | Path | None = None,
    expected_last_hash: str | None = None,
) -> dict[str, Any]:
    """Validate and append exactly one event, returning the stored object.

    A complete event mapping may be passed for convenience, but generated
    sequence/hash/id fields are always recomputed.  Caller-supplied ``hash`` or
    chain fields are rejected rather than silently trusted.
    """
    if event is not None:
        if not isinstance(event, Mapping):
            raise EventLogError("event must be an object")
        forbidden = {"version", "sequence", "event_id", "prev_hash", "hash"}.intersection(event)
        if forbidden:
            raise EventLogError("caller cannot supply chain fields: " + ", ".join(sorted(forbidden)))
        contract_id = event.get("contract_id", contract_id)
        event_type = event.get("event_type", event_type)
        actor = event.get("actor", actor)
        payload = event.get("payload", payload)
        timestamp = event.get("timestamp", timestamp)
    target = Path(path)
    anchor_target = Path(anchor_path) if anchor_path is not None else None
    if target.is_symlink() or (anchor_target is not None and anchor_target.is_symlink()):
        raise EventLogError("event log and anchor paths must not be symlinks")
    lock_targets = [target]
    if anchor_target is not None:
        lock_targets.append(anchor_target)
    with _exclusive_locks(*lock_targets):
        report = validate_log(
            target,
            allow_missing=True,
            anchor_path=anchor_target,
            expected_last_hash=expected_last_hash,
        )
        if not report["ok"]:
            raise EventLogError("cannot append to invalid event log: " + "; ".join(report["errors"]))
        existing = _read_raw(target)
        stored = _new_event(
            sequence=len(existing) + 1,
            previous_hash=existing[-1]["hash"] if existing else "",
            contract_id=contract_id or "",
            event_type=event_type or "",
            actor=actor or "",
            payload=payload,
            timestamp=timestamp,
        )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(stored, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
                handle.flush()
                # Ensure a successful return means the append reached the OS.
                os.fsync(handle.fileno())
            _fsync_parent(target)
        except OSError as exc:
            raise EventLogError(f"cannot append event log: {exc}") from exc
        if anchor_target is not None:
            _write_anchor_atomically(
                anchor_target,
                bound_log_identity=log_identity(target),
                events=stored["sequence"],
                last_hash=stored["hash"],
            )
        return stored


verify_log = validate_log
append_audit_event = append_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or append a V4.2 runtime event log.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.add_argument("--anchor-path", type=Path)
    validate_parser.add_argument("--expected-last-hash")
    validate_parser.add_argument("--expected-events", type=int)
    append_parser = subparsers.add_parser("append")
    append_parser.add_argument("path", type=Path)
    append_parser.add_argument("--contract-id", required=True)
    append_parser.add_argument("--event-type", required=True)
    append_parser.add_argument("--actor", required=True)
    append_parser.add_argument("--payload-json", default="{}")
    append_parser.add_argument("--timestamp")
    append_parser.add_argument("--anchor-path", type=Path)
    append_parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_log(
                args.path,
                anchor_path=args.anchor_path,
                expected_last_hash=args.expected_last_hash,
                expected_events=args.expected_events,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
            return 0 if report["ok"] else 1
        try:
            payload = json.loads(args.payload_json)
        except json.JSONDecodeError as exc:
            raise EventLogError(f"payload JSON is invalid: {exc}") from exc
        if not isinstance(payload, dict):
            raise EventLogError("payload JSON must be an object")
        stored = append_event(
            args.path,
            contract_id=args.contract_id,
            event_type=args.event_type,
            actor=args.actor,
            payload=payload,
            timestamp=args.timestamp,
            anchor_path=args.anchor_path,
        )
        print(json.dumps(stored, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
        return 0
    except EventLogError as exc:
        print(f"event log error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
