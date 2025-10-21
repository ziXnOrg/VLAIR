import pytest

from orchestrator.core.orchestrator import Orchestrator


def test_analysis_missing_details_raises():
  o = Orchestrator()
  bad = {
    "type": "AgentResult",
    "id": "r",
    "parentId": "t",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "a.cpp"}]}
  }
  with pytest.raises(ValueError) as e:
    o.apply_agent_result(bad)
  assert "missing required field 'details'" in str(e.value)


def test_analysis_suggestions_wrong_type_raises():
  o = Orchestrator()
  bad = {
    "type": "AgentResult",
    "id": "r",
    "parentId": "t",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "a.cpp", "details": "x", "suggestions": "oops"}]}
  }
  with pytest.raises(ValueError) as e:
    o.apply_agent_result(bad)
  assert "field 'suggestions' must be a list" in str(e.value)


