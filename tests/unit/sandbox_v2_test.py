from __future__ import annotations

import io
import os
import sys
import subprocess
import platform
from typing import Any, Dict, List
from unittest.mock import patch


def test_policy_defaults() -> None:
  from exec.sandbox import SandboxPolicy
  p = SandboxPolicy()
  assert p.wall_time_s == 30 and p.cpu_time_s == 20
  assert p.mem_bytes == 512 * 2**20 and p.pids_max == 32
  assert p.nofile == 512 and p.output_bytes == 1 * 2**20
  assert p.enforce_network is False and p.allow_partial is True


def test_v2_structured_result_basic(monkeypatch) -> None:
  from exec import sandbox as sbx
  monkeypatch.setenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "1")

  captured: Dict[str, Any] = {}

  class _FakePopen:
    def __init__(self, cmd, stdout=None, stderr=None, text=False, env=None, preexec_fn=None):
      captured["cmd"] = cmd
      captured["env"] = env
      self.stdout = io.BytesIO(b"V2-OUT\n")
      self.stderr = io.BytesIO(b"V2-ERR\n")
      self.returncode = 0
    def wait(self, timeout=None):
      return self.returncode
    def kill(self):
      self.returncode = 137

  pol = sbx.SandboxPolicy(wall_time_s=5)
  with patch("exec.sandbox.subprocess.Popen", side_effect=_FakePopen):
    res = sbx.run_pytests_v2(["tests/unit/cli_query_test.py"], policy=pol)

  assert res["version"] == 2 and res["status"] in ("OK",)
  assert res["rc"] == 0 and isinstance(res["duration_ms"], int)
  assert isinstance(res["traceId"], str) and len(res["traceId"]) > 0
  assert "pytest" in res["cmd"]
  assert "V2-OUT" in res["stdout"] and "V2-ERR" in res["stderr"]
  enf = res["enforced"]["limits"]
  assert "cpu" in enf and "mem" in enf and "pids" in enf


def test_output_truncation_marker(monkeypatch) -> None:
  from exec import sandbox as sbx
  monkeypatch.setenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "1")

  big = b"X" * 2048

  class _FakePopen:
    def __init__(self, *args, **kwargs):
      self.stdout = io.BytesIO(big)
      self.stderr = io.BytesIO(big)
      self.returncode = 0
    def wait(self, timeout=None):
      return self.returncode
    def kill(self):
      self.returncode = 137

  pol = sbx.SandboxPolicy(output_bytes=1024, wall_time_s=5)
  with patch("exec.sandbox.subprocess.Popen", side_effect=_FakePopen):
    res = sbx.run_pytests_v2(["tests/unit/cli_query_test.py"], policy=pol)

  assert "[TRUNCATED at 1024 bytes]" in res["stdout"]
  assert "[TRUNCATED at 1024 bytes]" in res["stderr"]


def test_signal_mapping_helper_unix() -> None:
  from exec.sandbox import _normalize_status
  import signal as _sig
  status, rc, reason = _normalize_status(-getattr(_sig, "SIGXCPU", 24), False, "Linux")
  assert status == "CPU_LIMIT" and rc == 128 + getattr(_sig, "SIGXCPU", 24)
  status, rc, reason = _normalize_status(-getattr(_sig, "SIGTERM", 15), False, "Linux")
  assert status == "KILLED_TERM" and rc == 128 + getattr(_sig, "SIGTERM", 15)


def test_integration_timeout_enforced(tmp_path, monkeypatch) -> None:
  # Always safe; should work on all platforms
  from exec import sandbox as sbx
  monkeypatch.setenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "1")
  test_file = tmp_path / "test_sleep.py"
  import textwrap
  test_file.write_text(textwrap.dedent(
    """
    import time

    def test_sleep():
        time.sleep(5)
    """
  ))
  pol = sbx.SandboxPolicy(wall_time_s=1)
  res = sbx.run_pytests_v2([str(test_file)], policy=pol)
  assert res["status"] == "TIMEOUT" and res["rc"] == 124


