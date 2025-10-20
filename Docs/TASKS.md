# Project Task List (Next 15)

| # | Task Name | Description | Assignee | Priority | Status | Start Date | Due Date | References/Notes |
|---:|---|---|---|---|---|---|---|---|
| 1 | Extract HybridSearch surface | Enumerate HybridQuery/HybridSearchConfig/HybridResult fields for binding types; finalize config knobs and defaults | Principal Eng | High | Completed | 2025-10-20 | 2025-10-20 | Vesper/include/vesper/search/hybrid_searcher.hpp; Docs/ImplementationPlan.md P0 findings; P1/notes/hybrid_search_surface.md |
| 2 | Filter mapping design | Define JSON/KV grammar -> filter_expr mapping; document accepted operators/types | Principal Eng | High | Completed | 2025-10-20 | 2025-10-21 | P1/notes/filter_mapping_design.md; Vesper/include/vesper/metadata/metadata_store.hpp |
| 3 | Pybind11 type mapping | Design marshaling for embedding (List[float]/numpy), text, filters JSON; errors -> exceptions | Principal Eng | High | Completed | 2025-10-20 | 2025-10-21 | P1/notes/pybind_type_mapping.md |
| 4 | engine.hpp layout | Define engine state holders (IndexManager, BM25Index, HybridSearcher config); deterministic flags | Principal Eng | High | Completed | 2025-10-21 | 2025-10-21 | bindings/python/pyvesper/engine.hpp |
| 5 | engine.cpp skeleton | Implement engine_init/open_collection/upsert/search_hybrid stubs; error propagation | Principal Eng | High | Completed | 2025-10-21 | 2025-10-22 | bindings/python/pyvesper/engine.cpp |
| 6 | module.cpp bindings | Expose PyHybridQuery/Config/Result + functions via pybind11; docstrings, determinism note | Principal Eng | High | Completed | 2025-10-22 | 2025-10-22 | bindings/python/pyvesper/module.cpp |
| 7 | CMake wiring | Link include paths, compile features (C++20), link Vesper targets; wheel build script stub | Build | High | Completed | 2025-10-22 | 2025-10-22 | bindings/python/pyvesper/CMakeLists.txt |
| 8 | ContextStore.search | Map to pyvesper.search_hybrid; strategy from mode (dense/sparse/hybrid); filters conversion | Principal Eng | High | Completed | 2025-10-23 | 2025-10-23 | orchestrator/context/vesper_context_store.py |
| 9 | Context models | Define Document/Result models; add metadata typing and idempotency key helpers | Principal Eng | Medium | Completed | 2025-10-23 | 2025-10-23 | orchestrator/context/models.py |
| 10 | Schema validators | Implement validators.py/types.py; wire to schemas; add round-trip tests | Principal Eng | High | In Progress | 2025-10-24 | 2025-10-24 | orchestrator/schemas/{*.schema.json, validators.py, types.py} |
| 11 | Orchestrator DAG & scheduler | Implement dag.py (deps/ready-set), scheduler.py (bounded concurrency), retries/backoff | Principal Eng | High | In Progress | 2025-10-24 | 2025-10-25 | orchestrator/core/{dag.py,scheduler.py,retries.py,budgets.py} |
| 12 | CLI runner | Minimal `orchestrator run --goal` invoking core and printing trace | Principal Eng | Medium | In Progress | 2025-10-25 | 2025-10-25 | cli/orchestrator_cli.py |
| 13 | Unit tests batch 1 | bindings_test, context_store_test, schemas_test | QA | High | In Progress | 2025-10-25 | 2025-10-26 | tests/unit/* |
| 14 | Integration smoke | search_smoke_test (tiny in-memory dataset) with deterministic checks | QA | High | Pending | 2025-10-26 | 2025-10-26 | tests/integration/search_smoke_test.py |
| 15 | Micro-bench setup | hybrid_search_bench/upsert_bench; capture P50/P95; export CSV | QA | Medium | Not Started | 2025-10-26 | 2025-10-27 | bench/context/* |

Notes:
- All tasks must follow the Production Agentic Workflow (Understanding -> Planning -> Context -> Implementation -> Verification -> Reflection) and re-check Blueprint + rules at batch end.
- Determinism: temp=0, fixed seeds, idempotency keys; record model/version/params in logs for reproducibility.
