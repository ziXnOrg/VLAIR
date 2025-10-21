from __future__ import annotations

import pytest
from orchestrator.core.orchestrator import Orchestrator


def test_routing_falls_back_to_least_loaded() -> None:
  o = Orchestrator()
  # Make CodeGen busy and higher load; TestAgent idle lower load
  o.update_agent("CodeGenAgent", status="busy", load=5)
  o.update_agent("TestAgent", status="idle", load=1)
  out = o.submit_task({"type":"AgentTask","id":"t1","agent":"","payload":{"mode":"generate","target":"x"}})
  assert out["accepted"] is True


def test_routing_validates_specified_agent() -> None:
  o = Orchestrator()
  o.update_agent("TestAgent", status="down", load=0)
  with pytest.raises(ValueError):
    # Will attempt to route to down agent
    o._route_agent({"agent":"TestAgent"})

