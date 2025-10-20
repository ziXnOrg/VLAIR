from __future__ import annotations

import argparse
import json
import sys
import uuid

from orchestrator.core.orchestrator import Orchestrator
import os


def main() -> int:
  parser = argparse.ArgumentParser(prog="orchestrator")
  sub = parser.add_subparsers(dest="cmd", required=True)
  run = sub.add_parser("run", help="Run a task by providing JSON on stdin or via --file")
  run.add_argument("--file", type=str, default=None, help="Path to JSON AgentTask payload")
  status = sub.add_parser("status", help="List registered agents")
  reg = sub.add_parser("register", help="Register an agent")
  reg.add_argument("name", type=str)
  reg.add_argument("--cap", dest="caps", action="append", default=[])
  upd = sub.add_parser("update", help="Update agent status/load")
  upd.add_argument("name", type=str)
  upd.add_argument("--status", type=str, choices=["idle","busy","down"], default=None)
  upd.add_argument("--load", type=int, default=None)
  q = sub.add_parser("queue", help="Show queue metrics")
  args = parser.parse_args()

  if args.cmd == "run":
    data = None
    if args.file:
      with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    else:
      data = json.load(sys.stdin)

    o = Orchestrator()
    try:
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
    print(json.dumps({"ok": True, "agents": agents}))
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

  return 0


if __name__ == "__main__":
  raise SystemExit(main())


