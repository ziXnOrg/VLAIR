from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, Optional, Tuple


def stable_json_dumps(obj: Any) -> str:
  return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def make_idempotency_key(operation: str, payload: Dict[str, Any]) -> str:
  base = f"{operation}|{stable_json_dumps(payload)}"
  return hashlib.sha256(base.encode("utf-8")).hexdigest()


def idempotent(cache: Dict[str, Any]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
  def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
      key = make_idempotency_key(func.__name__, {"args": args[1:], "kwargs": kwargs})
      if key in cache:
        return cache[key]
      result = func(*args, **kwargs)
      cache[key] = result
      return result
    return wrapper
  return decorator


