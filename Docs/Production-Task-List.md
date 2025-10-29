# Production Readiness Task List (Blueprint.md Alignment)

Generated: 2025-10-29T00:35:00Z
Branch: debug/ci-windows-timeout-diagnostics
Standards: VLTAIR Production Agentic Workflow, coverage ≥85%, deterministic, fail-closed

---

## Batch 1: Context Engine

### Blueprint Requirements (Summary — Batch 1)
- Context Engine is central, persistent, and powered by Vesper (hybrid vector + BM25 search).
- Supports global/session/task scopes; semantic search APIs with AUTO/DENSE/SPARSE strategies.
- Durable: WAL + snapshots for crash recovery; content versioning and merging (especially for code/docs).
- Determinism: fixed seeds/config; stable ordering; reproducible results.
- Performance SLOs: hybrid search P50 around 1–3 ms (data-dependent) with budget enforcement.
- Filter capability: metadata filters with well-defined grammar and operators.

### Current Implementation Status (Batch 1)
- Files inspected:
  - bindings/python/pyvesper/{engine.hpp, engine.cpp, module.cpp}
  - orchestrator/context/{vesper_context_store.py, context_store.py, models.py, idempotency.py}
  - tests/unit/{context_store_test.py, vesper_context_store_mock_test.py}
  - Docs/ImplementationPlan.md (Phase 1/2 references)
- Specification alignment: Has gaps
- Production readiness: Needs hardening

### Gaps and Issues (Batch 1)


