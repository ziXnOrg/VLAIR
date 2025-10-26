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

# === Phase 1 MVP: OS-level sandboxing (per ADR-0001) ===
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
_STATUS_DENIED = "SANDBOX_DENIED"


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
      if sig == getattr(signal, "SIGSYS", 31):
        return _STATUS_DENIED, 128 + sig, f"SIGSYS (signal {sig})"
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


# ---- CI diagnostics (env-guarded) ----
def _ci_diag_enabled() -> bool:
  try:
    return os.getenv("VLTAIR_CI_DIAG", "0") == "1" and os.getenv("GITHUB_ACTIONS", "").lower() == "true"
  except Exception:
    return False


def _ci_diag_write(event: str, payload: Dict[str, Any]) -> None:
  if not _ci_diag_enabled():
    return
  try:
    import json as _json
    import datetime as _dt
    path = os.getenv("VLTAIR_CI_DIAG_PATH", os.path.join("ci_diagnostics", "run_pytests_v2_windows.jsonl"))
    dirn = os.path.dirname(path)
    if dirn:
      os.makedirs(dirn, exist_ok=True)
    rec: Dict[str, Any] = {
      "ts": _dt.datetime.utcnow().isoformat() + "Z",
      "event": event,
    }
    rec.update(payload)
    with open(path, "a", encoding="utf-8") as f:
      f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
  except Exception:
    # Never raise from diagnostics
    pass

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

# ---- Linux seccomp (Phase 3, optional) ----

# Phase 3 (Linux): seccomp-bpf capability detection
# Requirements:
#  - Linux kernel with seccomp-bpf (>= 3.5; broadly available on modern distros)
#  - libseccomp shared library (e.g., libseccomp.so.2) present at runtime
# Behavior:
#  - Pure detection: returns (False, reason) when unsupported; caller MUST degrade to Phase 2
# Determinism:
#  - No side effects; stable, terse reason strings suitable for surfacing in enforcement.fallback_reason

def _detect_seccomp_lib() -> tuple[bool, str]:
  if _IS_WINDOWS or platform.system() != "Linux":
    return False, "not-linux"
  try:
    import ctypes  # noqa: F401
    for name in ("libseccomp.so.2", "libseccomp.so", "libseccomp.so.1"):
      try:
        ctypes.CDLL(name)
        return True, ""
      except Exception:
        continue
    return False, "libseccomp not found"
  except Exception as e:
    return False, f"{e.__class__.__name__}: {e}"


# Phase 3 (Linux): Apply permissive filter (ALLOW) with explicit TRAP for network syscalls.
# Limitations:
#  - Syscall names can vary by architecture; unresolved names are ignored (policy remains permissive).
#  - Only network syscalls are trapped; all others allowed to minimize breakage of Python/pytest internals.
#  - TRAP action causes SIGSYS, which we normalize deterministically to SANDBOX_DENIED.
# Fallback:
#  - If libseccomp is missing or filter load fails, this preexec is effectively a no-op and caller retains Phase 2 behavior.

def _make_linux_seccomp_preexec_block_net():  # type: ignore[return-type]
  # Install a permissive filter (ALLOW) with explicit TRAP on network-related syscalls.
  # This avoids broad allowlists that can break Python/pytest.
  def _apply():
    import ctypes
    lib = None
    for name in ("libseccomp.so.2", "libseccomp.so", "libseccomp.so.1"):
      try:
        lib = ctypes.CDLL(name)
        break
      except Exception:
        continue
    if lib is None:
      return
    # Types and prototypes
    c_void_p = ctypes.c_void_p
    c_int = ctypes.c_int
    c_uint = ctypes.c_uint
    lib.seccomp_init.argtypes = [c_uint]
    lib.seccomp_init.restype = c_void_p
    lib.seccomp_rule_add.argtypes = [c_void_p, c_uint, c_int, c_uint]
    lib.seccomp_rule_add.restype = c_int
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = c_int
    lib.seccomp_load.argtypes = [c_void_p]
    lib.seccomp_load.restype = c_int
    lib.seccomp_release.argtypes = [c_void_p]
    lib.seccomp_release.restype = None

    SCMP_ACT_ALLOW = 0x7FFF0000
    SCMP_ACT_TRAP = 0x00030000

    ctx = lib.seccomp_init(SCMP_ACT_ALLOW)
    if not ctx:
      return
    try:
      deny = [
        b"socket", b"connect", b"accept", b"accept4", b"bind", b"listen",
        b"sendto", b"sendmsg", b"sendmmsg", b"recvfrom", b"recvmsg", b"recvmmsg",
        b"getsockname", b"getpeername", b"shutdown", b"setsockopt", b"getsockopt",
      ]
      for nm in deny:
        scno = lib.seccomp_syscall_resolve_name(nm)
        if scno >= 0:
          lib.seccomp_rule_add(ctx, SCMP_ACT_TRAP, scno, 0)
      lib.seccomp_load(ctx)
    finally:
      lib.seccomp_release(ctx)
  return _apply


