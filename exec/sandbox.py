from __future__ import annotations

"""
VLTAIR Sandbox (Phase 1/2): pytest runner with OS-level resource limits.

Determinism & coverage
- Enforces deterministic env: PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1
- Propagates COVERAGE_PROCESS_START and PYTHONPATH to enable subprocess coverage

OS-level enforcement (graceful, capability-detected)
- Windows (Phase 1): Job Objects (process/memory/process-count limits) when available
  * Can be disabled for testing via VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB=1
- Linux/macOS (Phase 1): rlimits via preexec_fn (RLIMIT_CPU, RLIMIT_AS, RLIMIT_NPROC, RLIMIT_NOFILE)
- Linux (Phase 2 opt-in): cgroups v2 adapter (memory.max, pids.max, cpu.max)
  * Enable with VLTAIR_SANDBOX_ENABLE_CGROUPS_V2=1; falls back to rlimits if unavailable
- Windows (Phase 2 opt-in): Restricted Token preparation
  * Enable with VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN=1; combined with Job Objects when applicable
  * Spawning with the restricted token is attempted only if supported; otherwise reported and gracefully skipped
- Partial enforcement allowed by default (policy.allow_partial=True)

Default budgets (configurable via SandboxPolicy)
- wall_time_s=30, cpu_time_s=20, mem_bytes=512 MiB, pids_max=32, nofile=512
- output_bytes=1 MiB per stream; network isolation not enforced in MVP

Interfaces
- run_pytests_v2(paths, policy) -> dict{version=2, status, rc, reason, stdout, stderr,
  duration_ms, cmd, traceId, enforced}
- run_pytests(paths, timeout_s) -> (rc, combined_output): shim over v2 for compatibility

Normalized status/rc mapping
- OK=0; TIMEOUT=124; CPU_LIMIT=128+SIGXCPU (commonly 152); MEM_LIMIT=137;
  KILLED_TERM=143; KILLED_KILL=137; INTERNAL_ERROR=1

Output handling
- Concurrent capture with deterministic truncation marker: "[TRUNCATED at N bytes]"
"""

from typing import Any, Dict, List, Mapping, Tuple
import os
import subprocess
import sys
import time
import uuid


def _build_env(base: Mapping[str, str], env_overrides: Dict[str, str] | None = None) -> Dict[str, str]:
  """Create a child environment overlay with deterministic settings.

  - Preserve COVERAGE_PROCESS_START and PYTHONPATH if present in the parent.
  - Set PYTHONHASHSEED=0 (unless explicitly set by parent).
  - Set PYTHONDONTWRITEBYTECODE=1.
  """
  env: Dict[str, str] = dict(base)
  # Determinism
  env.setdefault("PYTHONHASHSEED", "0")
  env["PYTHONDONTWRITEBYTECODE"] = "1"
  # Explicitly propagate coverage-related vars if present
  if "COVERAGE_PROCESS_START" in base:
    env["COVERAGE_PROCESS_START"] = base["COVERAGE_PROCESS_START"]
  if "PYTHONPATH" in base:
    env["PYTHONPATH"] = base["PYTHONPATH"]
  # Apply caller overrides last
  if env_overrides:
    env.update(env_overrides)
  return env

# === Phase 1 MVP: OS-level sandboxing (per ADR-XXXX) ===
from dataclasses import dataclass
import threading
import io
import platform
import signal

# Phase 2 feature flags (opt-in)
_ENABLE_CGROUPS_V2 = (os.getenv("VLTAIR_SANDBOX_ENABLE_CGROUPS_V2", "0") == "1")
_ENABLE_RESTRICTED_TOKEN = (os.getenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN", "0") == "1")

import contextlib

_IS_WINDOWS = os.name == "nt"
_USE_WIN_JOB = _IS_WINDOWS and os.getenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "0") != "1"

@dataclass
class SandboxPolicy:
  wall_time_s: int = 30
  cpu_time_s: int = 20
  mem_bytes: int = 512 * 2**20
  pids_max: int = 32
  nofile: int = 512  # Unix only
  output_bytes: int = 1 * 2**20
  enforce_network: bool = False  # best-effort (not implemented in MVP)
  allow_partial: bool = True     # if False and a requested cap is unavailable -> INTERNAL_ERROR

