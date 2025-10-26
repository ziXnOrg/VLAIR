from __future__ import annotations

import pytest

from orchestrator.agents.base import Agent
from orchestrator.core.registry import AgentRegistry


def test_agent_base_default_behavior() -> None:
    # Base class can be instantiated, but run() must be overridden; default raises
    a = Agent("X")
    with pytest.raises(NotImplementedError):
        a.run({"id": "t1"}, None)

    # Subclass without run() inherits NotImplementedError behavior
    class _BadAgent(Agent):
        pass

    with pytest.raises(NotImplementedError):
        _BadAgent("Y").run({"id": "t2"}, None)


class _OkAgent(Agent):
    def run(self, task, ctx=None):  # type: ignore[override]
        return {
            "type": "AgentResult",
            "id": "r1",
            "parentId": task.get("id", ""),
            "agent": self.name,
            "payload": {},
        }


def test_agent_subclass_can_instantiate_and_run() -> None:
    a = _OkAgent("Ok")
    out = a.run({"id": "t1"}, None)
    assert out.get("type") == "AgentResult" and out.get("agent") == "Ok"


def test_registry_duplicate_registration_error() -> None:
    r = AgentRegistry()
    r.register("A", ["cap"])  # ok
    with pytest.raises(ValueError):
        r.register("A", ["cap"])  # duplicate


def test_registry_missing_lookup_and_isolation() -> None:
    r1 = AgentRegistry()
    r2 = AgentRegistry()
    r1.register("A", ["cap"])
    assert r1.get("A") is not None
    assert r2.get("A") is None
