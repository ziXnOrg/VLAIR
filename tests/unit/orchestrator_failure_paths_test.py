import pytest

from orchestrator.core.orchestrator import Orchestrator


def test_apply_agent_result_ignores_malformed_delta():
  o = Orchestrator()
  # malformed delta (not a dict)
  bad = {
    "type": "AgentResult",
    "id": "r1",
    "parentId": "t1",
    "agent": "CodeGenAgent",
    "payload": {"delta": 123}
  }
  # Should not raise
  o.apply_agent_result(bad)


def test_validate_agent_result_rejects_missing_fields():
  o = Orchestrator()
  invalid = {
    "type": "AgentResult",
    # missing id/parentId
    "agent": "CodeGenAgent",
    "payload": {}
  }
  with pytest.raises(Exception):
    # Route through public validator path
    o.handle_result(invalid)


def test_apply_agent_result_rejects_bad_test_artifact_fields():
  o = Orchestrator()
  bad_missing_name = {
    "type": "AgentResult",
    "id": "r1",
    "parentId": "t1",
    "agent": "TestAgent",
    "payload": {"artifacts": [{"kind": "test_result", "status": "pass"}]}
  }
  with pytest.raises(ValueError) as e1:
    o.apply_agent_result(bad_missing_name)
  assert "missing required field 'test_name'" in str(e1.value)

  bad_missing_status = {
    "type": "AgentResult",
    "id": "r1",
    "parentId": "t1",
    "agent": "TestAgent",
    "payload": {"artifacts": [{"kind": "test_result", "test_name": "t"}]}
  }
  with pytest.raises(ValueError) as e2:
    o.apply_agent_result(bad_missing_status)
  assert "missing required field 'status'" in str(e2.value)


