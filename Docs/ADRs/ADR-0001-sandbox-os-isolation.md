# ADR-0001: OS-level sandboxing for exec/sandbox.py

Status: Proposed
Date: 2025-10-24
Authors: VLTAIR Core

## Context

The current exec/sandbox.py provides a minimal, deterministic test runner that:
- Spawns pytest in a subprocess with a wall-clock timeout
- Ensures deterministic env (PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1)
- Propagates COVERAGE_PROCESS_START and PYTHONPATH for subprocess coverage

Limitations (security/reliability):
- No OS-level resource enforcement (CPU, memory, process count)
- No privilege reduction; no syscall/network restrictions
- No bounded output beyond Python buffer sizes

VLTAIR requirements (non-negotiables per .augment/rules):
- Determinism & reproducibility; security-conscious tool use; explicit error handling
- Performance budgets (≤5% overhead for key paths); interface stability; coverage ≥85%

Goal: Add OS-level sandboxing with graceful cross-platform behavior while preserving the current API for callers and meeting VLTAIR’s constraints.

## Decision Drivers
- Threat model: Malicious/buggy tests can exhaust CPU/memory, fork-bomb, or produce massive output
- Portability: Windows, Linux, macOS support without mandatory non-stdlib deps
- Determinism: Stable, documented rc/status mapping; repeatable outcomes
- Maintainability: Clear abstraction with platform-specific backends; capability detection
- Developer ergonomics: Backward-compatible API; structured results for observability

## Considered Options

### Option A — Platform-specific native sandbox (recommended)
- Windows: Job Objects (MVP), optional Restricted Token
- Linux: rlimits (MVP), optional cgroups v2 and seccomp-bpf (feature-flagged)
- macOS: rlimits (MVP)
Pros: Stronger guarantees where available; no container dependency; controlled overhead
Cons: Multiple code paths; uneven parity (macOS weaker); capability/permission checks needed

### Option B — Lightweight rlimits-only (Unix) + Job Objects (Windows)
Pros: Simple, minimal code; broadly available
Cons: Weaker isolation (no syscall/network controls; memory limits unreliable on macOS)

### Option C — External sandbox tools (firejail/bubblewrap/nsjail; Windows AppContainer wrappers)
Pros: Strong isolation via existing tools
Cons: New dependencies; portability/ops burden; not universally available across platforms

(Rejected) Option D — Containerized execution (Docker/Podman) for unit tests
- Adds heavy dependencies and environment coupling; not suitable as default for dev/CI flows

## Decision
Adopt Option A with graceful degradation and feature detection. Provide a unified SandboxPolicy and a structured result that reports what was enforced. Keep the existing run_pytests(paths, timeout_s) API unchanged (shim to v2 with defaults). Add run_pytests_v2(paths, policy) for policy-driven callers and richer observability.

## Feature Matrix (MVP + optional)

| Capability | Windows (Job Obj) | Linux (rlimits) | Linux (cgroups v2) | Linux (seccomp) | macOS (rlimits) |
|---|---|---:|---:|---:|---:|
| Wall timeout | Yes | Yes | n/a | n/a | Yes |
| CPU time | Yes (rate/time) | Yes (RLIMIT_CPU) | n/a | n/a | Yes (RLIMIT_CPU) |
| Memory | Yes (job limit) | Fallback (RLIMIT_AS) | Yes (memory.max) | n/a | Best-effort (RLIMIT_AS) |
| PIDs/processes | Yes (active process limit) | Fallback (RLIMIT_NPROC) | Yes (pids.max) | n/a | Best-effort (RLIMIT_NPROC) |
| Open files | n/a | Yes (RLIMIT_NOFILE) | n/a | n/a | Yes (RLIMIT_NOFILE) |
| Network/syscalls | No | No | No | Optional (seccomp) | No |
| Work dir isolation | Yes (cwd) | Yes (cwd) | n/a | n/a | Yes (cwd) |
| Output caps | Yes (userland truncation) | Yes | n/a | n/a | Yes |

Notes:
- Linux cgroups/seccomp are optional and feature-detected; policy reports partial enforcement if unavailable.
- macOS lacks first-class cgroups/seccomp; we rely on rlimits and userland controls.

## Resource Budget Defaults (can be tuned)

| Resource | Default |
|---|---|
| Wall time | 30 s |
| CPU time | 20 s |
| Memory | 512 MiB |
| Processes (PIDs) | 32 |
| Open files (NOFILE) | 512 |
| Output cap per stream | 1 MiB |

## Error/Status Mapping (normalized)

| Status | rc | Unix signal example | Description |
|---|---:|---:|---|
| OK | 0 | – | Tests passed |
| TIMEOUT | 124 | – | Wall-clock timeout exceeded |
| CPU_LIMIT | 152 | SIGXCPU=24 → 128+24 | CPU time limit exceeded |
| MEM_LIMIT | 137 | SIGKILL=9 → 128+9 | OOM kill or memory limit hit |
| KILLED_TERM | 143 | SIGTERM=15 → 128+15 | Terminated by TERM |
| KILLED_KILL | 137 | SIGKILL=9 → 128+9 | Force-killed |
| FORBIDDEN_SYSCALL | 159 | SIGSYS=31 → 128+31 | Seccomp violation (optional) |
| INTERNAL_ERROR | 1 | – | Sandbox internal failure |

