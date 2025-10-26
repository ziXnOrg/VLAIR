from __future__ import annotations

from typing import Any, Dict, Protocol

# AgentContext defines the narrow surface agents can rely on at runtime.
# It is intentionally minimal to avoid tight coupling with orchestrator internals.
class AgentContext(Protocol):
  def get(self, key: str, default: Any | None = None) -> Any: ...


class Agent:
  name: str

  def __init__(self, name: str) -> None:
    self.name = name

  def run(self, task: Dict[str, Any], ctx: AgentContext | None = None) -> Dict[str, Any]:
    raise NotImplementedError


