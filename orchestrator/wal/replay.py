from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .events import Event, canonicalize_event
from .writer import wal_path, append_event


def _read_jsonl(path: str) -> List[Event]:
    events: List[Event] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                except Exception:
                    # Skip malformed lines deterministically
                    continue
                events.append(canonicalize_event(obj))
    except FileNotFoundError:
        return []
    return events


def load_events(run_id: str, wal_dir: Optional[str] = None) -> List[Event]:
    path = wal_path(run_id, wal_dir)
    evs = _read_jsonl(path)
    # Stable ordering: first by seq, then by ts as tiebreaker
    evs.sort(key=lambda e: (int(e.get("seq", 0) or 0), int(e.get("ts", 0) or 0)))
    return evs


def replay_run(run_id: str, wal_dir: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic replay that returns recorded outputs only (no external calls).

    For now, we return the ordered list of events to validate determinism. A fuller
    replay would route events to reducers and rebuild outputs/state.
    """
    evs = load_events(run_id, wal_dir)
    return {"ok": True, "run_id": run_id, "count": len(evs), "events": evs}


# ---- Cancellation and rollback helpers (deterministic semantics) ----

def record_cancellation(run_id: str, reason: str, *, wal_dir: Optional[str] = None, ts_ms: Optional[int] = None, seq: Optional[int] = None) -> Event:
    return append_event(run_id, "task_cancelled", {"reason": str(reason)}, wal_dir=wal_dir, ts_ms=ts_ms, seq=seq)


def rollback_to_snapshot(current_state: Dict[str, Any], snapshot_state: Dict[str, Any], *, run_id: str, cancelled_tasks: Optional[List[str]] = None, wal_dir: Optional[str] = None, ts_ms: Optional[int] = None, seq: Optional[int] = None) -> Tuple[Dict[str, Any], Event]:
    """Return a restored copy of snapshot_state and record a rollback event.

    - `cancelled_tasks` list, if provided, is recorded in the WAL event payload.
    - The function is pure w.r.t. returned state (does not mutate inputs).
    """
    new_state = json.loads(json.dumps(snapshot_state))  # deep copy via JSON for determinism
    payload = {"cancelled": list(cancelled_tasks or [])}
    ev = append_event(run_id, "rollback", payload, wal_dir=wal_dir, ts_ms=ts_ms, seq=seq)
    return new_state, ev

