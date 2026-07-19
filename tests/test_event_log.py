import json
import multiprocessing
from pathlib import Path

import pytest

from scripts.event_log import EventLogError, append_event, event_hash, log_identity, main, validate_log


def _append_many(log_path: str, anchor_path: str, worker: int, count: int) -> None:
    for index in range(count):
        append_event(
            log_path,
            anchor_path=anchor_path,
            contract_id="c-1",
            event_type="task.routed",
            actor=f"worker-{worker}",
            payload={"worker": worker, "index": index},
        )


def test_append_creates_hash_chain(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    first = append_event(path, contract_id="c-1", event_type="task.routed", actor="router", payload={"lane": "fast"})
    second = append_event(path, contract_id="c-1", event_type="action.denied", actor="policy", payload={"reason": "no approval"})
    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["prev_hash"] == first["hash"]
    assert second["hash"] == event_hash({key: value for key, value in second.items() if key != "hash"})
    report = validate_log(path)
    assert report["ok"] is True
    assert report["events"] == 2


def test_tampering_blocks_validation_and_future_append(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    append_event(path, contract_id="c-1", event_type="task.routed", actor="router", payload={})
    line = json.loads(path.read_text(encoding="utf-8"))
    line["payload"]["lane"] = "governed"
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    report = validate_log(path)
    assert report["ok"] is False
    with pytest.raises(EventLogError, match="invalid event log"):
        append_event(path, contract_id="c-1", event_type="task.closed", actor="router", payload={})


def test_secret_like_payload_is_rejected(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    with pytest.raises(EventLogError, match="secret"):
        append_event(path, contract_id="c-1", event_type="credential.used", actor="policy", payload={"token": "do-not-log"})
    with pytest.raises(EventLogError, match="secret"):
        append_event(path, contract_id="c-1", event_type="credential.used", actor="policy", payload={"value": "ghp_123456789012345678901234"})


def test_append_rejects_caller_chain_fields(tmp_path: Path):
    with pytest.raises(EventLogError, match="chain fields"):
        append_event(
            tmp_path / "events.jsonl",
            {"contract_id": "c-1", "event_type": "task.routed", "actor": "router", "hash": "fake"},
        )


def test_invalid_timestamp_and_blank_lines_fail_closed(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    with pytest.raises(EventLogError, match="ISO-8601"):
        append_event(path, contract_id="c-1", event_type="task.routed", actor="router", timestamp="tomorrow")
    path.write_text("\n", encoding="utf-8")
    assert validate_log(path)["ok"] is False


def test_missing_log_and_tail_truncation_fail_when_anchored(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    assert validate_log(path)["ok"] is False
    append_event(path, contract_id="c-1", event_type="task.routed", actor="router", payload={})
    second = append_event(path, contract_id="c-1", event_type="task.closed", actor="router", payload={})
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n", encoding="utf-8")
    report = validate_log(
        path,
        expected_last_hash=second["hash"],
        expected_events=2,
    )
    assert report["ok"] is False
    assert report["anchored"] is True
    assert any("anchor" in error for error in report["errors"])


def test_anchor_pair_detects_missing_side_and_tail_truncation(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    first = append_event(
        path,
        anchor_path=anchor,
        contract_id="c-1",
        event_type="task.routed",
        actor="router",
        payload={},
    )
    second = append_event(
        path,
        anchor_path=anchor,
        contract_id="c-1",
        event_type="task.closed",
        actor="router",
        payload={},
    )
    assert validate_log(path, anchor_path=anchor)["anchor"] == {
        "version": 2,
        "log_identity": log_identity(path),
        "events": 2,
        "last_hash": second["hash"],
    }
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[0] + "\n", encoding="utf-8")
    report = validate_log(path, anchor_path=anchor)
    assert report["ok"] is False
    assert any("anchor" in error for error in report["errors"])
    with pytest.raises(EventLogError, match="invalid event log"):
        append_event(
            path,
            anchor_path=anchor,
            contract_id="c-1",
            event_type="task.closed",
            actor="router",
            payload={},
        )
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    anchor.unlink()
    report = validate_log(path, anchor_path=anchor)
    assert report["ok"] is False
    assert "event log exists but anchor is missing" in report["errors"]
    anchor.write_text(
        json.dumps({
            "version": 2,
            "log_identity": log_identity(path),
            "events": 1,
            "last_hash": first["hash"],
        }),
        encoding="utf-8",
    )
    path.unlink()
    report = validate_log(path, anchor_path=anchor)
    assert report["ok"] is False
    assert "event log anchor exists but event log is missing" in report["errors"]


def test_concurrent_anchor_appends_produce_one_contiguous_chain(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    context = multiprocessing.get_context("spawn")
    workers = [
        context.Process(target=_append_many, args=(str(path), str(anchor), worker, 6))
        for worker in range(4)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
        assert worker.exitcode == 0
    report = validate_log(path, anchor_path=anchor)
    assert report["ok"] is True
    assert report["events"] == 24
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [event["sequence"] for event in events] == list(range(1, 25))
    assert [event["prev_hash"] for event in events[1:]] == [event["hash"] for event in events[:-1]]


def test_symlink_aliases_cannot_bypass_event_log_locking(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    append_event(
        path,
        anchor_path=anchor,
        contract_id="c-1",
        event_type="task.routed",
        actor="router",
        payload={},
    )
    log_alias = tmp_path / "events-alias.jsonl"
    anchor_alias = tmp_path / "anchor-alias.json"
    try:
        log_alias.symlink_to(path)
        anchor_alias.symlink_to(anchor)
    except OSError as exc:  # pragma: no cover - platform policy may forbid symlinks
        pytest.skip(f"symlinks unavailable: {exc}")

    assert validate_log(log_alias, anchor_path=anchor)["ok"] is False
    assert validate_log(path, anchor_path=anchor_alias)["ok"] is False
    with pytest.raises(EventLogError, match="must not be symlinks"):
        append_event(
            log_alias,
            anchor_path=anchor,
            contract_id="c-1",
            event_type="task.closed",
            actor="router",
            payload={},
        )


def test_anchor_is_bound_to_one_canonical_log(tmp_path: Path):
    first_log = tmp_path / "first.jsonl"
    second_log = tmp_path / "second.jsonl"
    anchor = tmp_path / "shared.anchor.json"
    append_event(
        first_log,
        anchor_path=anchor,
        contract_id="c-1",
        event_type="task.routed",
        actor="router",
        payload={},
    )

    with pytest.raises(EventLogError, match="different event log"):
        append_event(
            second_log,
            anchor_path=anchor,
            contract_id="c-2",
            event_type="task.routed",
            actor="router",
            payload={},
        )
    assert not second_log.exists()
    assert validate_log(first_log, anchor_path=anchor)["ok"] is True


def test_event_log_cli(tmp_path: Path, capsys):
    path = tmp_path / "events.jsonl"
    anchor = tmp_path / "events.anchor.json"
    assert main(["append", str(path), "--anchor-path", str(anchor), "--contract-id", "c-1", "--event-type", "task.routed", "--actor", "router", "--json"]) == 0
    capsys.readouterr()
    assert main(["validate", str(path), "--anchor-path", str(anchor), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
