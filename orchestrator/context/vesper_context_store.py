from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Union

import pyvesper

from .models import SearchResult

Mode = Literal["dense", "sparse", "hybrid"]


class VesperContextStore:
  def __init__(self, engine: Optional[pyvesper.Engine] = None) -> None:
    self._engine = engine or pyvesper.Engine()
    # Deterministic by default per project rules
    self._engine.set_deterministic(True)

  def initialize(self, config: Dict[str, str]) -> None:
    self._engine.initialize(config)

  def open_scope(self, name: str, schema_json: Optional[str] = None) -> None:
    self._engine.open_collection(name, schema_json)

  def add(self,
          ids: Sequence[int],
          vectors: Sequence[Union[Sequence[float], Any]],
          metadata: Sequence[Dict[str, str]]) -> None:
    self._engine.upsert(list(ids), vectors, list(metadata))

  def search(self,
             text: str = "",
             embedding: Optional[Union[Sequence[float], Any]] = None,
             *,
             k: int = 10,
             mode: Mode = "hybrid",
             filters: Optional[Union[Dict[str, str], str]] = None,
             rrf_k: float = 60.0,
             dense_weight: float = 0.5,
             sparse_weight: float = 0.5,
             rerank_factor: int = 10) -> List[SearchResult]:
    cfg = pyvesper.HybridSearchConfig()
    cfg.k = int(k)
    cfg.rrf_k = float(rrf_k)
    cfg.dense_weight = float(dense_weight)
    cfg.sparse_weight = float(sparse_weight)
    cfg.rerank_factor = int(rerank_factor)

    if mode == "dense":
      cfg.query_strategy = pyvesper.QueryStrategy.DENSE_FIRST
      cfg.fusion_algorithm = pyvesper.FusionAlgorithm.WEIGHTED_SUM
    elif mode == "sparse":
      cfg.query_strategy = pyvesper.QueryStrategy.SPARSE_FIRST
      cfg.fusion_algorithm = pyvesper.FusionAlgorithm.WEIGHTED_SUM
    else:
      cfg.query_strategy = pyvesper.QueryStrategy.AUTO
      cfg.fusion_algorithm = pyvesper.FusionAlgorithm.RECIPROCAL_RANK

    results = self._engine.search_hybrid(text, embedding, filters, cfg)

    out: List[SearchResult] = []
    for r in results:
      out.append(
        SearchResult(
          doc_id=int(r.doc_id),
          score=float(r.fused_score),
          dense_score=float(r.dense_score),
          sparse_score=float(r.sparse_score),
          dense_rank=int(r.dense_rank),
          sparse_rank=int(r.sparse_rank),
          metadata=None,
        )
      )
    return out
