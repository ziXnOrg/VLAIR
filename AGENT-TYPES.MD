# VLTAIR Agent Types — Batch Research

This document captures staged research and design details for VLTAIR’s agent types under the orchestrator. Each batch tightens determinism, observability, and security while specifying structured reasoning procedures (deliberate steps, branching search) tailored to each agent. All procedures are deterministic and event‑sourced; no free‑form hidden reasoning is persisted — only structured plans, checkpoints, and artifacts.

Goals
- Deterministic procedures and replayable state for every agent step
- Clear inputs/outputs and payload schemas per agent
- Branching “trees of candidates” with budgeted selection heuristics
- Redaction, sandboxing, and timeouts integrated with diagnostics
- Orchestrator‑compatible results (payload.delta/doc, artifacts, coverage hints)

References
- base interface: orchestrator/agents/base.py:12
- code generation: orchestrator/agents/codegen.py:8
- static analysis: orchestrator/agents/static_analysis.py:8
- test runner: orchestrator/agents/test_agent.py:9
- test generator: orchestrator/agents/test_gen.py:8
- redaction helpers: orchestrator/obs/redaction.py:1


## Batch 1 — Surfaces, Deterministic Procedures, Selection Heuristics

This batch documents the target scope and concrete procedures (SoP) for each current agent. These are implementation‑ready and align with Phase 2 acceptance gates (determinism, budgets, ≥85% coverage, artifact capture).

Important: Current code contains a class name overlap for Test agents (both runner and generator define `TestAgent`). We will keep this doc precise using names TestRunner and TestGen for clarity; code can be refactored in a later task.


### CodeGenAgent

Purpose
- Produce minimal, deterministic file deltas for creation/modification tasks.
- Support “spec → plan → patch → self‑check” loops under bounded budgets.

Inputs
- task.payload: { action|mode, target, instructions?, content? }
- Context: read‑only problem facts from ContextStore (optional; dry‑run via `VLTAIR_TEST_MODE=1`).

Outputs
- AgentResult with `payload.delta.doc` (path, content)
- Optional artifacts: diff summaries, self‑check notes, compile/test probes (redacted)

Deterministic Procedure
1) Normalize payload: action, target, instructions; fix seeds and disable wall‑clock use.
2) If `content` provided, prefer it; otherwise synthesize minimal default for language (`.py`, etc.).
3) Plan step (deterministic):
   - Extract acceptance criteria from instructions (regex rules, file paths, symbols).
   - Generate a “change plan” structure: unit of change, expected symbols, affected tests.
4) Candidate generation (branching, k<=3):
   - Candidate A: minimal implementation for acceptance criteria.
   - Candidate B: same plus type hints and docstring.
   - Candidate C (optional): structured stub + TODO markers for follow‑up agents.
5) Self‑check scoring (deterministic ranks):
   - Static score: parses/compiles, lints clean, symbol existence, diff size.
   - Heuristic score: spec coverage (keywords hit, API surface matched).
6) Select highest‑score candidate (stable tie‑break by (score, path, hash)).
7) Emit delta and artifacts; redact details with `sanitize_text` for any logs.

Selection Heuristics (stable)
- Hard constraints: must compile, must define required symbols.
- Scores: (+2) compiles, (+1) ruff clean, (+1) mypy stub‑safe, (+1) minimal diff lines, (+1) spec keywords ≥80%.

Observability & Security
- Emit spans: `agent.codegen.plan`, `agent.codegen.candidates`, `agent.codegen.select` with low‑cardinality attrs.
- Redact logs/artifacts via `sanitize_text` and field hooks.
- No network; filesystem writes only via orchestrator application of deltas.

Timeouts & Budgets
- `time_budget_ms`, `candidate_budget` (default 3), `lint_budget_ms` — all enforced; emit TIMEOUT when exceeded.

Example Orchestrator Usage
- Input: { action: "create", target: "src/util/math.py", instructions: "add add(a,b)" }
- Output: delta with function skeleton and docstring; artifact noting symbol `add` exists.


### StaticAnalysisAgent

Purpose
- Produce deterministic findings from static heuristics and lightweight parsing; feed Debug and CodeGen with actionable hints.

Inputs
- task.payload: { target, scope?, ruleset? }
- Context: optional code text via ContextStore lookup.

