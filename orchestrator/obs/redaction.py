from __future__ import annotations

import os
import re
from typing import Iterable, List, Dict, Any, cast


_REDACTION_PATTERNS: tuple[re.Pattern[str], ...] = (
  # SSN like 123-45-6789
  re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
  # Credit card numbers (13-16 digits, allowing separators)
  re.compile(r"\b(?:\d[ -]?){13,16}\b"),
  # OpenAI-style keys sk-...
  re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
  # GitHub tokens ghp_/gho_/ghs_/ghu_
  re.compile(r"\bgh[opus]_[A-Za-z0-9]{20,}\b"),
  # Google API key
  re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
  # Slack token xox[baprs]-...
  re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
  # AWS Access Key ID (AKIA...)
  re.compile(r"AKIA[0-9A-Z]{16}"),
  # JWT tokens (header.payload.signature)
  re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"),
  # Bearer tokens
  re.compile(r"(?i)Bearer\s+[A-Za-z0-9_\-\.~+/]+=*"),
  # Generic key/value sensitive fields
  re.compile(r"(?i)(password|secret|token|api[_-]?key|access[_-]?token|authorization)\s*[:=]\s*\S+"),
  # Email addresses
  re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
  # PEM private keys (single-line tolerant)
  re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]* PRIVATE KEY-----".replace(" ",""), re.DOTALL),
)


def _dynamic_prefix_patterns() -> List[re.Pattern[str]]:
  prefixes = os.environ.get("VLTAIR_REDACT_PREFIXES", "").strip()
  if not prefixes:
    return []
  out: List[re.Pattern[str]] = []
  for raw in prefixes.split(','):
    p = raw.strip()
    if not p:
      continue
    # Build a pattern matching prefix followed by typical token chars
    try:
      rx = re.compile(rf"\b{re.escape(p)}[A-Za-z0-9_\-]{{8,}}\b")
      out.append(rx)
    except re.error:
      continue
  return out


def sanitize_text(message: str, *, extra_patterns: Iterable[str] | None = None) -> str:
  """Redact sensitive substrings from message.

  Args:
    message: input string possibly containing sensitive data
    extra_patterns: optional iterable of regex pattern strings to add

  Returns:
    Redacted message with sensitive tokens replaced by <<REDACTED>>
  """
  result = str(message)
  # Apply static patterns
  for pat in _REDACTION_PATTERNS:
    result = pat.sub("<<REDACTED>>", result)
  # Apply dynamic prefix-based patterns
  for pat in _dynamic_prefix_patterns():
    result = pat.sub("<<REDACTED>>", result)
  # Apply caller-supplied extra patterns
  if extra_patterns:
    for p in extra_patterns:
      try:
        rx = re.compile(p)
        result = rx.sub("<<REDACTED>>", result)
      except re.error:
        # ignore invalid extra patterns
        continue
  return result


def _parse_field_paths(env_value: str) -> List[List[str]]:
  paths: List[List[str]] = []
  for raw in env_value.split(','):
    s = raw.strip()
    if not s:
      continue
    parts = [p for p in s.split('.') if p]
    if parts:
      paths.append(parts)
  return paths


def _sanitize_at_path(obj: Any, path: List[str]) -> None:
  if not path:
    return
  key = path[0]
  rest = path[1:]
  if isinstance(obj, dict):
    if key in obj:
      if rest:
        _sanitize_at_path(obj[key], rest)
      else:
        val_any = cast(Any, obj[key])
        if isinstance(val_any, list):
          redacted_list: List[Any] = []
          for itm in cast(List[Any], val_any):
            redacted_list.append(sanitize_text(itm) if isinstance(itm, str) else itm)
          obj[key] = redacted_list
        else:
          obj[key] = sanitize_text(str(val_any))
  elif isinstance(obj, list):
    for item in cast(List[Any], obj):
      _sanitize_at_path(item, path)


def sanitize_artifact(art: Dict[str, Any], kind: str) -> None:
  """Field-based redaction: sanitize configured fields on an artifact dict.

  Environment variables:
    - VLTAIR_REDACT_FIELDS: comma-separated list of key paths (e.g., "log,details,meta.token")
    - VLTAIR_REDACT_FIELDS_<KIND>: same but scoped per artifact kind, KIND uppercased
  """
  fields_global = os.environ.get("VLTAIR_REDACT_FIELDS", "")
  fields_kind = os.environ.get(f"VLTAIR_REDACT_FIELDS_{kind.upper()}", "")
  paths: List[List[str]] = []
  if fields_global:
    paths.extend(_parse_field_paths(fields_global))
  if fields_kind:
    paths.extend(_parse_field_paths(fields_kind))
  for p in paths:
    _sanitize_at_path(art, p)
