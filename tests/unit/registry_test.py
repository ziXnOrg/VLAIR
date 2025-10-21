from __future__ import annotations

import time
from orchestrator.core.registry import AgentRegistry


def test_registry_register_and_list() -> None:
  r = AgentRegistry()
  r.register("A", ["x"]) 
  r.register("B", ["y"]) 
  names = sorted([a.name for a in r.list()])
  assert names == ["A", "B"]


def test_select_least_loaded_idle_and_tiebreak() -> None:
  r = AgentRegistry()
  r.register("B", ["x"]) 
  r.register("A", ["x"]) 
  r.update_status("A", status="idle", load=2)
  r.update_status("B", status="idle", load=1)
  # B has lower load
  assert r.select_for("") == "B"
  # equalize loads -> lexicographic by name
  r.update_status("A", load=1)
  assert r.select_for("") == "A"


def test_ttl_filters_stale_agents() -> None:
  r = AgentRegistry()
  r.register("A", ["x"]) 
  # Make A stale by backdating heartbeat
  a = r.get("A")
  assert a is not None
  a.last_heartbeat = time.time() - 120
  assert r.select_for("", ttl_s=60) == ""


def test_specified_agent_validation() -> None:
  r = AgentRegistry()
  r.register("A", ["x"]) 
  # Available
  assert r.select_for("A") == "A"
  # Mark down
  r.update_status("A", status="down")
  assert r.select_for("A") == ""
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


