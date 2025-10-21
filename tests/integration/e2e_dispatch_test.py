from unittest.mock import Mock

import time

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore
from orchestrator.context.models import CodeDocument, TextDocument


def test_e2e_codegen_analysis_test_flow():
  # Mock ContextStore to capture persistence calls
  mock_store = Mock(spec=ContextStore)
  o = Orchestrator()
  o.set_context_store(mock_store)

  # 1) Submit a CodeGen task (stubs produce delta.doc and diff_summary)
  t1 = {"type": "AgentTask", "id": "t-codegen", "agent": "CodeGenAgent", "payload": {"action": "create", "target": "src/new_feature.cpp"}}
  out1 = o.submit_task(t1)
  assert out1["accepted"] is True

  # 2) Submit an Analysis task (stubs produce analysis artifact)
  t2 = {"type": "AgentTask", "id": "t-analysis", "agent": "StaticAnalysisAgent", "payload": {"target": "src/new_feature.cpp"}}
  out2 = o.submit_task(t2)
  assert out2["accepted"] is True

  # 3) Submit a Test task (stubs produce test_result + coverage_hint)
  t3 = {"type": "AgentTask", "id": "t-test", "agent": "TestAgent", "payload": {"mode": "execute", "target": "src/new_feature.cpp"}}
  out3 = o.submit_task(t3)
  assert out3["accepted"] is True

  # Allow async workers to process
  time.sleep(0.2)

  # Assertions: persistence helpers called
  assert mock_store.add_code_documents.called
  assert mock_store.add_text_documents.called
  assert mock_store.add_test_results.called
