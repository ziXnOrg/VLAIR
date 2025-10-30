# TestGenAgent Prompts and Guardrails

Purpose
- Deterministic test generation with coverage-oriented templates and key edge cases.
- Produce edits as a delta: prefer full-file content for generated tests in Phase 2.

Determinism
- Temperature: 0 (no sampling); fixed seeds when applicable; avoid wall-clock or environment-dependent data.
- Stable formatting and imports; adhere to project standards (ruff/black for Python).

Templates (Phase 2 baseline)
- Python tests (pytest style):
  - Smoke import: ensure module imports successfully.
  - Existence checks: functions/classes exist.
  - Edge-case stubs: skeletons for boundary inputs without executing external I/O.

Output contract
- AgentResult.payload.delta.doc:
  - path: string (e.g., "test_<module>.py")
  - content: string (complete test file contents)
- Future phases may add artifacts (coverage hints) and unified diffs when originals are known.

Security/Privacy
- Do not embed secrets/PII. Rely on redaction hooks for logs/artifacts.
- Avoid executing network or filesystem operations in generated tests.

