from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class CodeGenAgent(Agent):
  def __init__(self) -> None:
    super().__init__("CodeGenAgent")

  def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
    payload = task.get("payload", {})
    target = payload.get("target", "")
    # Produce AgentResult-shaped dict
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {
        "delta": {
          "doc": {
            "path": target,
            "content": "/* generated */\n",
          }
        }
      }
    }


