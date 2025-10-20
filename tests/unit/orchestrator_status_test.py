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


