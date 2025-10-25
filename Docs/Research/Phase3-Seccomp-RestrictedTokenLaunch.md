# Phase 3 Planning: Linux seccomp-bpf + Windows Restricted Token launch

Thought framework
- Planning/operations: ReAct (incremental explore + act)
- Design decisions: CoT (explicit multi-step reasoning)

STOP gates (VLTAIR 01-production-workflow)
- STOP before ADR decision; submit ADR for review/approval
- STOP before any external/side-effecting action (OS policy, driver install, CI runners)
- STOP after test failures; include RCA and minimal fix before proceeding

Scope (Phase 3)
- Linux: seccomp-bpf syscall filtering for sandboxed subprocesses spawned by exec/sandbox.py
- Windows: spawn test process with a Restricted Token (low IL / removed privileges), combined with Job Objects
- Feature-flagged, opt-in by default; backward-compatible fallbacks (Phase 1/2)

Non-negotiables (project-level)
- Determinism and reproducibility (temperature=0, fixed seeds, idempotency keys)
- Correctness-first; tests drive implementation; failure paths covered
- Interface stability; versioned task/result schemas; backward-compatible changes
- Security-conscious tool use; explicit error handling; no silent failures
- Performance: <5% overhead vs Phase 2; document SLOs and environment
- Coverage: ≥85% overall; failure-path tests included

Acceptance criteria (map to tests)
- Linux (seccomp-bpf)
  - AC-L1: When flag VLTAIR_SANDBOX_ENABLE_SECCOMP=1 and platform supports seccomp, sandboxed child starts under a restrictive filter and disallowed syscalls are blocked with a deterministic, mapped status (e.g., EPERM → SANDBOX_DENIED).
  - AC-L2: Provide minimal default allowlist (read-only filesystem ops, network off by default, basic process/thread, time, FD mgmt). Configurable policy surface behind flag.
  - AC-L3: Capability detection prevents activation on unsupported kernels (graceful fallback to Phase 2).
  - AC-L4: Integration tests (platform-gated) demonstrate enforcement on CI runners that support seccomp; skipped otherwise.
- Windows (Restricted Token launch)
  - AC-W1: When flag VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH=1, child process is created using a restricted token (CreateRestrictedToken + CreateProcessAsUser/CreateProcessWithTokenW) and attached to a Job Object.
  - AC-W2: Capability detection/logging when privileges are insufficient (graceful fallback to Phase 2 behavior).
  - AC-W3: Integration tests (platform-gated) validate restricted token properties (reduced privileges, integrity level) without requiring admin rights.
- Cross-cutting
  - AC-X1: Structured enforcement reporting extended with Phase 3 fields (policy kind, enabled, effective, reason on fallback).
  - AC-X2: CLI status reflects Phase 3 capability flags and effective state.
  - AC-X3: Performance overhead <5% vs Phase 2 on representative test matrix; attach bench artifacts.

Architecture mapping
- exec/sandbox.py: add optional seccomp-bpf setup (Linux) and restricted-token process creation path (Windows) under feature flags
- cli/orchestrator_cli.py: expose/echo Phase 3 flags in status
- tests/unit + tests/integration: platform-gated tests and stubs for capability detection
- Docs/ADRs: ADR-XXXX-sandbox-phase3-seccomp-token.md records decisions

First principles & invariants
- Fail closed for forbidden operations when enabled; otherwise fail safe (graceful fallback) with explicit reason
- Deterministic status mapping for denial events; no reliance on wall-clock or nondeterministic ordering
- Least privilege by default; no secret leakage in logs/errors
- Stable/public interfaces: do not break Phase 1/2 callers; version enforcement report

Alternatives (Linux seccomp)
- A1: Use prctl(SECCOMP) + BPF filter assembled via libseccomp (preferred: readability, portability)
- A2: Handcraft BPF via seccomp syscall without libseccomp (lower deps, higher complexity, error-prone)
- A3: Namespaces + Landlock (optional complement; out-of-scope for Phase 3)

Alternatives (Windows token launch)
- B1: CreateRestrictedToken + CreateProcessWithTokenW (preferred if privileges allow)
- B2: CreateRestrictedToken + CreateProcessAsUser (requires SeAssignPrimaryTokenPrivilege; may not be available)
- B3: AppContainer sandbox (Windows 8+; stronger isolation but requires manifesting; possibly follow-up)

Risks & mitigations
- Kernel/userland variance (seccomp, Windows privileges): mitigate via robust capability detection and skip/soft-fail
- CI environment differences: platform-gated tests with stubs; document required runners
- Performance regressions: micro-bench before/after; enforce <5% budget; document configs
- Maintainability: prefer libseccomp bindings or a small C shim to keep policies readable/tested

Test plan
- Unit: policy assembly, capability detection, error-path coverage; deterministic seeds
- Integration (platform-gated): enforce a known-denied syscall (e.g., socket, ptrace) and verify mapped status
- Windows: verify token attributes (reduced privileges/integrity) via WinAPI inspection where feasible
- CLI: status command shows Phase 3 effective flags
- Coverage: ensure ≥85% overall; add failure-path tests

Performance plan
- Extend existing benches to include sandbox-on vs sandbox-off cases; publish P50/P95 with 95% CI; assert ≤5% regression vs Phase 2

Security considerations
- Threat model: untrusted test code attempts privileged syscalls or capability escalation; we block/contain
- Logging: redact sensitive info; no token/secret leakage; avoid printing raw syscall args

Open questions
- Preferred libseccomp binding strategy (direct ctypes vs C extension vs third-party lib)?
- Minimal cross-distro kernel features to support? RHEL/Ubuntu LTS targets?
- Windows token creation privilege assumptions on CI runners?

Next steps (proposed)
1) Draft ADR-XXXX-sandbox-phase3-seccomp-token (STOP for approval)
2) Spike: seccomp policy skeleton + capability probe (no enforcement by default)
3) Add CLI/status plumbing and reporting fields
4) Implement platform-gated tests and minimal enforcement
5) Bench + document; iterate to pass all gates

