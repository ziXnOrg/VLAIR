from typing import Any, Dict, List, Optional, Sequence, Union

import pytest

from orchestrator.context.context_store import ContextStore
from orchestrator.context.models import SearchResult


class MockBackend:
  def __init__(self) -> None:
    self.calls: List[Dict[str, Any]] = []

  def search(self,
             text: str = "",
             embedding: Optional[Union[Sequence[float], Any]] = None,
             *,
             k: int = 10,
             mode: "str" = "hybrid",
             filters: Optional[Union[Dict[str, str], str]] = None,
             rrf_k: float = 60.0,
             dense_weight: float = 0.5,
             sparse_weight: float = 0.5,
             rerank_factor: int = 10) -> List[SearchResult]:
    self.calls.append({
      "text": text,
      "k": k,
      "mode": mode,
      "filters": filters,
      "rrf_k": rrf_k,
      "dense_weight": dense_weight,
      "sparse_weight": sparse_weight,
      "rerank_factor": rerank_factor,
    })
    # Return a dummy result
    return [SearchResult(doc_id=1, score=1.0, dense_score=0.5, sparse_score=0.5, dense_rank=1, sparse_rank=1, metadata=None)]


def test_structured_query_forwards_params() -> None:
  backend = MockBackend()
  ctx = ContextStore(backend=backend)  # type: ignore[arg-type]

  out = ctx.structured_query(text="hello", k=7, mode="hybrid", filters={"type": "text"}, rrf_k=42.0, dense_weight=0.7, sparse_weight=0.3, rerank_factor=5)

  assert isinstance(out, list)
  assert len(out) == 1
  assert out[0].doc_id == 1
  assert backend.calls, "backend.search was not called"
  call = backend.calls[-1]
  assert call["text"] == "hello"
  assert call["k"] == 7
  assert call["mode"] == "hybrid"
  assert call["filters"] == {"type": "text"}
  assert call["rrf_k"] == 42.0
  assert call["dense_weight"] == 0.7
  assert call["sparse_weight"] == 0.3
  assert call["rerank_factor"] == 5
