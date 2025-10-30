from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from .events import Event, canonicalize_event


def wal_path(run_id: str, wal_dir: Optional[str] = None) -> str:
    d = wal_dir or os.environ.get("VLTAIR_WAL_DIR") or os.path.join(os.getcwd(), "wal")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{run_id}.jsonl")


def _read_last_seq(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as f:
            last = None
            for line in f:
                line = line.strip()
                if not line:
                    continue
                last = line
            if not last:
                return 0
            ev = json.loads(last)
            return int(ev.get("seq", 0) or 0)
    except FileNotFoundError:
        return 0
    except Exception:
        return 0


def append_event(
    run_id: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    wal_dir: Optional[str] = None,
    ts_ms: Optional[int] = None,
    seq: Optional[int] = None,
) -> Event:
    path = wal_path(run_id, wal_dir)
    if ts_ms is None:
        ts_ms = int(time.time() * 1000)
    if seq is None:
        seq = _read_last_seq(path) + 1
    record: Dict[str, Any] = {
        "run_id": str(run_id),
        "type": str(event_type),
        "seq": int(seq),
        "ts": int(ts_ms),
        "payload": payload if isinstance(payload, dict) else {},
    }
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(data + "\n")
    return canonicalize_event(record)