def _read_stream_limited(pipe, limit: int) -> tuple[str, bool]:
  """Read bytes from a pipe up to limit; drain remainder to avoid blocking.
  Returns (decoded_text, truncated_flag)."""
  buf = bytearray()
  truncated = False
  try:
    while True:
      chunk = pipe.read(64 * 1024)
      if not chunk:
        break
      # Ensure bytes
      if isinstance(chunk, str):
        chunk = chunk.encode("utf-8", "replace")
      if len(buf) < limit:
        remaining = limit - len(buf)
        buf += chunk[:remaining]
      # Always drain remainder to avoid producer blocking
      if len(buf) >= limit:
        truncated = True
    # done
  except Exception:
    truncated = True
  finally:
    try:
      pipe.close()
    except Exception:
      pass
  text = buf.decode("utf-8", errors="replace")
  if truncated:
    text += f"\n[TRUNCATED at {limit} bytes]\n"
  return text, truncated

# ---- Error/status normalization ----
_STATUS_OK = "OK"
_STATUS_TIMEOUT = "TIMEOUT"
_STATUS_CPU = "CPU_LIMIT"
_STATUS_MEM = "MEM_LIMIT"
_STATUS_TERM = "KILLED_TERM"
_STATUS_KILL = "KILLED_KILL"
_STATUS_INTERNAL = "INTERNAL_ERROR"

# Subset of NTSTATUS that plausibly indicate memory/resource termination
_NTSTATUS_MEM = {0xC0000017, 0xC00000A7, 0xC00000A2}  # NO_MEMORY, COMMITMENT_LIMIT, WORKING_SET_QUOTA

def _normalize_status(returncode: int, timed_out: bool, plat: str) -> tuple[str, int, str]:
  if timed_out:
    return _STATUS_TIMEOUT, 124, "wall timeout"
  if returncode == 0:
    return _STATUS_OK, 0, "ok"
  if plat != "Windows":
    # Unix: negative return code means terminated by signal
    if returncode < 0:
      sig = -returncode
      if sig == getattr(signal, "SIGXCPU", 24):
        return _STATUS_CPU, 128 + sig, f"SIGXCPU (signal {sig})"
      if sig == getattr(signal, "SIGKILL", 9):
        return _STATUS_KILL, 128 + sig, f"SIGKILL (signal {sig})"
      if sig == getattr(signal, "SIGTERM", 15):
        return _STATUS_TERM, 128 + sig, f"SIGTERM (signal {sig})"
      return _STATUS_INTERNAL, 1, f"terminated by signal {sig}"
    # Non-zero exit; unknown cause
    return _STATUS_INTERNAL, 1, f"exit code {returncode}"
  # Windows: best-effort mapping for NTSTATUS-like codes
  try:
    code = int(returncode) & 0xFFFFFFFF
    if code in _NTSTATUS_MEM:
      return _STATUS_MEM, 137, f"NTSTATUS 0x{code:08X} (memory/resource)"
  except Exception:
    pass
  return _STATUS_INTERNAL, 1, f"exit code {returncode}"

# ---- Unix rlimits (Linux/macOS) ----

def _make_unix_preexec(policy: SandboxPolicy):  # type: ignore[return-type]
  import resource  # Unix only
  def _apply():
    # CPU seconds
    try:
      resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_time_s, policy.cpu_time_s))
    except Exception:
      pass
    # Address space (bytes)
    try:
      resource.setrlimit(resource.RLIMIT_AS, (policy.mem_bytes, policy.mem_bytes))
    except Exception:
      pass
    # Processes
    try:
      resource.setrlimit(resource.RLIMIT_NPROC, (policy.pids_max, policy.pids_max))
    except Exception:
      pass
    # Open files
    try:
      resource.setrlimit(resource.RLIMIT_NOFILE, (policy.nofile, policy.nofile))
    except Exception:
      pass
  return _apply

# ---- Phase 2: capability detection & thin adapters ----

