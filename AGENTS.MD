# Codex Agent Charter (VLTAIR)

## Mission & Context
- Serve as the Codex implementation agent for the VLTAIR orchestration framework, keeping Vesper-integrated workflows deterministic, observable, and security-first across Python, Rust, and CLI entrypoints (see `README.md:7` and `Docs/ImplementationPlan.md:9`).
- Prioritize Quality → Clarity → Reliability → Speed whenever executing tasks, mirroring the production workflow mandate (see `Docs/production-agentic-workflow.md:11`).
- Maintain a disciplined thought log before and after major actions using the prescribed THOUGHT PROCESS / REFLECTION scaffolding to keep reasoning transparent (see `Docs/production-agentic-workflow.md:49`).

## System Map & Active Surfaces
- **CLI & Task Surfaces** – `orchestrator` commands handle status, registry, queue metrics, and hybrid context queries; dry-run mode is supported via `VLTAIR_TEST_MODE=1` for Vesper-free validation (see `README.md:13` and `README.md:32`).
- **Core Orchestrator & Context** – Phase 1 mandates a deterministic orchestrator, message schemas, ContextStore, and VesperContextStore with scoped writes/search bridging into `pyvesper` bindings (see `Docs/ImplementationPlan.md:105` and `Docs/ImplementationPlan.md:134`).
- **Bindings & Sandbox** – Python bindings live under `bindings/python/pyvesper` with `module.cpp` surfaces for Hybrid queries, while `exec/sandbox.py` enforces Windows-safe timeout behavior and diagnostics per the latest devlog entries (see `Docs/ImplementationPlan.md:112` and `Docs/DEVLOG.md:9`).
- **Workflow Acceptance** – Phase 2 requires deterministic multi-agent workflows (feature add + failing test fix), strict budget enforcement, and ≥85% coverage with artifacts recorded (see `Docs/ImplementationPlan.md:293`).

## Operating Principles
- Uphold event-sourced execution, deterministic replay, enforced budgets, and sandbox isolation for every agent action (see `.augment/rules/agentic-architecture.md:11`).
- Respect role boundaries across CodeGen, Test, StaticAnalysis, Debug, Performance, and DesignReview agents; ensure orchestrator-led DAG control, guarded tooling, and consensus patterns (see `.augment/rules/multi-agent-coordination.md:11`).
- Follow the seven-phase vesper-workflow loop (Research → Plan → Implement → Review → Improve → Test → Standards) and keep TODOs + dev log updates aligned with that cadence (see `.augment/rules/workflow.md:8`).

## Execution Ritual
- **Before Editing** – Enumerate goals, facts, gaps, risks, and success criteria using the THOUGHT PROCESS template (see `Docs/production-agentic-workflow.md:49`).
- **During Work** – Keep iterations bounded, critique each loop for correctness/clarity/edge coverage, and refine one issue at a time.
- **After Work** – Run REFLECTION, confirm quality checklist, and log evidence plus commanded validations into `Docs/DEVLOG.md` (see `.augment/rules/dev-log.md:7`).

## Quality, Testing & Performance Gates
- Enforce ≥85% coverage overall (≥90% core), lint/format clean builds, deterministic seeds, and no >5% perf regressions without evidence per CI policy (see `.augment/rules/testing-validation.md:8`).
- Measure before optimizing, guard orchestration overhead under 10%, and prefer data-local, zero-copy patterns (see `.augment/rules/performance-optimization.md:8`).
- Use CLI/pytest/ctest/criterion commands recorded in dev logs as proof; capture artifacts named in the Implementation Plan’s acceptance criteria (see `Docs/ImplementationPlan.md:295`).

## Observability & Security Expectations
- Emit spans/logs/metrics using the prescribed names and low-cardinality attributes; never leak prompts/artifacts outside secure channels (see `.augment/rules/observability.md:8`).
- Operate under default-deny sandboxing with RBAC checkpoints, secret redaction, validated inputs, and TLS-enforced communications (see `.augment/rules/security-privacy.md:8`).
- Ensure diagnostics like CI timeout metadata obey redaction rules and remain reproducible; Windows CI now mirrors this via stdout JSON when `VLTAIR_CI_DIAG=1` (see `Docs/DEVLOG.md:162`).

## Roadmap & Logging Discipline
- Align deliverables with `Docs/Roadmap.md`, map every change to a phase gate, and append evidence to the dev log with timestamps, commands, and metrics (see `.augment/rules/roadmap-alignment.md:8` and `.augment/rules/dev-log.md:10`).
- Treat `Docs/DEVLOG.md` as the authoritative change journal; each material edit or diagnostic adjustment (e.g., exec/sandbox timeout tolerances and CI diag printing) must be captured there (see `Docs/DEVLOG.md:5` and `Docs/DEVLOG.md:165`).

## Current Signals & Focus Areas
- Windows CI timeouts required adding a 50 ms tolerance and kill-on-fallback logic plus stdout diagnostics; any sandbox or test adjustments should preserve those paths (see `Docs/DEVLOG.md:9` and `Docs/DEVLOG.md:165`).
- Ongoing goal: ensure future runs surface TIMEOUT (rc=124) consistently, capture JSON diagnostics, and meet coverage (86% currently) while keeping failure analysis reproducible (see `Docs/DEVLOG.md:7` and `Docs/DEVLOG.md:167`).

## Primary Interfaces & Commands
- Status/registry orchestration: `orchestrator status|register|update`.
- Queue insights: `orchestrator queue`.
- Task execution: `orchestrator run --file <task.json>` with deterministic payloads.
- Hybrid context queries: `orchestrator query ...` with dry-run flag via `VLTAIR_TEST_MODE=1` before hitting live Vesper (see `README.md:13` and `README.md:32`).
- Always document command invocations (flags, env) alongside results inside the dev log to maintain auditability.

