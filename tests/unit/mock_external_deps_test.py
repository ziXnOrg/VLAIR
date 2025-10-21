from unittest.mock import MagicMock

from orchestrator.context.context_store import ContextStore
from orchestrator.context.models import TextDocument, DiffSummaryDocument, CoverageHintDocument


def test_context_store_add_text_documents_uses_backend_add():
  fake_backend = MagicMock()
  store = ContextStore(backend=fake_backend)
  doc = TextDocument(id=1, title="t", content="c", metadata={"origin": "TestAgent"})
  store.add_text_documents([doc], [[0.0]])
  fake_backend.add.assert_called_once()
  args, kwargs = fake_backend.add.call_args
  ids, vecs, meta = args
  assert ids == [1]
  assert vecs == [[0.0]]
  assert meta[0]["type"] == "text"


def test_context_store_add_diff_and_coverage_use_backend_add():
  fake_backend = MagicMock()
  store = ContextStore(backend=fake_backend)
  diff = DiffSummaryDocument(id=2, target="a.cpp", files_changed=1, insertions=2, deletions=0, metadata={"origin": "CodeGenAgent"})
  cov = CoverageHintDocument(id=3, files=["a.cpp","b.cpp"], line_rate=0.9, metadata={"origin": "TestAgent"})
  store.add_diff_summaries([diff])
  store.add_coverage_hints([cov])
  assert fake_backend.add.call_count == 2
  # Validate last call for coverage
  args, kwargs = fake_backend.add.call_args
  ids, vecs, meta = args
  assert ids == [3]
  assert meta[0]["type"] == "coverage_hint"
  assert "files" in meta[0]


