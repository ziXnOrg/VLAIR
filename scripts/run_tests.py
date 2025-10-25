#!/usr/bin/env python3
"""
Cross-platform test runner for VLTAIR.

Purpose:
- Ensure subprocess coverage collection for CLI tests by setting
  COVERAGE_PROCESS_START and prepending the repo root to PYTHONPATH so
  sitecustomize.py is importable at interpreter startup.

Usage examples:
- python scripts/run_tests.py
- python scripts/run_tests.py -k cli_query -q
- python scripts/run_tests.py tests/unit/cli_registry_test.py -v

Notes:
- No new dependencies; uses only the Python standard library.
- Exits with pytest's return code for CI integration.
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path


def main(argv: list[str]) -> int:
    # Compute repo root as parent of this scripts/ directory
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    # Prepare environment
    env = os.environ.copy()
    # Ensure coverage auto-start in subprocesses.
    env.setdefault("COVERAGE_PROCESS_START", str(repo_root / ".coveragerc"))
    # On Windows, a prior crashed run can leave the default data file locked.
    # Use a per-process data file to avoid PermissionError on erase.
    env.setdefault("COVERAGE_FILE", str(repo_root / f".coverage.unit.{os.getpid()}"))

    # Prepend repo_root to PYTHONPATH (so sitecustomize.py at repo root is importable)
    existing_pp = env.get("PYTHONPATH", "")
    if existing_pp:
        env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{existing_pp}"
    else:
        env["PYTHONPATH"] = str(repo_root)

    # Default pytest args; allow additional args passthrough
    default_args = [
        "-m", "pytest",
        "tests/unit/",
        "-v",
        "--cov=orchestrator",
        "--cov=cli",
        "--cov-report=term-missing",
    ]
    # If caller specified explicit targets (e.g., a path starting with tests/), still append
    # to defaults so coverage flags remain consistent.
    passthrough = argv[:] if argv else []

    cmd = [sys.executable, *default_args, *passthrough]

    # Brief header for visibility/determinism
    print("[run-tests] COVERAGE_PROCESS_START=", env.get("COVERAGE_PROCESS_START"))
    print("[run-tests] COVERAGE_FILE=", env.get("COVERAGE_FILE"))
    print("[run-tests] PYTHONPATH=", env.get("PYTHONPATH"))
    print("[run-tests] CWD=", os.getcwd())
    print("[run-tests] Exec:", " ".join(cmd))

    proc = subprocess.run(cmd, env=env)
    return int(proc.returncode)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

