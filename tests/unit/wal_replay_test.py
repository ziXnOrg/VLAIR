import os
import json
from orchestrator.wal.replay import load_events, replay_run


def test_replay_determinism(tmp_path):
    wal_dir = tmp_path
    # Prepare mixed WAL files for two runs
    r1 = wal_dir / "r1.jsonl"
    r2 = wal_dir / "r2.jsonl"
    r1.write_text("\n".join([
        json.dumps({"run_id": "r1", "type": "task_submitted", "seq": 1, "ts": 1000, "payload": {}}),
        json.dumps({"run_id": "r1", "type": "task_completed", "seq": 2, "ts": 2000, "payload": {"ok": True}}),
        "",
    ]), encoding="utf-8")
    r2.write_text(json.dumps({"run_id": "r2", "type": "noop", "seq": 1, "ts": 1500, "payload": {}}) + "\n", encoding="utf-8")

    evs = load_events("r1", wal_dir=str(wal_dir))
    assert [e["seq"] for e in evs] == [1, 2]

    out1 = replay_run("r1", wal_dir=str(wal_dir))
    out2 = replay_run("r1", wal_dir=str(wal_dir))
    assert out1["ok"] and out2["ok"]
    assert out1["count"] == 2 and out2["count"] == 2
    # Deterministic ordering and content
    assert out1["events"] == out2["events"]

