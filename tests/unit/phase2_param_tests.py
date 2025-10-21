import pytest
from typing import Any, Dict, List, Tuple

from orchestrator.core.orchestrator import Orchestrator


@pytest.mark.parametrize(
  "summary,expect",
  [
    ({"files_changed": 1, "insertions": 2, "deletions": 0}, (1, 2, 0)),
    ({"files_changed": 0, "insertions": 0, "deletions": 0}, (0, 0, 0)),
    ({"insertions": 5}, (0, 5, 0)),
  ],
)
def test_param_diff_summary(summary: Dict[str, int], expect: Tuple[int, int, int], monkeypatch: Any) -> None:
  o = Orchestrator()
  captured: Dict[str, Any] = {}
  def fake_add_text(docs: List[Any], vecs: List[Any]) -> None:
    captured["text"] = docs[0].content
  def fake_add_diff(diffs: List[Any]) -> None:
    captured["diff"] = (diffs[0].files_changed, diffs[0].insertions, diffs[0].deletions)
  o._ensure_ctx().add_text_documents = fake_add_text  # type: ignore
  o._ensure_ctx().add_diff_summaries = fake_add_diff  # type: ignore
  res = {"type": "AgentResult", "id": "r", "parentId": "t", "agent": "CodeGenAgent", "payload": {"artifacts": [{"kind": "diff_summary", "summary": summary}]}}
  o.apply_agent_result(res)
  assert captured["diff"] == expect


@pytest.mark.parametrize(
  "files,rate",
  [
    (["a.cpp"], 0.8),
    ([], 0.0),
    (["a.cpp","b.cpp"], 1.0),
  ],
)
def test_param_coverage_hint(files: List[str], rate: float, monkeypatch: Any) -> None:
  o = Orchestrator()
  captured: Dict[str, Any] = {}
  def fake_add_text(docs: List[Any], vecs: List[Any]) -> None:
    captured["text"] = docs[0].content
  def fake_add_cov(hints: List[Any]) -> None:
    captured["cov"] = (hints[0].files, hints[0].line_rate)
  o._ensure_ctx().add_text_documents = fake_add_text  # type: ignore
  o._ensure_ctx().add_coverage_hints = fake_add_cov  # type: ignore
  res = {"type": "AgentResult", "id": "r", "parentId": "t", "agent": "TestAgent", "payload": {"artifacts": [{"kind": "coverage_hint", "files": files, "line_rate": rate}]}}
  o.apply_agent_result(res)
  assert captured["cov"] == (files, rate)


@pytest.mark.parametrize(
  "severity,suggestions",
  [
    ("info", []),
    ("warn", ["rename variable", "extract function"]),
    ("error", ["fix null check"]),
  ],
)
def test_param_analysis_variants(severity: str, suggestions: List[str]) -> None:
  o = Orchestrator()
  res = {
    "type": "AgentResult",
    "id": "ra",
    "parentId": "ta",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "c.cpp", "details": "d", "severity": severity, "suggestions": suggestions}]}
  }
  # Should not raise; persistence covered in other tests
  o.apply_agent_result(res)


@pytest.mark.parametrize(
  "artifacts",
  [
    ([{"kind": "diff_summary", "summary": {"files_changed": 1, "insertions": 1, "deletions": 0}},
      {"kind": "coverage_hint", "files": ["x.cpp"], "line_rate": 0.5}]),
    ([{"kind": "analysis", "target": "x.cpp", "details": "ok", "severity": "info"},
      {"kind": "test_result", "test_name": "t1", "status": "pass", "log": ""}]),
  ],
)
def test_param_combined_multi_artifacts(artifacts: List[Dict[str, Any]]) -> None:
  o = Orchestrator()
  res = {
    "type": "AgentResult",
    "id": "rc",
    "parentId": "tc",
    "agent": "CodeGenAgent",
    "payload": {"artifacts": artifacts}
  }
  o.apply_agent_result(res)


@pytest.mark.parametrize(
  "bad_severity",
  [
    pytest.param("critical", id="invalid-critical"),
    pytest.param("", id="empty"),
    pytest.param("LOW", id="case-mismatch"),
  ],
)
def test_param_analysis_invalid_severity_raises(bad_severity: str) -> None:
  o = Orchestrator()
  res = {
    "type": "AgentResult",
    "id": "ra2",
    "parentId": "ta2",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "c.cpp", "details": "d", "severity": bad_severity}]}
  }
  import pytest as _pytest
  with _pytest.raises(ValueError):
    o.apply_agent_result(res)


@pytest.mark.parametrize(
  "suggestions",
  [
    ["a" * 257],
    [str(i) for i in range(11)],
  ],
)
def test_param_analysis_invalid_suggestions_raises(suggestions: List[str]) -> None:
  o = Orchestrator()
  res = {
    "type": "AgentResult",
    "id": "ra3",
    "parentId": "ta3",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "c.cpp", "details": "d", "severity": "info", "suggestions": suggestions}]}
  }
  import pytest as _pytest
  with _pytest.raises(ValueError):
    o.apply_agent_result(res)


def test_test_result_log_redaction(monkeypatch: Any) -> None:
  o = Orchestrator()
  captured: Dict[str, Any] = {}
  def fake_add_text(docs: List[Any], vecs: List[Any]) -> None:
    captured["text"] = docs[0].content
  def fake_add_tr(results: List[Any]) -> None:
    captured["log"] = results[0].log
  o._ensure_ctx().add_text_documents = fake_add_text  # type: ignore
  o._ensure_ctx().add_test_results = fake_add_tr  # type: ignore
  secret = "User SSN: 123-45-6789"
  res = {
    "type": "AgentResult",
    "id": "rt",
    "parentId": "tt",
    "agent": "TestAgent",
    "payload": {"artifacts": [{"kind": "test_result", "test_name": "t", "status": "pass", "log": secret}]}
  }
  o.apply_agent_result(res)
  assert "<<REDACTED>>" in captured["log"]
  assert "123-45-6789" not in captured["log"]


@pytest.mark.parametrize(
  "details",
  [
    "Email: user@example.com",
    "Key sk-abcdEFGHijklMNOP1234",
    "Bearer abcdefghijklmnop",
  ],
)
def test_param_analysis_details_redaction(details: str) -> None:
  o = Orchestrator()
  captured: Dict[str, Any] = {}
  def fake_add_text(docs: List[Any], vecs: List[Any]) -> None:
    captured["text"] = docs[0].content
  o._ensure_ctx().add_text_documents = fake_add_text  # type: ignore
  res = {
    "type": "AgentResult",
    "id": "ra4",
    "parentId": "ta4",
    "agent": "StaticAnalysisAgent",
    "payload": {"artifacts": [{"kind": "analysis", "target": "d.cpp", "details": details, "severity": "info"}]}
  }
  o.apply_agent_result(res)
  assert "<<REDACTED>>" in captured["text"]


