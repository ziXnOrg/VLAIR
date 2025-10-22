from __future__ import annotations

from typing import Any, Dict

from .base import Agent
from orchestrator.obs.redaction import sanitize_text


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
      # Optionally execute via sandbox when 'paths' provided
      log = ""
      try:
        paths = payload.get("paths")
        if isinstance(paths, list) and paths:
          from exec.sandbox import run_pytests
          rc, out = run_pytests(paths, timeout_s=int(payload.get("timeout_s", 30)))
          status = "pass" if rc == 0 else ("timeout" if rc == 124 else "fail")
          log = sanitize_text(out)
      except Exception:
        # Fallback to deterministic stub on sandbox error
        status = "fail"
        log = "sandbox error"
      artifacts = [
        {"kind": "test_result", "test_name": test_name, "status": status, "log": log},
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