def _detect_cgroups_v2() -> tuple[bool, Dict[str, Any], str]:
  """Detect if cgroups v2 unified hierarchy is present (Linux only).
  Returns (detected, details, reason). details contains {root, controllers}.
  """
  if _IS_WINDOWS or platform.system() != "Linux":
    return False, {"root": "", "controllers": []}, "not-linux"
  root = "/sys/fs/cgroup"
  controllers_path = os.path.join(root, "cgroup.controllers")
  try:
    if not os.path.exists(controllers_path):
      return False, {"root": root, "controllers": []}, "cgroup.controllers not found"
    with open(controllers_path, "r", encoding="utf-8", errors="ignore") as f:
      controllers = f.read().strip().split()
    return True, {"root": root, "controllers": controllers}, ""
  except Exception as e:
    return False, {"root": root, "controllers": []}, f"{e.__class__.__name__}: {e}"


def _setup_cgroup_v2(trace_id: str, policy: SandboxPolicy) -> tuple[str | None, Dict[str, Any], str]:
  """Create a transient cgroup and configure basic limits.
  Returns (path, details, reason). details contains {applied, path, limits{...}}.
  """
  detected, info, reason = _detect_cgroups_v2()
  details: Dict[str, Any] = {"applied": False, "path": "", "limits": {"memory.max": "", "pids.max": "", "cpu.max": ""}}
  if not detected:
    return None, details, reason
  root = info.get("root", "/sys/fs/cgroup")
  path = os.path.join(root, "vltair", trace_id)
  details["path"] = path
  try:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
      os.mkdir(path)
    except FileExistsError:
      pass
  except Exception as e:
    return None, details, f"mkdir failed: {e}"

  def _write_limit(name: str, value: str) -> bool:
    try:
      with open(os.path.join(path, name), "w", encoding="utf-8") as f:
        f.write(value)
      details["limits"][name] = value
      return True
    except Exception:
      return False

  mem_ok = True
  if policy.mem_bytes > 0:
    mem_ok = _write_limit("memory.max", str(policy.mem_bytes))
  else:
    _write_limit("memory.max", "max")
  pids_ok = True
  if policy.pids_max > 0:
    pids_ok = _write_limit("pids.max", str(policy.pids_max))
  else:
    _write_limit("pids.max", "max")
  # cpu.max: thin adapter - constrain to 1 CPU share (quota=period=100000)
  cpu_ok = _write_limit("cpu.max", "100000 100000")
  details["applied"] = bool(mem_ok or pids_ok or cpu_ok)
  return path, details, ""


def _detect_restricted_token_support() -> tuple[bool, str]:
  """Best-effort detection for Windows Restricted Token support.
  Returns (detected, reason)."""
  if not _IS_WINDOWS:
    return False, "not-windows"
  try:
    import ctypes  # noqa: F401
    adv = ctypes.WinDLL("advapi32", use_last_error=True)  # type: ignore[attr-defined]
    has_fn = getattr(adv, "CreateRestrictedToken", None) is not None
    return bool(has_fn), "" if has_fn else "CreateRestrictedToken missing"
  except Exception as e:
    return False, f"{e.__class__.__name__}: {e}"


def _win_try_create_restricted_token() -> tuple[bool, str]:
  """Attempt to create a restricted token from current process token.
  Returns (ok, reason). Does not spawn with the token (privilege-sensitive)."""
  if not _IS_WINDOWS:
    return False, "not-windows"
  try:
    import ctypes
    import ctypes.wintypes as wt
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    OpenProcessToken = adv.OpenProcessToken
    GetCurrentProcess = k32.GetCurrentProcess
    CloseHandle = k32.CloseHandle
    CreateRestrictedToken = adv.CreateRestrictedToken
    # Access: TOKEN_ASSIGN_PRIMARY(0x0001) | TOKEN_DUPLICATE(0x0002) | TOKEN_QUERY(0x0008)
    access = 0x0001 | 0x0002 | 0x0008
    hTok = wt.HANDLE()
    if not OpenProcessToken(GetCurrentProcess(), access, ctypes.byref(hTok)):
      return False, "OpenProcessToken failed"
    newTok = wt.HANDLE()
    # Flags: DISABLE_MAX_PRIVILEGE = 0x1
    ok = CreateRestrictedToken(hTok, 0x1, 0, None, 0, None, 0, None, ctypes.byref(newTok))
    CloseHandle(hTok)
    if not ok:
      return False, "CreateRestrictedToken failed"
    CloseHandle(newTok)
    return True, ""
  except Exception as e:
    return False, f"{e.__class__.__name__}: {e}"


