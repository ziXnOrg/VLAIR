from __future__ import annotations

from typing import Any, Dict

# Canonical keys for WAL events. We keep the schema minimal and stable.
# All events are single-line JSON records.
# {
#   "run_id": str,
#   "type": str,                 # e.g., "task_submitted", "task_completed", "task_cancelled", "snapshot_created", "rollback"
#   "seq": int,                  # strictly increasing per-run sequence number (1-based)
#   "ts": int,                   # unix epoch milliseconds
#   "payload": dict              # arbitrary JSON-safe payload (low-cardinality fields preferred)
# }

Event = Dict[str, Any]


def canonicalize_event(event: Event) -> Event:
    """Return an event with only canonical keys (defensive copy).

    Unknown keys are preserved to avoid data loss but downstream code should rely
    only on the canonical keys defined above. This keeps replay tolerant to
    non-breaking additions.
    """
    return {
        "run_id": event.get("run_id"),
        "type": event.get("type"),
        "seq": int(event.get("seq", 0) or 0),
        "ts": int(event.get("ts", 0) or 0),
        "payload": event.get("payload", {}),
        **{k: v for k, v in event.items() if k not in {"run_id", "type", "seq", "ts", "payload"}},
    }

