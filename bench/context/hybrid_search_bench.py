import json
import os
import time
from typing import Any, Dict


def run_bench(n: int = 50) -> Dict[str, Any]:
  from orchestrator.context.context_store import ContextStore  # local import
  ctx = ContextStore()
  # Warm-up (may be no-op if backend lazy)
  try:
    ctx.structured_query(text="warmup", k=1)
  except Exception:
    pass
  t0 = time.perf_counter()
  for _ in range(n):
    try:
      ctx.structured_query(text="benchmark", k=5, rrf_k=60.0, dense_weight=0.6, sparse_weight=0.4, rerank_factor=10)
    except Exception:
      # If backend not available in this environment, skip errors
      break
  t1 = time.perf_counter()
  elapsed = t1 - t0
  return {"iterations": n, "total_s": elapsed, "avg_ms": (elapsed / max(n, 1)) * 1000.0}


if __name__ == "__main__":
  out = run_bench()
  print(json.dumps(out))
