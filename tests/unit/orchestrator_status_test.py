import io
import json
import contextlib

from cli.orchestrator_cli import main as cli_main


def test_cli_status_outputs_agents(monkeypatch):
  # Capture stdout
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    monkeypatch.setattr("sys.argv", ["orchestrator", "status"])  # type: ignore[attr-defined]
    rc = cli_main()
  out = buf.getvalue()
  assert rc == 0
  data = json.loads(out)
  assert data["ok"] is True
  assert isinstance(data["agents"], list)





def test_cli_status_includes_sandbox_phase3_flags(monkeypatch):
  import json, io, contextlib
  from cli.orchestrator_cli import main as cli_main
  # Set flags deterministically
  monkeypatch.setenv("VLTAIR_SANDBOX_ENABLE_SECCOMP", "1")
  monkeypatch.setenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH", "0")
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    monkeypatch.setattr("sys.argv", ["orchestrator", "status"])  # type: ignore[attr-defined]
    rc = cli_main()
  data = json.loads(buf.getvalue())
  assert rc == 0 and data["ok"] is True
  sbx = data.get("sandbox", {}).get("phase3", {})
  assert isinstance(sbx, dict)
  flags = sbx.get("flags", {})
  assert flags.get("linux_seccomp") is True and flags.get("windows_restricted_launch") is False
