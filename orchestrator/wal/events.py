from __future__ import annotations

from typing import Any, Dict, TypedDict


class Event(TypedDict, total=False):
    run_id: str
    type: str
    seq: int
    ts: int
    payload: Dict[str, Any]


def canonicalize_event(event: Dict[str, Any]) -> Event:
    rid = str(event.get("run_id", ""))
    et = str(event.get("type", ""))
    payload = event.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    seq_val = event.get("seq")
    ts_val = event.get("ts")
    try:
        seq = int(seq_val) if seq_val is not None else 0
    except Exception:
        seq = 0
    try:
        ts = int(ts_val) if ts_val is not None else 0
    except Exception:
        ts = 0
    return Event(run_id=rid, type=et, seq=seq, ts=ts, payload=payload)
