# Agent Orchestration Framework — Implementation Plan

## Purpose

- Single source of truth for building the Agent Orchestration Framework integrated with Vesper as the context engine.
- Strict alignment with `Docs/Blueprint.md`, `Docs/production-agentic-workflow.md`, and `.cursor/rules/*`.
- Phases 1 and 2 are fully mapped with workflow-embodied batches (Understanding -> Planning -> Context Gathering -> Implementation (RED->GREEN->REFACTOR) -> Verification -> Reflection). Later phases are outlined and expanded as we progress.

## Global Non-Negotiables (rules-aligned)

- Determinism and reproducibility: temperature=0, fixed seeds, idempotency keys; record model/version/params; reproducible runs.
- Correctness-first: tests drive changes; failure-path coverage; property-based tests where applicable; coverage >= 85%.
- Interface stability: versioned schemas for AgentTask/Result/Error; backward-compatible evolution.
- Security-conscious tool use; explicit error handling; no silent failures; sandbox for executing tests/tools.
- Crash-safety optional; snapshot/rollback only when persistence semantics are in-scope.

---

## Phase 0 — Context Synthesis and Repository Recon (Baseline)

### P0-Batch 0.1 — Blueprint Deep Read and Index

- Understanding:
  - Read `Docs/Blueprint.md` fully, focusing on:
    - System Architecture; Primary Orchestrator; Specialized Sub-Agents (CodeGen, TestGen/Exec, StaticAnalysis, Debug, DesignReview, Refactor, Planning).
    - Inter-Agent Communication (message envelopes; schema fields and versioning; metrics); Context Engine patterns (hybrid search, scopes, metadata filters, optional versioning/merge/snapshot); Determinism and consistency.
    - Performance SLOs (context query P50 about 1-3 ms) and acceptance criteria.
- Planning:
  - Define extraction checklist for referenced sections; identify target APIs and invariants to uphold.
- Context Gathering:
  - Create `P0/notes/blueprint_index.md` (links to sections, key bullets, acceptance criteria snapshots).
- Implementation:
  - Author `P0/notes/blueprint_index.md`.
- Verification:
  - Sanity-check coverage of all relevant sections.
- Reflection:
  - Capture open questions/gaps for P0.2.
- Rule Alignment Check:
  - Re-read `.cursor/rules/00-index.mdc` and `01-production-workflow.mdc` and confirm conformance.

### P0-Batch 0.2 — Vesper Capability Recon and Gap Analysis (read-only)

- References (files to scan):
  - `Vesper/include/vesper/**` (public interfaces, naming, C/C++ headers)
  - `Vesper/src/index/{hnsw.cpp, ivf_pq.cpp, bm25.cpp, index_manager.cpp, query_planner.cpp}`
  - `Vesper/src/search/{hybrid_searcher.cpp, fusion_algorithms.cpp}`
  - `Vesper/src/io/{async_io.cpp, prefetch_manager.cpp}`
  - `Vesper/src/metadata/metadata_store.cpp`
  - `Vesper/bench/micro/**`, `Vesper/tests/**`, `Vesper/CMakeLists.txt`
- Understanding:
  - Inventory dense, sparse (BM25), hybrid fusion, metadata filter capabilities, return formats, and any public C API hooks.
- Planning:
  - Define evaluation criteria vs Blueprint needs; identify minimal binding surface for Phase 1.
- Context Gathering:
  - Extract candidate function/class entry points; note constraints and threading assumptions.
- Implementation:
  - Author `P0/notes/vesper_capability_matrix.md` (features present/missing; risks).
- Verification:
  - Validate hybrid search and metadata filters are reachable and testable.
- Reflection:
  - Summarize gaps for Phases 1-3 (e.g., uniform hybrid entrypoint, filter operators/types, optional snapshots).
- Rule Alignment Check:
  - Re-read `02-coding-standards-cpp.mdc`, `03-ci-and-quality-gates.mdc`.

### P0-Batch 0.3 — Alignment Report and Backlog Seeds

- Implementation:
  - Author `P0/notes/implementation_alignment_report.md`:
    - Mapping Blueprint -> Vesper surfaces (search, filters, fusion, indexes, metadata, IO).
    - Determinism enforcement strategy (fixed seeds, idempotency keys, prompt capture and versioning).
    - Minimal binding surface for Phase 1; expanded in later phases.
- Verification:
  - Peer-check against Blueprint and rules.
- Reflection:
  - Seed risk register and mitigation list for Phases 1-3.
