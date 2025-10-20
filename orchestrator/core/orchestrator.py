from __future__ import annotations

from typing import Any, Dict, Optional, cast

from orchestrator.schemas.validators import validate_agent_task, validate_agent_result
from .scheduler import Scheduler, ScheduledTask
from .registry import AgentRegistry
from orchestrator.agents.codegen import CodeGenAgent
from orchestrator.agents.test_agent import TestAgent
from orchestrator.agents.static_analysis import StaticAnalysisAgent
from orchestrator.context.context_store import ContextStore
from orchestrator.context.models import CodeDocument


class Orchestrator:
  def __init__(self) -> None:
    self._registry = AgentRegistry()
    # seed default agents for routing demo
    self._registry.register("CodeGenAgent", ["codegen"]) 
    self._registry.register("TestAgent", ["testgen", "testexec"]) 
    self._registry.register("StaticAnalysisAgent", ["analysis"]) 
    self._agent_handlers: Dict[str, Any] = {
      "CodeGenAgent": CodeGenAgent().run,
      "TestAgent": TestAgent().run,
      "StaticAnalysisAgent": StaticAnalysisAgent().run,
    }
    self._scheduler = Scheduler(max_concurrency=2)
    self._scheduler.start(self._handle_scheduled, router=self._route_agent)
    self._ctx: Optional[ContextStore] = None

  def submit_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
    # Validate schema first; raises ValueError on failure
    validated = validate_agent_task(task)
    max_attempts = 3
    budget_ms = None
    c = validated.constraints
    if c and c.timeoutMs is not None:
      budget_ms = int(c.timeoutMs)
    trace_id = self._scheduler.enqueue(task, max_attempts=max_attempts, budget_ms=budget_ms)
    return {"accepted": True, "taskId": validated.id, "agent": validated.agent, "traceId": trace_id}

  def handle_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
    validated = validate_agent_result(result)
    return {"ok": True, "resultId": validated.id, "agent": validated.agent}

  def _handle_scheduled(self, item: ScheduledTask) -> None:
    # Placeholder dispatch; in Task 11 we would route to agents by type
    # For now we only validate again to simulate guarded processing
    try:
      validate_agent_task(item.task)
      agent = item.agent or self._route_agent(item.task)
      handler = self._agent_handlers.get(agent, self._handle_noop)
      result: Dict[str, Any] = handler(item.task)
      # Validate and accept AgentResult shape
      if result.get("type") == "AgentResult":
        validate_agent_result(result)
        self.apply_agent_result(result)
    except Exception as e:
      # Surface validation with trace ID
      raise ValueError(f"traceId={item.trace_id} validation failed: {e}")

  def _route_agent(self, task: Dict[str, Any]) -> str:
    agent = task.get("agent", "")
    return self._registry.select_for(agent)

  # --- Agent registry operations ---
  def register_agent(self, name: str, capabilities: list[str]) -> None:
    self._registry.register(name, capabilities)

  def update_agent(self, name: str, *, status: str | None = None, load: int | None = None) -> None:
    self._registry.update_status(name, status=status, load=load)

  # --- Agent stub handlers ---
  def _handle_noop(self, item: ScheduledTask) -> None:
    return

  def queue_metrics(self) -> Dict[str, Any]:
    return self._scheduler.metrics()

  def set_context_store(self, store: ContextStore) -> None:
    self._ctx = store

  def _ensure_ctx(self) -> ContextStore:
    if self._ctx is None:
      self._ctx = ContextStore()
    return self._ctx

  def apply_agent_result(self, result: Dict[str, Any]) -> None:
    # Apply delta.doc to context as code/text documents (code path first)
    payload: Dict[str, Any] = result.get("payload", {})
    delta_obj: Any = payload.get("delta")
    if isinstance(delta_obj, dict):
      delta: Dict[str, Any] = cast(Dict[str, Any], delta_obj)
    else:
      delta = {}
    doc_obj: Any = delta.get("doc")
    doc: Dict[str, Any] | None = cast(Dict[str, Any], doc_obj) if isinstance(doc_obj, dict) else None
    if doc is not None:
      path = str(doc.get("path") or "")
      content = str(doc.get("content") or "")
      if path or content:
        code_doc = CodeDocument(id=hash(path) & 0x7FFFFFFF, path=path, language="", content=content, metadata={"origin": str(result.get("agent", ""))})
        self._ensure_ctx().add_code_documents([code_doc], [[0.0]])
    # Artifacts handling: text docs and test results
    artifacts_any: Any = payload.get("artifacts")
    from typing import List as _List
    artifacts_obj: _List[Any] | None = cast(_List[Any], artifacts_any) if isinstance(artifacts_any, list) else None
    if artifacts_obj is not None:
      for item_any in artifacts_obj:
        art: Dict[str, Any]
        if isinstance(item_any, dict):
          art = cast(Dict[str, Any], item_any)
        else:
          continue
        kind = str(art.get("kind", ""))
        if kind == "text":
          from orchestrator.context.models import TextDocument
          title_val: Any = art.get("title")
          content_val: Any = art.get("content")
          title = str(title_val) if title_val is not None else ""
          content = str(content_val) if content_val is not None else ""
          doc_id = hash(title + content) & 0x7FFFFFFF
          text_doc = TextDocument(id=doc_id, title=title, content=content, metadata={"origin": str(result.get("agent", ""))})
          self._ensure_ctx().add_text_documents([text_doc], [[0.0]])
        elif kind == "test_result":
          from orchestrator.context.models import TestResultDocument, TextDocument
          tn_val: Any = art.get("test_name")
          st_val: Any = art.get("status")
          log_val: Any = art.get("log")
          test_name = str(tn_val) if tn_val is not None else ""
          status = str(st_val) if st_val is not None else ""
          log = str(log_val) if log_val is not None else None
          doc_id = hash(test_name + status + (log or "")) & 0x7FFFFFFF
          if not test_name:
            raise ValueError("AgentResult artifact 'test_result' missing required field 'test_name'")
          if not status:
            raise ValueError("AgentResult artifact 'test_result' missing required field 'status'")
          tr = TestResultDocument(id=doc_id, test_name=test_name, status=status, log=log, metadata={"origin": str(result.get("agent", ""))})
          # Persist via dedicated helper, and also render a text doc for retrieval
          self._ensure_ctx().add_test_results([tr])
          rendered = f"[{status}] {test_name}\n{log or ''}"
          text_doc = TextDocument(id=doc_id, title=f"test:{test_name}", content=rendered, metadata={"origin": str(result.get("agent", ""))})
          self._ensure_ctx().add_text_documents([text_doc], [[0.0]])
