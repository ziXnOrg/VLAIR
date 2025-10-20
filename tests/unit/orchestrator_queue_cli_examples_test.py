import subprocess, sys, json


def test_cli_queue_outputs_metrics_json():
  # Invoke as a script to exercise argparse entrypoint
  proc = subprocess.run([sys.executable, "-m", "cli.orchestrator_cli", "queue"], capture_output=True, text=True)
  assert proc.returncode == 0
  data = json.loads(proc.stdout)
  assert data.get("ok") is True
  assert "queued" in data and "workers" in data


