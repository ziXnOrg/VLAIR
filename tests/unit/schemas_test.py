import pytest

from orchestrator.schemas.types import AgentTask, AgentResult, AgentError
from orchestrator.schemas.validators import (
  validate_agent_task,
  validate_agent_result,
  validate_agent_error,
)


def test_agent_task_valid():
  data = {
    "type": "AgentTask",
    "id": "uuid-1",
    "parentId": None,
    "agent": "CodeGenAgent",
    "payload": {"action": "create", "target": "a.cpp"},
    "constraints": {"timeoutMs": 1000, "deterministic": True, "idempotencyKey": "k"},
    "protocolVersion": 1,
  }
  model = validate_agent_task(data)
  assert model.agent == "CodeGenAgent"


def test_agent_task_invalid_missing_required():
  data = {"type": "AgentTask", "id": "uuid-1"}
  with pytest.raises(ValueError):
    validate_agent_task(data)


def test_agent_result_valid():
  data = {
    "type": "AgentResult",
    "id": "uuid-2",
    "parentId": "uuid-1",
    "agent": "CodeGenAgent",
    "payload": {"delta": {"doc": {"id": "d1", "path": "a.cpp", "content": "int x;"}}, "newTasks": [{"agent": "TestAgent", "payload": {"mode": "generate", "target": "a.cpp"}}]},
    "metrics": {"tokensUsed": 10, "timeMs": 50},
  }
  model = validate_agent_result(data)
  assert model.metrics and model.metrics.tokensUsed == 10


def test_agent_result_invalid_payload_shape():
  bad = {
    "type": "AgentResult",
    "id": "uuid-9",
    "parentId": "uuid-1",
    "agent": "CodeGenAgent",
    "payload": {"delta": {"doc": 123}},
  }
  with pytest.raises(ValueError):
    validate_agent_result(bad)


def test_agent_error_valid():
  data = {
    "type": "AgentError",
    "id": "uuid-3",
    "parentId": "uuid-1",
    "agent": "CodeGenAgent",
    "error": {"code": "Timeout", "message": "Exceeded"},
  }
  model = validate_agent_error(data)
  assert model.error.code == "Timeout"


def test_agent_task_payload_shapes_by_agent():
  # CodeGen
  cg = {
    "type": "AgentTask",
    "id": "t1",
    "agent": "CodeGenAgent",
    "payload": {"action": "create", "target": "a.cpp", "content": "int x;"},
  }
  assert validate_agent_task(cg).payload["target"] == "a.cpp"

  # Test generate
  tg = {
    "type": "AgentTask",
    "id": "t2",
    "agent": "TestAgent",
    "payload": {"mode": "generate", "target": "a.cpp"},
  }
  assert validate_agent_task(tg).payload["mode"] == "generate"

  # Test execute
  te = {
    "type": "AgentTask",
    "id": "t3",
    "agent": "TestAgent",
    "payload": {"mode": "execute", "tests": ["::all"]},
  }
  assert validate_agent_task(te).payload["mode"] == "execute"

  # StaticAnalysis
  sa = {
    "type": "AgentTask",
    "id": "t4",
    "agent": "StaticAnalysisAgent",
    "payload": {"target": ["a.cpp", "b.cpp"], "severity": "warn"},
  }
  assert validate_agent_task(sa).payload["severity"] == "warn"

  # Debug
  dbg = {
    "type": "AgentTask",
    "id": "t5",
    "agent": "DebugAgent",
    "payload": {"errorLog": "stacktrace..."},
  }
  assert validate_agent_task(dbg).payload["errorLog"]


