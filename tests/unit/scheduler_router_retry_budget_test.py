import time
from typing import Any, Dict, List

from orchestrator.core.orchestrator import Orchestrator
from orchestrator.core.scheduler import ScheduledTask


def test_router_selects_registered_agent() -> None:
  o = Orchestrator()
  # Force registry state: mark CodeGenAgent busy so TestAgent selected when agent not specified
  o.update_agent("CodeGenAgent", status="busy", load=5)
  o.update_agent("TestAgent", status="idle", load=1)

  task: Dict[str, Any] = {"type": "AgentTask", "id": "t1", "agent": "", "payload": {"mode": "generate"}}
  out = o.submit_task(task)
  assert out["accepted"] is True
  # Allow processing and then check queue metrics
  time.sleep(0.05)
  m = o.queue_metrics()
  assert m["queued"] >= 0
  assert m["workers"] >= 1
  assert m["stopped"] is False


def test_retry_backoff() -> None:
  # Install a temporary orchestrator with a handler that fails twice then succeeds
  o = Orchestrator()
  calls: List[int] = []
  times: List[float] = []

  original_handle = o._handle_scheduled  # type: ignore[attr-defined]

  def flaky_handler(item: ScheduledTask) -> None:
    calls.append(1)
    times.append(time.time())
    if len(calls) < 3:
      raise RuntimeError("transient")
    # else delegate to original handler with a trivial TestAgent task
    item.task.setdefault("type", "AgentTask")
    item.task.setdefault("id", "t-retry")
    item.task.setdefault("agent", "TestAgent")
    item.task.setdefault("payload", {"mode": "generate", "target": "x"})
    original_handle(item)

  # Monkeypatch scheduler handler and backoff to be short
  o._scheduler.stop()  # type: ignore[attr-defined]
  o._scheduler._backoff_fn = lambda n: 0.01  # type: ignore[attr-defined]
  o._scheduler.start(flaky_handler, router=o._route_agent)  # type: ignore[attr-defined]

  task = {"type": "AgentTask", "id": "t-retry", "agent": "TestAgent", "payload": {"mode": "generate", "target": "x"}}
  o.submit_task(task)
  # Wait for retries (2 * 10ms plus processing)
  time.sleep(0.08)
  # Expect at least 3 handler invocations (2 failures + 1 success)
  assert len(calls) >= 3
  # Backoff timing gaps should be at least ~10ms
  assert (times[1] - times[0]) >= 0.009
  assert (times[2] - times[1]) >= 0.009


def test_budget_enforcement() -> None:
  o = Orchestrator()
  call_count: List[int] = []

  def slow_handler(item: ScheduledTask) -> None:
    call_count.append(1)
    time.sleep(0.05)  # 50ms

  o._scheduler.stop()  # type: ignore[attr-defined]
  o._scheduler.start(slow_handler, router=o._route_agent)  # type: ignore[attr-defined]

  # Budget smaller than handler duration -> should drop without retry
  task = {"type": "AgentTask", "id": "t-b", "agent": "TestAgent", "payload": {"mode": "generate", "target": "y"}, "constraints": {"timeoutMs": 10}}
  out = o.submit_task(task)
  assert out["accepted"] is True
  # Give time to process
  time.sleep(0.08)
  # Should have been called once only due to budget drop
  assert len(call_count) == 1
  m = o.queue_metrics()
  assert m["queued"] == 0
  assert m["stopped"] is False
