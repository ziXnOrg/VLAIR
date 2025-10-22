from __future__ import annotations

from orchestrator.agents.debug_agent import DebugAgent
from orchestrator.schemas.validators import validate_agent_result


def test_debug_agent_emits_delta_and_analysis() -> None:
  a = DebugAgent()
  task = {"type":"AgentTask","id":"t","agent":"DebugAgent","payload":{"errorLog":"failure in test","target":"a.cpp"}}
  res = a.run(task)
  v = validate_agent_result(res)
  assert v.agent == "DebugAgent"
  p = res["payload"]
  assert p.get("delta", {}).get("doc", {}).get("path") == "a.cpp"
  arts = p.get("artifacts", [])
  assert any(x.get("kind") == "analysis" for x in arts)
