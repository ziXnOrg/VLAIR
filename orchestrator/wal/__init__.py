"""WAL package for event recording and deterministic replay.

Lightweight JSONL-based WAL utilities (no external deps), used by tests and
optionally by the CLI. The orchestrator can integrate with these helpers to
record events and enable replay.
"""

