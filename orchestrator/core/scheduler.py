from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class ScheduledTask:
  trace_id: str
  task: Dict[str, Any]
  agent: Optional[str] = None
  attempts: int = 0
  max_attempts: int = 3
  next_at: float = 0.0
  budget_ms: Optional[int] = None


class Scheduler:
  def __init__(self, *, max_concurrency: int = 2, backoff_fn: Optional[Callable[[int], float]] = None) -> None:
    self._q: "queue.Queue[ScheduledTask]" = queue.Queue()
    self._max = max_concurrency
    self._workers: list[threading.Thread] = []
    self._stop = threading.Event()
    self._handler: Optional[Callable[[ScheduledTask], None]] = None
    self._router: Optional[Callable[[Dict[str, Any]], str]] = None
    self._backoff_fn: Callable[[int], float] = backoff_fn or (lambda n: float(min(2 ** n, 60)))

  def start(self, handler: Callable[[ScheduledTask], None], router: Optional[Callable[[Dict[str, Any]], str]] = None) -> None:
    self._handler = handler
    self._router = router
    for _ in range(self._max):
      t = threading.Thread(target=self._run, daemon=True)
      t.start()
      self._workers.append(t)

  def stop(self) -> None:
    self._stop.set()
    for _ in self._workers:
      self._q.put(ScheduledTask(trace_id="", task={}))
    for w in self._workers:
      w.join(timeout=1.0)

  def enqueue(self, task: Dict[str, Any], *, max_attempts: int = 3, budget_ms: Optional[int] = None) -> str:
    trace_id = str(uuid.uuid4())
    agent = self._router(task) if self._router else task.get("agent")
    self._q.put(ScheduledTask(trace_id=trace_id, task=task, agent=agent, attempts=0, max_attempts=max_attempts, next_at=time.time(), budget_ms=budget_ms))
    return trace_id

  def metrics(self) -> Dict[str, Any]:
    return {
      "queued": self._q.qsize(),
      "workers": len(self._workers),
      "stopped": self._stop.is_set(),
    }

  def _run(self) -> None:
    assert self._handler is not None
    while not self._stop.is_set():
      item = self._q.get()
      if self._stop.is_set():
        break
      try:
        now = time.time()
        if item.next_at > now:
          time.sleep(item.next_at - now)
        start = time.time()
        self._handler(item)
        # budget accounting: if exceeded, drop
        if item.budget_ms is not None:
          elapsed_ms = int((time.time() - start) * 1000)
          if elapsed_ms > item.budget_ms:
            # budget exceeded; do not retry
            continue
      except Exception:
        # retry with exponential backoff
        item.attempts += 1
        if item.attempts < item.max_attempts:
          delay = self._backoff_fn(item.attempts)
          item.next_at = time.time() + delay
          self._q.put(item)
        else:
          # drop after max attempts
          pass
      finally:
        self._q.task_done()