- Rule Alignment Check:
  - Re-read `06-pr-and-commit-standards.mdc`, `07-docs-and-adr.mdc`.

### P0 Research Findings (Grounded)

- Hybrid searcher API and behavior (see `Vesper/include/vesper/search/hybrid_searcher.hpp`, `Vesper/src/search/hybrid_searcher.cpp`):
  - `HybridQuery{text, dense_embedding, filter}` and `HybridSearchConfig{k, query_strategy, fusion_algorithm, rrf_k, dense_weight, sparse_weight, rerank_factor}`
  - Strategies: AUTO, DENSE_FIRST, SPARSE_FIRST, PARALLEL; Fusion algorithms: RECIPROCAL_RANK, WEIGHTED_SUM, MAX_SCORE, LATE_INTERACTION (fallback to weighted)
  - Implementation fuses dense/sparse via `fusion_algorithms` (RRF, Weighted), ranks and truncates to `k`
- Metadata filtering (see `Vesper/include/vesper/metadata/metadata_store.hpp`):
  - `MetadataStore` supports bitmap/range indexes; `utils::kv_to_filter`, `parse_filter_json`, and `filter_to_json` helpers
  - Filter evaluation yields Roaring bitmaps; used to mask dense/sparse searches in hybrid path
- Index and planner surfaces (see `Vesper/src/index/index_manager.cpp`, `Vesper/src/index/query_planner.cpp`):
  - `IndexManager` orchestrates index families; provides search entry for dense path
  - `QueryPlanner` holds a cost model and historical performance for adaptive parameters
- Implications for bindings:
  - We will expose a unified `search_hybrid` that accepts text and/or embedding, `k`, and simple filter dict or JSON (converted to `filter_expr` via utils);
  - Config knobs (`QueryStrategy`, fusion weights, RRF `k`, rerank factor) must be exposed for tuning
  - Results will include `doc_id`, `dense_score`, `sparse_score`, `fused_score`, and ranks
- Determinism considerations:
  - Hybrid search is deterministic for fixed inputs; planner/history may adapt over time; we will add a config to disable adaptive tuning in deterministic mode (bindings-layer flag or environment override)

---

## Phase 1 — Foundations: Bindings, Context Engine, Orchestrator Core (FULLY MAPPED)

### Objectives

- Provide deterministic minimal Python bindings for Vesper hybrid search and upserts.
- Implement ContextStore with scopes, filters, idempotent writes.
- Define v1 JSON schemas for message envelopes; implement deterministic orchestrator core.
- Establish tests, CI gates, micro-benchmarks; emit reproducible artifacts.

### P1-Batch 1.1 — pybind11 Scaffolding and Build

- Files:
  - `bindings/python/pyvesper/CMakeLists.txt`
  - `bindings/python/pyvesper/{module.cpp, engine.hpp, engine.cpp}`
- Target binding surface (C++ → Python):
  - Types:
    - `PyHybridSearchConfig` mapping to `vesper::search::HybridSearchConfig` (k, query_strategy, fusion_algorithm, rrf_k, dense_weight, sparse_weight, rerank_factor)
    - `PyHybridQuery` mapping to `vesper::search::HybridQuery` (text, dense_embedding, optional filter JSON)
    - `PyHybridResult {doc_id, dense_score, sparse_score, fused_score, dense_rank, sparse_rank}`
  - Functions:
    - `engine_init(config: dict) -> None`
    - `open_collection(name: str, schema: Optional[dict]) -> None`
    - `upsert(docs: List[dict]) -> None` (id, vector, metadata)
    - `search_hybrid(query: PyHybridQuery, cfg: PyHybridSearchConfig) -> List[PyHybridResult]`
    - Optional (feature-gated): `snapshot(label: str) -> None`, `wal_flush() -> None`
  - Filters:
    - Accept `filters: Dict[str,str|number|bool]` or JSON string → convert to `filter_expr` via `vesper::metadata::utils::parse_filter_json` or `kv_to_filter`
- Build & packaging:
  - Windows MSVC or ClangCL; produce wheel (win_amd64)
- Acceptance:
  - Importable module; smoke test `search_hybrid` returns plausible results; deterministic outputs for fixed inputs
- Rule Alignment Check:
  - `02-coding-standards-cpp`, `03-ci-and-quality-gates`

### P1-Batch 1.2 — ContextStore and VesperContextStore (Python)

- Files:
  - `orchestrator/context/{context_store.py, vesper_context_store.py, models.py}`
