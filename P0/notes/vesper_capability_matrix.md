# Vesper Capability Matrix - Search, Filters, Fusion, IO

## Purpose
Inventory current Vesper capabilities and map them to Blueprint requirements for the context engine.

## Search Capabilities
- Dense vector search:
  - HNSW (in-memory): fast recall/latency
  - IVF-PQ/OPQ (disk/memory hybrid): compact storage
- Sparse/BM25:
  - BM25 term matching present (see src/index/bm25.cpp)
- Hybrid fusion:
  - fusion_algorithms.cpp, hybrid_searcher.cpp merge dense and sparse candidates

## Metadata Filters
- metadata_store.cpp: key/value filters; confirm operators and types supported
- Query planner: verify filter pushdown in hybrid flows

## Collections and Management
- index_manager.cpp: lifecycle (create, open, insert, commit)
- query_planner.cpp: top-k planning and fusion hooks

## IO and Snapshots (optional early)
- async_io.cpp, prefetch_manager.cpp: IO pipelines
- Snapshot/WAL: confirm presence and maturity; feature-gate in early phases

## Return Formats
- IDs, scores, optional metadata; confirm stable structures for binding surface

## Performance Envelopes
- Micro benches in bench/micro/** measure hybrid search P50/P95
- Target: P50 about 1-3 ms for representative session sizes

## Risks and Gaps
- Uniform hybrid entrypoint for dense+sparse+filters API for bindings
- Filter expression richness (operators, types)
- Snapshot/rollback maturity (gated to later phases)

## Binding Targets (Phase 1)
- engine_init(config)
- open_collection(name, schema)
- upsert(documents with embeddings and metadata)
- search_hybrid(query_text or embedding, k, filters, options)
- (optional) snapshot(label), wal_flush() disabled by default
