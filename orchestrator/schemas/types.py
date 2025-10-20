from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

try:
  # pydantic v1/v2 compatible imports
  from pydantic import BaseModel, Field
except Exception as e:  # pragma: no cover
  raise RuntimeError("pydantic is required for schema types") from e


class Constraints(BaseModel):
  timeoutMs: Optional[int] = Field(default=None, ge=0)
  deterministic: Optional[bool] = Field(default=None)
  idempotencyKey: Optional[str] = Field(default=None)


class Metrics(BaseModel):
  tokensUsed: Optional[int] = Field(default=None, ge=0)
  timeMs: Optional[int] = Field(default=None, ge=0)


class AgentTask(BaseModel):
  type: Literal["AgentTask"]
  id: str
  parentId: Optional[str] = None
  agent: str
  payload: Dict[str, Any]
  constraints: Optional[Constraints] = None
  protocolVersion: int = Field(default=1, ge=1)


class AgentResult(BaseModel):
  type: Literal["AgentResult"]
  id: str
  parentId: str
  agent: str
  payload: Dict[str, Any] = Field(default_factory=dict)
  metrics: Optional[Metrics] = None
  protocolVersion: int = Field(default=1, ge=1)


class AgentErrorDetail(BaseModel):
  code: str
  message: str
  details: Optional[str] = None


class AgentError(BaseModel):
  type: Literal["AgentError"]
  id: str
  parentId: str
  agent: str
  error: AgentErrorDetail
  protocolVersion: int = Field(default=1, ge=1)


# -----------------------
# Payload model variants
# -----------------------

class CodeGenPayload(BaseModel):
  action: Literal["create", "modify"]
  target: str
  instructions: Optional[str] = None
  content: Optional[str] = None  # for direct create/modify


class TestGenPayload(BaseModel):
  mode: Literal["generate"]
  target: str
  function: Optional[str] = None


class TestExecPayload(BaseModel):
  mode: Literal["execute"]
  tests: Optional[Union[str, List[str]]] = None


class StaticAnalysisPayload(BaseModel):
  target: Union[str, List[str]]
  severity: Optional[Literal["info", "warn", "error"]] = None


class DebugPayload(BaseModel):
  errorLog: str
  target: Optional[str] = None


# -----------------------
# Result payload variants
# -----------------------

class DeltaDoc(BaseModel):
  id: Optional[str] = None
  type: Optional[str] = None
  path: Optional[str] = None
  content: Optional[str] = None
  metadata: Optional[Dict[str, Any]] = None


class Delta(BaseModel):
  doc: Optional[DeltaDoc] = None
  diff: Optional[str] = None
  summary: Optional[str] = None


class NewTaskRef(BaseModel):
  agent: str
  payload: Dict[str, Any]


class ResultPayload(BaseModel):
  delta: Optional[Delta] = None
  artifacts: Optional[List[Any]] = None
  newTasks: Optional[List[NewTaskRef]] = None



