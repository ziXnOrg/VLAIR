from __future__ import annotations

import time
from unittest.mock import Mock

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.context.context_store import ContextStore


def test_e2e_failing_test_fix_loop() -> None:
  mock_store = Mock(spec=ContextStore)
  o = Orchestrator()
  o.set_context_store(mock_store)

  # Start with a failing test execution (simulate via TestAgent execute with paths -> sandbox mock is not invoked here)
  t_test_fail = {"type":"AgentTask","id":"t-fail","agent":"TestAgent","payload":{"mode":"execute","target":"src/bug.cpp","test":"test_bug","paths":[]}}
  out_fail = o.submit_task(t_test_fail)
  assert out_fail["accepted"] is True

  # Submit DebugAgent to propose a patch
  t_debug = {"type":"AgentTask","id":"t-debug","agent":"DebugAgent","payload":{"errorLog":"AssertionError","target":"src/bug.cpp"}}
  out_debug = o.submit_task(t_debug)
  assert out_debug["accepted"] is True

  # Submit CodeGenAgent to apply the patch (in real loop, debug might create a new task)
  t_codegen = {"type":"AgentTask","id":"t-code","agent":"CodeGenAgent","payload":{"action":"modify","target":"src/bug.cpp"}}
  out_code = o.submit_task(t_codegen)
  assert out_code["accepted"] is True

  # Re-run tests
  t_test_pass = {"type":"AgentTask","id":"t-pass","agent":"TestAgent","payload":{"mode":"execute","target":"src/bug.cpp","test":"test_bug"}}
  out_pass = o.submit_task(t_test_pass)
  assert out_pass["accepted"] is True

  time.sleep(0.3)
  # Persistence happened along the loop
  assert mock_store.add_code_documents.called
  assert mock_store.add_text_documents.called
  assert mock_store.add_test_results.called
