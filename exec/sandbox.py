from __future__ import annotations

from typing import List, Tuple
import subprocess
import sys


def run_pytests(paths: List[str], timeout_s: int = 30) -> Tuple[int, str]:
  cmd = [sys.executable, "-m", "pytest", "-q", *paths]
  try:
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return out.returncode, out.stdout + out.stderr
  except subprocess.TimeoutExpired:
    return 124, "timeout"