Outputs
- AgentResult with `payload.artifacts = [ { kind: "analysis", target, details, severity, suggestions[] } ]`

Deterministic Procedure
1) Load configured ruleset (built‑in stable rule IDs).
2) Parse file (tokenize/AST where applicable) without external IO.
3) Run rules and collect findings with stable ordering (by line, rule_id).
4) Emit artifacts; redact details; include suggestions as structured edits (function name, line hint, rationale ID).

Ruleset Examples (stable)
- SA001: Missing docstring on public function.
- SA010: Unused import.
- SA021: Broad `except:`.
- SA040: Function too long (>80 lines).

Observability & Security
- Spans: `agent.static.rules`, `agent.static.findings`.
- Redaction for `details` fields; no network.

Budgets
- `max_findings` (cap, default 50), `time_budget_ms` with graceful truncation artifact if exceeded.

Example Orchestrator Usage
- Input: { target: "orchestrator/agents/codegen.py" }
- Output: one or more `analysis` artifacts with severity/info and suggestion list.


### TestRunner (current: orchestrator/agents/test_agent.py)

Purpose
- Execute test suites deterministically in sandbox; return status + redacted logs; map rc=124 to TIMEOUT consistently.

Inputs
- task.payload: { mode: "execute", paths: ["tests/unit/..."], timeout_s?, test? }

Outputs
- AgentResult with `artifacts`:
  - `{ kind: "test_result", test_name, status(pass|fail|timeout), log }`
  - `{ kind: "coverage_hint", files[], line_rate }` (heuristic or measured)

Deterministic Procedure
1) Validate `paths` and `timeout_s`.
2) Call sandbox runner (Windows‑safe) with configured timeout and 50ms tolerance; map rc→status.
3) Redact stdout/stderr via `sanitize_text` and field redaction hooks.
4) Emit coverage hints (stable heuristic when precise data unavailable in dry‑run).

Observability & Security
- Spans: `agent.test.exec`, attrs: path_count, timeout_s, rc.
- Redact logs; respect `VLTAIR_CI_DIAG=1` for JSON stdout diag passthrough when present.

Budgets & Timeouts
- `timeout_s` enforced; kill‑on‑fallback logic consistent with sandbox; emit diagnostic artifact if exceeded.

Example Orchestrator Usage
- Input: { mode: "execute", paths: ["tests/unit/codegen_test.py"], timeout_s: 30 }
- Output: `test_result` with status and sanitized log; `coverage_hint`.


### TestGen (current: orchestrator/agents/test_gen.py)

Purpose
- Generate deterministic, import‑safe test skeletons targeting modules and functions to accelerate coverage growth.

Inputs
- task.payload: { mode: "generate", target: "pkg/mod.py", function? }

Outputs
- AgentResult with `payload.delta.doc` → Phase 2 baseline: `test_<module>.py` content (no subdirectory). A future batch may derive `tests/<derived>/...` paths when orchestrator provides context.
- Optional `coverage_hint` artifact estimating impacted files.

Deterministic Procedure
1) Derive module import name and test filename from `target` (path rules are stable and OS‑agnostic).
2) Render a fixed skeleton: smoke import + optional symbol existence check.
3) Optional branching (k<=2) for alt skeletons (pytest param scaffolding vs. minimal); select by minimal lines.
4) Emit delta; add artifact linking target→test path mapping for orchestrator indexing.

Observability & Security
- Spans: `agent.testgen.derive`, `agent.testgen.render`.
- No network; redact nothing by default (content is benign).

Budgets
- `candidate_budget` (default 1–2), `time_budget_ms` for path derivation and render.

Example Orchestrator Usage
- Input: { target: "orchestrator/agents/codegen.py", function: "CodeGenAgent" }
- Output: `test_codegen.py` with `test_smoke_import` and `test_CodeGenAgent_exists`.


### DebugAgent

Purpose
- Given failing tests or error logs, produce a minimal patch proposal and actionable analysis to drive a repair loop.

Inputs
- task.payload: { target: "<file or patch path>", errorLog?, failingTest? }
- Context: optional recent `analysis` and `test_result` artifacts for correlation.

Outputs
- AgentResult with `payload.delta.doc` for a candidate patch file or direct file edit
- `artifacts`: at least one `{ kind: "analysis", target, details, severity, suggestions }`