# ---- Windows Job Objects (minimal) ----
if _IS_WINDOWS:
  import ctypes
  import ctypes.wintypes as wt
  HANDLE = wt.HANDLE
  DWORD = wt.DWORD
  SIZE_T = ctypes.c_size_t
  ULONG_PTR = ctypes.c_void_p
  class LARGE_INTEGER(ctypes.Structure):
    _fields_ = [("QuadPart", ctypes.c_longlong)]
  class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
      ("ReadOperationCount", ctypes.c_uint64),
      ("WriteOperationCount", ctypes.c_uint64),
      ("OtherOperationCount", ctypes.c_uint64),
      ("ReadTransferCount", ctypes.c_uint64),
      ("WriteTransferCount", ctypes.c_uint64),
      ("OtherTransferCount", ctypes.c_uint64),
    ]
  class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
      ("PerProcessUserTimeLimit", LARGE_INTEGER),
      ("PerJobUserTimeLimit", LARGE_INTEGER),
      ("LimitFlags", DWORD),
      ("MinimumWorkingSetSize", SIZE_T),
      ("MaximumWorkingSetSize", SIZE_T),
      ("ActiveProcessLimit", DWORD),
      ("Affinity", ULONG_PTR),
      ("PriorityClass", DWORD),
      ("SchedulingClass", DWORD),
    ]
  class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
      ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
      ("IoInfo", IO_COUNTERS),
      ("ProcessMemoryLimit", SIZE_T),
      ("JobMemoryLimit", SIZE_T),
      ("PeakProcessMemoryUsed", SIZE_T),
      ("PeakJobMemoryUsed", SIZE_T),
    ]
  # Constants
  JobObjectExtendedLimitInformation = 9
  JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
  JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
  # Kernel32 bindings
  _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
  _CreateJobObjectW = _k32.CreateJobObjectW
  _CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
  _CreateJobObjectW.restype = HANDLE
  _SetInformationJobObject = _k32.SetInformationJobObject
  _SetInformationJobObject.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p, DWORD]
  _SetInformationJobObject.restype = wt.BOOL
  _AssignProcessToJobObject = _k32.AssignProcessToJobObject
  _AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]
  _AssignProcessToJobObject.restype = wt.BOOL
  _CloseHandle = _k32.CloseHandle
  _CloseHandle.argtypes = [HANDLE]
  _CloseHandle.restype = wt.BOOL

  def _win_create_job_and_config(policy: SandboxPolicy):
    enforced = {"mem": {"requested": policy.mem_bytes, "applied": False},
                "pids": {"requested": policy.pids_max, "applied": False},
                "cpu": {"requested": policy.cpu_time_s, "applied": False}}
    job = _CreateJobObjectW(None, None)
    if not job:
      return None, enforced, "CreateJobObject failed"
    try:
      info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
      flags = 0
      # Process memory limit
      if policy.mem_bytes > 0:
        flags |= JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = SIZE_T(policy.mem_bytes)
      # Active process limit
      if policy.pids_max > 0:
        flags |= JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        info.BasicLimitInformation.ActiveProcessLimit = DWORD(policy.pids_max)
      info.BasicLimitInformation.LimitFlags = DWORD(flags)
      ok = _SetInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info))
      if ok:
        enforced["mem"]["applied"] = bool(policy.mem_bytes > 0)
        enforced["pids"]["applied"] = bool(policy.pids_max > 0)
      else:
        return job, enforced, "SetInformationJobObject failed"
      return job, enforced, ""
    except Exception as e:
      return job, enforced, f"job config error: {e}"


