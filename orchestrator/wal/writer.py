from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from .events import Event, canonicalize_event


def _default_wal_dir() -> str:
    return os.environ.get("VLTAIR_WAL_DIR", os.path.join(os.getcwd(), "wal"))


def wal_path(run_id: str, wal_dir: Optional[str] = None) -> str:
    d = wal_dir or _default_wal_dir()
    return os.path.join(d, f"{run_id}.jsonl")


def _next_seq(path: str) -> int:
    try:
        n = 0
        with open(path, "r", encoding="utf-8") as f:
            for n, _ in enumerate(f, start=1):
                pass
        return n + 1
    except FileNotFoundError:
        return 1
    except Exception:
        # On any unexpected error, fall back to 1 to avoid crashing production paths.
        return 1


def append_event(
    run_id: str,
    event_type: str,
    payload: Dict[str, Any] | None = None,
    *,
    wal_dir: Optional[str] = None,
    ts_ms: Optional[int] = None,
    seq: Optional[int] = None,
) -> Event:
    """Append a single JSONL event to the WAL.

    Deterministic/defensive behaviors:
    - Creates the WAL directory if missing.
    - Computes `seq` as last_line+1 if not provided.
    - Uses integer milliseconds; `ts_ms` can be injected in tests.
    - Writes using json.dumps(sort_keys=True, separators=(",", ":")) for stable bytes.
    """
    d = wal_dir or _default_wal_dir()
    os.makedirs(d, exist_ok=True)
    path = wal_path(run_id, d)
    ev: Event = {
        "run_id": str(run_id),
        "type": str(event_type),
        "seq": int(seq if seq is not None else _next_seq(path)),
        "ts": int(ts_ms if ts_ms is not None else int(time.time() * 1000)),
        "payload": dict(payload or {}),
    }
    ev = canonicalize_event(ev)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
    return ev

