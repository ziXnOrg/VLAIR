from __future__ import annotations

from typing import Any, Dict

from pydantic import ValidationError

from .types import (
  AgentTask,
  AgentResult,
  AgentError,
  CodeGenPayload,
  TestGenPayload,
  TestExecPayload,
  StaticAnalysisPayload,
  DebugPayload,
  ResultPayload,
)


def validate_agent_task(data: Dict[str, Any]) -> AgentTask:
  try:
    model = AgentTask(**data)
    # Payload shape validation by agent kind
    agent = model.agent
    p = model.payload
    try:
      if agent == "CodeGenAgent":
        CodeGenPayload(**p)
      elif agent == "TestAgent" and p.get("mode") == "generate":
        TestGenPayload(**p)
      elif agent == "TestAgent" and p.get("mode") == "execute":
        TestExecPayload(**p)
      elif agent == "StaticAnalysisAgent":
        StaticAnalysisPayload(**p)
      elif agent == "DebugAgent":
        DebugPayload(**p)
      # else allow flexible payloads for other agents
    except ValidationError as e:
      raise ValueError(str(e))
    return model
  except ValidationError as e:  # pragma: no cover
    raise ValueError(str(e))


def validate_agent_result(data: Dict[str, Any]) -> AgentResult:
  try:
    model = AgentResult(**data)
    # Result payload structural validation (delta/artifacts/newTasks)
    ResultPayload(**model.payload)
    return model
  except ValidationError as e:  # pragma: no cover
    raise ValueError(str(e))


def validate_agent_error(data: Dict[str, Any]) -> AgentError:
  try:
    return AgentError(**data)
  except ValidationError as e:  # pragma: no cover
    raise ValueError(str(e))


