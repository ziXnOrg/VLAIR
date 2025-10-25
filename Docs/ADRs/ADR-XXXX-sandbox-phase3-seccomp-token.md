---
Title: ADR-XXXX — Sandbox Phase 3: Linux seccomp-bpf + Windows Restricted Token Launch
Status: Proposed
Date: 2025-10-25
Authors: VLTAIR Team
---

Context
- We completed Phase 2 (cgroups v2 adapter, Restricted Token capability detection). Next, we aim to strengthen OS isolation with Linux seccomp-bpf and a Windows restricted-token launch path.
- Constraints: Determinism, security-first, backward compatibility with Phases 1/2; feature-flagged opt-in; performance overhead <5%; coverage ≥85%.

Problem Statement
- Limit available syscalls (Linux) and privileges (Windows) for sandboxed test processes launched by exec/sandbox.py, without breaking environments lacking support.

Decision Options
- Linux
  - L-A: prctl(SECCOMP) using libseccomp to assemble a readable BPF allowlist (Preferred)
  - L-B: Raw BPF assembly via seccomp syscall (No extra deps, but error-prone)
  - L-C: Defer seccomp; rely on rlimits/cgroups only (Insufficient isolation)
- Windows
  - W-A: CreateRestrictedToken + CreateProcessWithTokenW; attach to Job Object (Preferred)
  - W-B: CreateRestrictedToken + CreateProcessAsUser (requires privileges; may not be portable)
  - W-C: AppContainer-based sandbox (stronger isolation; higher complexity; follow-up)

Decision (Proposed)
- Adopt L-A and W-A behind feature flags:
  - VLTAIR_SANDBOX_ENABLE_SECCOMP=1 to enable seccomp on Linux with capability detection and graceful fallback.
  - VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH=1 to enable token-based spawning on Windows (fallback to Phase 2 if privileges insufficient).
- Expose structured enforcement reporting fields and reflect in CLI status.

Consequences
- Positive: Stronger isolation, least-privilege runtime, auditable policy.
- Negative: Platform variance; need robust detection and skip paths; small overhead to startup latency.

Compatibility & Migration
- No breaking changes. Phase 1/2 behavior remains default. New flags opt-in Phase 3 capabilities.

Security & Determinism
- Denials map to deterministic statuses; avoid logging sensitive syscall args; stable policies with versioning.

Performance
- Target <5% overhead vs Phase 2. Bench before/after; attach artifacts and env manifests.

Validation & Tests
- Unit: policy assembly, capability detection, failure paths.
- Integration (platform-gated): verify denied syscall mapping (Linux); verify token attributes and reduced privileges (Windows).
- CI: keep coverage ≥85%; zero new warnings; gates green.

Implementation Plan (High-level)
1) Capability probes and flags; reporting schema updates.
2) Linux: minimal allowlist via libseccomp (or thin C shim), attach to child via preexec_fn.
3) Windows: restricted token creation + CreateProcessWithTokenW path; attach to Job Object.
4) Platform-gated tests; CLI status plumbing; docs updates.
5) Benchmarks + performance review.

STOP Gate
- Do not implement until this ADR is reviewed and approved.

References
- seccomp(2), prctl(2), libseccomp docs
- Windows CreateRestrictedToken, CreateProcessWithTokenW, integrity levels
- VLTAIR rules: 00-index, 01-production-workflow, 03-ci-and-quality-gates, 05-security-and-safety