Deterministic Procedure
1) Parse failing signals (stable regex to extract file:line, AssertionError messages).
2) Generate change plan: symbol to modify, minimal diff region, guardrails.
3) Branch candidates (k<=3):
   - C1: minimal guard fix (e.g., handle None).
   - C2: boundary adjustment (off‑by‑one, wrong default).
   - C3: tighten exception handling or types.
4) Static validate each candidate: compiles, symbol present, imports intact.
5) Rank by static score + size; emit top candidate; attach analysis artifact.

Observability & Security
- Spans: `agent.debug.plan`, `agent.debug.candidates`, `agent.debug.select`.
- Redact `errorLog` before persisting; no network.

Budgets & Timeouts
- Enforce candidate/time budgets; if budget exceeded, emit partial plan with rationale.

Example Orchestrator Usage
- Input: { target: "fix.patch", errorLog: "Traceback..." }
- Output: patch delta and analysis describing hypothesized root cause.


## Batch 2 — Cross‑Agent Chains and Trees (design)

Overview & Goals
- Elevate single‑agent procedures into orchestrator‑led, deterministic workflows that search a bounded space of multi‑step solutions.
- Represent flows as TDAGs and within‑step branching as candidate trees; enforce budgets and halting across the whole run.
- Capture complete evidence: plans, candidates, scores, selection decisions, redacted logs, and coverage hints.

Workflows (Phase 2 acceptance aligned)
- Workflow A — Feature Add (P2‑2.7)
  - StaticAnalysis → CodeGen → TestGen → TestRunner → [Debug loop if needed] → TestRunner
- Workflow B — Fix Failing Test (P2‑2.8)
  - TestRunner → Debug → CodeGen → TestRunner

Deterministic Candidate Tree Model
- Node (immutable):
  - id: stable hash of {agent, inputs, candidate_rank, parent_id}
  - agent: CodeGen|Debug|TestGen|StaticAnalysis|TestRunner
  - inputs: normalized payload + minimal context snapshot refs (no raw large content)
  - artifact_refs: IDs of emitted artifacts (stored in ContextStore)
  - scores: {hard_constraints_pass: bool, static_score: float, heuristics: {k:v}}
  - cost: {time_ms, tokens=0 for local, tool_cost}
  - status: proposed|expanded|selected|rejected
- Edge: parent_id → child_id with reason (e.g., “address finding SA010”, “fix AssertionError: …”).
- Tree constraints: branching factor B≤3 per agent step; depth capped by workflow definition; global node cap N.

Search Policies (deterministic)
- Beam search (default): width=B, depth=D. Priority = (hard_pass, static_score desc, cost asc, path_hash asc).
- Best‑first fallback: priority queue by static_score; tie‑break by deterministic tuple above.
- Iterative deepening option: D grows 1→Dmax under remaining budget; preserves determinism.
- Halting: success conditions met; or global budget/time exhausted; or no candidates remaining that pass hard constraints.

Scoring & Selection
- Hard constraints (must all pass):
  - CodeGen/Debug: parses/compiles; required symbol(s) exist; diff size < max_lines.
  - TestGen: syntactically valid; imports resolve; naming policy respected.
  - StaticAnalysis: rule execution completed; findings schema valid.
  - TestRunner: rc mapped to pass|fail|timeout; log redacted.
- Static score (0–10, deterministic):
  - +2 compiles/imports ok; +1 lints clean; +1 mypy stub‑safe; +1 minimal diff size (smaller is better);
  - +1 spec keyword coverage ≥80%; +1 aligns with finding severity; +1 increases coverage estimate; +1 test names policy; +1 zero unnecessary changes.
- Selection rationale: emitted as `artifact(kind="selection_decision")` with inputs, scores, and tie‑break tuple.

Budgets & Halting Conditions
- Per‑step budgets: time_budget_ms, candidate_budget (B), expand_budget_per_node.
- Global budgets: total_time_ms, total_nodes (N), max_iterations for debug loop.
- Policy checks: preflight deny if remaining budget insufficient; emit `artifact(kind="budget_denied")`.

Observability (rules‑aligned)
- Spans: `agent.workflow.start`, `agent.workflow.expand`, `agent.workflow.select`, `agent.workflow.halt`.
- Attributes (allowlist): agent.role, run.id, task.id, workflow.name, width, depth, selected.score, error.code.
- Structured logs: JSON with redaction via `sanitize_text` and field hooks for `analysis.details`, `test_result.log`.
- Metrics: counters for nodes expanded/selected; histograms for step latencies and rc categories.