Notes:
- Windows terminations are mapped heuristically to the normalized rc; the structured result includes platform-native reason (e.g., NTSTATUS, job limit category).
- Structured results include a `status` enum, `reason`, and `enforced` summary for determinism and diagnostics.

## Non-goals (MVP)
- Full network isolation across all platforms
- Container-based execution as default
- chroot/namespace isolation on Unix
- Perfect parity across all OSes (documented differences acceptable)

## Interface & Compatibility
- Keep: `run_pytests(paths: list[str], timeout_s: int) -> tuple[int,str]` (shim)
- Add: `run_pytests_v2(paths: list[str], policy: SandboxPolicy) -> SandboxResultV2`
- Add: `SandboxPolicy` (dataclass) — platform-agnostic resource limits and behavior flags
- Add: `SandboxResultV2` — structured result with status, rc, reason, stdout/stderr (truncated), duration_ms, cmd, traceId, enforced summary
- TestAgent remains on run_pytests for now; migration to v2 is optional and documented (timeline below)

### Example (sketch)
```python
dataclass
class SandboxPolicy:
    wall_time_s: int = 30
    cpu_time_s: int = 20
    mem_bytes: int = 512 * 2**20
    pids_max: int = 32
    nofile: int = 512
    output_bytes: int = 1 * 2**20
    enforce_network: bool = False  # best-effort; optional (Linux+seccomp)

class SandboxResultV2(TypedDict):
    version: int
    status: str
    rc: int
    reason: str
    stdout: str
    stderr: str
    duration_ms: int
    cmd: list[str]
    traceId: str
    enforced: dict  # {capability: {requested: X, applied: bool, details: ...}}
```

## Implementation Notes (Phased Rollout)

Phase 1 (MVP):
- Windows: Job Objects (create job; set ExtendedLimitInformation for memory/process count; CPU rate/time if available); AssignProcessToJobObject
- Linux/macOS: rlimits via preexec_fn (RLIMIT_CPU, RLIMIT_AS, RLIMIT_NOFILE, RLIMIT_NPROC)
- All: deterministic env, working dir isolation, bounded stdout/stderr (truncate at 1 MiB with clear "[TRUNCATED]" tag), wall timeout
- Capability detection: report enforcement per platform; never silently skip requested constraints

Phase 2:
- Linux: cgroups v2 (memory.max, pids.max, optional cpu.max) when permitted (sysfs or systemd-run scope)
- Windows (optional): Restricted Token for privilege reduction

Phase 3 (feature-flagged, optional):
- Linux: seccomp-bpf minimal profile (block networking and dangerous syscalls), only when libseccomp available and policy requests it

Behavior:
- If a strict SandboxPolicy requests a capability not available, return INTERNAL_ERROR unless `allow_partial=True` is set on the policy; when partial allowed, return status with `reason="PARTIAL_ENFORCEMENT"` and details
- Normalize rc per table; include platform-native info in `reason`

## Testing Strategy & Acceptance Criteria

Unit tests (all OSes):
- Policy validation and defaulting
- Command construction and env overlay (no regressions)
- Output truncation logic and deterministic markers
- Error mapping from platform-native termination → normalized status/rc

Integration tests (capability-gated, skip if unsupported):
- CPU limit: run CPU hog → CPU_LIMIT
- Memory limit: run malloc/consume → MEM_LIMIT (137)
- PIDs limit: spawn children → enforcement triggers
- Timeout: sleep forever → TIMEOUT (124)
- Output flood: print >1MiB → truncated with marker

Determinism:
- Two consecutive runs under same policy produce identical status/rc and headers

CI Matrix:
- Windows 10/11; Ubuntu 22.04/24.04; macOS latest
- Capability detection logs; flaky tests forbidden; overall coverage ≥85% (sandbox enforcement code ≥90%)

## Performance Validation
- Measure per-run overhead vs current minimal sandbox: setup/teardown and steady-state
- Targets: <5% overhead on typical unit test tasks (wall time)
- Record environment, seeds, policy, and versions for reproducibility

## Migration Plan
- T0: Land MVP (Phase 1) with run_pytests shim → run_pytests_v2(default_policy)
- T1: Add TestAgent optional path to consume structured result (traceId/status) without breaking existing behavior
- T2: Document policy knobs for TestExec scenarios; default remains conservative and deterministic

## Consequences
Positive:
- Stronger safety and reliability; resource budgets enforced; improved diagnostics and observability
Negative:
- Platform-specific code and uneven feature parity; optional dependencies for advanced features
Neutral:
- Backward-compatible API preserved; clear documentation reduces developer friction

## Security & Safety Alignment
- No silent failures: enforcement summary always present; partial enforcement explicitly reported
- Least privilege where feasible (Restricted Token optional); deterministic failures
- Redaction remains in orchestrator layer; bounded outputs reduce leakage risk

## References
- Windows Job Objects (CreateJobObject/AssignProcessToJobObject/SetInformationJobObject)
- Windows Restricted Tokens (CreateRestrictedToken)
- Linux rlimits (resource.setrlimit; RLIMIT_CPU/RLIMIT_AS/RLIMIT_NOFILE/RLIMIT_NPROC)
- Linux cgroups v2 (memory.max, pids.max, cpu.max)
- Linux seccomp-bpf (libseccomp)
- VLTAIR Rules: 00-index, 01-production-workflow, 05-security-and-safety

