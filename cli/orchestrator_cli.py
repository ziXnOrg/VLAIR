from __future__ import annotations

import argparse
import json
import sys
import uuid

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
      print(json.dumps({"ok": False, "traceId": trace_id, "error": str(e)}))
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
      print(json.dumps({"ok": False, "traceId": trace_id, "error": str(e)}))
      return 1

  return 0


if __name__ == "__main__":
  raise SystemExit(main())