Security & Privacy
- RBAC checkpoints at: workflow start, tool/sandbox calls, and artifact egress.
- Redaction: apply pattern and field‑based hooks; forbid raw prompts/logs in exported telemetry; store hashes/refs.
- Sandbox: Windows‑safe execution with +50ms tolerance and kill‑on‑fallback; map rc=124 to TIMEOUT consistently.

Workflow Specifications
- A: Feature Add
  1) StaticAnalysis (target set) → findings (ordered by severity, line)
  2) CodeGen (per finding, B≤3) → select top candidate diff
  3) TestGen (if coverage gap) → deterministic skeletons; B≤2; select minimal
  4) TestRunner (impacted tests) → status and sanitized logs
  5) If fail/timeout: Debug (B≤3) → top candidate; then TestRunner. Iterate ≤K.
  Halting: all tests pass or budgets exhausted.
- B: Fix Failing Test
  1) TestRunner (scope: failing test or suite) → failing signals
  2) Debug (B≤3) → propose fix plan + patch
  3) CodeGen (apply plan deterministically) → diff
  4) TestRunner → verify; halt on pass or budgets exhausted.

Agent‑Specific Branching (within candidate trees)
- CodeGen: minimal impl; typed/docstring variant; guard‑logic variant. Rank by score then diff size.
- Debug: guard fix; boundary fix; type/exception adjustment. Validate compiles; choose smallest passing patch.
- TestGen: minimal smoke; symbol‑exists variant. Prefer minimal.
- StaticAnalysis: non‑branching; findings feed next steps.
- TestRunner: evaluator; non‑branching; contributes evidence and halting signals.

Artifacts & Schemas (additive, versioned)
- `candidate_list`: [{id, agent, inputs_hash, static_score, hard_pass, cost, rationale}]
- `selection_decision`: {selected_id, candidates:[id..], tie_break: [score, cost, hash]}
- `workflow_trace`: {nodes:[…], edges:[…], budgets:{…}, halting_reason}
- `budget_denied`: {step, remaining, required, policy}
All artifacts pass through field redaction (env: `VLTAIR_REDACT_FIELDS*`).

Determinism & Replay
- Seeds fixed (0); time abstracted; ordered reductions; tie‑break tuple stable.
- Hash inputs and content for node IDs; store only refs in logs/metrics; full content lives in ContextStore.
- Replay mode: substitute recorded outputs; verify scores/selection identical.

CLI & Config (non‑executing design)
- Example spec (orchestrator run):
  {
    "type": "WorkflowTask",
    "id": "wf1",
    "name": "feature_add",
    "entry": "A",
    "payload": { "targets": ["orchestrator/agents/codegen.py"] },
    "budgets": { "total_time_ms": 60000, "total_nodes": 40, "beam_width": 3, "max_iterations": 3 }
  }
- Orchestrator prints JSON trace summary with counts, selected path, halting reason (dry‑run permitted).

Validation Plan (when implemented)
- Unit: deterministic selection given fixed candidate matrices; halting on budgets; artifact schema validators.
- Integration: run Workflow A and B on seed scenarios; assert rc mapping, redaction, and selection determinism.
- Coverage: ≥85% overall, with per‑agent branching logic covered.
- Perf: coordination overhead <10% of wall‑time vs direct single‑agent runs.

Risks & Mitigations
- Candidate explosion → cap B,N; prune by hard constraints early.
- Non‑deterministic tool output → sandbox flags, stable versions, record external values.
- Log sensitivity → strict redaction, field policies, secrets prefixes env‑config.
- Flaky tests/timeouts → rc=124 semantics, +50ms tolerance, deterministic retries policy.


## Batch 3 — Advanced Heuristics and Policies (design)

Objective
- Deliver world‑class, research‑informed workflows while preserving VLTAIR’s determinism, security, and reproducibility.
- Improve candidate quality and selection via frozen heuristics, deterministic search, and cross‑agent consensus.

Global Meta‑Policies (deterministic)
- Policy engine: allow/deny/flag per action type (autofix on/off, file globs allowlist, max diff lines, severity thresholds).
- Budget tiers: default, aggressive, conservative — map to total_time_ms, node caps, and per‑agent budgets.
- Risk scoring: combine patch size, touched hotspots, security rule hits, and test delta into a stable 0–1 score.
- Trust zones: restrict modifications in security‑sensitive areas unless accompanied by StaticAnalysis high‑confidence autofixes.

