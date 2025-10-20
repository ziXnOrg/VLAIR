# Implementation Alignment Report

## Mapping Blueprint -> Vesper Surfaces

- Hybrid Search (dense + sparse):
  - Vesper: src/search/hybrid_searcher.cpp, src/search/fusion_algorithms.cpp
  - Index backends: src/index/{hnsw.cpp, ivf_pq.cpp, bm25.cpp}
  - Query planner and index manager: src/index/{query_planner.cpp, index_manager.cpp}

- Metadata Filters:
  - Vesper: src/metadata/metadata_store.cpp (confirm operators/types and filter pushdown)

- Context Engine API (to expose via bindings):
  - engine_init(config)
  - open_collection(name, schema)
  - upsert(documents with embeddings + metadata)
  - search_hybrid(query_text|embedding, k, filters, options)
  - (optional later) snapshot(label), wal_flush()

- Message Schemas (Orchestrator <-> Agents):
  - AgentTask.schema.json
  - AgentResult.schema.json (delta, artifacts, newTasks, metrics)
  - AgentError.schema.json

- Determinism & Reproducibility:
  - Enforce temp=0, fixed seeds; idempotency keys; record model+params

## Phase 1 Binding Surface (Minimal, Deterministic)
- Keep search/write surfaces narrow and stable; feature-gate optional IO (snapshot/WAL)

## Risk and Mitigation
- Filter expressiveness: document supported operators early; add translation layer if needed
- Hybrid API shape: expose one stable entrypoint that composes dense + sparse + filters
- IO features: defer to Phase 3 if stability unclear

## Next Steps
- Proceed with pybind11 scaffolding and ContextStore implementation per Phase 1 plan
- Validate performance envelopes with micro-benchmarks; store artifacts
