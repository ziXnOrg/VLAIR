from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Dict, List, Optional, Set


@dataclass
class AgentInfo:
  name: str
  capabilities: Set[str] = field(default_factory=set)
  status: str = "idle"  # idle|busy|down
  load: int = 0          # lower is better
  last_heartbeat: float = 0.0


class AgentRegistry:
  def __init__(self) -> None:
    """Thread-safe in-memory registry of agents and their status.

    Notes:
    - Duplicate registrations are rejected to avoid accidental overwrites.
    - Heartbeats are used to filter out stale agents during selection.
    """
    self._agents: Dict[str, AgentInfo] = {}
    self._lock = threading.RLock()

  def register(self, name: str, capabilities: List[str]) -> None:
    """Register a new agent name with capabilities.

    Raises:
      ValueError: if an agent with the same name already exists.
    """
    with self._lock:
      if name in self._agents:
        raise ValueError(f"Agent '{name}' already registered")
      self._agents[name] = AgentInfo(name=name, capabilities=set(capabilities), last_heartbeat=time.time())

  def list(self) -> List[AgentInfo]:
    with self._lock:
      return list(self._agents.values())

  def update_status(self, name: str, *, status: str | None = None, load: int | None = None) -> None:
    with self._lock:
      if name not in self._agents:
        return
      a = self._agents[name]
      if status is not None:
        a.status = status
      if load is not None:
        a.load = load
      a.last_heartbeat = time.time()

  def update_heartbeat(self, name: str) -> None:
    with self._lock:
      if name in self._agents:
        self._agents[name].last_heartbeat = time.time()

  def get(self, name: str) -> Optional[AgentInfo]:
    with self._lock:
      return self._agents.get(name)

  def list_active(self, ttl_s: int = 60) -> List[AgentInfo]:
    now = time.time()
    with self._lock:
      return [a for a in self._agents.values() if (now - a.last_heartbeat) <= ttl_s and a.status != "down"]

  def select_for(self, agent_name: str, ttl_s: int = 60) -> str:
    # Prefer exact name if healthy
    with self._lock:
      if agent_name:
        a = self._agents.get(agent_name)
        if a and a.status != "down" and (time.time() - a.last_heartbeat) <= ttl_s:
          return agent_name
      # Otherwise pick least-loaded idle among active
      active = self.list_active(ttl_s)
      candidates = [a for a in active if a.status == "idle"] or active
      if not candidates:
        return ""
      candidates.sort(key=lambda a: (a.load, a.name))
      return candidates[0].name


