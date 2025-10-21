from unittest.mock import MagicMock

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore


def test_analysis_artifact_persisted_as_text_doc():
  o = Orchestrator()
  fake_store = MagicMock(spec=ContextStore)
  o.set_context_store(fake_store)
  res = {
    "type": "AgentResult",
    "id": "r2",
    "parentId": "t2",
    "agent": "StaticAnalysisAgent",
    "payload": {
      "artifacts": [
        {"kind": "analysis", "target": "foo.cpp", "details": "No major issues found"}
      ]
    },
  }
  o.apply_agent_result(res)
  assert fake_store.add_text_documents.call_count == 1
  args, _ = fake_store.add_text_documents.call_args
  docs, _ = args
  assert docs[0].title.startswith("analysis:")
  assert "No major issues" in docs[0].content


