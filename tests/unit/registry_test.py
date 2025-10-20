from orchestrator.core.registry import AgentRegistry


def test_registry_selects_exact_name_when_available():
  r = AgentRegistry()
  r.register("A1", ["cap"]) 
  r.register("A2", ["cap"]) 
  assert r.select_for("A1") == "A1"


def test_registry_fallbacks_to_idle_least_loaded():
  r = AgentRegistry()
  r.register("A1", ["cap"]) 
  r.register("A2", ["cap"]) 
  r.update_status("A1", status="idle", load=5)
  r.update_status("A2", status="idle", load=1)
  # Unknown requested agent -> choose least loaded idle
  assert r.select_for("Unknown") == "A2"


def test_registry_skips_down_agents():
  r = AgentRegistry()
  r.register("A1", ["cap"]) 
  r.register("A2", ["cap"]) 
  r.update_status("A1", status="down", load=0)
  r.update_status("A2", status="idle", load=2)
  assert r.select_for("A1") == "A2"