def run_pytests_v2(
  paths: List[str],
  policy: SandboxPolicy | None = None,
  env_overrides: Dict[str, str] | None = None,
) -> Dict[str, Any]:
  """Run pytest with OS-level resource limits (Phase 1/2).
  Returns a structured result with normalized status and enforcement summary."""
  trace_id = uuid.uuid4().hex
  if not paths:
    return {"version": 2, "status": _STATUS_INTERNAL, "rc": 1, "reason": "no test paths provided",
            "stdout": "", "stderr": "no test paths provided", "duration_ms": 0, "cmd": [],
            "traceId": trace_id, "enforced": {}}
  pol = policy or SandboxPolicy()
  env = _build_env(os.environ, env_overrides)
  cmd: List[str] = [sys.executable, "-m", "pytest", "-v", *paths]

  # Phase 2 feature flags are read dynamically to support tests that toggle via env
  enable_cg = (os.getenv("VLTAIR_SANDBOX_ENABLE_CGROUPS_V2", "0") == "1")
  enable_rt = (os.getenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN", "0") == "1")

  enforced: Dict[str, Any] = {
    "platform": platform.system(),
    "limits": {
      "cpu": {"requested": pol.cpu_time_s, "applied": False},
      "mem": {"requested": pol.mem_bytes, "applied": False},
      "pids": {"requested": pol.pids_max, "applied": False},
      "nofile": {"requested": pol.nofile, "applied": False},
    },
    "cgroups_v2": {
      "enabled_env": enable_cg,
      "detected": False,
      "applied": False,
      "path": "",
      "reason": "",
      "limits": {},
    },
    "restricted_token": {
      "enabled_env": enable_rt,
      "detected": False,
      "prepared": False,
      "applied": False,
      "reason": "",
    },
  }

  # Start process with platform-specific enforcement
  t0 = time.perf_counter()
  timed_out = False
  stdout_text = stderr_text = ""
  cgroup_path: str | None = None
  try:
    if _IS_WINDOWS and (os.getenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", "0") != "1"):
      # Job Objects (Phase 1)
      job, win_enf, err = _win_create_job_and_config(pol)
      if job is None and not pol.allow_partial:
        return {"version": 2, "status": _STATUS_INTERNAL, "rc": 1, "reason": err, "stdout": "", "stderr": err,
                "duration_ms": 0, "cmd": cmd, "traceId": trace_id, "enforced": enforced}
      enforced["limits"].update(win_enf)
      # Restricted Token (Phase 2 opt-in)
      if enable_rt:
        det, rsn = _detect_restricted_token_support()
        enforced["restricted_token"]["detected"] = det
        if det:
          ok, prep_reason = _win_try_create_restricted_token()
          enforced["restricted_token"]["prepared"] = ok
          if not ok:
            enforced["restricted_token"]["reason"] = prep_reason
        else:
          enforced["restricted_token"]["reason"] = rsn
      # Spawn normally and assign to Job
      p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, env=env)
      try:
        if job:
          _AssignProcessToJobObject(job, HANDLE(p._handle))  # type: ignore[attr-defined]
      except Exception:
        pass
    else:
      # Unix branch (and Windows when jobs are explicitly disabled): preexec rlimits + optional cgroups v2
      preexec = None
      if not _IS_WINDOWS:
        try:
          preexec = _make_unix_preexec(pol)
          enforced["limits"]["cpu"]["applied"] = True
          enforced["limits"]["mem"]["applied"] = True
          enforced["limits"]["pids"]["applied"] = True
          enforced["limits"]["nofile"]["applied"] = True
        except Exception:
          if not pol.allow_partial:
            return {"version": 2, "status": _STATUS_INTERNAL, "rc": 1, "reason": "rlimit init failed",
                    "stdout": "", "stderr": "rlimit init failed", "duration_ms": 0, "cmd": cmd,
                    "traceId": trace_id, "enforced": enforced}
        # Phase 2: cgroups v2 (opt-in)
        if enable_cg:
          det, info, rsn = _detect_cgroups_v2()
          enforced["cgroups_v2"]["detected"] = det
          if not det:
            enforced["cgroups_v2"]["reason"] = rsn
          else:
            cgroup_path, cg_details, cg_err = _setup_cgroup_v2(trace_id, pol)
            enforced["cgroups_v2"].update({k: v for k, v in cg_details.items() if k in ("applied", "path", "limits")})
            if cg_err:
              enforced["cgroups_v2"]["reason"] = cg_err
      p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, env=env, preexec_fn=preexec)
      # Attach to cgroup after spawn (if created)
      if cgroup_path:
        try:
          with open(os.path.join(cgroup_path, "cgroup.procs"), "w", encoding="utf-8") as f:
            f.write(str(p.pid))
          enforced["cgroups_v2"]["applied"] = True
        except Exception as e:
          enforced["cgroups_v2"]["reason"] = f"attach failed: {e}"

    assert p.stdout is not None and p.stderr is not None

    # Read stdout/stderr concurrently with caps
    out_buf: list[str] = [""]
    err_buf: list[str] = [""]
    t_out = threading.Thread(target=lambda: out_buf.__setitem__(0, _read_stream_limited(p.stdout, pol.output_bytes)[0]))
    t_err = threading.Thread(target=lambda: err_buf.__setitem__(0, _read_stream_limited(p.stderr, pol.output_bytes)[0]))
    t_out.start(); t_err.start()

    try:
      p.wait(timeout=pol.wall_time_s)
    except subprocess.TimeoutExpired:
      timed_out = True
      with contextlib.suppress(Exception):
        p.kill()
    finally:
      t_out.join(); t_err.join()

    stdout_text, stderr_text = out_buf[0], err_buf[0]
    duration_ms = int((time.perf_counter() - t0) * 1000)
    rc_raw = p.returncode if p.returncode is not None else (124 if timed_out else 1)
    status, rc, reason = _normalize_status(int(rc_raw), timed_out, enforced["platform"])
    return {"version": 2, "status": status, "rc": rc, "reason": reason,
            "stdout": stdout_text, "stderr": stderr_text, "duration_ms": duration_ms,
            "cmd": cmd, "traceId": trace_id, "enforced": enforced}
  except Exception as e:
    duration_ms = int((time.perf_counter() - t0) * 1000)
    return {"version": 2, "status": _STATUS_INTERNAL, "rc": 1, "reason": f"{e.__class__.__name__}: {e}",
            "stdout": "", "stderr": f"{e.__class__.__name__}: {e}", "duration_ms": duration_ms,
            "cmd": cmd, "traceId": trace_id, "enforced": enforced}



