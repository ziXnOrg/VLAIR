from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class TestAgent(Agent):
  def __init__(self) -> None:
    super().__init__("TestAgent")

  def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
    mode = task.get("payload", {}).get("mode", "")
    if mode == "execute":
      test_name = task.get("payload", {}).get("test", "all")
      status = "pass"
      # In real impl, would run and capture logs
      return {
        "type": "AgentResult",
        "id": f"res-{task.get('id','')}",
        "parentId": task.get("id", ""),
        "agent": self.name,
        "payload": {
          "artifacts": [
            {
              "kind": "test_result",
              "test_name": test_name,
              "status": status,
              "log": ""
            }
          ]
        }
      }
    else:
      return {
        "type": "AgentResult",
        "id": f"res-{task.get('id','')}",
        "parentId": task.get("id", ""),
        "agent": self.name,
        "payload": {"artifacts": [{"kind": "test_gen", "target": task.get("payload", {}).get("target", "")}]} 
      }


