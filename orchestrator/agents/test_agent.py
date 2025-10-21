from __future__ import annotations

from typing import Any, Dict

from .base import Agent


class TestAgent(Agent):
  def __init__(self) -> None:
    super().__init__("TestAgent")

  def run(self, task: Dict[str, Any], ctx: Any | None = None) -> Dict[str, Any]:
    payload = task.get("payload", {})
    mode = payload.get("mode", "generate")
    target = payload.get("target", payload.get("test", "all"))
    if mode == "execute":
      test_name = payload.get("test", target)
      status = "pass"
      # Deterministic execution stub; logs empty by default
      artifacts = [
        {"kind": "test_result", "test_name": test_name, "status": status, "log": ""},
        {"kind": "coverage_hint", "files": [f"{target}"], "line_rate": 0.75},
      ]
      return {
        "type": "AgentResult",
        "id": f"res-{task.get('id','')}",
        "parentId": task.get("id", ""),
        "agent": self.name,
        "payload": {"artifacts": artifacts},
      }
    # generate
    return {
      "type": "AgentResult",
      "id": f"res-{task.get('id','')}",
      "parentId": task.get("id", ""),
      "agent": self.name,
      "payload": {"artifacts": [{"kind": "test_gen", "target": target}]},
    }


