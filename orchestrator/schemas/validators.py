from __future__ import annotations

from typing import Any, Dict, List

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


ALLOWED_ANALYSIS_SEVERITY = {"info", "warn", "error"}


def _validate_analysis_artifacts(agent: str, payload: Dict[str, Any]) -> None:
  if agent != "StaticAnalysisAgent":
    return
  arts_any = payload.get("artifacts")
  if not isinstance(arts_any, list):
    return
  for item in arts_any:
    if not isinstance(item, dict):
      continue
    if item.get("kind") != "analysis":
      continue
    if item.get("details") is None:
      raise ValueError("analysis artifact missing 'details'")
    sev = str(item.get("severity", "info"))
    if sev not in ALLOWED_ANALYSIS_SEVERITY:
      raise ValueError(f"analysis artifact invalid 'severity': {sev}")
    suggestions = item.get("suggestions")
    if suggestions is not None:
      if not isinstance(suggestions, list):
        raise ValueError("analysis artifact 'suggestions' must be a list when provided")
      if len(suggestions) > 10:
        raise ValueError("analysis artifact 'suggestions' too many items (>10)")
      for s in suggestions:
        if not isinstance(s, str):
          raise ValueError("analysis artifact 'suggestions' items must be strings")
        if len(s) > 256:
          raise ValueError("analysis artifact 'suggestions' item exceeds 256 chars")


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
    # Additional hardening for StaticAnalysisAgent analysis artifacts
    _validate_analysis_artifacts(model.agent, model.payload)
    return model
  except ValidationError as e:  # pragma: no cover
    raise ValueError(str(e))


def validate_agent_error(data: Dict[str, Any]) -> AgentError:
  try:
    return AgentError(**data)
  except ValidationError as e:  # pragma: no cover
    raise ValueError(str(e))


