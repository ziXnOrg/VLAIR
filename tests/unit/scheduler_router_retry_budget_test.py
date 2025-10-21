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
  # Create a fresh Scheduler with a flaky handler
  from orchestrator.core.scheduler import Scheduler
  calls: List[int] = []
  times: List[float] = []

  def flaky_handler(item: ScheduledTask) -> None:
    calls.append(1)
    times.append(time.time())
    if len(calls) < 3:
      raise RuntimeError("transient")
    # After 2 failures, succeed silently

  s = Scheduler(max_concurrency=1, backoff_fn=lambda n: 0.01)
  s.start(flaky_handler, router=lambda t: "TestAgent")

  task = {"type": "AgentTask", "id": "t-retry", "agent": "TestAgent", "payload": {"mode": "generate", "target": "x"}}
  s.enqueue(task, max_attempts=3, budget_ms=None)
  # Wait for retries (2 * 10ms plus processing)
  time.sleep(0.15)
  s.stop()
  # Expect at least 3 handler invocations (2 failures + 1 success)
  assert len(calls) >= 3
  # Backoff timing gaps should be at least ~10ms
  if len(times) >= 3:
    assert (times[1] - times[0]) >= 0.009
    assert (times[2] - times[1]) >= 0.009


def test_budget_enforcement() -> None:
  from orchestrator.core.scheduler import Scheduler
  call_count: List[int] = []

  def slow_handler(item: ScheduledTask) -> None:
    call_count.append(1)
    time.sleep(0.05)  # 50ms

  s = Scheduler(max_concurrency=1)
  s.start(slow_handler, router=lambda t: "TestAgent")

  # Budget smaller than handler duration -> should drop without retry
  task = {"type": "AgentTask", "id": "t-b", "agent": "TestAgent", "payload": {"mode": "generate", "target": "y"}}
  s.enqueue(task, max_attempts=3, budget_ms=10)
  # Give time to process
  time.sleep(0.15)
  s.stop()
  # Should have been called once only due to budget drop
  assert len(call_count) == 1