def _compose_preexec(funcs):  # type: ignore[return-type]
  def _run_all():
    for f in funcs:
      if f:
        try:
          f()
        except Exception:
          # Best-effort: do not crash child preexec
          pass
  return _run_all


# Phase 3 (Windows): Restricted token support detection.
# Notes:
#  - Presence of CreateRestrictedToken is a proxy for capability; successful spawn can still require privileges
#    (e.g., SeAssignPrimaryTokenPrivilege, SeIncreaseQuotaPrivilege) at CreateProcessWithTokenW time.

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


# Phase 3 (Windows): Best-effort restricted token creation probe (no process spawn).
# Privilege expectations:
#  - OpenProcessToken(TOKEN_ASSIGN_PRIMARY|TOKEN_DUPLICATE|TOKEN_QUERY) may fail on locked-down environments.
#  - DuplicateTokenEx for a primary token can also require SeAssignPrimaryTokenPrivilege.
# Behavior:
#  - Deterministic outcome with stable reason; callers should surface reason and fall back to Phase 2 when False.

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


# Phase 3 (Windows): Spawn with restricted primary token (CreateProcessWithTokenW).
# Behavior:
#  - Redirects stdout/stderr via CreatePipe; assigns process to an existing Job Object when provided.
#  - Deterministic error messages include GetLastError (GLE) for diagnosability.
# Privilege requirements and fallbacks:
#  - CreateProcessWithTokenW commonly requires SeAssignPrimaryTokenPrivilege and SeIncreaseQuotaPrivilege;
#    standard users often lack these privileges. On failure, callers MUST fall back to the normal Popen path
#    and report enforcement.phase3.fallback_reason.