Deterministic Search Upgrades
- Beam‑MCTS hybrid: beam of breadth B; within each beam node, run fixed‑iteration UCT with evaluation = static_score and deterministic playouts (no randomness).
- UCT parameters are fixed (c, iterations) and versioned in policy; exploration order stable by content hash.
- Early stopping: halt node expansion when marginal score gain < epsilon (fixed) for K consecutive expansions.

Frozen Learned Scorers (vendored)
- Offline‑trained, tiny models (e.g., logistic regression) stored as JSON weights; infer deterministically, no runtime training.
- Feature sets (stable, language‑agnostic where possible):
  - Diff metrics: added/removed lines, AST edit distance, touched public API.
  - Code quality: ruff/mypy flags count, cyclomatic complexity delta.
  - Test impact: predicted coverage increase, number of targeted tests.
  - Stability: import/compile status, symbol existence, exception risk heuristics.
- Outputs feed into `static_score` as a bounded additive bonus (+0..+2) with version pinning.

Agent‑Specific World‑Class Enhancements

- CodeGenAgent
  - AST‑aware patch minimality: prefer edits that reduce AST edit distance and avoid public API breakage.
  - Contract mining: extract simple “pre/post” invariants from docstrings and existing tests; enforce as checks (deterministic regex + AST guards).
  - Template‑guided repair: maintain a canonical set of repair templates (guard‑null, off‑by‑one, default param, error propagation) with stable IDs.
  - Static self‑checks: ast.parse/import; stub type checks; style pass; side‑effect and IO surface heuristics.
  - Review loop (deterministic debate):
    - Proposer: CodeGen candidates (≤3).
    - Reviewer: StaticAnalysis critique with rule references and risk score.
    - Judge: Policy ties resolved by (score desc, risk asc, diff size asc, id asc).

- StaticAnalysisAgent
  - Rule families: correctness, style, safety, complexity, API stability; documented rule IDs (SAxxx) and severities.
  - Lightweight data‑flow/taint patterns (deterministic): propagate sources→sinks for common Python hazards (exec/eval, subprocess, SQL string concat).
  - Autofix suggestions: structured hunks referencing rule IDs; confidence levels (low/med/high) computed from context (e.g., unused import = high).
  - SARIF‑like export mapping for tooling interoperability (internal schema preserved, mapping optional).

- TestGen
  - Coverage‑aware planning: if context reports <threshold coverage, propose tests for top public functions and error paths.
  - Robust value sets: boundary triples (min/typical/max), None/empty, invalid type, large size; deterministic enumerations per type hint.
  - Metamorphic patterns (deterministic): idempotence, commutativity (when inferred), exception guarantees.
  - Parametrized tests favored over property‑based to avoid runtime randomness; property tests allowed only with fixed seeds and bounded example sets.
  - Naming/structure policy: Arrange‑Act‑Assert skeleton; docstrings include invariant rationale for traceability.

- TestRunner
  - Impacted test selection: diff→module mapping + cached import graph to select a minimal subset first, escalate to full suite on success.
  - Flake probe (bounded): repeat once on fail if log patterns indicate nondeterminism; mark `status=flaky` and do not block fix loop.
  - Hermetic execution: standardize env (locale, TZ, seeds); redact logs; honor Windows timeout tolerance and rc=124 mapping.

- DebugAgent
  - Spectrum‑based fault localization (deterministic): use fail/pass coverage vectors to produce suspiciousness rankings (e.g., Ochiai‑style formula with fixed math).
  - Failure taxonomy: assertion mismatch, exception type mismatch, import error, type error; map to repair templates.
  - Minimal‑risk patching: prioritize smaller hunk count and local guards; avoid API changes unless instructed.
  - Post‑fix sanity: import/compile + StaticAnalysis re‑run on changed files before handing off to TestRunner.

Cross‑Agent Synergy & Consensus
- Shared scoreboard: per artifact/candidate features and scores aggregated; accessible to subsequent agents via ContextStore.
- Judge/Reviewer roles: StaticAnalysis acts as reviewer; policy engine as judge for tie‑breaks; Debug provides causality evidence.
- Feedback arcs: TestRunner’s failing signals refine Debug; Debug’s plan narrows CodeGen search space; StaticAnalysis findings seed both.
- Knowledge graph: nodes for findings, patches, tests, results; edges tracked for provenance and audit.

