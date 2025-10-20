from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class StaticAnalysisAgent(Agent):
  def __init__(self) -> None:
    super().__init__("StaticAnalysisAgent")

  def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
    target = task.get("payload", {}).get("target")
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {"artifacts": [{"kind": "analysis", "target": target}]}
    }


