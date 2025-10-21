import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _ensure_pyvesper_on_path() -> None:
  # Try to import; if it fails, add the built extension path (Windows Release layout)
  try:
    import pyvesper  # noqa: F401
    return
  except Exception:
    pass

  repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
  candidate = os.path.join(repo_root, "build", "bindings", "python", "pyvesper", "Release")
  if os.path.isdir(candidate):
    sys.path.insert(0, candidate)
  try:
    import pyvesper  # noqa: F401
  except Exception:
    pytest.skip("pyvesper not importable; build the extension first")


_ensure_pyvesper_on_path()

try:
  import pyvesper  # noqa: E402
except ImportError:
  pytest.skip("pyvesper not importable; skipping context_store_test", allow_module_level=True)

from orchestrator.context.vesper_context_store import VesperContextStore  # noqa: E402
from orchestrator.context.context_store import ContextStore  # noqa: E402
from orchestrator.context.models import CodeDocument, TextDocument  # noqa: E402


def _hybrid_result(doc_id: int, dense: float, sparse: float, fused: float, dr: int, sr: int):
  r = pyvesper.HybridResult()
  r.doc_id = doc_id
  r.dense_score = dense
  r.sparse_score = sparse
  r.fused_score = fused
  r.dense_rank = dr
  r.sparse_rank = sr
  return r


@pytest.mark.parametrize(
  "mode, expected_strategy, expected_fusion",
  [
    ("hybrid", pyvesper.QueryStrategy.AUTO, pyvesper.FusionAlgorithm.RECIPROCAL_RANK),
    ("dense", pyvesper.QueryStrategy.DENSE_FIRST, pyvesper.FusionAlgorithm.WEIGHTED_SUM),
    ("sparse", pyvesper.QueryStrategy.SPARSE_FIRST, pyvesper.FusionAlgorithm.WEIGHTED_SUM),
  ],
)
def test_contextstore_search_mode_mapping(mode, expected_strategy, expected_fusion):
  engine = MagicMock()
  engine.search_hybrid.return_value = [
    _hybrid_result(1, 0.9, 0.8, 0.85, 1, 1),
    _hybrid_result(2, 0.7, 0.9, 0.80, 2, 2),
  ]

  store = VesperContextStore(engine=engine)
  results = store.search(
    text="hello",
    embedding=[0.1, 0.2],
    k=5,
    mode=mode,
    filters={"type": "code"},
    rrf_k=42.0,
    dense_weight=0.6,
    sparse_weight=0.4,
    rerank_factor=7,
  )

  # Verify engine called with proper arguments
  assert engine.search_hybrid.call_count == 1
  args, kwargs = engine.search_hybrid.call_args
  assert args[0] == "hello"
  assert args[1] == [0.1, 0.2]
  assert args[2] == {"type": "code"}

  cfg = args[3]
  assert isinstance(cfg, pyvesper.HybridSearchConfig)
  assert cfg.k == 5
  assert cfg.rrf_k == pytest.approx(42.0)
  assert cfg.dense_weight == pytest.approx(0.6)
  assert cfg.sparse_weight == pytest.approx(0.4)
  assert cfg.rerank_factor == 7
  assert cfg.query_strategy == expected_strategy
  assert cfg.fusion_algorithm == expected_fusion

  # Verify result mapping
  assert len(results) == 2
  assert results[0].doc_id == 1
  assert results[0].score == pytest.approx(0.85)
  assert results[0].dense_score == pytest.approx(0.9)
  assert results[0].sparse_score == pytest.approx(0.8)
  assert results[0].dense_rank == 1
  assert results[0].sparse_rank == 1

def test_contextstore_add_code_documents_calls_backend_correctly():
  engine = MagicMock()
  store = ContextStore(backend=VesperContextStore(engine=engine))
  docs = [CodeDocument(id=1, path="a.cpp", language="cpp", content="int a;", metadata={"origin": "user"})]
  vecs = [[0.1, 0.2]]
  store.add_code_documents(docs, vecs)
  # Validate upsert call shape via VesperContextStore.add -> engine.upsert
  assert engine.upsert.call_count == 1
  args, kwargs = engine.upsert.call_args
  ids, vectors, metas = args
  assert ids == [1]
  assert vectors == vecs
  assert metas[0]["type"] == "code"
  assert metas[0]["path"] == "a.cpp"
  assert metas[0]["language"] == "cpp"
  assert "idempotency_key" in metas[0]


def test_contextstore_add_text_documents_calls_backend_correctly():
  engine = MagicMock()
  store = ContextStore(backend=VesperContextStore(engine=engine))
  docs = [TextDocument(id=2, title="n", content="hello", metadata={"origin": "agent"})]
  vecs = [[0.3, 0.4]]
  store.add_text_documents(docs, vecs)
  assert engine.upsert.call_count == 1
  args, kwargs = engine.upsert.call_args
  ids, vectors, metas = args
  assert ids == [2]
  assert vectors == vecs
  assert metas[0]["type"] == "text"
  assert metas[0]["title"] == "n"
  assert "idempotency_key" in metas[0]