Observability & Metrics (expanded)
- New spans: `agent.codegen.review`, `agent.debug.localize`, `agent.test.select`, `agent.policy.decision`.
- Metrics: selection regret (gap between selected score and next best), node expansion efficiency (selected/expanded), coverage delta estimate.
- Logs: structured “selection_decision” with candidate matrix snapshot (scores and reasons), redacted fields enforced.

Performance & Cost Controls
- Coordination overhead target <10%; preflight checks ensure tools (lint/type) run within budgets.
- Memoize ASTs, import graphs, and findings per content hash to avoid re‑computation across candidates.
- Batch policy checks; emit a single decision artifact per step.

Evaluation & Validation Strategy (offline, deterministic)
- Golden scenarios: curated tasks for feature add and bug fix; store expected candidate matrices and selections.
- Evals: success rate, patch minimality, test coverage uplift, time/node budgets adherence.
- Safety: ensure redaction on all logs; verify no leakage in artifacts; RBAC policies honored in dry‑run.

Risks & Mitigations (advanced)
- Over‑constrained policies blocking progress → surface `policy_denied` artifacts with rationale and override hint.
- Learned scorer bias → versioned weights with A/B offline eval; roll back by version switch without code changes.
- False‑positive autofixes → confidence thresholds and reviewer gating; never auto‑apply low‑confidence patches.


## Observability, Security, and Determinism (shared)

Spans/Logs/Metrics
- Use low‑cardinality attributes: agent, action, target type, candidate_count, selected_score.
- Redaction via `orchestrator/obs/redaction.py` for logs and artifact fields; support env‑based field lists.

Sandbox & Timeouts
- All executions via sandbox; Windows tolerance (+50ms) and kill‑on‑fallback path preserved; TIMEOUT emits rc=124 consistently.

Reproducibility
- Record seeds=0, temp=0, versions, and inputs in artifacts or spans. For dry‑run, require `VLTAIR_TEST_MODE=1`.

Acceptance & Coverage
- Maintain overall ≥85% (≥90% core) coverage with per‑agent unit tests; capture artifacts named in Implementation Plan.


## Open Issues & Next Steps

- Naming conflict: both TestRunner and TestGen export `TestAgent` classes (orchestrator/agents/test_agent.py:9, orchestrator/agents/test_gen.py:8). Propose renaming to `TestRunnerAgent` and `TestGenAgent` in a separate task.
- Add schema validators for `analysis`, `test_result`, and `coverage_hint` artifacts if not already covered in `orchestrator/schemas`.
- Wire spans and redaction hooks in each agent implementation.
- Implement candidate branching and selection where marked above; add unit tests to verify deterministic selection.


## Batch 4 — Operationalization, Context Versioning, and Evaluation Harness (design)

Overview & Goals
- Move from agent/workflow design to operational excellence: safe rollouts, context versioning/merge, deterministic replay at scale, and rigorous offline evaluation.
- Ensure state-of-the-art synergy by coupling hierarchical planning with policy governance, red-team safety, and CI gates, without sacrificing determinism.

Context Versioning & Merge (event-sourced)
- Document types and semantics
  - CodeDocument: immutable content with content_hash; patches apply only when `base_hash` matches.
  - TestDocument: additive by default; name collision handled via deterministic disambiguation.
  - AnalysisArtifact/CoverageHint: append-only with TTL and stable IDs; no merge.
- Patch envelopes (deterministic)
  - Unified diff or full-file payloads; always include `base_hash`, `new_hash`, and `idempotency_key`.
  - Orchestrator enforces WAL-first logging before apply; failure leaves state intact.
- Conflict detection & recovery
  - If `base_hash` mismatch, emit `artifact(kind="merge_conflict")` including expected/actual hashes and hunk map.
  - Recovery paths:
    1) Auto-rebase (safe subset): re-anchor hunks by AST or nearest unchanged anchors; only if 100% confident and within policy.
    2) Human-in-the-loop or DebugAgent-guided replan when anchoring fails or policy denies.
