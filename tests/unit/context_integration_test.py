from unittest.mock import MagicMock

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore


def test_apply_agent_result_writes_code_doc():
  o = Orchestrator()
  # Patch context store via setter to avoid protected access
  fake_store = MagicMock(spec=ContextStore)
  o.set_context_store(fake_store)
  res = {
    "type": "AgentResult",
    "id": "r1",
    "parentId": "t1",
    "agent": "CodeGenAgent",
    "payload": {"delta": {"doc": {"path": "a.cpp", "content": "int x;"}}},
  }
  o.apply_agent_result(res)
  assert fake_store.add_code_documents.call_count == 1
  args, _ = fake_store.add_code_documents.call_args
  docs, _vectors = args
  assert docs[0].path == "a.cpp"
  assert "origin" in docs[0].metadata