def _win_spawn_with_restricted_token(cmd: list[str], env: dict[str, str], job: HANDLE | None, cwd: str | None):
    """Spawn a child process with a restricted primary token using CreateProcessWithTokenW.
    Returns an object with .stdout/.stderr file objects and .wait(timeout)->rc semantics.
    Raises RuntimeError on failure with a deterministic message.
    """
    import os as _os
    import subprocess as _sp
    import msvcrt as _msvcrt
    import ctypes
    import ctypes.wintypes as wt

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # --- Structs ---
    class SECURITY_ATTRIBUTES(ctypes.Structure):
      _fields_ = [("nLength", wt.DWORD), ("lpSecurityDescriptor", ctypes.c_void_p), ("bInheritHandle", wt.BOOL)]

    class STARTUPINFOW(ctypes.Structure):
      _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR), ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD), ("dwY", wt.DWORD), ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD), ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
      ]

    class PROCESS_INFORMATION(ctypes.Structure):
      _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]

    # --- Constants ---
    TOKEN_ASSIGN_PRIMARY = 0x0001
    TOKEN_DUPLICATE = 0x0002
    TOKEN_QUERY = 0x0008
    DISABLE_MAX_PRIVILEGE = 0x0001

    LOGON_WITH_PROFILE = 0x00000001
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    STARTF_USESTDHANDLES = 0x00000100

    HANDLE_FLAG_INHERIT = 0x00000001
    INFINITE = 0xFFFFFFFF
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102

    # --- Prototypes ---
    OpenProcessToken = adv.OpenProcessToken
    OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
    OpenProcessToken.restype = wt.BOOL

    GetCurrentProcess = k32.GetCurrentProcess
    GetCurrentProcess.argtypes = []
    GetCurrentProcess.restype = wt.HANDLE

    CreateRestrictedToken = adv.CreateRestrictedToken
    CreateRestrictedToken.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, ctypes.POINTER(wt.HANDLE)]
    CreateRestrictedToken.restype = wt.BOOL

    DuplicateTokenEx = getattr(adv, "DuplicateTokenEx", None)
    if DuplicateTokenEx:
      DuplicateTokenEx.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(SECURITY_ATTRIBUTES), wt.DWORD, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
      DuplicateTokenEx.restype = wt.BOOL

    CreateProcessWithTokenW = adv.CreateProcessWithTokenW
    CreateProcessWithTokenW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPCWSTR, wt.LPWSTR, wt.DWORD, ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
    CreateProcessWithTokenW.restype = wt.BOOL

    CreatePipe = k32.CreatePipe
    CreatePipe.argtypes = [ctypes.POINTER(wt.HANDLE), ctypes.POINTER(wt.HANDLE), ctypes.POINTER(SECURITY_ATTRIBUTES), wt.DWORD]
    CreatePipe.restype = wt.BOOL

    SetHandleInformation = k32.SetHandleInformation
    SetHandleInformation.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD]
    SetHandleInformation.restype = wt.BOOL

    GetStdHandle = k32.GetStdHandle
    GetStdHandle.argtypes = [wt.DWORD]
    GetStdHandle.restype = wt.HANDLE

    WaitForSingleObject = k32.WaitForSingleObject
    WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    WaitForSingleObject.restype = wt.DWORD

    GetExitCodeProcess = k32.GetExitCodeProcess
    GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    GetExitCodeProcess.restype = wt.BOOL

    CloseHandle = k32.CloseHandle
    CloseHandle.argtypes = [wt.HANDLE]
    CloseHandle.restype = wt.BOOL

    AssignProcessToJobObject = _AssignProcessToJobObject  # reuse bound symbol

    def _fail(msg: str) -> RuntimeError:
      gle = ctypes.get_last_error() or 0
      return RuntimeError(f"{msg} (GLE={gle})")

    # --- Build pipes (stdout/stderr) ---
    sa = SECURITY_ATTRIBUTES(wt.DWORD(ctypes.sizeof(SECURITY_ATTRIBUTES)), None, wt.BOOL(True))
    h_out_r, h_out_w = wt.HANDLE(), wt.HANDLE()
    h_err_r, h_err_w = wt.HANDLE(), wt.HANDLE()
    if not CreatePipe(ctypes.byref(h_out_r), ctypes.byref(h_out_w), ctypes.byref(sa), 0):
      raise _fail("CreatePipe stdout failed")
    if not CreatePipe(ctypes.byref(h_err_r), ctypes.byref(h_err_w), ctypes.byref(sa), 0):
      # cleanup stdout pipe
      CloseHandle(h_out_r); CloseHandle(h_out_w)
      raise _fail("CreatePipe stderr failed")
    # Parent read ends must be non-inheritable
    SetHandleInformation(h_out_r, HANDLE_FLAG_INHERIT, 0)
    SetHandleInformation(h_err_r, HANDLE_FLAG_INHERIT, 0)

    # --- Create restricted primary token ---
    hTok = wt.HANDLE()
    if not OpenProcessToken(GetCurrentProcess(), TOKEN_ASSIGN_PRIMARY | TOKEN_DUPLICATE | TOKEN_QUERY, ctypes.byref(hTok)):
      # cleanup pipes
      CloseHandle(h_out_r); CloseHandle(h_out_w); CloseHandle(h_err_r); CloseHandle(h_err_w)
      raise _fail("OpenProcessToken failed")
    newTok = wt.HANDLE()
    if not CreateRestrictedToken(hTok, DISABLE_MAX_PRIVILEGE, 0, None, 0, None, 0, None, ctypes.byref(newTok)):
      CloseHandle(hTok); CloseHandle(h_out_r); CloseHandle(h_out_w); CloseHandle(h_err_r); CloseHandle(h_err_w)
      raise _fail("CreateRestrictedToken failed")
    CloseHandle(hTok)

    # Best-effort ensure primary token via DuplicateTokenEx if available
    if DuplicateTokenEx:
      primaryTok = wt.HANDLE()
      # SecurityImpersonation=2, TokenPrimary=1
      if not DuplicateTokenEx(newTok, TOKEN_ASSIGN_PRIMARY | TOKEN_QUERY, None, 2, 1, ctypes.byref(primaryTok)):
        CloseHandle(newTok); CloseHandle(h_out_r); CloseHandle(h_out_w); CloseHandle(h_err_r); CloseHandle(h_err_w)
        raise _fail("DuplicateTokenEx failed")
      CloseHandle(newTok)
      hToUse = primaryTok
    else:
      hToUse = newTok

    # --- STARTUPINFO and environment ---
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    si.dwFlags = STARTF_USESTDHANDLES
    si.hStdInput = GetStdHandle(wt.DWORD(0xFFFFfff6))  # STD_INPUT_HANDLE(-10)
    si.hStdOutput = h_out_w
    si.hStdError = h_err_w

    pi = PROCESS_INFORMATION()

    # Command line and environment block
    cmdline = _sp.list2cmdline(cmd)
    cmdbuf = ctypes.create_unicode_buffer(cmdline)
    # Deterministic environment block: sorted by key
    items = sorted((k, env[k]) for k in env)
    block = "\0".join([f"{k}={v}" for k, v in items]) + "\0\0"
    envbuf = ctypes.create_unicode_buffer(block)

    ok = CreateProcessWithTokenW(hToUse, LOGON_WITH_PROFILE, None, cmdbuf, CREATE_UNICODE_ENVIRONMENT, envbuf, cwd, ctypes.byref(si), ctypes.byref(pi))
    # Child inherits write ends; parent must close them after spawn
    CloseHandle(h_out_w); CloseHandle(h_err_w)
    if not ok:
      CloseHandle(hToUse); CloseHandle(h_out_r); CloseHandle(h_err_r)
      raise _fail("CreateProcessWithTokenW failed")

    # Assign to job if provided
    try:
      if job:
        AssignProcessToJobObject(job, pi.hProcess)
    except Exception:
      pass

    # Wrap read handles as binary file objects
    fd_out = _msvcrt.open_osfhandle(int(h_out_r.value), 0)
    fd_err = _msvcrt.open_osfhandle(int(h_err_r.value), 0)
    f_out = _os.fdopen(fd_out, "rb", buffering=0)
    f_err = _os.fdopen(fd_err, "rb", buffering=0)

    class _WinProc:
      def __init__(self, hProc, hTh, fout, ferr):
        self._hProc = hProc; self._hTh = hTh
        self.stdout = fout; self.stderr = ferr
        self.returncode = None
      def wait(self, timeout=None):
        ms = INFINITE if timeout is None else int(max(0, timeout) * 1000)
        res = WaitForSingleObject(self._hProc, ms)
        if res == WAIT_TIMEOUT:
          raise _sp.TimeoutExpired(cmd, timeout)
        code = wt.DWORD()
        if not GetExitCodeProcess(self._hProc, ctypes.byref(code)):
          self.returncode = 1
        else:
          self.returncode = int(code.value)
        # Close thread handle; keep process handle until kill/GC
        try:
          CloseHandle(self._hTh)
        except Exception:
          pass
        return self.returncode
      def kill(self):
        # Best-effort terminate
        try:
          k32.TerminateProcess(self._hProc, 137)
        except Exception:
          pass

    return _WinProc(pi.hProcess, pi.hThread, f_out, f_err)


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
  enable_seccomp = (os.getenv("VLTAIR_SANDBOX_ENABLE_SECCOMP", "0") == "1")
  enable_rlaunch = (os.getenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH", "0") == "1")


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
    "phase3": {
      "policy_kind": "none",
      "enabled": bool(enable_seccomp or enable_rlaunch),
      "effective": False,
      "fallback_reason": "",
      "version": 0,
    },

  }

  # Start process with platform-specific enforcement
  t0 = time.perf_counter()
  timed_out = False
  stdout_text = stderr_text = ""
  cgroup_path: str | None = None
  _ci_diag_write("start", {
    "traceId": trace_id,
    "platform": enforced["platform"],
    "cwd": os.getcwd(),
    "cmd": cmd,
    "policy": {
      "wall_time_s": pol.wall_time_s,
      "cpu_time_s": pol.cpu_time_s,
      "mem_bytes": pol.mem_bytes,
      "pids_max": pol.pids_max,
      "nofile": pol.nofile,
      "output_bytes": pol.output_bytes,
      "allow_partial": pol.allow_partial,
    },
    "env_flags": {
      "VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB": os.getenv("VLTAIR_SANDBOX_DISABLE_WINDOWS_JOB", ""),
      "VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN": os.getenv("VLTAIR_SANDBOX_ENABLE_RESTRICTED_TOKEN", ""),
      "VLTAIR_SANDBOX_ENABLE_CGROUPS_V2": os.getenv("VLTAIR_SANDBOX_ENABLE_CGROUPS_V2", ""),
    }
  })

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
      # Phase 3: restricted token launch (opt-in)
      used_restricted = False
      if enable_rlaunch:
        enforced["phase3"]["policy_kind"] = "restricted_token"
        enforced["phase3"]["enabled"] = True
        det, rsn = _detect_restricted_token_support()
        if not det:
          enforced["phase3"]["fallback_reason"] = rsn
        else:
          try:
            p = _win_spawn_with_restricted_token(cmd, env, job, None)
            enforced["phase3"]["effective"] = True
            enforced["phase3"]["version"] = 1
            used_restricted = True
          except Exception as e:
            enforced["phase3"]["fallback_reason"] = f"{e}"

      if not used_restricted:
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
      # Phase 3: seccomp (opt-in)
      if enable_seccomp and platform.system() == "Linux":
        enforced["phase3"]["policy_kind"] = "seccomp"
        enforced["phase3"]["enabled"] = True
        det, rsn = _detect_seccomp_lib()
        if not det:
          enforced["phase3"]["fallback_reason"] = rsn
        else:
          try:
            seccomp_pre = _make_linux_seccomp_preexec_block_net()
            preexec = _compose_preexec([preexec, seccomp_pre])
            enforced["phase3"]["effective"] = True
            enforced["phase3"]["version"] = 1
          except Exception as e:
            enforced["phase3"]["fallback_reason"] = f"seccomp init failed: {e}"

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

    _ci_diag_write("spawned", {
      "traceId": trace_id,
      "pid": int(getattr(p, "pid", -1)),
      "platform": enforced["platform"],
    })

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
    # Deterministic fallback: if the measured wall time exceeded the policy limit
    # but no TimeoutExpired was observed (rare on Windows CI), treat as timeout.
    if (not timed_out) and (pol.wall_time_s is not None) and (duration_ms >= int(pol.wall_time_s * 1000)):
      timed_out = True

    rc_raw = 124 if timed_out else (p.returncode if p.returncode is not None else 1)
    status, rc, reason = _normalize_status(int(rc_raw), timed_out, enforced["platform"])
    _ci_diag_write("completed", {
      "traceId": trace_id,
      "returncode": int(rc_raw),
      "timed_out": bool(timed_out),
      "status": status,
      "rc_mapped": rc,
      "reason": reason,
      "duration_ms": duration_ms,
      "stdout_len": len(stdout_text),
      "stderr_len": len(stderr_text),
      "stdout_sample": stdout_text[:500],
      "stderr_sample": stderr_text[:500],
    })

    return {"version": 2, "status": status, "rc": rc, "reason": reason,
            "stdout": stdout_text, "stderr": stderr_text, "duration_ms": duration_ms,
            "cmd": cmd, "traceId": trace_id, "enforced": enforced}
  except Exception as e:
    duration_ms = int((time.perf_counter() - t0) * 1000)
    _ci_diag_write("exception", {
      "traceId": trace_id,
      "type": e.__class__.__name__,
      "msg": str(e),
      "duration_ms": duration_ms,
    })

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

