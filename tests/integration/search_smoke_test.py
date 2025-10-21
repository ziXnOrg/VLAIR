import json
import os
import subprocess
import sys


def test_cli_query_dry_run_smoke() -> None:
  env = os.environ.copy()
  env["VLTAIR_TEST_MODE"] = "1"
  cmd = [sys.executable, "-m", "cli.orchestrator_cli", "--redact-prefix", "sk-", "query", "--text", "hello", "--k", "3", "--mode", "hybrid", "--rrf-k", "60", "--dense-weight", "0.6", "--sparse-weight", "0.4", "--rerank-factor", "10", "--filter-kv", "type=text"]
  proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
  assert proc.returncode == 0
  out = json.loads(proc.stdout)
  assert out["ok"] is True
  assert out.get("dryRun") is True
  q = out.get("query", {})
  assert q.get("text") == "hello"
  assert q.get("k") == 3
  assert q.get("mode") == "hybrid"
  assert q.get("rrf_k") == 60
  assert q.get("dense_weight") == 0.6
  assert q.get("sparse_weight") == 0.4
  assert q.get("rerank_factor") == 10
  assert q.get("filters") == {"type": "text"}
