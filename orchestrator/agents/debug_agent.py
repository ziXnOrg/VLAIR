from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class DebugAgent(Agent):
  def __init__(self) -> None:
    super().__init__("DebugAgent")

  def run(self, task: Dict[str, Any], ctx: Any | None = None) -> Dict[str, Any]:
    payload = task.get("payload", {})
    error_log = payload.get("errorLog", "")
    target = payload.get("target", "fix.patch")
    # Deterministic stub: propose a minimal patch content referencing the target
    patch = f"/* patch for {target} */\n"
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {
        "delta": {
          "doc": {
            "path": target,
            "content": patch,
          }
        },
        "artifacts": [
          {"kind": "analysis", "target": target, "details": "Proposed minimal fix", "severity": "info", "suggestions": []}
        ]
      }
    }
