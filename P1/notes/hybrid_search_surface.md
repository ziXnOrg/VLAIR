# Hybrid Search Surface Extraction (Vesper)

## Sources
- Vesper/include/vesper/search/hybrid_searcher.hpp
- Vesper/src/search/hybrid_searcher.cpp
- Vesper/src/search/fusion_algorithms.cpp
- Vesper/include/vesper/metadata/metadata_store.hpp (filter utils)

## Types to Bind (C++ -> Python)

### PyHybridQuery
- text: str (UTF-8)
- dense_embedding: List[float] (or numpy array of float32)
- filter: Optional[str|Dict[str, Any]]
  - JSON string or KV dict; converted to `filter_expr` via `metadata::utils::parse_filter_json` or `kv_to_filter`

### PyHybridSearchConfig
- k: int (default 10)
- query_strategy: enum { AUTO, DENSE_FIRST, SPARSE_FIRST, PARALLEL }
- fusion_algorithm: enum { RECIPROCAL_RANK, WEIGHTED_SUM, MAX_SCORE, LATE_INTERACTION }
- rrf_k: float (default ~60.0)
- dense_weight: float (0..1, default 0.5)
- sparse_weight: float (0..1, default 0.5)
- rerank_factor: int (default 10)

### PyHybridResult
- doc_id: int (uint64)
- dense_score: float
- sparse_score: float
- fused_score: float
- dense_rank: int
- sparse_rank: int

## Function Surface
- engine_init(config: dict) -> None
- open_collection(name: str, schema: Optional[dict]) -> None
- upsert(docs: List[dict]) -> None
  - doc: {"id": int, "vector": List[float] (float32), "metadata": Dict[str, Any]}
- search_hybrid(query: PyHybridQuery, cfg: PyHybridSearchConfig) -> List[PyHybridResult]
- (feature-gated) snapshot(label: str) -> None
- (feature-gated) wal_flush() -> None

## Strategy & Fusion Details
- Strategies: AUTO determines based on presence of text/embedding; SPARSE_FIRST requires query.text; DENSE_FIRST requires embedding; PARALLEL executes both.
- Fusion:
  - Reciprocal Rank Fusion (RRF): fused by ranks with `rrf_k` parameter
  - Weighted Sum: linear combination via `dense_weight`, `sparse_weight`
  - Max Score: per-id max of normalized scores
  - Late Interaction: stubbed to Weighted Sum for now

## Filters
- Preferred input: JSON expression or KV dict (AND of terms)
- Conversion: `metadata::utils::parse_filter_json(json)` or `kv_to_filter(kv)` -> `filter_expr` -> Roaring bitmap
- Early support target: equality matches and numeric ranges; extended operators TBD in Task 2

## Determinism Considerations
- Hybrid search is deterministic for fixed inputs/config and fixed index state
- Planner history/adaptive tuning should be disabled in deterministic mode (bindings-level flag)
- Record config and seed in logs; idempotency keys for write paths

## Result Ordering and Limits
- Sort by fused_score descending
- Truncate to top-k as configured

## Errors and Validation
- Missing text for SPARSE_FIRST or missing embedding for DENSE_FIRST: return structured error
- Validate embedding dtype/length on input; normalize to float32 contiguous
- Validate enum values; default AUTO/RECIPROCAL_RANK if unspecified

## Next Steps (Feeds Task 3–7)
- Marshaling design for numpy arrays and JSON filter strings
- Enum exposure and docstrings in pybind11
- Wheel packaging and import smoke test
