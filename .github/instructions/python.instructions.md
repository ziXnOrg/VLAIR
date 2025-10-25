---
applyTo: "**/*.py"
---

Python‑specific Copilot review guidance for VLTAIR:

- Typing and errors: enforce strong typing; explicit error returns (no silent failures); structured JSON errors include traceId; do not log secrets.
- Determinism: set PYTHONHASHSEED=0 in tests; avoid non‑deterministic sources (random/time/thread‑unsafe globals). Use fixed seeds and stable ordering for algorithms and CLI outputs.
- Tests: prefer extending tests under tests/unit; ensure failure‑path coverage; coverage ≥85% overall; platform‑gate OS features (skip cleanly if unsupported). For CLIs, prefer subprocess tests for argparse with deterministic exit codes (0 success, 1 error).
- Dependencies: avoid adding new runtime dependencies unless strictly necessary and approved.
- Security: validate inputs and bounds; respect redaction/RLS; flag risky OS calls or sandbox bypass potential.

