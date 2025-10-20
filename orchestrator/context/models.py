from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional, Literal, Any, Type, Mapping


# -------------------------
# Search results (immutable)
# -------------------------


@dataclass(frozen=True)
class SearchResult:
  doc_id: int
  score: float
  dense_score: float
  sparse_score: float
  dense_rank: int
  sparse_rank: int
  metadata: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class Document:
  id: int
  content: str
  metadata: Dict[str, str]


# -------------------------
# Document variants & metadata typing
# -------------------------

# Minimal runtime-checked schemas (lightweight alternative to pydantic)

CodeStatus = Literal["added", "modified", "unchanged"]
TestStatus = Literal["pass", "fail", "error", "skipped"]


def _assert_type(name: str, value: Any, expected: Type[Any]) -> None:
  if not isinstance(value, expected):
    raise ValueError(f"{name} must be {expected.__name__}, got {type(value).__name__}")


def validate_metadata(metadata: Mapping[str, Any], *, required: Mapping[str, Type[Any]], optional: Mapping[str, Type[Any]] = {}) -> None:
  for k, tp in required.items():
    if k not in metadata:
      raise ValueError(f"missing required metadata field: {k}")
    _assert_type(k, metadata[k], tp)
  for k, v in metadata.items():
    if k in required:
      continue
    if k in optional:
      _assert_type(k, v, optional[k])
    # else: allow extra keys for forward-compatibility


@dataclass(frozen=True)
class CodeDocument:
  id: int
  path: str
  language: str
  content: str
  # metadata: origin, version, status
  metadata: Dict[str, Any]

  def __post_init__(self) -> None:
    validate_metadata(
      self.metadata,
      required={"origin": str},
      optional={"version": int, "status": str},
    )

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)


@dataclass(frozen=True)
class TextDocument:
  id: int
  title: str
  content: str
  metadata: Dict[str, Any]

  def __post_init__(self) -> None:
    validate_metadata(self.metadata, required={"origin": str}, optional={"tags": dict})

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)


@dataclass(frozen=True)
class TestResultDocument:
  id: int
  test_name: str
  status: str  # use TestStatus literals at call sites
  log: Optional[str]
  metadata: Dict[str, Any]

  def __post_init__(self) -> None:
    validate_metadata(self.metadata, required={"origin": str}, optional={"run_id": str, "time_ms": (int)})

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)