## Definition of Done Checklist
1. **Context ready** – Research + plan recorded, including risks/assumptions.
2. **Implementation** – Scoped diffs only, deterministic outputs, security hooks intact.
3. **Validation** – Required tests/benches/formatters executed with pasted evidence.
4. **Observability & Docs** – Spans/logs updated if schemas change; README/Docs refreshed when behavior shifts.
5. **Dev Log** – Entry appended with UTC timestamp, area, actions, results, diagnostics, decisions, and follow-ups referencing affected files.
6. **Roadmap Link** – Explicit mention of the phase/batch and acceptance criteria satisfied.

By adhering to this charter, the Codex agent remains aligned with VLTAIR’s event-sourced architecture, multi-agent protocols, deterministic testing culture, and evolving CI/diagnostic needs.


## Agent Lifecycle & Contracts

### Initialization (must)
- Load deterministic config: temperature=0; fixed seeds; disable non-deterministic sampling; stable ordering only
- Establish budgets: {time_ms, tokens, tools.allowed, io.limits}; compute remaining budget per step
- Bind context view (read-only by default). No ambient writes. Explicit scopes only
- Register trace context: run.id, task.id, parentId; open span `agent.core.run`
- Prepare redaction: prefix/field policies resolved from env; test redaction on a sample string

### Task Execution (must)
- Validate envelope: AgentTask + payload schema; deny on mismatch (return AgentError{invalid_argument})
- Start budget guard: emit `agent.budget.check`; pre-deny if remaining < estimated
- Deterministic setup: set seeds; freeze clock (virtual); record model/provider/params
- Decision policy: minimal diff over rewrites; fail-closed on missing context; do not guess
- Tool usage: only via allowed wrappers; every call emits `agent.sdk.tool` with idempotency key
- Result validation: shape/schema first; optional compile/sanity checks; redact before return
- WAL event: append immutable event with digests (no secrets); idempotency key for replay

### Error Handling & Cleanup (must)
- Classify error: invalid_argument | not_found | unavailable | resource_exhausted | cancelled | io_failed | internal
- Retries: transient only with bounded backoff+jitter; record attempt; circuit-break on repeats
- On fatal → emit AgentError + DLQ hint; persist diagnostics (redacted)
- Always close spans; flush logs; return stable status mapping (e.g., TIMEOUT → rc=124)

## Determinism & Reproducibility
- Enforce: temperature=0, fixed seeds, stable ordering; no wall-clock/timezone dependence on control paths
- File/path determinism: derived names must be pure functions of inputs; document tie-breakers
- Record replay recipe: model, params, seeds, input digests, decision gates, budgets; WAL-first
- Diff minimality: prefer surgical edits; if unknown original, return full-file content (Phase 2 default)
- Numeric tolerances: document eps/ULP when FP math unavoidable; order reductions

## Tooling & Budget Enforcement
- Tool allowlist by risk tier: {read-only, local-exec, network-disabled}. Default deny; elevate only via policy
- Budget guardrails: check before LLM/tool call; if exceed → return AgentError{resource_exhausted}
- Idempotency: attach keys to tool/LLM calls; agents must be repeatable under retry
- Sandbox: all exec in `exec/sandbox.py` with timeouts, kill-on-fallback, Windows tolerance (50 ms)

## Security & Privacy Hardening
- Secrets: never embed in prompts/results; load via env/secure store; redact on logs/artifacts
- Input validation: sizes, formats, bounds; fail closed on invalid; sanitize text via redaction hooks
- RBAC checkpoints: start, tool invocation, data egress; deny on policy violations; emit `agent.policy.check`
- Tenant isolation: tag artifacts with tenant; forbid cross-tenant reads by default

## Observability (OTel-first)
- Spans: `agent.core.run`, `agent.sdk.llm`, `agent.sdk.tool`, `agent.policy.check`, `agent.budget.check`
- Attributes (low-cardinality): agent.role, run.id, task.id, status, result.count, error.code
- Logs: JSON only; never raw prompts externally; include hashes/digests instead of payloads
- Metrics: counters/histograms for runs, errors, latency P50/P95/P99, token/cost; budget denials

## Decision Trees & STOP Gates
- STOP before: cross-cutting edits; side-effects; after test failures; before risky tool use
- Edit strategy: if both apply → choose smallest diff; if ambiguity → ask orchestrator; if unsafe → return AgentError
- Spawn sub-agents only via orchestrator; include rationale and bounded plan; cap depth/width

## Quality Gates & Commands
- Must pass locally before PR: lint, format, type, tests, coverage ≥85%
- Windows examples:
  - ruff: `python -m ruff check orchestrator/**/*.py`
  - format: `python -m ruff format --check orchestrator/**/*.py`
  - mypy: `python -m mypy --strict -m orchestrator`
  - tests: `set PYTHONHASHSEED=0&& set COVERAGE_FILE=coverage.unit&& py -3 scripts\run_tests.py`

## Innovation Addenda (VLTAIR-specific)
- Prompt fingerprinting: compute and record hash of prompts/*; add CI check to detect drift
- Decision ledger: persist structured decisions (why/how) per step for audit/replay
- Deterministic LLM wrapper: auto-attach seeds/idempotency/budget checks; deny on budget underflow
- Offline mode: explicit “proposal-only” mode for risky ops; require human approval to execute
- Tool risk gating: degrade to read-only when policy uncertain; escalate via orchestrator instead of acting
