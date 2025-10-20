import pytest

from orchestrator.core.orchestrator import Orchestrator


def test_orchestrator_submit_task_validates_schema():
  o = Orchestrator()
  task = {
    "type": "AgentTask",
    "id": "t1",
    "agent": "CodeGenAgent",
    "payload": {"action": "create", "target": "a.cpp"},
  }
  res = o.submit_task(task)
  assert res["accepted"] is True
  assert res["taskId"] == "t1"


def test_orchestrator_submit_task_rejects_invalid():
  o = Orchestrator()
  bad = {"type": "AgentTask", "id": "t2", "agent": "CodeGenAgent", "payload": {"action": "noop"}}
  with pytest.raises(ValueError):
    o.submit_task(bad)


def test_orchestrator_handle_result_validates_schema():
  o = Orchestrator()
  res = {
    "type": "AgentResult",
    "id": "r1",
    "parentId": "t1",
    "agent": "CodeGenAgent",
    "payload": {"delta": {"doc": {"id": "d1", "path": "a.cpp", "content": "int x;"}}},
  }
  out = o.handle_result(res)
  assert out["ok"] is True


