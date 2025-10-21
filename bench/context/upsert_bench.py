import json
import time
from typing import Any, Dict, List


def run_bench(n: int = 100) -> Dict[str, Any]:
  from orchestrator.context.context_store import ContextStore  # local import
  ctx = ContextStore()
  ids: List[int] = list(range(1, n + 1))
  vecs: List[List[float]] = [[0.0, 0.1, 0.2] for _ in ids]
  metas: List[Dict[str, str]] = [{"type": "text", "title": f"doc-{i}"} for i in ids]
  t0 = time.perf_counter()
  try:
    ctx.add(ids, vecs, metas)
  except Exception:
    # Allow environments without backend
    pass
  t1 = time.perf_counter()
  elapsed = t1 - t0
  return {"count": n, "total_s": elapsed, "avg_ms_per_doc": (elapsed / max(n, 1)) * 1000.0}


if __name__ == "__main__":
  out = run_bench()
  print(json.dumps(out))
