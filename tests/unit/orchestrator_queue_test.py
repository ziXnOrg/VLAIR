import io
import json
import contextlib

from cli.orchestrator_cli import main as cli_main


def test_cli_queue_metrics(monkeypatch):
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf):
    monkeypatch.setattr("sys.argv", ["orchestrator", "queue"])  # type: ignore[attr-defined]
    rc = cli_main()
  out = buf.getvalue()
  data = json.loads(out)
  assert rc == 0
  assert data["ok"] is True
  assert "queued" in data and "workers" in data


