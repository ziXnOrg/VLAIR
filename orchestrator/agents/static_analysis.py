from __future__ import annotations

from typing import Any, Dict, List

from .base import Agent


class StaticAnalysisAgent(Agent):
  def __init__(self) -> None:
    super().__init__("StaticAnalysisAgent")

  def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload", {})
    target = payload.get("target")
    # Produce a richer analysis artifact; in real impl this would parse code
    findings: List[Dict[str, Any]] = [
      {
        "kind": "analysis",
        "target": target,
        "details": "No major issues found",
        "severity": "info",
        "suggestions": []
      }
    ]
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {"artifacts": findings}
    }


