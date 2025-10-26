---
Title: ADR-0002 — Sandbox Phase 3: Linux seccomp-bpf + Windows Restricted Token Launch
Status: Accepted
Date: 2025-10-25
Authors: VLTAIR Team
---

Context
- Phase 2 delivered cgroups v2 integration and Windows Restricted Token capability detection. Phase 3 strengthens OS isolation with Linux seccomp-bpf and a Windows restricted-token launch path, both opt-in behind feature flags.
- Non‑negotiables: Determinism, explicit error model (no silent failures), backward compatibility with Phases 1/2; performance overhead ≤5%; coverage ≥85%; zero warnings/static analysis clean.

Problem Statement
- Limit available syscalls (Linux) and privileges (Windows) for sandboxed test processes launched by exec/sandbox.py, while gracefully degrading on platforms lacking support or sufficient privileges.

Decision
- Adopt Linux L-A (libseccomp) and Windows W-A (CreateRestrictedToken + CreateProcessWithTokenW) behind feature flags:
  - VLTAIR_SANDBOX_ENABLE_SECCOMP=1 enables a restrictive seccomp allowlist on Linux, with capability detection and deterministic fallback when unsupported.
  - VLTAIR_SANDBOX_ENABLE_RESTRICTED_LAUNCH=1 enables restricted-token spawning on Windows and attaches the process to a Job Object; deterministic fallback if privileges are insufficient.
- Expose structured enforcement reporting fields (policy_kind, enabled, effective, fallback_reason, version) and reflect these in CLI status and logs.

Consequences
- Positive: Stronger isolation and least-privilege runtime with auditable, versioned policy.
- Negative: Platform variance and privileges may limit activation; minor startup overhead.

Compatibility & Migration
- Backward compatible: Phases 1/2 remain default behavior. Phase 3 features are opt-in via flags and capability detection.
- Fallback behavior: When the feature flag is set but capability/privilege is missing, execution proceeds under Phase 2 with explicit fallback_reason recorded (e.g., linux_seccomp_unsupported_kernel, windows_insufficient_privilege).
- Interfaces stable: CLI and structured result schemas are versioned; new fields are additive and backward compatible.

Security & Determinism (Error Model)
- Deterministic enforcement:
  - Linux: Disallowed syscalls are blocked with a stable, mapped status (e.g., EPERM/EACCES → SANDBOX_DENIED) and recorded in enforcement reporting.
  - Windows: Restricted token reduces privileges; attempted forbidden actions yield deterministic, mapped statuses.
- Error model: All failures return explicit statuses with human- and machine-readable details; no silent failures. Logs are structured and redact sensitive arguments; no secrets in traces.
- Determinism constraints: Fixed seeds; stable ordering; no reliance on wall-clock in enforcement decisions; policy versions are immutable once released.

Performance
- Target ≤5% overhead versus Phase 2 on representative workloads. Attach bench artifacts and environment manifests. Investigate and mitigate regressions beyond the budget before enabling by default (if ever).

Validation & Tests
- Unit: policy assembly, capability detection, error-path handling, deterministic status mapping.
- Integration (platform-gated):
  - Linux: demonstrate denied syscall mapping under seccomp.
  - Windows: validate token properties (reduced privileges, integrity level) without requiring admin rights.
- CI: gates green; coverage ≥85%; zero new warnings.

Implementation Plan (High-level)
1) Capability probes and feature flags; extend enforcement reporting and CLI status.
2) Linux: minimal allowlist via libseccomp (thin C shim if needed); apply in child via preexec_fn.
3) Windows: CreateRestrictedToken + CreateProcessWithTokenW path; attach to Job Object.
4) Platform-gated tests and docs; ensure deterministic mapping and explicit fallback reasons.
5) Benchmarks and performance review; attach artifacts.

STOP Gates
- STOP‑A: Before merging first enforcement code paths (post‑capability probes), review error model and reporting schema.
- STOP‑B: After Linux seccomp enforcement behind flag is implemented and tests pass (GREEN), review perf artifacts.
- STOP‑C: After Windows restricted‑token launch behind flag is implemented and tests pass (GREEN), review perf artifacts.
- STOP‑D: Before any change to default behavior (e.g., turning features on by default), require dedicated approval and full perf/security sign‑off.

References
- seccomp(2), prctl(2), libseccomp docs
- Windows CreateRestrictedToken, CreateProcessWithTokenW, integrity levels
- VLTAIR rules: 00-index, 01-production-workflow, 03-ci-and-quality-gates, 05-security-and-safety

