from __future__ import annotations

import argparse
import json
import sys
import uuid
from orchestrator.common.error_envelope import make_agent_error

from orchestrator.core.orchestrator import Orchestrator
import os


def main() -> int:
  parser = argparse.ArgumentParser(prog="orchestrator")
  # Global redaction config flags
  parser.add_argument("--redact-prefix", dest="redact_prefixes", action="append", default=[], help="Add a redaction prefix (can be repeated). Sets VLTAIR_REDACT_PREFIXES")
  parser.add_argument("--redact-fields", dest="redact_fields", type=str, default=None, help="Comma-separated field paths to redact. Sets VLTAIR_REDACT_FIELDS")
  sub = parser.add_subparsers(dest="cmd", required=True)
  run = sub.add_parser("run", help="Run a task by providing JSON on stdin or via --file")
  run.add_argument("--file", type=str, default=None, help="Path to JSON AgentTask payload")
  status = sub.add_parser("status", help="List registered agents and current redaction settings")
  reg = sub.add_parser("register", help="Register an agent")
  reg.add_argument("name", type=str)
  reg.add_argument("--cap", dest="caps", action="append", default=[])
  upd = sub.add_parser("update", help="Update agent status/load")
  upd.add_argument("name", type=str)
  upd.add_argument("--status", type=str, choices=["idle","busy","down"], default=None)
  upd.add_argument("--load", type=int, default=None)
  q = sub.add_parser("queue", help="Show queue metrics")
  query = sub.add_parser("query", help="Execute a structured query (hybrid/dense/sparse)")
  replay = sub.add_parser("replay", help="Deterministic replay from WAL")
  replay.add_argument("--run-id", dest="run_id", required=True, help="Run ID to replay")
  replay.add_argument("--wal-dir", dest="wal_dir", default=None, help="WAL directory (defaults to $VLTAIR_WAL_DIR or ./wal)")
  api = sub.add_parser("api", help="HTTP adapter operations")
  api_sub = api.add_subparsers(dest="acmd", required=True)
  api_serve = api_sub.add_parser("serve", help="Start the stdlib HTTP adapter")
  api_serve.add_argument("--host", type=str, default=None, help="Host to bind (default env VLTAIR_API_HOST or 127.0.0.1)")
  api_serve.add_argument("--port", type=str, default=None, help="Port to bind (default env VLTAIR_API_PORT or 8080)")
  api_serve.add_argument("--token", type=str, default=None, help="Auth token; sets VLTAIR_API_TOKEN")
  api_serve.add_argument("--allow-ip", dest="allow_ip", type=str, default=None, help="Comma-separated IP allowlist; sets VLTAIR_API_IP_ALLOWLIST")
  # Hidden test knob: duration to auto-stop in ms when VLTAIR_TEST_MODE=1
  api_serve.add_argument("--duration-ms", dest="duration_ms", type=int, default=None, help=argparse.SUPPRESS)
  api_serve.add_argument("--no-log", dest="no_log", action="store_true", help="Suppress startup/shutdown logs")
  trace_cmd = sub.add_parser("trace", help="Trace operations")
  trace_sub = trace_cmd.add_subparsers(dest="tcmd", required=True)
  trace_export = trace_sub.add_parser("export", help="Export trace HTML from telemetry JSONL")
  trace_export.add_argument("--input", required=True, help="Path to telemetry JSONL file")
  trace_export.add_argument("--output", required=True, help="Path to output HTML file")
  wf = sub.add_parser("workflow", help="Workflow operations (run/dry-run)")
  wf_sub = wf.add_subparsers(dest="wcmd", required=True)
  wf_run = wf_sub.add_parser("run", help="Run a deterministic workflow")
  wf_run.add_argument("--type", required=True, choices=["feature-add", "fix-failing"], dest="type")
  wf_run.add_argument("--goal", default="", help="Goal for feature-add")
  wf_run.add_argument("--file", required=True, help="Target file path")
  wf_run.add_argument("--test", default="", help="Pytest nodeid for fix-failing")
  wf_run.add_argument("--dry-run", action="store_true", dest="dry_run")
  wf_run.add_argument("--json", action="store_true", dest="json_out")
  wf_run.add_argument("--engine", choices=["direct", "scheduler-sync"], default="direct", dest="engine")
  query.add_argument("--text", type=str, default="", help="Query text")
  query.add_argument("--k", type=int, default=10, help="Top-k results")
  query.add_argument("--mode", type=str, choices=["hybrid","dense","sparse"], default="hybrid")
  query.add_argument("--rrf-k", dest="rrf_k", type=float, default=60.0)
  query.add_argument("--dense-weight", dest="dense_weight", type=float, default=0.5)
  query.add_argument("--sparse-weight", dest="sparse_weight", type=float, default=0.5)
  query.add_argument("--rerank-factor", dest="rerank_factor", type=int, default=10)
  query.add_argument("--filter-json", dest="filter_json", type=str, default=None, help="JSON string for filters")
  query.add_argument("--filter-kv", dest="filter_kv", action="append", default=[], help="key=value filter (repeatable)")
  args = parser.parse_args()

  # Apply global redaction env overrides if provided
  if args.redact_prefixes:
    os.environ["VLTAIR_REDACT_PREFIXES"] = ",".join(args.redact_prefixes)
  if args.redact_fields is not None:
    os.environ["VLTAIR_REDACT_FIELDS"] = args.redact_fields

  if args.cmd == "run":
    o = Orchestrator()
    try:
      if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
          data = json.load(f)
      else:
        data = json.load(sys.stdin)
      out = o.submit_task(data)
      print(json.dumps({"ok": True, **out}))
      return 0
    except Exception as e:
      trace_id = str(uuid.uuid4())
      err = make_agent_error(None, agent="CLI", code="invalid_argument", message="invalid task payload", details=str(e))
      print(json.dumps({"ok": False, "traceId": trace_id, "error": err}))
      return 1
  elif args.cmd == "status":
    o = Orchestrator()
    # Convert sets to lists for JSON serialization
    agents = []
    for a in o._registry.list():
      d = dict(a.__dict__)
      if isinstance(d.get("capabilities"), set):
        d["capabilities"] = sorted(list(d["capabilities"]))
      agents.append(d)
    # Gather redaction settings from environment
    prefixes = os.environ.get("VLTAIR_REDACT_PREFIXES", "")
    fields = os.environ.get("VLTAIR_REDACT_FIELDS", "")
    kind_fields: dict[str, str] = {}
    for k, v in os.environ.items():
      if k.startswith("VLTAIR_REDACT_FIELDS_") and k != "VLTAIR_REDACT_FIELDS_":
        kind_fields[k] = v
    # Sandbox Phase 3 flags (deterministic reporting)
    seccomp_flag = (os.environ.get("VLTAIR_SANDBOX_ENABLE_SECCOMP", "0") == "1")
    rlaunch_flag = (os.environ.get("VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH", "0") == "1")

    print(json.dumps({"ok": True, "agents": agents, "redaction": {"prefixes": prefixes, "fields": fields, "kindFields": kind_fields}, "sandbox": {"phase3": {"flags": {"linux_seccomp": seccomp_flag, "windows_restricted_launch": rlaunch_flag}, "effective": False, "policy_kind": "none", "version": 0}}}))
    return 0
  elif args.cmd == "register":
    o = Orchestrator()
    o.register_agent(args.name, args.caps)
    print(json.dumps({"ok": True}))
    return 0
  elif args.cmd == "update":
    o = Orchestrator()
    o.update_agent(args.name, status=args.status, load=args.load)
    print(json.dumps({"ok": True}))
    return 0
  elif args.cmd == "queue":
    # Ensure tests don't require pyvesper import: force lazy backend by avoiding search usage
    os.environ.setdefault("VLTAIR_TEST_MODE", "1")
    o = Orchestrator()
    print(json.dumps({"ok": True, **o.queue_metrics()}))
    return 0
  elif args.cmd == "query":
    # Build filters
    filt: object = None
    if args.filter_json:
      filt = args.filter_json
    elif args.filter_kv:
      kv: dict[str, str] = {}
      for item in args.filter_kv:
        if "=" in item:
          k, v = item.split("=", 1)
          kv[k] = v
      filt = kv
    # Dry-run path for tests without pyvesper
    if os.environ.get("VLTAIR_TEST_MODE", "") == "1":
      print(json.dumps({
        "ok": True,
        "dryRun": True,
        "query": {
          "text": args.text,
          "k": args.k,
          "mode": args.mode,
          "rrf_k": args.rrf_k,
          "dense_weight": args.dense_weight,
          "sparse_weight": args.sparse_weight,
          "rerank_factor": args.rerank_factor,
          "filters": filt if filt is not None else None,
        }
      }))
      return 0
    # Real execution
    try:
      from orchestrator.context.context_store import ContextStore  # type: ignore
      ctx = ContextStore()
      results = ctx.structured_query(
        text=args.text,
        k=int(args.k),
        mode=args.mode,  # type: ignore
        filters=filt,  # type: ignore
        rrf_k=float(args.rrf_k),
        dense_weight=float(args.dense_weight),
        sparse_weight=float(args.sparse_weight),
        rerank_factor=int(args.rerank_factor),
      )
      # Serialize results
      out = [{
        "doc_id": r.doc_id,
        "score": r.score,
        "dense_score": r.dense_score,
        "sparse_score": r.sparse_score,
        "dense_rank": r.dense_rank,
        "sparse_rank": r.sparse_rank,
      } for r in results]
      print(json.dumps({"ok": True, "results": out}))
      return 0
    except Exception as e:
      trace_id = str(uuid.uuid4())
      err = make_agent_error(None, agent="CLI", code="internal", message="query error", details=str(e))
      print(json.dumps({"ok": False, "traceId": trace_id, "error": err}))
      return 1

  elif args.cmd == "api":
    if args.acmd == "serve":
      # Resolve host/port from CLI > env > defaults
      host = args.host or os.environ.get("VLTAIR_API_HOST") or "127.0.0.1"
      port_str = args.port or os.environ.get("VLTAIR_API_PORT") or "8080"
      try:
        port = int(port_str)
      except Exception as e:
        err = make_agent_error(None, agent="CLI", code="invalid_argument", message="invalid port", details=str(e))
        print(json.dumps({"ok": False, "error": err}))
        return 1
      if args.token is not None:
        os.environ["VLTAIR_API_TOKEN"] = str(args.token)
      if args.allow_ip is not None:
        os.environ["VLTAIR_API_IP_ALLOWLIST"] = str(args.allow_ip)
      try:
        from orchestrator.transports.http_adapter import HttpAgentServer
        srv = HttpAgentServer(host, port)
        httpd, bound_port = srv.start()
        start_log = {"event":"server.start","host":host,"port":bound_port,"pid":os.getpid()}
        print(json.dumps(start_log)) if not getattr(args, "no_log", False) else None
        # Test mode auto-stop
        if os.environ.get("VLTAIR_TEST_MODE", "") == "1":
          duration = args.duration_ms if args.duration_ms is not None else 300
          import time
          time.sleep(max(0, int(duration)) / 1000.0)
          srv.stop()
          print(json.dumps({"event":"server.stop","reason":"TEST_MODE"})) if not getattr(args, "no_log", False) else None
          return 0
        # Serve until Ctrl+C
        try:
          httpd.serve_forever()
        except KeyboardInterrupt:
          srv.stop()
          print(json.dumps({"event":"server.stop","reason":"SIGINT"})) if not getattr(args, "no_log", False) else None
          return 0
      except OSError as e:
        err = make_agent_error(None, agent="CLI", code="unavailable", message="bind failure", details=str(e))
        print(json.dumps({"ok": False, "error": err}))
        return 1
      except Exception as e:
        err = make_agent_error(None, agent="CLI", code="internal", message="server error", details=str(e))
        print(json.dumps({"ok": False, "error": err}))
        return 1

  elif args.cmd == "trace":
    if args.tcmd == "export":
      try:
        events: list[dict] = []
        with open(args.input, "r", encoding="utf-8") as f:
          for line in f:
            s = line.strip()
            if not s:
              continue
            try:
              events.append(json.loads(s))
            except Exception:
              # Skip malformed line deterministically
              continue
        from orchestrator.obs.trace_ui import export_html
        export_html(events, args.output)
        print(json.dumps({"event": "trace.export", "input": args.input, "output": args.output, "count": len(events)}))
        return 0
      except Exception as e:
        err = make_agent_error(None, agent="CLI", code="invalid_argument", message="trace export error", details=str(e))
        print(json.dumps({"ok": False, "error": err}))
        return 1

  elif args.cmd == "replay":
    try:
      from orchestrator.wal.replay import replay_run
      out = replay_run(args.run_id, wal_dir=args.wal_dir)
      print(json.dumps(out))
      return 0
    except Exception as e:
      trace_id = str(uuid.uuid4())
      err = make_agent_error(None, agent="CLI", code="invalid_argument", message="replay error", details=str(e))
      print(json.dumps({"ok": False, "traceId": trace_id, "error": err}))
      return 1
  elif args.cmd == "workflow":
    from cli.workflow_commands import handle_workflow_run
    if args.wcmd == "run":
      return handle_workflow_run(args)
    return 0

  return 0


if __name__ == "__main__":
  raise SystemExit(main())