def test_integration_cpu_limit_unix(tmp_path, monkeypatch) -> None:
  if platform.system() == "Windows":
    import pytest
    pytest.skip("CPU rlimit not supported on Windows in MVP")
  from exec import sandbox as sbx
  test_file = tmp_path / "test_cpu.py"
  # Busy loop to burn CPU
  test_file.write_text(
    """
import time

def test_spin():
  x = 0
  while True:
    x += 1
"""
  )
  pol = sbx.SandboxPolicy(cpu_time_s=1, wall_time_s=10)
  res = sbx.run_pytests_v2([str(test_file)], policy=pol)
  assert res["status"] in {"CPU_LIMIT", "KILLED_KILL", "TIMEOUT"}




def test_phase2_linux_cgroups_reporting_with_stubs(monkeypatch) -> None:
  from exec import sandbox as sbx
  # Force non-Windows path and enable feature flag
  monkeypatch.setenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "1")
  monkeypatch.setenv("VLTAIR_SANDBOX_ENABLE_CGROUPS_V2", "1")
  monkeypatch.setattr(sbx, "_IS_WINDOWS", False, raising=False)
  # Stub detection and setup to avoid requiring root/system support
  monkeypatch.setattr(sbx, "_detect_cgroups_v2", lambda: (True, {"root": "/sys/fs/cgroup", "controllers": ["memory", "pids", "cpu"]}, ""))
  monkeypatch.setattr(sbx, "_setup_cgroup_v2", lambda trace_id, pol: ("/sys/fs/cgroup/vltair/"+trace_id, {"applied": True, "path": "/sys/fs/cgroup/vltair/"+trace_id, "limits": {"memory.max": str(pol.mem_bytes), "pids.max": str(pol.pids_max), "cpu.max": "100000 100000"}}, ""))

  class _FakePopen:
    def __init__(self, *args, **kwargs):
      self.stdout = io.BytesIO(b"OK\n"); self.stderr = io.BytesIO(b"")
      self.returncode = 0; self.pid = 12345
    def wait(self, timeout=None):
      return self.returncode
    def kill(self):
      self.returncode = 137

  with patch("exec.sandbox.subprocess.Popen", side_effect=_FakePopen):
    res = sbx.run_pytests_v2(["tests/unit/cli_query_test.py"], policy=sbx.SandboxPolicy())
  cg = res["enforced"].get("cgroups_v2", {})
  assert cg.get("enabled_env") is True and cg.get("detected") is True
  assert cg.get("applied") in (True, False)  # attachment attempted via stub


def test_phase2_windows_restricted_token_reporting_with_stubs(monkeypatch) -> None:
  from exec import sandbox as sbx
  # Enable restricted token reporting
  monkeypatch.setenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN", "1")
  # Force Windows job path skipping for ease: we'll still record detection
  monkeypatch.setenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "1")
  # Stub detection to True regardless of platform
  monkeypatch.setattr(sbx, "_detect_restricted_token_support", lambda: (True, ""))
  monkeypatch.setattr(sbx, "_win_try_create_restricted_token", lambda: (True, ""))

  class _FakePopen:
    def __init__(self, *args, **kwargs):
      self.stdout = io.BytesIO(b"OK\n"); self.stderr = io.BytesIO(b"")
      self.returncode = 0
    def wait(self, timeout=None):
      return self.returncode

  with patch("exec.sandbox.subprocess.Popen", side_effect=_FakePopen):
    res = sbx.run_pytests_v2(["tests/unit/cli_query_test.py"], policy=sbx.SandboxPolicy())
  rt = res["enforced"].get("restricted_token", {})
  # Enabled via env; with stubs we should see detected/prepared flags set
  assert rt.get("enabled_env") is True
  assert rt.get("detected") in (True, False)  # may be False on non-Windows without stub; here True via stub
  # prepared may be True per stub but applied remains False in MVP
  assert rt.get("prepared") in (True, False)
