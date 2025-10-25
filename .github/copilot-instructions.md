VLTAIR Copilot Code Review Instructions

When reviewing pull requests in this repository, enforce these project non‑negotiables and review style:

- Determinism & reproducibility: temperature=0, fixed seeds (e.g., PYTHONHASHSEED=0), stable ordering, idempotency keys; no hidden wall‑clock or randomness on core paths.
- Quality gates: zero warnings (linters/static analysis treated as errors); tests green; coverage ≥85% overall (higher for core orchestrator/scheduling); ≤5% perf regression; document environment, seeds, and artifacts when claiming performance.
- Security & reliability: strict input validation/bounds; explicit error handling (no silent failures); structured logs/traces without secrets; redaction/RLS honored; least privilege for OS calls and tool invocations; flag sandbox bypass risks.
- Acceptance‑first: map changes to acceptance criteria and tests; verify failure‑path tests are present; prefer extending existing tests in tests/unit; platform‑gate OS features and skip cleanly on unsupported runners.
- Python (general): strong typing; explicit error returns; deterministic prompts/seeds; CLI: deterministic outputs, exit code 0 on success/1 on error, JSON errors include traceId.
- C++ (Vesper): RAII; no exceptions on hot paths; use status/std::expected; conform to .clang-format/.clang-tidy; document complexity for public APIs; deterministic algorithms and stable orders; avoid needless allocations on hot paths.
- Performance: respect budgets; reference or attach bench artifacts; call out potential >5% regressions with a minimal mitigation plan.
- Review style: be specific and actionable; propose minimal suggested changes; explain why; prioritize correctness, security, determinism, and perf before style.
- Outcome summary: if any gates are unmet, summarize violations with a minimal fix plan; otherwise post a concise “Gates OK” noting security, determinism, tests/coverage, perf, and static analysis.