- API mapping:
  - `VesperContextStore.search(query, k, filters, mode)` → builds `PyHybridQuery` and `PyHybridSearchConfig` (mode maps to strategy: dense/sparse/hybrid)
  - `add_document` → packages id/vector/metadata; calls `upsert`
  - `merge_document` → stub; planned in Phase 3
- Filters & scopes:
  - Provide `scope` argument to route collections (global/session/task) if needed; map to collection name internally
- Acceptance:
  - Unit tests for `search`/`add_document` with mocked bindings; integration calling real bindings when available
- Rule Alignment Check:
  - `01-production-workflow`, `04-testing-and-benchmarks`

### P1-Batch 1.4 — Orchestrator Core and Scheduler (excerpt: CLI)

CLI examples:

- Submit with constraints (timeoutMs):
  - `orchestrator run --file task.json` where `task.json` contains `{ "type":"AgentTask", "id":"t1", "agent":"CodeGenAgent", "payload": {"action":"create","target":"a.cpp"}, "constraints": {"timeoutMs": 100} }`
- View registered agents:
  - `orchestrator status`
- Queue metrics:
  - `orchestrator queue` prints `{ ok:true, queued, workers, stopped }`.
  - Interpret: `queued` = pending tasks, `workers` = active worker threads, `stopped` = scheduler state.
  - Example output: `{ "ok": true, "queued": 0, "workers": 2, "stopped": false }`.
  - For JSON piping: `orchestrator queue | jq .queued`.
- Structured query:
  - Dry-run (no Vesper): `VLTAIR_TEST_MODE=1 orchestrator query --text "vector search" --k 5 --mode hybrid --rrf-k 60 --dense-weight 0.6 --sparse-weight 0.4 --rerank-factor 10 --filter-kv type=text`
  - Real query (with Vesper): `orchestrator query --text "coverage hints" --k 10 --mode hybrid --filter-json '{"type":"coverage_hint"}'`

---

### P1-Batch 1.4 — Orchestrator Core and Scheduler (Testing Notes)

- Router tests:
  - Verify agent selection falls back to least-loaded idle when agent unspecified.
  - Validate queue metrics expose queued/workers/stopped fields.
- Retry/backoff tests:
  - Simulate transient failures; assert ≥2 retries and backoff gaps (~10ms with patched backoff).
- Budget tests:
  - Enforce timeoutMs budget < handler runtime; assert single invocation and drop (no retry).

---

## Phase 2 — Baseline Agents and End-to-End Workflows (FULLY MAPPED)

### Objectives (Phase 2)

- Implement deterministic CodeGen, TestGen/Exec, StaticAnalysis, and Debug agents with clear scopes and guardrails.
- Demonstrate two complete workflows: feature add; failing-test fix loop.
- Enforce budgets and determinism; integrate with ContextStore.

### P2-Batch 2.0 — Research Synthesis (pre-Batch)

- Files:
  - `P2/notes/agent_workflows_research.md`
- Deliverables:
  - Summarize CodeGen/TestGen/Exec/StaticAnalysis/Debug workflows; identify context interactions, result payloads, and validator gaps.
  - Capture acceptance criteria and SLOs for Phase 2 agents and workflows.
- Acceptance:
  - Notes published; gaps list created and referenced below; ImplementationPlan updated accordingly.
- References:
  - `P1/notes/*` methodology replicated for Phase 2

### P2-Batch 2.1 — Agent Interfaces and Registry

- Files:
  - `agents/{base.py, registry.py}`
- Deliverables:
  - Base `Agent.run(task, ctx)`; Registry mapping `agent` string to concrete class
- Acceptance:
  - Unit tests for base behavior and registry loading
- Alignment Check

### P2-Batch 2.2 — CodeGenAgent

- Files:
  - `agents/codegen.py`; `prompts/codegen.md`
- Scope & Guardrails:
  - Deterministic prompts; return `delta` as unified diff or full file content; adhere to coding standards; minimize change surface
- Acceptance:
  - Unit tests validate result schema; integration applies diff to temp workspace and checks syntax/compile (language-dependent)

### P2-Batch 2.3 — TestAgent (Generate)

- Files:
  - `agents/test_gen.py`; `prompts/test_gen.md`
- Deliverables:
  - Deterministic test generation; coverage-oriented templates; edge cases included
- Acceptance:
  - Unit tests for schema; integration generating tests for a sample module; check determinism

### P2-Batch 2.4 — TestAgent (Execute)

- Files:
  - `agents/test_exec.py`; `exec/sandbox.py`
- Deliverables:
  - Windows-safe sandboxed execution; capture logs/timings; return `AgentError(TestFailure)` on failures
