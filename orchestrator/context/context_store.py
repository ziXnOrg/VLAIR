from __future__ import annotations

from typing import List, Optional, Sequence, Union, Dict, Any, TYPE_CHECKING

from .models import SearchResult
from .models import TestResultDocument, DiffSummaryDocument, CoverageHintDocument
from typing import Literal
Mode = Literal["dense", "sparse", "hybrid"]
if TYPE_CHECKING:
  from .vesper_context_store import VesperContextStore
from .models import CodeDocument, TextDocument
from .idempotency import make_idempotency_key


class ContextStore:
  def __init__(self, backend: Optional["VesperContextStore"] = None) -> None:
    if backend is None:
      # Lazy import to avoid importing pyvesper at module load (tests can inject mocks)
      from .vesper_context_store import VesperContextStore  # type: ignore
      self._backend = VesperContextStore()
    else:
      self._backend = backend

  def initialize(self, config: Dict[str, str]) -> None:
    self._backend.initialize(config)

  def open_scope(self, name: str, schema_json: Optional[str] = None) -> None:
    self._backend.open_scope(name, schema_json)

  def add(self,
          ids: Sequence[int],
          vectors: Sequence[Union[Sequence[float], Any]],
          metadata: Sequence[Dict[str, str]]) -> None:
    self._backend.add(ids, vectors, metadata)

  def add_code_documents(self,
                         docs: Sequence[CodeDocument],
                         vectors: Sequence[Union[Sequence[float], Any]]) -> None:
    if len(docs) != len(vectors):
      raise ValueError("docs and vectors must have same length")
    ids: List[int] = []
    meta: List[Dict[str, str]] = []
    for d in docs:
      ids.append(d.id)
      m: Dict[str, str] = {
        **{k: str(v) for k, v in d.metadata.items()},
        "type": "code",
        "path": d.path,
        "language": d.language,
      }
      m["idempotency_key"] = make_idempotency_key("add_code_document", {"id": d.id, "path": d.path, "content": d.content})
      meta.append(m)
    self._backend.add(ids, vectors, meta)

  def add_text_documents(self,
                         docs: Sequence[TextDocument],
                         vectors: Sequence[Union[Sequence[float], Any]]) -> None:
    if len(docs) != len(vectors):
      raise ValueError("docs and vectors must have same length")
    ids: List[int] = []
    meta: List[Dict[str, str]] = []
    for d in docs:
      ids.append(d.id)
      m: Dict[str, str] = {
        **{k: str(v) for k, v in d.metadata.items()},
        "type": "text",
        "title": d.title,
      }
      m["idempotency_key"] = make_idempotency_key("add_text_document", {"id": d.id, "title": d.title, "content": d.content})
      meta.append(m)
    self._backend.add(ids, vectors, meta)

  def add_test_results(self, results: Sequence[TestResultDocument]) -> None:
    ids: List[int] = []
    vectors: List[Sequence[float]] = []
    meta: List[Dict[str, str]] = []
    for r in results:
      ids.append(r.id)
      # Use a dummy 1D vector; backends may ignore for non-searchable docs or support sparse-only later
      vectors.append([0.0])
      m: Dict[str, str] = {
        **{k: str(v) for k, v in r.metadata.items()},
        "type": "test_result",
        "test_name": r.test_name,
        "status": r.status,
      }
      if r.log is not None:
        # Keep logs out of metadata to avoid bloat; include a hash instead
        import hashlib
        m["log_hash"] = hashlib.sha256(r.log.encode("utf-8")).hexdigest()
      meta.append(m)
    self._backend.add(ids, vectors, meta)

  def add_diff_summaries(self, diffs: Sequence[DiffSummaryDocument]) -> None:
    ids: List[int] = []
    vectors: List[Sequence[float]] = []
    meta: List[Dict[str, str]] = []
    for d in diffs:
      ids.append(d.id)
      vectors.append([0.0])
      m: Dict[str, str] = {
        **{k: str(v) for k, v in d.metadata.items()},
        "type": "diff_summary",
        "target": d.target,
        "files_changed": str(d.files_changed),
        "insertions": str(d.insertions),
        "deletions": str(d.deletions),
      }
      meta.append(m)
    self._backend.add(ids, vectors, meta)

  def add_coverage_hints(self, hints: Sequence[CoverageHintDocument]) -> None:
    ids: List[int] = []
    vectors: List[Sequence[float]] = []
    meta: List[Dict[str, str]] = []
    for h in hints:
      ids.append(h.id)
      vectors.append([0.0])
      m: Dict[str, str] = {
        **{k: str(v) for k, v in h.metadata.items()},
        "type": "coverage_hint",
        "files": ",".join(h.files),
        "line_rate": str(h.line_rate),
      }
      meta.append(m)
    self._backend.add(ids, vectors, meta)

  def search(self,
             text: str = "",
             embedding: Optional[Union[Sequence[float], Any]] = None,
             *,
             k: int = 10,
             mode: Mode = "hybrid",
             filters: Optional[Union[Dict[str, str], str]] = None) -> List[SearchResult]:
    return self._backend.search(text, embedding, k=k, mode=mode, filters=filters)

  def structured_query(self,
                       *,
                       text: str = "",
                       embedding: Optional[Union[Sequence[float], Any]] = None,
                       k: int = 10,
                       mode: Mode = "hybrid",
                       filters: Optional[Union[Dict[str, str], str]] = None,
                       rrf_k: float = 60.0,
                       dense_weight: float = 0.5,
                       sparse_weight: float = 0.5,
                       rerank_factor: int = 10) -> List[SearchResult]:
    """Minimal structured query wrapper for advanced knobs.

    This forwards to the backend search with explicit fusion/strategy parameters.
    """
    # Delegate to backend with extended parameters if available
    backend = getattr(self._backend, "search")
    return backend(text, embedding, k=k, mode=mode, filters=filters,
                   rrf_k=rrf_k, dense_weight=dense_weight, sparse_weight=sparse_weight,
                   rerank_factor=rerank_factor)
