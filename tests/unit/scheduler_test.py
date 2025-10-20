import time
import pytest

from orchestrator.core.scheduler import Scheduler, ScheduledTask


def test_scheduler_enqueues_and_dispatches():
  seen: list[str] = []

  def handler(item: ScheduledTask) -> None:
    seen.append(item.trace_id)

  s = Scheduler(max_concurrency=1)
  s.start(handler)
  tid = s.enqueue({"type": "AgentTask", "id": "t1"})
  # allow time for worker
  time.sleep(0.1)
  s.stop()
  assert tid in seen


def test_scheduler_retries_with_backoff(monkeypatch):
  calls = {"n": 0}
  seen: list[str] = []

  def handler(item: ScheduledTask) -> None:
    calls["n"] += 1
    seen.append(item.trace_id)
    raise RuntimeError("retry me")

  # deterministic small backoff
  s = Scheduler(max_concurrency=1, backoff_fn=lambda n: 0.01)
  s.start(handler)
  s.enqueue({"type": "AgentTask", "id": "t1"}, max_attempts=2)
  time.sleep(0.05)
  s.stop()
  # handler invoked at least twice (initial + one retry)
  assert calls["n"] >= 2


def test_scheduler_drops_when_budget_exceeded():
  calls = {"n": 0}

  def handler(item: ScheduledTask) -> None:
    calls["n"] += 1
    time.sleep(0.03)  # 30ms

  s = Scheduler(max_concurrency=1)
  s.start(handler)
  s.enqueue({"type": "AgentTask", "id": "t1"}, max_attempts=3, budget_ms=5)
  time.sleep(0.1)
  s.stop()
  # Only one attempt should be made; budget exceeded prevents retry
  assert calls["n"] == 1