- Snapshots and rollback
  - Lightweight snapshots by content hash sets; rollback via restoring prior snapshot and reapplying WAL up to checkpoint.
  - Replay confirms deterministic equivalence (scores, selections, halting reasons).

Hierarchical Planning & Assignment (TDAG → micro tasks)
- Planner decomposes goals into leaf tasks tagged for agent roles; leaves must be ≤ policy-defined complexity.
- Prioritization:
  - Critical path first (findings with severity ≥ threshold; tests covering core modules).
  - Mixed strategy: parallelize independent leaves under backpressure; enforce global budgets.
- Assignment policy:
  - Skill-to-task mapping with diversity threshold (avoid repeated patterns when candidates tie within ε).
  - Deterministic tie-breaks by tuple (score, risk, diff_size, id).

Governance & Policy Versioning
- Version every policy bundle: `policy/vX.Y.Z/` including search params, budgets, learned weights, and rule toggles.
- Feature flags (deterministic): enable advanced heuristics (Beam–MCTS, taint rules, spectrum localization) per bundle; default OFF for canary.
- Rollout plan:
  - Canary (small golden set) → Shadow (evaluate vs main) → Gradual ramp (N%) → Full.
  - Automatic rollback on regression (coverage drop, selection regret ↑, perf >10% overhead, or safety violations).
- Auditability: policy/version recorded on every artifact and selection decision.

Evaluation Harness & Scorecards (offline, deterministic)
- Golden tasks:
  - Feature-add scenarios (new function, IO guard, API docstring) and failing-test fixes (off-by-one, null guard, import error).
  - For each, store candidate matrices (scores, rationales) and expected selections.
- Metrics:
  - Success rate (selected path passes all tests), patch minimality (AST edit distance), coverage uplift, coordination overhead, TIMEOUT rate, redaction compliance.
- Repro harness:
  - `VLTAIR_TEST_MODE=1` dry-run; seeded tools; frozen lint/type toolchains.
  - Deterministic transformers for logs to ensure stable redaction.

Safety, Privacy, and Red-Team Patterns
- Prompt/log injection hardening: treat inputs as untrusted; redact before storage; flag suspicious patterns (regex rules, policy deny list).
- Sensitive area protection: require `trust_zone=high` for patches in security-critical files; mandate StaticAnalysis high-confidence autofix.
- PII/Sensitive content gates: enforce `VLTAIR_REDACT_PREFIXES` and `VLTAIR_REDACT_FIELDS*` on all artifacts; add unit evals that simulate secrets.

Performance & Cost Management at Scale
- Cache reuse: ASTs, import graphs, coverage maps memoized per content_hash.
- Work stealing with limits: keep orchestration overhead <10%; prioritize ready nodes with highest expected score gain per ms.
- Deferred heavy checks: run mypy/complex linters only on selected candidate path (not on all branches).

Cross-Language Extensibility
- Language adapters: define minimal AST/diff interfaces for Python/Rust/TS; CodeGen and StaticAnalysis select adapters via target extension.
- Policy bundles version toolchains per language; selection heuristics normalized to comparable 0–10 ranges.

Operational Runbooks
- Pre-flight checklist: policy version, budgets, seeds, redaction config, sandbox tolerance, CI diag flag.
- Failure playbooks: merge conflict, rc=124 TIMEOUT spike, selection regret anomaly, redaction drift — each with deterministic probes and rollback steps.

Open Questions (for subsequent batches)
- Where to place auto-rebase capabilities (Debug vs new RebaseAgent) while preserving determinism and safety?
- What minimal SARIF mapping subset is most useful for external tools without schema drift risks?
- Should we allow limited property-based tests when seeds+examples are fully frozen, or stick to parametrized tests only?


## Batch 5 — Developer Experience, Migration Playbooks, and CI/Policy Tooling (design)

Intent
- Translate the advanced designs into a world‑class developer and operator experience: frictionless local workflows, iron‑clad CI gates, safe migrations, and clear SLO dashboards — all deterministic and audit‑friendly.

DX Foundations (deterministic by default)
- Workspace conventions
  - `policy/` — versioned bundles (vX.Y.Z) with JSON schemas for search params, budgets, learned weights, rule toggles.
  - `eval/` — golden tasks, candidate matrices, expected selections, coverage baselines; includes per‑scenario README and acceptance thresholds.
  - `scenarios/` — real‑world task JSONs and workflow specs (A/B), dry‑runnable with `VLTAIR_TEST_MODE=1`.
  - `docs/playbooks/` — operator and developer runbooks (pre‑flight, failure triage, rollback).