def run_pytests_v1(
  paths: List[str],
  timeout_s: int = 60,
  env_overrides: Dict[str, str] | None = None,
) -> Dict[str, Any]:
  """Run pytest on given paths with a deterministic environment.

  Returns a structured dict (versioned) containing rc, stdio, timing, and cmd.
  This function is intended for future adoption by callers that want traceability.
  """
  trace_id = uuid.uuid4().hex
  result: Dict[str, Any]

  # Validate inputs conservatively (backward compatible with shim expectations)
  if not paths:
    return {
      "version": 1,
      "rc": 1,
      "stdout": "",
      "stderr": "no test paths provided",
      "duration_ms": 0,
      "cmd": [],
      "traceId": trace_id,
    }

  env = _build_env(os.environ, env_overrides)
  cmd: List[str] = [sys.executable, "-m", "pytest", "-v", *paths]

  t0 = time.perf_counter()
  try:
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=env)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
      "version": 1,
      "rc": int(cp.returncode),
      "stdout": cp.stdout or "",
      "stderr": cp.stderr or "",
      "duration_ms": duration_ms,
      "cmd": cmd,
      "traceId": trace_id,
    }
  except subprocess.TimeoutExpired as e:  # type: ignore[misc]
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
      "version": 1,
      "rc": 124,
      "stdout": "",
      "stderr": str(e),
      "duration_ms": duration_ms,
      "cmd": cmd,
      "traceId": trace_id,
    }
  except Exception as e:  # pragma: no cover (rare unexpected errors)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
      "version": 1,
      "rc": 1,
      "stdout": "",
      "stderr": f"{e.__class__.__name__}: {e}",
      "duration_ms": duration_ms,
      "cmd": cmd,
      "traceId": trace_id,
    }
  return result


def run_pytests(paths: List[str], timeout_s: int = 60) -> Tuple[int, str]:
  """Backward-compatible shim that returns (rc, combined_output).

  - Uses run_pytests_v2 under the hood for OS-level enforcement per ADR.
  - Prepends a single header line with traceId and duration for correlation.
  """
  res = run_pytests_v2(paths, policy=SandboxPolicy(wall_time_s=int(timeout_s)))
  header = f"[sandbox] traceId={res['traceId']} duration_ms={res['duration_ms']}\n"
  combined = header + (res.get("stdout", "") or "") + (res.get("stderr", "") or "")
  return int(res.get("rc", 1)), combined

