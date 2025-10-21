from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class CodeGenAgent(Agent):
  def __init__(self) -> None:
    super().__init__("CodeGenAgent")

  def run(self, task: Dict[str, Any], ctx: Any | None = None) -> Dict[str, Any]:
    payload = task.get("payload", {})
    target = payload.get("target", "")
    action = payload.get("action", payload.get("mode", "create"))
    # Deterministic content derived from inputs (no randomness)
    content = f"/* generated:{action}:{target} */\n"
    diff_summary = {
      "insertions": 1,
      "deletions": 0,
      "files_changed": 1
    }
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {
        "delta": {
          "doc": {
            "path": target,
            "content": content,
          }
        },
        "artifacts": [
          {"kind": "diff_summary", "target": target, "summary": diff_summary}
        ]
      }
    }


