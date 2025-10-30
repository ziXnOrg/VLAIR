from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from .writer import wal_path, append_event
from .events import Event


def load_events(run_id: str, *, wal_dir: Optional[str] = None) -> List[Event]:
    path = wal_path(run_id, wal_dir)
    out: List[Event] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev: Dict[str, Any] = json.loads(line)
                    out.append(ev)  # type: ignore[arg-type]
                except Exception:
                    # skip malformed
                    continue
    except FileNotFoundError:
        return []
    # Canonical replay order by (seq, ts)
    out.sort(key=lambda e: (int(e.get("seq", 0) or 0), int(e.get("ts", 0) or 0)))
    return out


def record_cancellation(
    run_id: str,
    reason: str,
    *,
    wal_dir: Optional[str] = None,
    ts_ms: Optional[int] = None,
    seq: Optional[int] = None,
) -> Event:
    return append_event(run_id, "task.cancelled", {"reason": str(reason)}, wal_dir=wal_dir, ts_ms=ts_ms, seq=seq)

