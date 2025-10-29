import os
from orchestrator.wal.replay import record_cancellation, rollback_to_snapshot


def test_deterministic_cancellation(tmp_path):
    wal_dir = tmp_path
    run_id = "run123"

    # Record a cancellation deterministically
    ev_cancel = record_cancellation(run_id, reason="timeout", wal_dir=str(wal_dir), ts_ms=1234567890, seq=1)
    assert ev_cancel["type"] == "task_cancelled"
    assert ev_cancel["payload"]["reason"] == "timeout"
    assert ev_cancel["ts"] == 1234567890
    assert ev_cancel["seq"] == 1

    # Prepare a snapshot and current state
    current = {"inflight": {"t1": "running", "t2": "running"}}
    snapshot = {"inflight": {"t1": "queued"}}

    new_state, ev_rb = rollback_to_snapshot(current, snapshot, run_id=run_id, cancelled_tasks=["t1", "t2"], wal_dir=str(wal_dir), ts_ms=1234567891, seq=2)
    # State restored deterministically to snapshot
    assert new_state == snapshot and new_state is not snapshot  # deep copy
    # WAL event recorded with deterministic fields
    assert ev_rb["type"] == "rollback"
    assert ev_rb["seq"] == 2 and ev_rb["ts"] == 1234567891
    assert ev_rb["payload"]["cancelled"] == ["t1", "t2"]

    # Ensure WAL file exists and contains two lines
    p = tmp_path / f"{run_id}.jsonl"
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2

