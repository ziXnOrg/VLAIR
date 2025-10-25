from __future__ import annotations

from orchestrator.context.idempotency import make_idempotency_key, idempotent


def test_make_idempotency_key_stable() -> None:
  p1 = {"b":2, "a":1}
  p2 = {"a":1, "b":2}
  k1 = make_idempotency_key("op", p1)
  k2 = make_idempotency_key("op", p2)
  assert k1 == k2 and len(k1) == 64


def test_idempotent_decorator_caches_results() -> None:
  cache: dict[str, int] = {}

  @idempotent(cache)
  def add(a: int, b: int) -> int:
    return a + b

  r1 = add(1, 2)
  r2 = add(1, 2)
  assert r1 == 3 and r2 == 3 and len(cache) == 1




def test_idempotent_decorator_on_method_skips_self_and_shared_cache() -> None:
  calls = {"count": 0}
  cache: dict[str, int] = {}

  class C:
    @idempotent(cache)
    def mul(self, a: int, b: int) -> int:  # type: ignore[valid-type]
      calls["count"] += 1
      return a * b

  c1 = C(); c2 = C()
  assert c1.mul(2,3) == 6
  assert c2.mul(2,3) == 6  # should reuse cached result despite different self
  assert calls["count"] == 1


def test_idempotent_kwargs_order_equivalent() -> None:
  cache: dict[str, int] = {}
  @idempotent(cache)
  def f(x: int = 1, y: int = 2) -> int:
    return x + y
  r1 = f(y=3, x=4)
  r2 = f(x=4, y=3)
  assert r1 == 7 and r2 == 7
  assert len(cache) == 1  # same idempotency key


def test_idempotent_exception_not_cached() -> None:
  cache: dict[str, int] = {}
  @idempotent(cache)
  def boom(x: int) -> int:
    raise ValueError("fail")
  import pytest
  with pytest.raises(ValueError):
    boom(1)
  # A second call should still raise and not be cached
  with pytest.raises(ValueError):
    boom(1)
  assert len(cache) == 0