- Acceptance:
  - Integration test demonstrating failure capture with details

### P2-Batch 2.5 — StaticAnalysisAgent

- Files:
  - `agents/static_analysis.py`; `prompts/static_review.md`
- Deliverables:
  - Structured findings (severity, location, suggestion); optional auto-fix behind flag
- Acceptance:
  - Unit tests for findings schema; integration on sample code

### P2-Batch 2.6 — DebugAgent

- Files:
  - `agents/debug.py`; `prompts/debug.md`
- Deliverables:
  - Diagnose failing test; retrieve relevant code from context; propose minimal patch diff; deterministic outputs
- Acceptance:
  - Integration: failing test -> proposed patch -> re-run passes

### P2-Batch 2.7 — Workflow A: Feature Add

- Flow:
  - CodeGen -> StaticAnalysis -> TestGen -> TestExec; if failure -> Debug loop -> TestExec -> success
- Acceptance:
  - Scenario integration validates whole loop; determinism and budgets enforced; logs present

### P2-Batch 2.8 — Workflow B: Fix Failing Test

- Flow:
  - TestExec -> Debug -> CodeGen -> TestExec -> success
- Acceptance:
  - Scenario integration validates successful fix; determinism preserved

### P2-Batch 2.9 — Phase 2 Validation and DX

- CI gates:
  - Coverage >= 85%; artifacts attached; determinism logs present
- Bench:
  - End-to-end timings; token/runtime budgets recorded
- CLI examples:
  - `orchestrator run --file task.json` validates and enqueues; on error prints `{ ok:false, traceId, error }`
- Reflection and Alignment Check:
  - Re-open Blueprint and rules; open issues for Phase 3

### Phase 2 — Redaction & Security Hardening (NEW)

- Files:
  - `orchestrator/obs/redaction.py`, `SECURITY.md`, `cli/orchestrator_cli.py`
- Deliverables:
  - Pattern-based and field-based redaction hooks with env config; documentation; CLI flags to toggle `VLTAIR_REDACT_PREFIXES` and `VLTAIR_REDACT_FIELDS`.
  - Parameterized tests for redaction/invalid severities/suggestions; multi-artifact flows; performance micro-bench with SLOs.
- Acceptance:
  - All sensitive patterns redacted in tests; field-based selectors applied; perf meets SLO; docs updated.

### Phase 2 Acceptance Criteria

- Both workflows complete deterministically; Debug loop resolves failing tests; budgets enforced; coverage >= 85%; artifacts/benchmarks attached.

---

## Phase 3 — Context Versioning, Merge, and Hierarchical Planning (OUTLINE)
- Context versioning and three-way merge strategy; conflict detection; optimistic concurrency checks; optional MergeAgent; snapshots/rollback gated.
- Orchestrator hierarchical scheduling; parallelism with backpressure and concurrency limits; causal consistency choices.
- Extended observability: agent timelines; event-sourced audit for replay.
- Alignment ritual after each batch.

## Phase 4 — Interoperability, Transport, and Tool Catalog (OUTLINE)
- Protocol adapters (HTTP/gRPC) for remote agents; envelope mapping; auth/policy.
- Tool definitions library; extended sandboxing; simple trace UI.
- Alignment ritual after each batch.

## Phase 5 — Scale, Packaging, and Release (OUTLINE)
- Packaging (wheels/binaries), CI/CD; reproducible builds; docs/ADRs finalized; performance tuning; multi-project orchestration.
- Alignment ritual after each batch.

---

## Cross-Cutting References
- Blueprint sections to re-check frequently:
  - Specialized Sub-Agents; Context Engine; Message Schemas; Orchestrator responsibilities; Determinism and planning; Performance SLOs.
- Vesper files routinely referenced:
  - `include/vesper/**`
  - `src/search/{hybrid_searcher.cpp, fusion_algorithms.cpp}`
  - `src/index/{hnsw.cpp, ivf_pq.cpp, bm25.cpp, index_manager.cpp, query_planner.cpp}`
  - `src/metadata/metadata_store.cpp`
  - `src/io/{async_io.cpp, prefetch_manager.cpp}`
  - `bench/micro/**`, `tests/**`, `CMakeLists.txt`
- Cursor rules to consult at each batch end:
  - `00-index`, `01-production-workflow`, `02-coding-standards-cpp`, `03-ci-and-quality-gates`, `04-testing-and-benchmarks`, `05-security-and-safety`, `06-pr-and-commit-standards`, `07-docs-and-adr`, `08-python-and-orchestrator-standards` (when enabled).
