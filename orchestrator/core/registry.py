from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class AgentInfo:
  name: str
  capabilities: Set[str] = field(default_factory=set)
  status: str = "idle"  # idle|busy|down
  load: int = 0          # lower is better


class AgentRegistry:
  def __init__(self) -> None:
    self._agents: Dict[str, AgentInfo] = {}

  def register(self, name: str, capabilities: List[str]) -> None:
    self._agents[name] = AgentInfo(name=name, capabilities=set(capabilities))

  def list(self) -> List[AgentInfo]:
    return list(self._agents.values())

  def update_status(self, name: str, *, status: str | None = None, load: int | None = None) -> None:
    if name not in self._agents:
      return
    a = self._agents[name]
    if status is not None:
      a.status = status
    if load is not None:
      a.load = load

  def select_for(self, agent_name: str) -> str:
    # Prefer exact name if registered and not down
    if agent_name and agent_name in self._agents and self._agents[agent_name].status != "down":
      return agent_name
    # Otherwise pick the least loaded idle agent
    candidates = [a for a in self._agents.values() if a.status == "idle"]
    if not candidates:
      candidates = [a for a in self._agents.values() if a.status != "down"]
    if not candidates:
      return ""
    best = sorted(candidates, key=lambda a: a.load)[0]
    return best.name