- Local commands (documented, non‑executing design)
  - `orchestrator policy validate --bundle policy/vX.Y.Z` → schema + referential checks.
  - `orchestrator workflow dry-run --file scenarios/feature_add.json --bundle vX.Y.Z` → JSON trace summary.
  - `orchestrator eval run --suite eval/golden` → offline evaluation and scorecard.
- Templates
  - Agent test templates (unit): deterministic candidate matrices and selection checks per agent.
  - Scenario templates (integration): feature add and failing‑test fix reproducible stories with seeded logs.

Policy Registry & Governance
- Registry schema: { name, version, created_at, search_params, budgets, feature_flags, scorers, rule_overrides, notes }.
- Bundle immutability: once published, contents are read‑only; supersede via new version; changelog required.
- Doctor/diff tools: `policy diff` prints field‑level changes; `policy doctor` flags incompatible toggles (e.g., enabling autofix without reviewer gate).
- Provenance: every artifact and selection decision references the active bundle/version; exported in summaries.

CI Integration & Gates
- Pipelines
  - Unit stage: agent unit tests with coverage ≥85% overall (≥90% core if applicable).
  - Integration stage: run Workflow A/B in dry‑run; verify JSON traces; assert deterministic selection; ensure rc=124 mapping.
  - Eval stage: golden scorecards; thresholds on success rate, minimality (AST), coverage uplift, overhead <10%.
  - Security stage: redaction tests; policy doctor; deny if violations.
  - Bench stage: micro‑benches; emit JSON artifacts; compare deltas vs baseline with guardrails.
- Artifacts
  - coverage.xml, bench JSONs, workflow trace summaries, selection decisions, policy bundle manifest, redaction compliance report.

Migration Playbooks
- Single‑agent → multi‑agent
  - Start with StaticAnalysis → CodeGen loop; add TestGen/TestRunner; finally add Debug loop.
  - Enable feature flags incrementally via canary bundles; monitor selection regret and overhead.
- Naming conflict resolution
  - Rename `TestAgent` classes to `TestRunnerAgent` and `TestGenAgent` with orchestrator registry migration helper; preserve API via compatibility alias until next minor.
- Language expansion
  - Introduce adapters for new languages under feature flags; gate on adapter coverage and rule parity.
- Policy rollbacks
  - Roll back by version swap; artifacts keep provenance; replay confirms pre/post equivalence on golden sets.

Observability & SLO Dashboards
- Dashboards
  - Selection regret (P50/P95), node expansion efficiency, TIMEOUT rate, coverage uplift per run, overhead share, redaction compliance.
  - Drill‑downs by workflow type (A/B), agent role, target area (security‑sensitive vs general).
- Alerts
  - On regret spike, overhead >10%, TIMEOUT rate > threshold, coverage dip, or redaction violation; attach last N traces.

Reproducibility & Toolchain Locking
- Tool lockfiles: pin ruff/mypy/pytest versions and CLI flags; vendor learned scorer weights.
- Env capture: record Python version, OS, timezone, locale; normalize seeds and deterministic flags.
- Snapshot and replay: export/import run manifests; verify identical selections and halting reasons.

Data Retention & Privacy
- TTLs for artifacts (analysis/test logs) with redaction applied on ingest; purge after TTL; audit log remains hashed.
- RBAC scopes for reading sensitive artifacts; deny cross‑tenant access; anonymize metrics.

Release & Packaging
- Policy bundle releases accompany code releases; changelog includes toggles and scorer version.
- Release artifacts: policy manifest, eval scorecards, trace summaries, bench results, coverage reports.
- Quality bar: no release if eval or security gates fail; document waivers with explicit justifications.

Onboarding & Education
- Guided tour: “Hello Workflow A/B” dry‑run exercises; expected outputs and how to read traces.
- Checklists: pre‑flight (policy, budgets, seeds), post‑run (artifacts, metrics, regressions), incident response.

Synergy Reinforcement
- Codify feedback loops through shared scoreboard and provenance graph; ensure each agent both consumes and contributes structured signals.
- Keep beams narrow and choices principled through policy; favor small, reversible changes guided by StaticAnalysis and validated by TestRunner.
