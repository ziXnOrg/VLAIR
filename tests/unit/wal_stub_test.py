from __future__ import annotations

import time
from pathlib import Path
from typing import List

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.wal.replay import load_events


def _wait_for_events(run_id: str, *, wal_dir: str, at_least: int, timeout_s: float = 2.0) -> List[dict]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        evs = load_events(run_id, wal_dir=wal_dir)
        if len(evs) >= at_least:
            return evs
        time.sleep(0.05)
    return load_events(run_id, wal_dir=wal_dir)


def test_wal_append_sequence(tmp_path: Path) -> None:
    wal_dir = str(tmp_path)
    run_id = "run-wal-stub-1"
    orch = Orchestrator(run_id=run_id, wal_dir=wal_dir)
    task = {
        "type": "AgentTask",
        "id": "t-1",
        "agent": "TestAgent",
        "payload": {"mode": "generate", "target": "foo"},
    }
    r = orch.submit_task(task)
    assert r["accepted"] is True

    evs = _wait_for_events(run_id, wal_dir=wal_dir, at_least=4)
    types = [e.get("type") for e in evs]
    assert types[:2] == ["task.accepted", "task.started"]
    assert "result.applied" in types
    assert types[-1] == "task.completed"


def test_snapshot_deterministic(tmp_path: Path) -> None:
    wal_dir = str(tmp_path)
    orch = Orchestrator(run_id="snap-1", wal_dir=wal_dir)
    snap1 = orch.snapshot(ts_ms=1234567890123)
    snap2 = orch.snapshot(ts_ms=1234567890123)
    assert snap1 == snap2
    assert snap1["state"]["results"]["applied_count"] == 0


def test_cancel_emits_cancelled(tmp_path: Path) -> None:
    wal_dir = str(tmp_path)
    run_id = "run-cancel-1"
    orch = Orchestrator(run_id=run_id, wal_dir=wal_dir)
    # Unknown agent will cause routing error -> cancellation emitted
    task = {"type": "AgentTask", "id": "t-x", "agent": "NoSuch", "payload": {}}
    try:
        orch.submit_task(task)
    except Exception:
        pass
    evs = _wait_for_events(run_id, wal_dir=wal_dir, at_least=1)
    assert any(e.get("type") == "task.accepted" for e in evs)
    # start may not occur if routing fails before handler, but cancel should
    assert any(e.get("type") == "task.cancelled" for e in evs)