| ID | Severity  | Description | Affected Files | Effort |
|----|-----------|-------------|----------------|--------|
| CE-1 | Critical | No WAL + snapshot integration for durable recovery per Blueprint (event-sourced or snapshot approach). | orchestrator/context/context_store.py, orchestrator/core/*, Docs/ADRs/* | Large |
| CE-2 | Critical | No content versioning/merge support exposed through ContextStore for code/doc artifacts. | orchestrator/context/context_store.py, orchestrator/workflows/* | Large |
| CE-3 | Important | SearchResult metadata not returned (currently `metadata=None`); loses useful context for downstream agents. | orchestrator/context/vesper_context_store.py:44 | Small |
| CE-4 | Important | Filters grammar/validation not enforced; `filters` is pass-through (Dict/str). Deterministic grammar + validation missing. | orchestrator/context/vesper_context_store.py, tests/unit/* | Medium |
| CE-5 | Important | Deterministic handling for numpy/array embeddings not explicitly tested (type marshalling + copy behavior). | bindings/python/pyvesper/*, tests/unit/* | Medium |
| CE-6 | Nice-to-have | Performance SLO measurement and CI gate for hybrid search (P50/P95) not established at Context Engine layer. | bench/context/*, CI | Small |

### Remediation Tasks (Batch 1)
- [ ] CE-1: Design and ADR for WAL + Snapshot (event log schema, snapshot boundaries). Acceptance: ADR approved; reference implementation surface agreed; tests define resume semantics.
- [ ] CE-2: Add content versioning hooks (version field, merge policy) with deterministic merge helpers. Acceptance: unit tests for version/merge; integration shows code doc merges preserved.
- [ ] CE-3: Return metadata in VesperContextStore.search results (map engine result metadata if available). Acceptance: updated test asserts metadata round-trip.
- [ ] CE-4: Define filters grammar (JSON/KV) and add validator + property tests. Acceptance: invalid filters rejected deterministically; valid examples pass; search called with normalized filter string/struct.
- [ ] CE-5: Add explicit tests for numpy/array embeddings (dtype/shape) and ensure zero-copy or documented copies. Acceptance: unit tests cover pyvesper marshalling; no crashes; deterministic results.
- [ ] CE-6: Add micro-bench for `search_hybrid` with CI thresholds; record P50/P95 JSON. Acceptance: CI publishes bench JSON and enforces ≤5% regression.

### Evidence and Validation (Batch 1)
- Commands:
  - `PYTHONHASHSEED=0 python -m pytest -q tests/unit/context_store_test.py tests/unit/vesper_context_store_mock_test.py`
  - Bench SLO: `python bench/context/hybrid_search_bench.py > bench_hybrid.json`
- Acceptance:
  - Tests cover metadata round-trip, filters validation, and embedding types.
  - Bench JSON recorded with thresholds; CI enforces regression gate.

#### Batch 1 — Addendum (Second-pass review on 2025-10-29)

Additional gaps found during the second-pass review, and corresponding remediation tasks. These are additive to CE-1…CE-6 above.

##### Additional Gaps and Issues (Batch 1)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| CE-7 | Important | Result ordering lacks explicit deterministic tie-breakers for equal fused_score; enforce stable sort by (score desc, doc_id asc). | orchestrator/context/vesper_context_store.py; tests/unit/* | Small |
| CE-8 | Important | Hybrid search config lacks strict validation (k>0, rrf_k>0, 0≤weights≤1, enums valid). Should raise deterministic ValueError with stable messages. | orchestrator/context/context_store.py; orchestrator/context/vesper_context_store.py | Small |


| CE-9 | Important | Filters not canonicalized; dict vs JSON string may yield different engine inputs. Normalize to canonical JSON (sorted keys, stable spacing) before search; add property tests. | orchestrator/context/context_store.py; orchestrator/context/vesper_context_store.py; orchestrator/context/idempotency.py | Small |
| CE-10 | Nice-to-have | Idempotent upsert batching: de-duplicate identical (id, vector) within a call; expose deterministic summary (n_inserted, n_updated, n_skipped). | orchestrator/context/context_store.py; orchestrator/context/idempotency.py | Medium |

##### Additional Remediation Tasks (Batch 1)
- [ ] CE-7: Implement stable tiebreakers and tests.
  - Acceptance: deterministic ordering when two or more results share the same score; sort key (score desc, doc_id asc) asserted in unit test.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/vesper_context_store_mock_test.py::test_deterministic_ordering`
- [ ] CE-8: Validate search config and raise stable errors.
  - Acceptance: invalid k, rrf_k, weights, or enums raise ValueError with stable message; valid configs pass through unchanged.
  - Validation: `python -m pytest -q tests/unit/context_store_test.py::test_search_config_validation`
- [ ] CE-9: Canonicalize filters and add property tests.
  - Acceptance: dict and JSON-string inputs produce identical canonical filter passed to engine; property test over random key orders passes; invalid grammar rejected deterministically.
  - Validation: `python -m pytest -q tests/unit/context_store_test.py::test_filter_canonicalization`
- [ ] CE-10: Upsert idempotency within a batch.
  - Acceptance: repeated items within the same call are counted as skipped; summary matches; behavior documented.
  - Validation: `python -m pytest -q tests/unit/context_store_test.py::test_upsert_batch_idempotency`

##### Validation additions (Batch 1)
- Benchmarks (no perf regressions):
  - `python bench/context/hybrid_search_bench.py > bench_hybrid.json`
  - Gate remains ≤5% regression relative to baseline.

---
#### Batch 1 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 1)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| CE-11 | Critical | Content versioning and deterministic three-way merge for text/code with conflict markers; expose diff/merge API and persist version metadata. | orchestrator/context/versioning.py (new); orchestrator/context/context_store.py; tests/unit/* | Medium |
| CE-12 | Important | Time-travel query: ability to execute searches against a snapshot at timestamp or WAL index; add API and tests. | orchestrator/context/vesper_context_store.py; orchestrator/wal/*; tests/integration/* | Medium |
| CE-13 | Important | Embedding adapter abstraction with deterministic seeding and offline stub; import guards and tests. | orchestrator/context/embeddings.py; tests/unit/* | Small |
| CE-14 | Important | Filters grammar spec and JSON Schema validation; stable error codes/messages; property tests over randomized inputs. | orchestrator/context/filters.py; Docs/Filters.md; tests/property/* | Medium |
| CE-15 | Nice-to-have | Hybrid search stability under concurrency: repeated runs with the same seed yield identical top-k and scores; add stress/property tests. | orchestrator/context/vesper_context_store.py; tests/property/* | Medium |

##### Additional Remediation Tasks (Third-pass — Batch 1)
- [ ] CE-11 (NEW 2025-10-29): Deterministic three-way merge + version metadata
  - Acceptance: for three inputs (base, ours, theirs) produce merged text; conflicts delimited by stable markers; API returns summary {added, removed, conflicts}; version metadata recorded in context store; docs updated.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/context_versioning_test.py::test_three_way_merge_deterministic`

- [ ] CE-12 (NEW 2025-10-29): Time-travel query against snapshot/WAL
  - Acceptance: `search(query, at=ts|wal_idx)` returns results identical to replaying to that point; tests create two snapshots and assert stable answers.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/context_timetravel_test.py::test_search_at_snapshot`

- [ ] CE-13 (NEW 2025-10-29): Embedding adapter + offline stub
  - Acceptance: Embeddings API resolves to stub when vendor lib missing; outputs deterministic vectors given fixed seed; tests skip vendor if unavailable.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/embeddings_adapter_test.py::test_offline_stub_deterministic`

- [ ] CE-14 (NEW 2025-10-29): Filters grammar + JSON Schema
  - Acceptance: invalid filters rejected with stable code `filters_invalid`; property test randomizes key order/types; canonicalization unchanged.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/property/filters_schema_prop_test.py::test_rejects_invalid`

- [ ] CE-15 (NEW 2025-10-29): Concurrency stability property test
  - Acceptance: concurrent 4× runs under same seed yield identical top-k ids/scores; tolerance 0 ULP; test passes on Linux/Windows.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/property/hybrid_search_stability_test.py::test_topk_stable_under_concurrency`


## Batch 2: Agent Runtime

### Blueprint Requirements (Summary — Batch 2)
- Deterministic sandbox; OS-level isolation; TIMEOUT rc mapping; Windows-friendly termination; output caps; coverage propagation.

### Current Implementation Status (Batch 2)
- Initial read indicates strong alignment, with Windows-specific fixes in place (watchdog + fallback). Detailed analysis pending next batch.

### Gaps and Issues (Batch 2)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| AR-1 | Important | Coverage env propagation incomplete (rcfile, datafile not forwarded to child). | exec/sandbox.py:_build_env | Small |
| AR-2 | Important | Output caps truncation marker not asserted by tests (risk of silent changes). | tests/unit/sandbox_v2_test.py | Small |
| AR-3 | Nice-to-have | Windows terminate→wait→kill semantics not explicitly modeled (terminate vs kill same on Windows); consider bounded wait for determinism in diagnostics. | exec/sandbox.py | Medium |
| AR-4 | Nice-to-have | Restricted token/cgroups detection features are untested; ensure skip-guarded coverage. | exec/sandbox.py; tests/unit/* | Medium |
| AR-5 | Nice-to-have | Sandbox overhead not measured; add micro-bench to guard orchestration overhead (<10%). | bench/*; CI | Medium |

### Remediation Tasks (Batch 2)
- [x] AR-1: Propagate `COVERAGE_RCFILE` and `COVERAGE_FILE` from parent to child in sandbox environment. Acceptance: env present in child (verified via unit/diag or mock).
- [x] AR-2: Add unit test to assert presence of `[TRUNCATED at N bytes]` when output exceeds cap. Acceptance: test passes, cap respected deterministically.
- [ ] AR-3: Add bounded wait timing to diagnostics on timeout path; document terminate/kill equivalence on Windows. Acceptance: CI diag includes duration and kill note on TIMEOUT.
- [ ] AR-4: Add skip-guarded tests for restricted token/cgroups detection that assert deterministic `detected/reason` fields are populated. Acceptance: tests pass on Linux/Windows with appropriate skips.
- [ ] AR-5: Add micro-bench for sandbox wrapper overhead and threshold in CI (<=10% of baseline). Acceptance: bench JSON attached; CI threshold enforced.

### Evidence and Validation (Batch 2)
- Commands:
  - `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py`
  - `python bench/context/hybrid_search_bench.py > bench_hybrid.json` (overhead can be inferred via wrapper bench if added)
- Acceptance:
  - Coverage env vars observed in child; truncation cap marker asserted by test; TIMEOUT rc mapping preserved; diagnostics include timing.


#### Batch 2 — Addendum (Second-pass review on 2025-10-29)

Additional gaps found during the second-pass review; these are additive to AR-1…AR-5 above.

##### Additional Gaps and Issues (Batch 2)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| AR-6 | Important | Assert coverage env propagation to child (`COVERAGE_PROCESS_START`, `COVERAGE_RCFILE`, `COVERAGE_FILE`). | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |
| AR-7 | Important | Windows cross-drive cwd behavior: when test paths are on a different drive than repo cwd, ensure child `cwd` is set accordingly; add unit test. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |
| AR-8 | Important | Watchdog fallback determinism: if `TimeoutExpired` not raised but duration ≥ wall limit, map to TIMEOUT; add unit test. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |
| AR-9 | Important | cgroups v2 detection/attach path lacks tests; assert deterministic `enforced.cgroups_v2{enabled_env,detected,applied,reason}`; skip on non-Linux. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Medium |
| AR-10 | Nice-to-have | Memory limit mapping on Unix: induce RLIMIT_AS breach and assert `MEM_LIMIT` or deterministic fallback; skip on Windows. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Medium |
| AR-11 | Nice-to-have | Output decode robustness: invalid UTF-8 bytes replaced deterministically; truncation marker preserved. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |
| AR-12 | Important | `allow_partial=False` failure paths: Windows JobObject unavailable or Unix rlimit init failure -> `INTERNAL_ERROR` with stable reason; add tests. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |
| AR-13 | Nice-to-have | Shim `run_pytests` header: assert `[sandbox] traceId=… duration_ms=…` prepended; add focused test. | exec/sandbox.py; tests/unit/sandbox_v2_test.py | Small |

##### Additional Remediation Tasks (Batch 2)
- [ ] AR-6 (NEW 2025-10-29): Add unit test `test_env_propagates_coverage_vars`.
  - Acceptance: child env includes `COVERAGE_PROCESS_START`, `COVERAGE_RCFILE`, and `COVERAGE_FILE` when set in parent.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_env_propagates_coverage_vars`
- [ ] AR-7 (NEW 2025-10-29): Add Windows-only test `test_windows_cross_drive_cwd_set` (importorskip on non-Windows).
  - Acceptance: when drives differ, `subprocess.Popen` receives `cwd` pointing to test path drive; no change when same drive.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_windows_cross_drive_cwd_set`
- [ ] AR-8 (NEW 2025-10-29): Add unit test `test_watchdog_timeout_fallback_deterministic` with fake Popen that exceeds wall limit without raising TimeoutExpired.
  - Acceptance: result maps to `status=="TIMEOUT" and rc==124`; duration_ms ≥ wall limit.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_watchdog_timeout_fallback_deterministic`
- [ ] AR-9 (NEW 2025-10-29): Add Linux-only test `test_cgroups_v2_detection_struct` toggling `VLTAIR_SANDBOX_ENABLE_CGROUPS_V2=1`.
  - Acceptance: `enforced.cgroups_v2` contains stable keys and reason; attach path updates `applied` or stable `reason`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_cgroups_v2_detection_struct`
- [ ] AR-10 (NEW 2025-10-29): Add Unix test `test_integration_mem_limit_unix` (skip on Windows) constraining `mem_bytes` to trigger `MEM_LIMIT` or deterministic fallback mapping.
  - Acceptance: status in {`MEM_LIMIT`,`KILLED_KILL`,`TIMEOUT`} with explanatory `reason`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_integration_mem_limit_unix`
- [ ] AR-11 (NEW 2025-10-29): Add unit test `test_output_decode_replacement` with invalid UTF-8 in streams.
  - Acceptance: replacement characters present and `[TRUNCATED at N bytes]` preserved when over cap.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_output_decode_replacement`
- [ ] AR-12 (NEW 2025-10-29): Add tests `test_allow_partial_false_windows_job_unavailable` and `test_allow_partial_false_unix_rlimit_error`.
  - Acceptance: result `status=="INTERNAL_ERROR"` with stable `reason` and `rc==1` when capability missing and `allow_partial=False`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_allow_partial_false_windows_job_unavailable tests/unit/sandbox_v2_test.py::test_allow_partial_false_unix_rlimit_error`
- [ ] AR-13 (NEW 2025-10-29): Add unit test `test_run_pytests_shim_header_present`.
  - Acceptance: `run_pytests()` returns combined output prefixed by `[sandbox] traceId=... duration_ms=...` line.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_run_pytests_shim_header_present`

#### Batch 2 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 2)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| AR-14 | Important | Virtual clock/time abstraction for sandbox and logs to remove wall-clock nondeterminism; durations computed from monotonic clock. | exec/sandbox.py; telemetry/sink.py; tests/unit/* | Medium |
| AR-15 | Important | Deterministic stdout/stderr truncation on UTF-8 boundaries; preserve `[TRUNCATED at N bytes]` and avoid broken code points. | exec/sandbox.py; tests/unit/* | Small |
| AR-16 | Important | Process/job cleanup: ensure no zombies or orphaned children on error/timeout; Windows JobObject group; Unix process group. | exec/sandbox.py; tests/integration/* | Medium |
| AR-17 | Nice-to-have | Deterministic tempdir strategy and cleanup (prefix with traceId, bounded length); guard Windows long-path pitfalls. | exec/sandbox.py; tests/unit/* | Small |

##### Additional Remediation Tasks (Third-pass — Batch 2)
- [ ] AR-14 (NEW 2025-10-29): Virtual clock for sandbox + logs
  - Acceptance: sandbox result includes `duration_ms` derived from monotonic; replacing system clock does not change outputs; unit tests monkeypatch time.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_virtual_clock_monotonic`

- [ ] AR-15 (NEW 2025-10-29): UTF-8 safe truncation
  - Acceptance: arbitrary bytes with multi-byte characters truncate at codepoint boundary; marker preserved with exact N.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_v2_test.py::test_utf8_safe_truncation`

- [ ] AR-16 (NEW 2025-10-29): No-zombie guarantee
  - Acceptance: after timeout/error, `psutil` (if available) or platform calls show no child processes; Windows JobObject terminates group; Unix sends SIGKILL to process group.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/sandbox_process_cleanup_test.py::test_children_terminated`

- [ ] AR-17 (NEW 2025-10-29): Deterministic tempdir + cleanup
  - Acceptance: temp dirs named `vl tair-<traceId>-<n>` (no spaces in final); removed on success/failure; path length < 200 on Windows.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/sandbox_tempdir_test.py::test_tempdir_deterministic_and_cleanup`

---

## Batch 3: Orchestrator Core

### Blueprint Requirements (Summary — Batch 3)
- Deterministic orchestrator: task management, routing, bounded concurrency, retries/backoff.
- DAG control for workflows; step readiness and completion tracking.
- Budget enforcement across steps; idempotency keys; result schema validation.
- Durability (WAL + snapshot) of orchestrator state and context changes; event-sourced logging.
- Strong consistency for single-writer context updates.

### Current Implementation Status (Batch 3)
- Files inspected:
  - orchestrator/core/{orchestrator.py, scheduler.py, dag.py, registry.py, errors.py}
  - orchestrator/workflows/workflows.py
  - tests/unit/\* (router/scheduler/orchestrator), tests/integration/\*
- Specification alignment: Has gaps
- Production readiness: Needs hardening

### Gaps and Issues (Batch 3)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OC-1 | Critical | No WAL + snapshot for orchestrator state (in-memory only). | orchestrator/core/orchestrator.py; Docs/ADRs/* | Large |
| OC-2 | Important | Retryable error taxonomy shallow; deterministic mapping for transport/agent failures missing. | orchestrator/core/errors.py; orchestrator/core/orchestrator.py | Medium |
| OC-3 | Important | Scheduler lacks idempotency keys and explicit retry history (attempt stamps). | orchestrator/core/scheduler.py | Medium |
| OC-4 | Important | DAG lacks cycle detection/validation; missing failure-path tests. | orchestrator/core/dag.py; tests/unit/* | Medium |
| OC-5 | Important | Budget enforcement/snapshots not persisted for inspection across steps. | orchestrator/core/orchestrator.py; orchestrator/budget/manager.py | Medium |
| OC-6 | Nice-to-have | Observability for queue/step timings/retries not consistently emitted. | orchestrator/core/*; orchestrator/obs/* | Medium |

### Remediation Tasks (Batch 3)
- [ ] OC-1: ADR for WAL + snapshot schema/checkpoints; implement stub interfaces. Acceptance: ADR approved; resume skeleton with mock WAL tests.
- [ ] OC-2: Define Retryable/NonRetryable error classes; map transport/agent errors deterministically; tests for backoff behavior. Acceptance: retries behave per taxonomy.
- [ ] OC-3: Add idempotency key propagation and attempt metadata in `ScheduledTask`; record retry history. Acceptance: tests assert timestamps/idempotency handling.
- [ ] OC-4: Add cycle detection and invalid-node checks in DAG; unit tests for failure paths. Acceptance: deterministic failure on cycles.
- [ ] OC-5: Integrate budget snapshots into orchestrator events; read-only inspection; unit tests validate propagation. Acceptance: budget visible deterministically.
- [ ] OC-6: Emit metrics/traces for queue ops, step durations, retries; unit tests assert metric increments. Acceptance: low-cardinality observability present.

### Evidence and Validation (Batch 3)
- Commands:
  - `PYTHONHASHSEED=0 python -m pytest -q tests/unit/orchestrator_* tests/unit/scheduler_* tests/unit/dag_*`
- Acceptance:
  - Unit tests for cycle detection, retry logs, idempotency keys, and budget propagation pass; observability asserts present.

---

### Batch 3 — Addendum (Second-pass review on 2025-10-29)

#### Additional Gaps Identified (Batch 3)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OC-7 | Important | Retry taxonomy: only retry RetryableError; classify AgentError; deterministic backoff clamp. | orchestrator/core/{scheduler.py,errors.py}, orchestrator/core/orchestrator.py | Small |
| OC-8 | Important | Deterministic scheduling: stable FIFO order and test-mode single worker; expose flag/seed. | orchestrator/core/scheduler.py | Small |
| OC-9 | Important | Deterministic DAG.ready() ordering; add cycle validation helper. | orchestrator/core/dag.py; tests/unit/dag_* | Small |
| OC-10 | Important | Handle AgentError path in orchestrator._handle_scheduled (retry vs drop by code). | orchestrator/core/orchestrator.py | Small |
| OC-11 | Critical | Single-writer guard for context updates; serialize apply_agent_result. | orchestrator/core/orchestrator.py; orchestrator/context/context_store.py | Medium |
| OC-12 | Critical | WAL hooks: define stub append()/snapshot() for orchestrator events/results. | orchestrator/wal/*; Docs/ADRs/* | Large |
| OC-13 | Medium | Consolidate error taxonomy; remove duplicate BudgetExceededError; unify imports. | orchestrator/core/errors.py; orchestrator/budget/manager.py | Small |

#### Remediation Tasks (Batch 3 — Second-pass)
- [ ] OC-7 (NEW 2025-10-29): Implement RetryableError-only retries and deterministic backoff
  - Acceptance: Scheduler retries only on RetryableError; NonRetryable or validation errors are not retried; backoff sequence [1, 2, 4] then clamp ≤60s.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/scheduler_test.py::test_retry_taxonomy_backoff`

- [ ] OC-8 (NEW 2025-10-29): Stable scheduling order and deterministic test-mode
  - Acceptance: Enqueuing tasks A,B,C runs in ABC order with max_concurrency=1; with >1 worker behind a flag, order remains FIFO per traceId.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/scheduler_test.py::test_fifo_order_deterministic`

- [ ] OC-9 (NEW 2025-10-29): DAG.ready() deterministic sort + cycle detection helper
  - Acceptance: `ready()` returns sorted IDs; `dag.validate()` raises on cycles; tests cover cycle and invalid node.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/dag_test.py::test_ready_sorted tests/unit/dag_test.py::test_cycle_detection`

- [ ] OC-10 (NEW 2025-10-29): Orchestrator handles AgentError
  - Acceptance: When handler returns AgentError with code==transient, scheduler retries; with code==fatal, drop; attempts history recorded.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/orchestrator_core_test.py::test_handle_agent_error_retry_vs_drop`

- [ ] OC-11 (NEW 2025-10-29): Single-writer guard for apply_agent_result
  - Acceptance: Concurrent `apply_agent_result()` calls are serialized; context_store.add_* is called without interleaving; test uses threads + barrier.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/orchestrator_core_test.py::test_single_writer_apply`

- [ ] OC-12 (NEW 2025-10-29): WAL append/snapshot stub and ADR
  - Acceptance: Introduce `orchestrator.wal` interface; Orchestrator emits wal.append events for AgentTask accepted and AgentResult applied; ADR approved.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/wal_stub_test.py::test_wal_append_called`

- [ ] OC-13 (NEW 2025-10-29): Error taxonomy consolidation
  - Acceptance: Remove duplicate BudgetExceededError from `orchestrator/core/errors.py`; imports resolve to `orchestrator.budget.manager.BudgetExceededError`; tests import and assert `.to_agent_error()` exists.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/errors_taxonomy_test.py::test_budget_exceeded_error_source`

---
#### Batch 3 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 3)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OC-14 | Critical | Deterministic replay mode driven by WAL to reconstruct orchestrator state at a point-in-time without external side-effects; dry-run option. | orchestrator/core/orchestrator.py; orchestrator/wal/*; tests/integration/* | Large |
| OC-15 | Important | Idempotency keys for external side-effects (e.g., tool/network calls) with dedupe journal; enforce on retries/replay. | orchestrator/core/orchestrator.py; orchestrator/core/scheduler.py; tests/unit/* | Medium |
| OC-16 | Important | Bounded queues/backpressure: explicit capacity and policy (reject/drop oldest) with deterministic error envelope/reason; metrics exposed. | orchestrator/core/scheduler.py; obs/metrics.py; tests/unit/* | Medium |
| OC-17 | Nice-to-have | Deterministic cancellation/rollback semantics for DAG nodes; record audit/WAL events and stable states. | orchestrator/core/dag.py; orchestrator/wal/*; tests/integration/* | Medium |

##### Additional Remediation Tasks (Third-pass — Batch 3)
- [x] OC-14 (NEW 2025-10-29): Replay orchestrator from WAL
  - Acceptance: `Orchestrator.replay(at=ts|idx, mode="dry-run")` rebuilds in-memory state and produces identical ready/set/completed lists vs recorded run; no external calls made in dry-run.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/orchestrator_replay_test.py::test_replay_reconstructs_state`

- [ ] OC-15 (NEW 2025-10-29): Idempotency keys for side-effects
  - Acceptance: On retry, duplicate external call with same idempotency key is skipped and recorded; journal survives process restart via WAL.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/orchestrator_idempotency_test.py::test_dedup_side_effects`

- [ ] OC-16 (NEW 2025-10-29): Bounded queues + backpressure
  - Acceptance: With `SCHEDULER_MAX_QUEUE=N`, enqueue beyond N triggers deterministic rejection (`queue_full`) or drops oldest when `POLICY=drop_oldest`; metrics increment; tests assert behavior.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/scheduler_backpressure_test.py::test_queue_capacity_policies`

- [x] OC-17 (NEW 2025-10-29): Deterministic cancel/rollback
  - Acceptance: Cancelling a DAG branch moves affected nodes to `cancelled` with stable audit/WAL events; replay reproduces identical states.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/dag_cancel_test.py::test_cancel_records_and_replays`



## Batch 4: Policy Engine & Budget Manager

### Blueprint Requirements (Summary — Batch 4)
- Policy: fail-closed decisions; explicit allow/deny/flag; deterministic evaluation and stable ordering; low-cardinality audit events; redaction guarantees.
- RBAC: subject → roles → resources; tenant scoping and wildcard patterns; parity across HTTP/gRPC.
- Budget: workflow/step budgets for time/tool-calls/tokens; telemetry of start/step/update/exceeded; inspection endpoints.

### Current Implementation Status (Batch 4)
- Files inspected: orchestrator/policy/engine.py; orchestrator/security/{rbac.py,redaction.py,policy.py}; orchestrator/budget/manager.py; transports adapters; tests/unit/*
- Specification alignment: Partially aligned
- Production readiness: Needs hardening

### Gaps and Issues (Batch 4)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| PE-1 | Important | Formal policy rules schema/ADR and validation missing (env JSON loosely parsed). | orchestrator/policy/engine.py; Docs/ADRs/* | Medium |
| PE-2 | Important | Audit event schema not formalized; ordering/fields asserted only in limited tests. | transports/*; telemetry/sink.py; tests/unit/* | Medium |
| PE-3 | Important | RBAC tenant scoping needs exhaustive E2E coverage across HTTP/gRPC (negative/edge cases). | transports/{http_adapter.py,grpc_adapter.py}; tests/integration/* | Medium |
| PE-4 | Nice-to-have | Deterministic sampling/rate-limits for policy audits not documented; add env knobs. | policy/engine.py; Docs/Observability.md | Small |
| PE-5 | Important | Budget telemetry not persisted/queried consistently via orchestrator surfaces. | core/orchestrator.py; budget/manager.py | Medium |

### Remediation Tasks (Batch 4)
- [ ] PE-1: Author ADR + schema for policy rules; add loader validation and property tests. Acceptance: invalid rules rejected deterministically; docs updated.
- [ ] PE-2: Define audit event schema and add tests asserting field order/stability; document in Observability.md. Acceptance: unit/integration tests pass with schema checks.
- [ ] PE-3: Extend integration suites for tenant RBAC on HTTP/gRPC including wildcard variations and negative paths. Acceptance: deterministic forbidden/unauthorized mapping.
- [ ] PE-4: Add deterministic sampling/rate-limit envs; document in Observability.md. Acceptance: unit tests for sampling gating.
- [ ] PE-5: Persist budget snapshots/events and add inspection endpoint parity + CLI. Acceptance: integration tests show stable budget visibility.

### Evidence and Validation (Batch 4)
- `PYTHONHASHSEED=0 python -m pytest -q tests/unit/policy_engine_test.py tests/integration/http_rbac_integration_test.py tests/integration/transport_grpc_parity_test.py`

---

#### Batch 4 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 4)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| PE-6 | Critical | Policy rules loader fails open on invalid/missing JSON; enforce fail-closed evaluation and add explicit knob to opt-in fail-open for dev only. | orchestrator/policy/engine.py | Small |
| PE-7 | Important | Determinism guards for evaluation not comprehensively tested (precedence, reasons ordering, header case-insensitivity). | orchestrator/policy/engine.py; tests/unit/policy_engine_test.py | Small |
| PE-8 | Important | RBAC grants loaded from env lack schema validation and fail-closed posture on bad config. | orchestrator/security/rbac.py; transports/{http_adapter.py,grpc_adapter.py} | Small |
| PE-9 | Important | RBAC parity and negative-path tests missing for gRPC (allow/deny, wildcard, tenant scoping). | orchestrator/transports/grpc_adapter.py; tests/integration/* | Medium |
| PE-10 | Important | RBAC tenant scoping edge cases (empty tenant, malformed resource, prefix* overlap) not covered. | orchestrator/security/rbac.py; tests/unit/rbac_test.py | Small |
| PE-11 | Nice-to-have | SecurityPolicy: add tests for header-case insensitivity and stable reason strings across branches. | orchestrator/security/policy.py; tests/unit/security_policy_test.py | Small |
| BM-1 | Important | Budget snapshot persistence/history missing beyond in-memory snapshot callback; add minimal in-memory ring and WAL hook stub. | orchestrator/budget/manager.py; orchestrator/core/orchestrator.py; orchestrator/wal/* | Medium |
| BM-2 | Important | Budget inspection history endpoint absent (`/v1/tasks/{taskId}/budget/history`); parity needed across HTTP/gRPC. | orchestrator/transports/http_adapter.py; orchestrator/transports/grpc_adapter.py | Medium |
| BM-3 | Nice-to-have | CLI surface for budget inspection (show current and recent snapshots). | cli/orchestrator_cli.py | Small |
| BM-4 | Important | Token budget enforcement not wired to real token usage accounting from LLM/tool calls; add adapter hook and deterministic counter. | orchestrator/budget/manager.py; orchestrator/core/orchestrator.py | Medium |
| BM-5 | Important | Persistence tests missing for budget history/snapshots (immutability, ordering, bounds). | tests/unit/budget_* | Small |

##### Additional Remediation Tasks (Batch 4)
- [ ] PE-6 (NEW 2025-10-29): Fail-closed policy loader with explicit dev override
  - Acceptance: `load_rules_from_env()` returns a sentinel RuleSet that causes evaluate() to deny when env JSON is invalid/empty unless `VLTAIR_POLICY_FAIL_OPEN=1` is set. Stable error reason "rules_invalid" is attached when denying due to config.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/policy_engine_test.py::test_fail_closed_on_invalid_rules`
- [ ] PE-7 (NEW 2025-10-29): Determinism property tests for evaluation
  - Acceptance: Precedence enforced (explicit deny > forbidden pattern > allow > default deny when reasons present). Reasons list is sorted and deduplicated; header matching is case-insensitive. Tests cover allow/deny/flag with stable outputs.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/policy_engine_test.py::test_deterministic_precedence_and_reasons`
- [ ] PE-8 (NEW 2025-10-29): RBAC grants schema validation + fail-closed
  - Acceptance: Invalid/missing `VLTAIR_RBAC_GRANTS` leads to default deny with stable reason `rbac_grants_invalid`; valid schema accepted. Unit tests cover malformed JSON, wrong types, and unknown fields.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/rbac_test.py::test_grants_schema_validation_fail_closed`
- [ ] PE-9 (NEW 2025-10-29): gRPC RBAC parity and negative paths
  - Acceptance: Parity tests for allow/deny across HTTP/gRPC for (actions: ListTools, RegisterTools, RunAgent). Include wildcard and tenant scoping; ensure deterministic error envelopes and traceparent echo. Skip when grpc/stubs unavailable.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/transport_grpc_parity_test.py::test_rbac_parity` (importorskip grpc)
- [ ] PE-10 (NEW 2025-10-29): Tenant scoping edge-case coverage
  - Acceptance: Tests for empty tenant, malformed `tenant:resource` strings, and overlapping `prefix*` patterns. Deterministic authorize() results and reasons asserted.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/rbac_test.py::test_tenant_scoping_edge_cases`
- [ ] PE-11 (NEW 2025-10-29): SecurityPolicy reason and header casing tests
  - Acceptance: Authorization via `Authorization: bearer ...` and `X-API-Token` behaves identically regardless of header case; reasons are stable strings: `unauthorized`, `forbidden:{ip}`, `method_forbidden:{method}`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/security_policy_test.py::test_header_case_insensitivity_and_reasons`
- [ ] BM-1 (NEW 2025-10-29): Budget persistence ring + WAL hook stub
  - Acceptance: Implement in-memory ring buffer per task (last N snapshots) and invoke `wal.append` stub on start/step/update/exceeded; snapshot() remains immutable. Tests assert ordering, bound N, and append calls.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/budget_persistence_test.py::test_ring_and_wal_hooks`
- [ ] BM-2 (NEW 2025-10-29): Budget history inspection endpoints
  - Acceptance: HTTP `GET /v1/tasks/{id}/budget/history` and gRPC equivalent return the last N snapshots with stable field ordering; RBAC-protected; 200 on success, 404 when task unknown.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/http_budget_endpoint_test.py::test_budget_history_endpoint`
- [ ] BM-3 (NEW 2025-10-29): CLI budget show
  - Acceptance: `orchestrator budget show --task <id> [--history]` prints deterministic JSON; structured error envelope on failure; docs updated.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/cli_budget_test.py::test_budget_show_history`
- [ ] BM-4 (NEW 2025-10-29): Token usage accounting hook
  - Acceptance: Introduce a deterministic `record_tokens(n:int, kind:"tool|llm")` API in BudgetManager and call sites in orchestrator; unit tests assert counters update and limits enforce.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/budget_manager_test.py::test_token_usage_accounting`
- [ ] BM-5 (NEW 2025-10-29): Persistence tests for budget history
  - Acceptance: Unit tests assert immutability, stable ordering, and eviction policy of the ring buffer; integration test verifies HTTP endpoint returns bounded history.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/budget_persistence_test.py::test_ring_eviction tests/integration/http_budget_endpoint_test.py::test_budget_history_bounded`


#### Batch 4 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 4)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| PE-12 | Important | Hot-reload policy rules with version stamp and deterministic evaluation switch-over (no partial application within a request). | orchestrator/policy/engine.py; telemetry/sink.py; tests/integration/* | Medium |
| PE-13 | Important | Redaction of sensitive tokens in policy reasons/audit fields before emission; ensure low-cardinality reasons. | orchestrator/policy/engine.py; telemetry/sink.py; obs/redaction.py | Small |
| BM-6 | Important | WAL serialization schema for budget events with immutability and snapshot invariants; property tests for ordering/bounds. | orchestrator/budget/manager.py; orchestrator/wal/*; tests/unit/* | Medium |

##### Additional Remediation Tasks (Third-pass — Batch 4)
- [ ] PE-12 (NEW 2025-10-29): Policy hot-reload + versioning
  - Acceptance: `PolicyEngine.load(version=V2)` swaps atomically; in-flight requests keep old version; events include `policy.version`; tests simulate concurrent evaluate() calls.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/policy_hotreload_test.py::test_atomic_swap_with_version`

- [ ] PE-13 (NEW 2025-10-29): Reason redaction and allowlist
  - Acceptance: Reasons emitted by policy are redacted via Redactor and drawn from a fixed allowlist; attempts to emit dynamic secrets are filtered.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/policy_engine_test.py::test_reasons_redacted_and_allowlisted`

- [ ] BM-6 (NEW 2025-10-29): Budget WAL schema invariants
  - Acceptance: Budget events serialize deterministically (field order stable), snapshots are immutable; property tests assert monotonic time/order and bounded history N.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/budget_wal_schema_test.py::test_budget_events_are_deterministic`

## Batch 5: Transport Layer (HTTP/gRPC)

### Blueprint Requirements (Summary — Batch 5)
- HTTP/gRPC parity for health, tools, agent run, streaming; deterministic trace IDs and traceparent echo.
- Fail-closed auth/policy/RBAC; structured error envelopes; metrics endpoint; optional TLS.

### Current Implementation Status (Batch 5)
- Files inspected: transports/{http_adapter.py,grpc_adapter.py}; tests/integration/*; docs
- Specification alignment: Mostly aligned for core routes; optional TLS not implemented
- Production readiness: Needs hardening

### Gaps and Issues (Batch 5)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| TL-1 | Critical | TLS and secure transport configuration absent (documented as optional); plan needed. | transports/*; Docs/Transport.md | Medium |
| TL-2 | Important | Error envelope parity across adapters not fully asserted (codes/details). | transports/*; tests/integration/* | Medium |
| TL-3 | Important | Streaming RPC coverage minimal; add deterministic tests for phases and errors. | grpc_adapter.py; tests/integration/* | Medium |
| TL-4 | Nice-to-have | Rate limiting/DoS protections not present; document policy. | transports/*; Docs/Security.md | Medium |
| TL-5 | Nice-to-have | Endpoint metrics coverage could be expanded; ensure low-cardinality names. | transports/*; obs/metrics.py | Small |

### Remediation Tasks (Batch 5)
- [ ] TL-1: Add TLS support notes and stubs (env toggles) or document reverse-proxy requirement; tests for secure headers. Acceptance: Transport.md updated; tests guarded.
- [ ] TL-2: Add tests asserting consistent error envelope mapping across HTTP/gRPC. Acceptance: parity suite passes.
- [ ] TL-3: Extend streaming tests for started/result/error phases and RBAC/policy enforcement. Acceptance: deterministic phase sequences asserted.
- [ ] TL-4: Document rate-limit/DoS strategy and add minimal env knobs for limits; tests for rejection path. Acceptance: docs + tests.
- [ ] TL-5: Expand metrics on key endpoints; unit tests assert increments. Acceptance: metrics snapshot shows new counters.

---

#### Batch 5 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 5)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| TL-6 | Important | Traceparent echo parity across HTTP/gRPC not fully asserted; ensure echo without affecting deterministic traceId computation. | transports/http_adapter.py; transports/grpc_adapter.py; tests/integration/* | Small |
| TL-7 | Important | gRPC optional dependency fallback lacks explicit determinism tests (GrpcUnavailable error message/behavior). | transports/grpc_adapter.py; tests/unit/* | Small |
| TL-8 | Important | HTTP request body size limit missing; add env knob and deterministic 413 payload_too_large mapping. | transports/http_adapter.py | Medium |
| TL-9 | Important | HTTP streaming parity: SSE/streaming not implemented; document and return 501 with stable envelope; gRPC streaming phases covered. | transports/http_adapter.py; Docs/Transport.md; tests/integration/* | Medium |
| TL-10 | Important | Consistent INTERNAL error mapping across transports for unexpected exceptions (HTTP 500/internal, gRPC error envelope). | transports/*; common/error_envelope.py; tests/integration/* | Medium |
| TL-11 | Small | Transport-level header normalization tests missing (authorization/traceparent case-insensitive across HTTP/gRPC). | transports/*; tests/* | Small |
| TL-12 | Nice-to-have | CORS support toggles (default deny) undocumented and untested; add deterministic headers when enabled. | transports/http_adapter.py; Docs/Transport.md | Small |
| TL-13 | Nice-to-have | HEAD/OPTIONS determinism for key endpoints (health/tools) undefined; add minimal handling or explicit 405. | transports/http_adapter.py; tests/unit/* | Small |

##### Additional Remediation Tasks (Batch 5)
- [ ] TL-6 (NEW 2025-10-29): Traceparent echo + traceId determinism
  - Acceptance: For HTTP, response contains `Traceparent` header equal to request header value when provided; for gRPC, initial metadata includes `traceparent`. In both transports, `traceId` remains the deterministic SHA-1 of request data and does not derive from `traceparent`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/transport_parity_test.py::test_traceparent_echo_and_traceid_determinism_http tests/integration/transport_parity_test.py::test_traceparent_echo_and_traceid_determinism_grpc`
- [ ] TL-7 (NEW 2025-10-29): gRPC optional fallback determinism
  - Acceptance: When grpc/stubs unavailable, constructing and starting `GrpcAgentServer` deterministically raises `RuntimeError("grpc unavailable: optional dependency or stubs not installed")`. Tests guarded with `pytest.importorskip("grpc", reason=...)` inverse (skip if present).
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/grpc_adapter_optional_test.py::test_unavailable_fallback_deterministic_error`
- [ ] TL-8 (NEW 2025-10-29): HTTP max body size limit
  - Acceptance: Add `VLTAIR_HTTP_MAX_BODY_BYTES` (default e.g., 1048576). Requests exceeding limit return 413 with error envelope `payload_too_large`; metrics increment for the route; no partial processing occurs.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/http_adapter_test.py::test_max_body_size_413_payload_too_large`
- [ ] TL-9 (NEW 2025-10-29): Streaming parity policy (HTTP Not Implemented)
  - Acceptance: Document that streaming is provided via gRPC (`RunAgentStream`) with deterministic `started→result/error` phases; HTTP responds `501 Not Implemented` for `/v1/agent/run/stream` with a stable envelope. Tests assert gRPC phases and HTTP 501.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/transport_streaming_parity_test.py::test_http_streaming_not_implemented tests/integration/transport_streaming_parity_test.py::test_grpc_streaming_started_result`
- [ ] TL-10 (NEW 2025-10-29): Internal error mapping consistency
  - Acceptance: Unexpected exceptions map to HTTP 500 with `internal` code and deterministic envelope; gRPC returns response with `error` envelope code `internal` and `ok=False`. Tests inject a controlled exception path.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/transport_error_mapping_test.py::test_internal_error_mapping_http tests/integration/transport_error_mapping_test.py::test_internal_error_mapping_grpc`
- [ ] TL-11 (NEW 2025-10-29): Header case-insensitivity tests (auth/traceparent)
  - Acceptance: `authorization` vs `Authorization` and `traceparent` vs `Traceparent` behave identically across HTTP/gRPC; transports normalize headers/metadata; results and envelopes are identical.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/http_adapter_test.py::test_header_case_insensitive_auth tests/integration/grpc_metadata_test.py::test_metadata_case_insensitive_auth`
- [ ] TL-12 (NEW 2025-10-29): Optional CORS toggles (default deny)
  - Acceptance: With `VLTAIR_HTTP_CORS_ORIGIN` set, HTTP responses include `Access-Control-Allow-Origin` with that exact value and safe defaults for `Vary` and `Access-Control-Allow-Methods`; otherwise, no CORS headers present. Low-cardinality metrics unchanged.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/http_cors_test.py::test_cors_disabled_by_default tests/unit/http_cors_test.py::test_cors_enabled_with_env`
- [ ] TL-13 (NEW 2025-10-29): HEAD/OPTIONS minimal handling
  - Acceptance: `HEAD /v1/health` returns 200 with no body and correct headers; `OPTIONS /v1/health` returns `Allow` header enumerating allowed methods; unknown methods return 405 with error envelope.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/http_options_head_test.py::test_head_health_and_options_allow`


#### Batch 5 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 5)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| TL-14 | Important | Deterministic server/client timeouts and keep-alive settings (env-driven) with stable timeout error mapping across HTTP/gRPC. | transports/http_adapter.py; transports/grpc_adapter.py; Docs/Transport.md | Medium |
| TL-15 | Important | Max message/frame size for gRPC (env) with deterministic `resource_exhausted` mapping; parity with HTTP body limit. | transports/grpc_adapter.py; tests/integration/* | Medium |
| TL-16 | Nice-to-have | Response compression toggles (gzip) opt-in with deterministic headers; default off. | transports/http_adapter.py; Docs/Transport.md | Small |
| TL-17 | Nice-to-have | gRPC streaming backpressure bounds with drop/reject policy and metrics; deterministic behavior under load. | transports/grpc_adapter.py; obs/metrics.py; tests/integration/* | Medium |

##### Additional Remediation Tasks (Third-pass — Batch 5)
- [ ] TL-14 (NEW 2025-10-29): Timeouts/keep-alive determinism
  - Acceptance: `VLTAIR_HTTP_IDLE_TIMEOUT_MS` and `VLTAIR_GRPC_DEADLINE_MS` configure timeouts; exceeded deadlines map to HTTP 504 `deadline_exceeded` and gRPC `DEADLINE_EXCEEDED`. Keep-alive pings gated via env; defaults documented.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/transport_timeouts_test.py::test_http_timeout_mapping tests/integration/transport_timeouts_test.py::test_grpc_deadline_mapping`

- [ ] TL-15 (NEW 2025-10-29): gRPC max message size limits
  - Acceptance: `VLTAIR_GRPC_MAX_MSG_BYTES` enforced; oversize requests return `resource_exhausted` with deterministic envelope; parity noted with HTTP 413.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/grpc_limits_test.py::test_max_message_size_resource_exhausted`

- [ ] TL-16 (NEW 2025-10-29): Optional gzip compression
  - Acceptance: With `VLTAIR_HTTP_GZIP=1`, responses include `Content-Encoding: gzip` for eligible endpoints; otherwise absent. Deterministic Vary header added.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/http_compression_test.py::test_gzip_off_by_default tests/unit/http_compression_test.py::test_gzip_enabled_headers`

- [ ] TL-17 (NEW 2025-10-29): Streaming backpressure bounds
  - Acceptance: Streaming send queue bounded by `VLTAIR_GRPC_STREAM_QUEUE=N`; when full, follow policy `reject` or `drop_oldest` deterministically; metrics increment. Documented in Transport.md.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/grpc_stream_backpressure_test.py::test_queue_bound_and_policy`

## Batch 6: Observability & Telemetry

### Blueprint Requirements (Summary — Batch 6)
- Structured logs, metrics, traces; low-cardinality attributes; redaction everywhere; replay helpers; optional OTel bridge.

### Current Implementation Status (Batch 6)
- Files inspected: orchestrator/telemetry/sink.py; orchestrator/obs/*; tests/unit/*; Docs/Observability.md
- Specification alignment: Partially aligned
- Production readiness: Needs hardening

### Gaps and Issues (Batch 6)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OB-1 | Important | Telemetry schema not formalized (events/traces/metrics naming); doc needed. | telemetry/sink.py; Docs/Observability.md | Medium |
| OB-2 | Important | Trace propagation across HTTP/gRPC not consistently covered; add tests. | transports/*; obs/tracing.py; tests/integration/* | Medium |
| OB-3 | Nice-to-have | Trace UI/replay helpers minimal; add deterministic replay examples. | obs/trace_ui.py; obs/replay.py | Medium |
| OB-4 | Nice-to-have | CI check for DEVLOG ToC freshness and release notes generation. | scripts/update_devlog_toc.py; scripts/release_notes_from_devlog.py | Small |

### Remediation Tasks (Batch 6)
- [ ] OB-1: Author telemetry schema doc and assert event fields/attributes via tests. Acceptance: Observability.md updated; tests pass.
- [ ] OB-2: Add traceparent/trace ID propagation tests for HTTP/gRPC. Acceptance: integration tests confirm echo/propagation.
- [ ] OB-3: Extend trace UI/replay helpers and examples; add snapshot tests. Acceptance: deterministic outputs.
- [ ] OB-4: Add a CI step to verify DEVLOG ToC is current and generate release notes on tag. Acceptance: CI step present and passing.

---

#### Batch 6 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 6)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OB-5 | Important | Span naming/coverage not standardized across core flows; ensure required spans exist and are deterministic. | obs/tracing.py; workflows/workflows.py; tests/integration/* | Small |
| OB-6 | Important | Attribute allowlist and redaction not enforced for span attrs/events; add filter and tests. | obs/tracing.py; telemetry/sink.py; obs/redaction.py | Medium |
| OB-7 | Important | Telemetry sink enablement toggle not fully tested for determinism (Null vs InMemory). | telemetry/sink.py; tests/unit/* | Small |
| OB-8 | Nice-to-have | Optional OTel bridge has no smoke tests and no sampling/export knobs documented. | obs/tracing.py; Docs/Observability.md; tests/integration/* | Small |
| OB-9 | Important | Run-level correlation: ensure tracer run_id is propagated through workflow events; add integration tests. | workflows/workflows.py; telemetry/sink.py; tests/integration/* | Medium |
| OB-10 | Important | Structured JSON logs policy not enforced (consistent keys, ts). CLI/server logs should include `ts` and low-cardinality fields. | cli/orchestrator_cli.py; exec/sandbox.py | Small |
| OB-11 | Important | Performance overhead budget for tracing/logging not validated; add microbench to ensure <10% overhead when enabled. | obs/tracing.py; tests/perf/* | Medium |
| OB-12 | Nice-to-have | Policy audit event shape/low-cardinality parity across transports not asserted. | transports/*; telemetry/sink.py; tests/integration/* | Small |

##### Additional Remediation Tasks (Batch 6)
- [ ] OB-5 (NEW 2025-10-29): Span naming + coverage
  - Acceptance: Spans `workflow.step` and `agent.invoke` are emitted during representative workflow runs with deterministic IDs; names remain stable across runs.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/observability_tracing_test.py::test_span_names_and_presence`
- [ ] OB-6 (NEW 2025-10-29): Attribute allowlist + redaction enforcement
  - Acceptance: Tracer filters attrs to allowlist {run_id, task.id, status, result.count, error.code}; all string fields in events/spans are sanitized by Redactor; tests cover emails, tokens, and dynamic prefixes.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/redaction_test.py::test_sanitize_text_patterns_and_fields`
- [ ] OB-7 (NEW 2025-10-29): Telemetry sink toggle determinism
  - Acceptance: With `VLTAIR_TELEMETRY_ENABLE=0`, `get_global_sink()` returns NullTelemetrySink; with `=1`, returns InMemoryTelemetrySink; both deterministic across calls in same process.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/telemetry_sink_test.py::test_enable_disable_toggle_deterministic`
- [ ] OB-8 (NEW 2025-10-29): Optional OTel bridge + sampling/export knobs
  - Acceptance: Document `VLTAIR_OTEL_EXPORT` and `VLTAIR_OTEL_SAMPLE_RATIO` (no-op defaults). If `opentelemetry` installed, tracer bridge creates nested spans without affecting local determinism or context; tests skip if OTel not installed.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/otel_bridge_test.py::test_optional_otel_bridge_smoke`
- [ ] OB-9 (NEW 2025-10-29): Run-level correlation in events
  - Acceptance: When a Tracer(run_id=R) is passed into workflow helpers, all recorded events include `run_id=R`; integration test asserts presence and stability.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/observability_tracing_test.py::test_run_id_propagated_in_events`
- [ ] OB-10 (NEW 2025-10-29): Structured JSON logs with `ts`
  - Acceptance: CLI/server logs include a top-level `ts` (UTC ISO8601Z), `event`, and low-cardinality fields; no raw secrets; tests parse JSON and assert keys.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/cli_logging_test.py::test_structured_json_logs_include_ts`
- [ ] OB-11 (NEW 2025-10-29): Observability overhead budget
  - Acceptance: Microbench test shows tracer-enabled run adds ≤10% median latency vs baseline for a small representative function; report median_ms and CI gate.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/perf/observability_overhead_test.py::test_tracer_overhead_budget`
- [ ] OB-12 (NEW 2025-10-29): Policy audit event shape parity
  - Acceptance: `policy.flag` events emitted by HTTP and gRPC transports share identical keys {event, transport, action, method, path, reasons}; reasons are low-cardinality strings; tests assert exact match.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/policy_audit_events_test.py::test_policy_flag_audit_event_shape`

#### Batch 6 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 6)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| OB-13 | Critical | Sampling & limits: head-sampling knob with deterministic rate and attribute length limits; drop unknown attributes. | obs/tracing.py; telemetry/sink.py; Docs/Observability.md | Medium |
| OB-14 | Important | Privacy redaction profiles (PII/secret patterns) configurable with tests to prevent leakage in spans/logs/metrics. | obs/redaction.py; telemetry/sink.py; tests/unit/* | Medium |
| OB-15 | Important | Trace replay from WAL/events: deterministic reconstruction of spans for a run; verify equivalence to live traces. | obs/replay.py; orchestrator/wal/*; tests/integration/* | Medium |
| OB-16 | Nice-to-have | Metrics units and names standardized with validation (ms, bytes, count); CI check asserts schema. | obs/metrics.py; scripts/validate_metrics_schema.py | Small |

##### Additional Remediation Tasks (Third-pass — Batch 6)
- [ ] OB-13 (NEW 2025-10-29): Sampling + attribute limits
  - Acceptance: `VLTAIR_TELEMETRY_SAMPLE_PCT` in [0,100] applied deterministically; attributes exceeding length are truncated with suffix `...`; unknown attributes dropped. Docs updated.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/tracing_sampling_test.py::test_sampling_and_attr_limits`

- [ ] OB-14 (NEW 2025-10-29): Redaction profiles
  - Acceptance: Redactor supports profiles `strict` and `standard`; tests verify emails, tokens, and 16+ hex strings are redacted; logs/spans/metrics pass through sanitizer.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/redaction_test.py::test_profiles_and_patterns`

- [ ] OB-15 (NEW 2025-10-29): Trace replay
  - Acceptance: Given WAL events for a run, `replay_to_spans(run_id)` yields the same span tree as captured live (names, attributes within allowlist); snapshot tests compare JSON.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/trace_replay_test.py::test_replay_matches_live`

- [ ] OB-16 (NEW 2025-10-29): Metrics schema validation
  - Acceptance: Introduce a metrics registry with units and names; CI script validates registration; tests assert ms/bytes/count units.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/metrics_registry_test.py::test_metric_units_and_names`


## Batch 7: Security & Privacy

### Blueprint Requirements (Summary — Batch 7)
- Fail-closed posture; RBAC; policy; redaction; secrets management; sandbox isolation; SBOM/provenance; supply chain hygiene.

### Current Implementation Status (Batch 7)
- Files inspected: security/{rbac.py,redaction.py,policy.py}; transports; scripts/*; Docs/Security.md (pending)
- Specification alignment: Partially aligned
- Production readiness: Needs hardening

### Gaps and Issues (Batch 7)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| SP-1 | Critical | TLS/secure transport missing (see TL-1); document secure deployment guidance. | Docs/Transport.md; transports/* | Medium |
| SP-2 | Important | Secrets scanning and pre-commit gates not present; add guardrails. | .pre-commit-config.yaml | Small |
| SP-3 | Important | Threat model and security posture doc missing. | Docs/Security.md | Medium |
| SP-4 | Nice-to-have | Sandbox network policy not enforced; document stance and future plan. | exec/sandbox.py; Docs/Security.md | Medium |

### Remediation Tasks (Batch 7)
- [ ] SP-1: TLS guidance and secure deployment doc; optional TLS support stubs or reverse-proxy recommendation. Acceptance: docs/tests.
- [ ] SP-2: Add pre-commit secret scanners (no secrets committed) and CI check. Acceptance: CI green; pre-commit runs locally.
- [ ] SP-3: Draft Threat Model in Docs/Security.md. Acceptance: reviewed and approved.
- [ ] SP-4: Document sandbox network policy; add env/flag placeholders; tests for denied network calls when enabled (Linux). Acceptance: docs + guarded tests.


#### Batch 7 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 7)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| SP-5 | Critical | RBAC enforcement coverage (HTTP/gRPC) with negative-path tests for unauthorized/forbidden across all endpoints. | orchestrator/security/rbac.py; orchestrator/transports/*; tests/integration/*; tests/unit/* | Medium |
| SP-6 | Important | Emit structured security audit events on deny (unauthorized/forbidden) with stable schema and redaction. | transports/*; telemetry/sink.py; Docs/Observability.md; tests/integration/* | Small |
| SP-7 | Important | End-to-end secrets redaction for headers/env in logs/telemetry (Authorization, X-API-Token, api_key); add tests. | telemetry/sink.py; obs/redaction.py; cli/orchestrator_cli.py; transports/* | Medium |
| SP-8 | Important | TLS/mTLS knobs and guidance: env vars + documented reverse-proxy pattern; deterministic refusal from stdlib server when TLS vars set. | Docs/Transport.md; orchestrator/security/policy.py; orchestrator/transports/http_adapter.py; cli/orchestrator_cli.py | Medium |
| SP-9 | Nice-to-have | Tamper-evident audit chaining for JSONL telemetry (rolling SHA-256) under opt-in flag; document and test. | telemetry/sink.py; Docs/Observability.md | Medium |
| SP-10 | Important | Supply chain hygiene: pre-commit secret scanner + CI vulnerability scan (pip-audit/bandit) with strict mode; docs for waivers. | .pre-commit-config.yaml; .github/workflows/ci.yml; Docs/Security.md | Small |
| SP-11 | Important | Sandbox Phase 3 security: assert Linux seccomp network TRAP → SANDBOX_DENIED and Windows restricted-launch fallback reasons. | exec/sandbox.py; tests/integration/sandbox_security_test.py | Medium |
| SP-12 | Important | Tenant tagging in audit/telemetry and cross-tenant deny tests (HTTP/gRPC parity). | transports/*; telemetry/sink.py; tests/integration/* | Small |

##### Additional Remediation Tasks (Batch 7)
- [ ] SP-5 (NEW 2025-10-29): RBAC coverage matrix (HTTP/gRPC)
  - Acceptance: For tools(list/get/register/delete), agent/run, and tasks/{id}/budget, when RBAC enabled and grants omit required actions/resources, requests return 403; missing/invalid token returns 401 when SecurityPolicy.allowed_tokens non-empty. Parity across HTTP and gRPC.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/security_rbac_matrix_test.py::test_http_and_grpc_rbac_matrix`
- [ ] SP-6 (NEW 2025-10-29): Security deny audit events
  - Acceptance: On any unauthorized/forbidden, emit event `security.deny` with keys {event, transport, subject, action, resource, tenant, reason, traceId}; reasons are low-cardinality; Authorization/token never included.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/security_audit_test.py::test_security_deny_event_shape`
- [ ] SP-7 (NEW 2025-10-29): Secrets redaction E2E
  - Acceptance: Telemetry events and CLI/server logs never contain raw secrets; Authorization and X-API-Token headers are redacted to `<<REDACTED>>`; dynamic prefixes from VLTAIR_REDACT_PREFIXES are honored.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/redaction_headers_test.py::test_auth_headers_redacted`
- [ ] SP-8 (NEW 2025-10-29): TLS/mTLS knobs + guidance
  - Acceptance: Document env `VLTAIR_TLS_CERT`, `VLTAIR_TLS_KEY`, `VLTAIR_TLS_CLIENT_CA` and recommend reverse-proxy TLS/mTLS. If any TLS env var is set, stdlib HTTP server exits deterministically with code=unavailable and message `tls_not_supported_use_proxy`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/cli_api_tls_knobs_test.py::test_tls_env_refusal_and_message`
- [ ] SP-9 (NEW 2025-10-29): Tamper-evident audit chaining
  - Acceptance: When `VLTAIR_TELEMETRY_ENABLE=1` and `VLTAIR_AUDIT_CHAIN_ENABLE=1`, each recorded event includes `chainPrev` and `chain` (sha256 over previous + current canonical JSON); tests verify chain continuity.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/telemetry_chain_test.py::test_event_chain_continuity`
- [ ] SP-10 (NEW 2025-10-29): Supply chain gates (dev-only)
  - Acceptance: `.pre-commit-config.yaml` includes secret scanning; CI adds pip-audit (strict) and bandit jobs (informational) without affecting runtime deps; baseline passes or has approved waivers.
  - Validation: `pre-commit run --all-files`; `python -m pip install pip-audit && pip-audit --strict`
- [ ] SP-11 (NEW 2025-10-29): Sandbox security assertions
  - Acceptance: With `VLTAIR_SANDBOX_ENABLE_SECCOMP=1` on Linux, a socket() attempt causes SANDBOX_DENIED; on Windows with restricted launch enabled but insufficient privileges, enforcement.phase3.fallback_reason is non-empty.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/sandbox_security_test.py::test_linux_seccomp_blocks_network`
- [ ] SP-12 (NEW 2025-10-29): Tenant tagging + cross-tenant deny
  - Acceptance: Audit/telemetry events include `tenant` from `x-tenant` (HTTP) or metadata (gRPC). Cross-tenant access attempts are denied and recorded with `reason` prefixed `deny:resource`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/tenant_isolation_test.py::test_cross_tenant_deny_and_audit`

---
#### Batch 7 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 7)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| SP-13 | Critical | Secret handling in crash paths: ensure exceptions/tracebacks/logs never include tokens/env; sanitize process dumps; add guards. | exec/sandbox.py; cli/orchestrator_cli.py; telemetry/sink.py | Medium |
| SP-14 | Important | Policy/RBAC schema versioning and migrations with fail-closed default when versions mismatch; doc rollover procedure. | orchestrator/policy/engine.py; security/rbac.py; Docs/Security.md | Medium |
| SP-15 | Important | Audit retention and readback: retention TTL and RBAC-protected retrieval endpoints with redaction applied. | telemetry/sink.py; transports/http_adapter.py; transports/grpc_adapter.py | Medium |
| SP-16 | Nice-to-have | Supply chain attestations verification helper (SLSA/verifier) as optional dev tool with docs; no runtime requirement. | scripts/verify_provenance.py; Docs/Security.md | Small |

##### Additional Remediation Tasks (Third-pass — Batch 7)
- [ ] SP-13 (NEW 2025-10-29): Crash-path secret redaction
  - Acceptance: Exceptions raised by CLI/server redact env/headers from messages; sandbox captures stderr with sanitizer; tests inject tokens and assert outputs contain `<<REDACTED>>`.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/logging_redaction_test.py::test_crash_path_redaction`

- [ ] SP-14 (NEW 2025-10-29): Policy/RBAC schema versioning
  - Acceptance: Policy `version` and RBAC grants `version` are required; mismatches fail closed with reason `schema_version_mismatch`; migration docs provided.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/policy_versioning_test.py::test_fail_closed_on_version_mismatch`

- [ ] SP-15 (NEW 2025-10-29): Audit retention + retrieval
  - Acceptance: `VLTAIR_AUDIT_TTL_DAYS` bounds in-memory/JSONL retention; HTTP/gRPC `GET /v1/audit?run_id=...` returns redacted events; RBAC enforced.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/integration/audit_retrieval_test.py::test_rbac_and_redaction`

- [ ] SP-16 (NEW 2025-10-29): Provenance verifier helper (optional)
  - Acceptance: `scripts/verify_provenance.py` reads release assets (provenance.json) and validates SLSA fields; docs provide usage; skipped in CI unless assets present.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/unit/provenance_verify_test.py::test_parse_and_verify_stub`


## Batch 8: Testing & CI/CD

### Blueprint Requirements (Summary — Batch 8)
- Coverage ≥85%; deterministic seeds; multi-platform gates; benches; reproducible builds; artifact upload; zero warnings policy.

### Current Implementation Status (Batch 8)
- Coverage gates present; benches job present; reproducibility/SBOM/provenance in place; Windows lane green.
- Specification alignment: Mostly aligned
- Production readiness: Needs polish

### Gaps and Issues (Batch 8)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| CI-1 | Important | Enforce zero warnings policy (pytest warnings fail CI); add lint/type gates if missing. | ci.yml; pytest.ini | Small |
| CI-2 | Nice-to-have | Automate DEVLOG ToC freshness and release notes generation on tag. | scripts/*; ci.yml | Small |
| CI-3 | Nice-to-have | Store bench baselines and compare deltas beyond thresholds for deeper reporting. | bench/*; ci.yml | Medium |

### Remediation Tasks (Batch 8)
- [ ] CI-1: Add `-W error` or pytest warnings-as-errors configuration for CI. Acceptance: CI fails on new warnings.
- [ ] CI-2: Add TOC freshness and release notes steps. Acceptance: CI step green.
- [ ] CI-3: Baseline bench store + comparison; report deltas in CI logs. Acceptance: artifacts include baseline/diff.

---

#### Batch 8 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 8)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| CI-4 | Important | Lint and type-check gates missing in CI (ruff + mypy strict) with zero-warnings policy. | .github/workflows/ci.yml; pyproject.toml | Small |
| CI-5 | Important | Deterministic test env not enforced across all jobs (missing PYTHONHASHSEED/TZ) — align Linux/GRPC/Repro jobs. | .github/workflows/ci.yml; pytest.ini | Small |
| CI-6 | Important | macOS Python test lane missing; add with coverage gating (≥85%) and same seeds. | .github/workflows/ci.yml | Small |
| CI-7 | Nice-to-have | Benchmark regression vs baseline (≤5% allowed) with artifacted diff report; thresholds today are absolute. | bench/*; .github/workflows/ci.yml | Medium |
| CI-8 | Important | Reproducible build verifier should assert identical SHA256 for wheels built with same SOURCE_DATE_EPOCH. | scripts/repro_check.py; .github/workflows/ci.yml | Small |
| CI-9 | Important | Release pipeline should attach SBOM (CycloneDX) and provenance.json to GitHub Release artifacts. | .github/workflows/release.yml | Small |
| CI-10 | Important | Stabilize Windows by splitting slow tests (marker `slow`) into dedicated lane; fast lane excludes `slow`. | tests/*; .github/workflows/ci.yml | Small |
| CI-11 | Important | Core-path coverage gate ≥90% for orchestrator core modules (scripted check on coverage.xml). | scripts/coverage_guard.py; .github/workflows/ci.yml | Medium |

##### Additional Remediation Tasks (Batch 8)
- [ ] CI-4 (NEW 2025-10-29): Add ruff + mypy gates in CI
  - Acceptance: CI includes steps `ruff .` (errors-as-fail) and `mypy --strict orchestrator cli exec tests`; pipeline fails on lint/type errors.
  - Validation: `PYTHONHASHSEED=0 ruff . --output-format=github` and `PYTHONHASHSEED=0 mypy --strict orchestrator cli exec tests`
- [ ] CI-5 (NEW 2025-10-29): Enforce deterministic env across jobs
  - Acceptance: All test jobs export `PYTHONHASHSEED=0` and `TZ=UTC`; logs show these values; tests pass deterministically.
  - Validation: `PYTHONHASHSEED=0 TZ=UTC python -m pytest -q -k test_smoke`
- [ ] CI-6 (NEW 2025-10-29): Add macOS unit test lane with coverage
  - Acceptance: New job `macos-python` runs `pytest -q --cov=orchestrator --cov=cli --cov-fail-under=85` with PYTHONHASHSEED=0; job green.
  - Validation: `uname` shows `Darwin` in job logs; coverage XML uploaded as artifact.
- [ ] CI-7 (NEW 2025-10-29): Perf baseline delta (≤5%)
  - Acceptance: Bench job compares current vs baseline JSON; fails if any metric regresses by >5%; uploads diff artifact.
  - Validation: `PYTHONHASHSEED=0 python scripts/bench_check.py --baseline bench/baseline --current . --threshold 0.05`
- [ ] CI-8 (NEW 2025-10-29): Stronger reproducibility check
  - Acceptance: `scripts/repro_check.py` rebuilds twice with same SOURCE_DATE_EPOCH and asserts identical SHA256 for wheels; job fails on mismatch.
  - Validation: `PYTHONHASHSEED=0 SOURCE_DATE_EPOCH=1700000000 python scripts/repro_check.py`
- [ ] CI-9 (NEW 2025-10-29): Release artifacts completeness
  - Acceptance: release.yml uploads `dist/sbom.json` and `dist/provenance.json` to the GitHub Release; visible under release assets.
  - Validation: GitHub release for a tag contains both files.
- [ ] CI-10 (NEW 2025-10-29): Windows slow/fast split
  - Acceptance: Windows CI runs two jobs: `windows-python-fast` with `-m "not slow"` and `windows-python-slow` with `-m slow`; both pass.
  - Validation: `PYTHONHASHSEED=0 pytest -q -m "not slow"` and `PYTHONHASHSEED=0 pytest -q -m slow`
- [ ] CI-11 (NEW 2025-10-29): Core-path ≥90% coverage guard
  - Acceptance: `scripts/coverage_guard.py` parses coverage.xml and fails if any of: `orchestrator/*core*` or specified critical modules <90%.
  - Validation: `PYTHONHASHSEED=0 python scripts/coverage_guard.py --paths orchestrator/orchestrator_core.py orchestrator/policy/engine.py`


#### Batch 8 — Third-Pass Addendum (Reflective Review on 2025-10-29)

##### Additional Gaps and Issues (Third-pass — Batch 8)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| CI-12 | Important | Locale determinism across jobs (LC_ALL=C.UTF-8, LANG=C.UTF-8) to stabilize sort/messages. | .github/workflows/ci.yml; pytest.ini | Small |
| CI-13 | Important | Packaging smoke in CI (build sdist/wheel and pip install --no-deps) to catch packaging issues early. | .github/workflows/ci.yml; pyproject.toml | Small |
| CI-14 | Important | CI cache correctness: keys include Python version + OS + hash of pyproject + scripts to avoid stale caches. | .github/workflows/ci.yml | Small |
| CI-15 | Nice-to-have | Coverage artifact merge sanity: upload XML per-OS and run a combine check script; gate on union result. | .github/workflows/ci.yml; scripts/coverage_merge_check.py | Medium |

##### Additional Remediation Tasks (Third-pass — Batch 8)
- [ ] CI-12 (NEW 2025-10-29): Locale determinism
  - Acceptance: All jobs export `LC_ALL=C.UTF-8` and `LANG=C.UTF-8`; logs confirm; no test output differences observed.
  - Validation: `PYTHONHASHSEED=0 LC_ALL=C.UTF-8 LANG=C.UTF-8 python -m pytest -q tests/unit/test_smoke.py::test_true`

- [ ] CI-13 (NEW 2025-10-29): Packaging smoke
  - Acceptance: CI job builds `sdist` and `wheel` and then `pip install --no-deps dist/*.whl`; `python -c "import orchestrator; print(orchestrator.__version__)"` succeeds.
  - Validation: `PYTHONHASHSEED=0 python -m build && python -m pip install --no-deps dist/*.whl && python -c "import orchestrator"`

- [ ] CI-14 (NEW 2025-10-29): Cache key correctness
  - Acceptance: Cache step keys include `${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('pyproject.toml', 'scripts/**', '.github/workflows/**') }}`; cache busts when these change.
  - Validation: Inspect CI logs to see cache miss after modifying pyproject/scripts.

- [ ] CI-15 (NEW 2025-10-29): Coverage merge sanity
  - Acceptance: Each OS uploads coverage.xml; a follow-up job merges and asserts ≥85% overall; failures reported with per-file breakdown.
  - Validation: `PYTHONHASHSEED=0 python scripts/coverage_merge_check.py --inputs cov-linux.xml cov-windows.xml --min 0.85`

## Batch 9: Packaging & Release

### Blueprint Requirements (Summary — Batch 9)
- Wheels/SDist with reproducible builds; SBOM/provenance; CHANGELOG; release notes; upgrade guidance; versioning policy.

### Current Implementation Status (Batch 9)
- Packaging implemented; reproducibility/ SBOM/ provenance in CI; release workflow on tag; docs updated.
- Specification alignment: Mostly aligned
- Production readiness: Needs finalization

### Gaps and Issues (Batch 9)


| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| PR-1 | Important | Versioning policy and upgrade guidance not formalized; add docs. | Docs/Deployment.md; CHANGELOG.md | Small |
| PR-2 | Nice-to-have | Automate CHANGELOG bump on tag; verify release notes attached. | release.yml; scripts/* | Small |

### Remediation Tasks (Batch 9)
- [ ] PR-1: Document versioning (semver/pre-release) and upgrade guidance; CHANGELOG conventions. Acceptance: docs present.
- [ ] PR-2: Ensure release attaches generated release_notes.md; optional CHANGELOG check. Acceptance: release run shows attached notes.

---

#### Batch 9 — Addendum (Second-pass review on 2025-10-29)

##### Additional Gaps and Issues (Batch 9)

| ID | Severity | Description | Affected Files | Effort |
|----|----------|-------------|----------------|--------|
| PR-3 | Important | License metadata mismatch (pyproject says Proprietary but classifiers say MIT); include LICENSE in wheels. | pyproject.toml; LICENSE; .github/workflows/ci.yml | Small |
| PR-4 | Important | Optional PyPI/TestPyPI publish workflow with manual approval and secrets guard; dry-run on PR. | .github/workflows/release.yml | Small |
| PR-5 | Nice-to-have | Automated release notes (conventional commits/compare link) and CHANGELOG enforcement gate. | .github/workflows/release.yml; CHANGELOG.md; scripts/* | Medium |
| PR-6 | Important | Supply chain provenance attestation (SLSA) and optional artifact signing (cosign) with secrets-gated path. | .github/workflows/release.yml | Medium |
| PR-7 | Nice-to-have | README install/verify section with checksum verification against provenance; smoke `import orchestrator`. | README.md; .github/workflows/ci.yml | Small |
| PR-8 | Important | Versioning & deprecation policy doc (semver, pre-release tags, API stability pre-1.0); upgrade guidance detail. | Docs/Versioning.md; Docs/Deployment.md | Small |
| PR-9 | Nice-to-have | Version bump helper (script or Hatch task) and tag consistency check; prevents mismatched versions. | scripts/version_bump.py; pyproject.toml | Medium |
| PR-10 | Important | Release rollback/runbook (yank PyPI, delete GH release, bump fix); checklist with deterministic steps. | Docs/Release-Runbook.md | Small |

##### Additional Remediation Tasks (Batch 9)
- [ ] PR-3 (NEW 2025-10-29): License metadata alignment
  - Acceptance: pyproject license matches classifiers; LICENSE file included in wheel/SDist; `twine check dist/*` passes; unpacked wheel contains LICENSE.
  - Validation: `PYTHONHASHSEED=0 python -m pip install -U build twine && python -m build && python -m twine check dist/*`
- [ ] PR-4 (NEW 2025-10-29): Optional PyPI/TestPyPI publish
  - Acceptance: release workflow supports TestPyPI for pre-releases and PyPI for stable with manual approval; guarded by `PYPI_TOKEN`/`TEST_PYPI_TOKEN` presence; dry-run mode on PRs.
  - Validation: Inspect workflow run: publish steps skipped without secrets; logs show `dry-run` on PRs.
- [ ] PR-5 (NEW 2025-10-29): Release notes + CHANGELOG gate
  - Acceptance: Release job generates notes (auto) including compare link; CI fails if CHANGELOG not updated for new version.
  - Validation: `git tag vX && gh release view vX --json body` contains compare link; CI step `changelog-check` green.
- [ ] PR-6 (NEW 2025-10-29): SLSA provenance + cosign (optional)
  - Acceptance: If signing secrets exist, attach `.intoto.jsonl` provenance and `.sig` files per artifact; otherwise skip deterministically.
  - Validation: Release assets include `*.intoto.*` and `*.sig` when secrets provided.
- [ ] PR-7 (NEW 2025-10-29): Install/verify guidance
  - Acceptance: README includes checksum verification instructions against `dist/provenance.json`; CI smoke test imports `orchestrator` and runs `orchestrator --help`.
  - Validation: `python - <<PY\nimport orchestrator; print('ok')\nPY`
- [ ] PR-8 (NEW 2025-10-29): Versioning & deprecation policy
  - Acceptance: New docs define semver, pre-release tags (a, rc), stability before 1.0, deprecation timelines, and upgrade guidance; linked from README and Deployment.
  - Validation: Docs merged; README/Deployment contain links.
- [ ] PR-9 (NEW 2025-10-29): Version bump helper + tag check
  - Acceptance: A helper script or Hatch task updates pyproject version and verifies tag matches version; CI check fails if mismatch.
  - Validation: `python scripts/version_bump.py 0.6.1a0 --dry-run` prints planned edits; CI logs show version/tag check.
- [ ] PR-10 (NEW 2025-10-29): Release rollback/runbook
  - Acceptance: Docs/Release-Runbook.md contains deterministic rollback steps (GH release delete, PyPI yank, version bump), prerequisites, and verification commands.
  - Validation: Doc present and linked from Deployment.



## Cross-Batch Integration — Third-Pass Addendum (Reflective Review on 2025-10-29)

### Additional Gaps and Issues (Cross-batch)

| ID | Severity | Description | Affected Areas | Effort |
|----|----------|-------------|----------------|--------|
| XB-1 | Critical | End-to-end acceptance test (feature-add workflow) missing: spec→code→tests→failing test→fix→green; enforced in CI with deterministic seeds/time. | workflows/*; tests/e2e/*; .github/workflows/ci.yml | Large |
| XB-2 | Important | Deterministic replay E2E: capture run WAL/telemetry and reproduce outputs and ordering with `--replay` across Context Engine + Orchestrator + Transports. | orchestrator/wal/*; cli/orchestrator_cli.py; tests/e2e/* | Large |
| XB-3 | Important | Dogfooding automation: periodic job uses VLTAIR to open a PR with generated tests/docs; results archived. | .github/workflows/dogfood.yml; scripts/* | Medium |
| XB-4 | Important | ADR index and traceability matrix linking Blueprint → tasks → tests; stale detector CI step. | Docs/ADRs/*; Docs/Production-Task-List.md; scripts/traceability_check.py | Medium |
| XB-5 | Nice-to-have | SDK parity planning + skeleton TS SDK: compile-only `tsc --noEmit` job and README; no runtime deps. | sdk/typescript/*; .github/workflows/ci.yml; Docs/SDK.md | Medium |

### Remediation Tasks (Cross-batch)
- [x] XB-1 (NEW 2025-10-29): E2E acceptance workflow
  - Acceptance: CI job `e2e-acceptance` executes the end-to-end scenario with `PYTHONHASHSEED=0 TZ=UTC LC_ALL=C.UTF-8`; all phases complete under time and token budgets; artifacts include logs and coverage.
  - Validation: `PYTHONHASHSEED=0 TZ=UTC LC_ALL=C.UTF-8 python -m pytest -q tests/e2e/feature_add_workflow_test.py::test_end_to_end`

- [ ] XB-2 (NEW 2025-10-29): Deterministic replay CLI
  - Acceptance: `orchestrator --replay <run_id>` reproduces outputs without external calls; diff vs live run is empty for recorded fields; docs updated.
  - Validation: `PYTHONHASHSEED=0 python -m pytest -q tests/e2e/replay_test.py::test_replay_matches_live`

- [ ] XB-3 (NEW 2025-10-29): Dogfood workflow
  - Acceptance: Scheduled GitHub Action opens/updates a PR that adds a small test or doc snippet produced by VLTAIR; CI proves determinism; job skips on forks.
  - Validation: Inspect Action run; PR contains generated artifact; CI green.

- [ ] XB-4 (NEW 2025-10-29): ADR index + traceability
  - Acceptance: `scripts/traceability_check.py` verifies each Blueprint requirement maps to at least one task and one test; CI step fails if gaps.
  - Validation: `PYTHONHASHSEED=0 python scripts/traceability_check.py --blueprint Docs/Blueprint.md --tasks Docs/Production-Task-List.md --tests tests/`

## Summary and Prioritization

### Blocker Issues (Must fix before release)
- None designated as Blocker in Batch 1; WAL/Snapshot and Versioning are Critical and scoped for Phase 8 per roadmap.

### Critical Issues (High priority)
- CE-1: WAL + Snapshot integration (ADR + plan)
- CE-2: Versioning/Merge support in ContextStore

### Overall Production Readiness Assessment
- Context Engine: ~70% complete for production (core search wired; determinism set; tests exist). Critical durability/versioning features pending (Phase 8). Metadata/filters/perf gating to be addressed with small/medium effort.
## Next Batch Focus

Given the Critical items identified and Blueprint priorities, the next execution batch should focus on:

- Batch 3: Orchestrator Core — WAL + snapshot ADR and stubs (OC-1), error taxonomy (OC-2), DAG validation (OC-4), and idempotency/retry metadata (OC-3). These are foundational for production durability and correctness.