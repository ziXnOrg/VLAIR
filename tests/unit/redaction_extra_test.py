from __future__ import annotations

import os
from orchestrator.obs.redaction import sanitize_text, sanitize_artifact


def test_redaction_dynamic_prefix(monkeypatch) -> None:
  monkeypatch.setenv("VLTAIR_REDACT_PREFIXES", "sk-,ghp_")
  s = "token sk-ABCDEFGH12345678 and ghp_ABCDEFGHIJKLMNOPQRST"
  out = sanitize_text(s)
  assert "<<REDACTED>>" in out and "sk-" not in out and "ghp_" not in out


def test_redaction_nested_field_paths(monkeypatch) -> None:
  monkeypatch.setenv("VLTAIR_REDACT_FIELDS", "details,meta.token,items.logs")
  art = {"kind":"analysis","details":"pass sk-HHHHHHHH12345678","meta":{"token":"sk-ABCDEFGH12345678"},"items":{"logs":"user@example.com"}}
  sanitize_artifact(art, "analysis")
  assert art["details"].find("<<REDACTED>>") >= 0
  assert art["meta"]["token"] == "<<REDACTED>>"
  assert art["items"]["logs"] == "<<REDACTED>>"


def test_redaction_list_values(monkeypatch) -> None:
  monkeypatch.setenv("VLTAIR_REDACT_FIELDS", "arr")
  art = {"arr":["email a@b.com", "ok"]}
  sanitize_artifact(art, "any")
  assert "<<REDACTED>>" in art["arr"][0] and art["arr"][1] == "ok"




def test_redaction_various_builtins(monkeypatch) -> None:
  s = "user@example.com SSN 123-45-6789 card 4111 1111 1111 1111 JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.a.b Bearer abcdef== AKIA1234567890ABCDEF"
  out = sanitize_text(s)
  # Basic sanity: sensitive tokens removed
  assert "user@example.com" not in out
  assert "123-45-6789" not in out
  assert "4111" not in out
  assert "eyJ" not in out
  assert "Bearer" not in out
  assert "AKIA" not in out


def test_redaction_extra_patterns_invalid_is_ignored() -> None:
  s = "hello SECRET42"
  out = sanitize_text(s, extra_patterns=["("])  # invalid regex
  assert out == s  # unchanged due to invalid pattern ignored


def test_redaction_kind_specific_env_fields(monkeypatch) -> None:
  monkeypatch.setenv("VLTAIR_REDACT_FIELDS_TEXT", "title")
  art = {"title": "API key sk-ABCDEFGH12345678", "content": "ok"}
  sanitize_artifact(art, "text")
  assert art["title"].endswith("<<REDACTED>>") and art["title"].startswith("API key ")
