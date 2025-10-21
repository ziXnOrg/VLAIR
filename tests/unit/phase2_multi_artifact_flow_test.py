from unittest.mock import MagicMock

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore


def test_multi_artifact_from_codegen_and_testagent():
  o = Orchestrator()
  fake_store = MagicMock(spec=ContextStore)
  o.set_context_store(fake_store)

  code_res = {
    "type": "AgentResult",
    "id": "r-code",
    "parentId": "t-code",
    "agent": "CodeGenAgent",
    "payload": {
      "delta": {"doc": {"path": "b.cpp", "content": "int b=1;"}},
      "artifacts": [{"kind": "diff_summary", "target": "b.cpp", "summary": {"insertions": 3, "deletions": 1, "files_changed": 1}}]
    },
  }
  o.apply_agent_result(code_res)
  # diff_summary persisted as text doc
  assert fake_store.add_text_documents.call_count >= 1

  test_res = {
    "type": "AgentResult",
    "id": "r-test",
    "parentId": "t-test",
    "agent": "TestAgent",
    "payload": {"artifacts": [
      {"kind": "test_result", "test_name": "test_b", "status": "pass", "log": ""},
      {"kind": "coverage_hint", "files": ["b.cpp"], "line_rate": 0.8}
    ]},
  }
  o.apply_agent_result(test_res)
  # ensure both test result and coverage hint were persisted
  assert fake_store.add_text_documents.call_count >= 2


