from __future__ import annotations

from unittest.mock import patch
from orchestrator.agents.test_agent import TestAgent


def test_testexec_timeout_maps_to_timeout_status() -> None:
  a = TestAgent()
  task = {"type":"AgentTask","id":"t","agent":"TestAgent","payload":{"mode":"execute","paths":["tests/sample.py"],"timeout_s":1}}
  with patch("exec.sandbox.run_pytests", return_value=(124, "")):
    res = a.run(task)
    art = res["payload"]["artifacts"][0]
    assert art["kind"] == "test_result" and art["status"] == "timeout"


def test_testexec_logs_are_redacted() -> None:
  a = TestAgent()
  task = {"type":"AgentTask","id":"t","agent":"TestAgent","payload":{"mode":"execute","paths":["tests/sample.py"]}}
  with patch("exec.sandbox.run_pytests", return_value=(1, "Bearer SECRET-123 and email a@b.com")):
    res = a.run(task)
    art = res["payload"]["artifacts"][0]
    log = art["log"]
    assert "SECRET-123" not in log and "a@b.com" not in log and "<<REDACTED>>" in log
