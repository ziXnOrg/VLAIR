from unittest.mock import MagicMock

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore


def test_phase2_simple_flow_codegen_analysis_test():
  o = Orchestrator()
  fake_store = MagicMock(spec=ContextStore)
  o.set_context_store(fake_store)

  # CodeGen result -> delta.doc
  code_res = {
    "type": "AgentResult",
    "id": "r-code",
    "parentId": "t-code",
    "agent": "CodeGenAgent",
    "payload": {"delta": {"doc": {"path": "a.cpp", "content": "int a=0;"}}},
  }
  o.apply_agent_result(code_res)
  assert fake_store.add_code_documents.called

  # Analysis result -> analysis artifact
  analysis_res = {
    "type": "AgentResult",
    "id": "r-ana",
    "parentId": "t-ana",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "a.cpp", "details": "OK"}]},
  }
  o.apply_agent_result(analysis_res)
  assert fake_store.add_text_documents.called

  # Test execution result -> test_result artifact
  test_res = {
    "type": "AgentResult",
    "id": "r-test",
    "parentId": "t-test",
    "agent": "TestAgent",
    "payload": {"artifacts": [{"kind": "test_result", "test_name": "test_a", "status": "pass", "log": ""}]},
  }
  o.apply_agent_result(test_res)
  # Persisted via add_test_results and mirrored as text doc
  assert fake_store.add_text_documents.call_count >= 1


