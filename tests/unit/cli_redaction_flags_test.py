import json
import subprocess
import sys
from typing import List, Optional

import pytest


@pytest.mark.parametrize(
    "prefixes, fields",
    [
        (["sk-", "ghp_"], "log,details"),
        ([], "meta.token"),
        (["AKIA"], ""),
    ],
)
def test_cli_status_shows_redaction_settings(prefixes: List[str], fields: Optional[str]) -> None:
  cmd: List[str] = [sys.executable, "-m", "cli.orchestrator_cli"]
  for p in prefixes:
    cmd.extend(["--redact-prefix", p])
  if fields is not None:
    cmd.extend(["--redact-fields", fields])
  cmd.append("status")
  proc = subprocess.run(cmd, capture_output=True, text=True)
  assert proc.returncode == 0
  out = json.loads(proc.stdout)
  assert out["ok"] is True
  # Check presence
  assert "redaction" in out
  # Prefixes are joined by comma; order preserved by construction
  if prefixes:
    for p in prefixes:
      assert p in out["redaction"]["prefixes"]
  # Fields echo back
  expected_fields = fields if fields is not None else ""
  assert out["redaction"]["fields"] == expected_fields



def test_cli_status_kind_specific_fields_echo(monkeypatch) -> None:
  # Ensure kind-specific env vars get surfaced in status output
  monkeypatch.setenv("VLTAIR_REDACT_FIELDS_BUILD", "secrets.token,meta.apiKey")
  proc = subprocess.run([sys.executable, "-m", "cli.orchestrator_cli", "status"], capture_output=True, text=True)
  assert proc.returncode == 0
  data = json.loads(proc.stdout)
  assert data.get("ok") is True
  kinds = data.get("redaction", {}).get("kindFields", {})
  assert "VLTAIR_REDACT_FIELDS_BUILD" in kinds
  assert kinds["VLTAIR_REDACT_FIELDS_BUILD"] == "secrets.token,meta.apiKey"
