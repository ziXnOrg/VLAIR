# ADR: OC-12 — WAL Append/Snapshot Integration with Orchestrator Lifecycle

Date: 2025-10-30
Status: Proposed
Decision: Integrate a minimal, deterministic Write-Ahead Log (WAL) for orchestrator lifecycle events and add a snapshot() stub.

## Context
VLTAIR aims for deterministic, event-sourced orchestration. OC-12 wires a thin WAL layer that captures the orchestrator lifecycle and provides a stable foundation for replay/rollback (OC-14/OC-17) and end-to-end debugging (XB-2).

## Decision
- Add orchestrator.wal.{writer,events,replay} with JSONL WAL supporting stable serialization and basic replay helpers
- Emit WAL at 5 points using dotted event names:
  - task.accepted, task.started, result.applied, task.completed, task.cancelled
- Add Orchestrator.snapshot(ts_ms) stub returning minimal counters in a stable structure
- WAL I/O is fail-open (never crashes orchestrator); orchestrator logic remains fail-closed

## Event Schema
```
{
  "run_id": "<str>",
  "type": "<str>",            // dotted name
  "seq": <int>,                 // 1-based, monotonic per run
  "ts": <int>,                  // epoch ms
  "payload": { ... }            // event-specific
}
```

## Append Points
- submit_task(): task.accepted after enqueue (includes traceId)
- _handle_scheduled(): task.started before handler; result.applied after apply; task.completed at end
- _handle_scheduled() exception path: task.cancelled with reason

## Snapshot Stub
```
{"run_id": str, "seq": int, "ts": int, "state": {"tasks": {"queued": int}, "results": {"applied_count": int}, "context_version": 0}}
```

## Replay Helpers
- writer.wal_path(run_id, wal_dir) -> file path
- writer.append_event(...) -> Event
- replay.load_events(run_id, wal_dir) -> List[Event] ordered by (seq, ts)
- replay.record_cancellation(...) convenience using type=task.cancelled

## Alternatives Considered
- Persist snapshots every N events: defer; document only
- Use SQLite/Parquet instead of JSONL: defer; JSONL is simplest and deterministic for now

## Consequences
- Enables deterministic WAL-based inspection and sets the stage for idempotent replay and rollback
- Adds minimal surface area (no external dependencies)
- Backwards-compatible: WAL is optional and fail-open

## Validation
- tests/unit/wal_stub_test.py exercises sequence and snapshot determinism
- Stable JSON serialization: separators=(",", ":"), sort_keys=True

## Future Work
- OC-15 Idempotency journal integration
- BM-1/BM-6 budget WAL extensions
- CE-12 time-travel via WAL
- Snapshot persistence to <wal_dir>/<run_id>.snapshot.jsonl every N events

