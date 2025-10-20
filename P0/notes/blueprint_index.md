# Blueprint Deep Index — Agent Orchestration Framework

## Purpose
This index anchors the key sections of `Docs/Blueprint.md` that govern our implementation of the Agent Orchestration Framework integrated with Vesper. It serves as the fast reference to verify scope, API contracts, and acceptance criteria during development.

## High-Level Architecture
- Primary Orchestrator: planning, delegation, scheduling, validation, aggregation, guardrails
- Specialized Sub-Agents:
  - CodeGenAgent: generate/modify code (diff/file outputs; deterministic mode)
  - TestAgent: generate tests; execute tests and report results
  - StaticAnalysisAgent: code review for quality and issues
  - DebugAgent: diagnose failures; propose minimal patches
  - DesignReviewAgent: architecture/design evaluations
  - RefactorAgent: non-functional improvements and merges
  - PlanningAgent (optional): assists in dynamic plan adjustment
- Custom Context Engine (Vesper-backed): hybrid dense+sparse search; scopes; metadata filters; optional versioning/merge and snapshots
- Agent Registry: types → constructors mapping; orchestrator-managed lifecycles

## Orchestrator Responsibilities
1) Interpret Goals → initial plan
2) Delegation & Scheduling → assign ready tasks; parallelize where safe
3) Guardrails & Constraints → timeouts, resource budgets, risk approvals
4) Aggregation of Results → merge diffs/artifacts into context
5) Validation & Critique → use tests/analysis; loop back on failure
6) Workflow Control → track DAG state; stop-on-criteria

## Agent Interface & Contracts
Interface: `run(task: AgentTask, ctx: ContextView) -> AgentResult|AgentError`
- AgentTask: `type, id, parentId, agent, payload, constraints{timeoutMs, deterministic, idempotencyKey}, protocolVersion`
- AgentResult: `type, id, parentId, agent, payload{delta, artifacts, newTasks}, metrics{tokensUsed, timeMs}`
- AgentError: `type, id, parentId, agent, error{code, message, details}`
- Determinism:
  - deterministic=true → temp=0, fixed seeds, stable formatting
  - idempotencyKey required for any write-effects to context

## Context Engine (Vesper)
- Data model: Document{id, type, path, content, metadata{origin, version, parentVersion, tags}, timestamps}
- Core ops:
  - search(query text/embedding, k, filters, mode=dense|sparse|hybrid)
  - write add_document(doc)
  - write merge_document(key, content, parent_version, strategy)
- Scopes: global / session / task; pinning and filters
- Hybrid retrieval: HNSW/IVF-PQ + BM25 fusion; metadata filter support
- Optional: snapshots/rollback; three-way merge and conflict detection

## Inter-Agent Communication
- Structured JSON envelopes (see AgentTask/Result/Error)
- Versioned protocol with validators
- Observability: traceId, parentId propagation; metrics on tokens/time

## Determinism & Consistency
- Deterministic orchestrator decisions under fixed seeds
- No hidden side-effects: all actions reflected in structured results
- Consistency policy: orchestrator-serialized writes; optional strong reads

## Performance Targets (Envelopes)
- Context search P50 ≈ 1–3 ms for typical session sizes; tail latency minimized
- End-to-end agent steps measured and budgeted (tokens/runtime)

## Security & Safety
- Structured tool use; sandbox for code/test execution
- Sanitized logs; minimal privileges; human approval for risky ops

## Acceptance Criteria Snapshots
- Minimal end-to-end path: add doc → hybrid search → orchestrator consumes → deterministic logs
- Workflows: Feature add and failing-test fix loop complete under budgets

## Cross-References
- System Architecture → Agents/Context/Orchestrator responsibilities
- Agent Type Specifications → behaviors, inputs/outputs, guardrails
- Context Engine Patterns → scopes, hybrid search, versioning/merge (later phases)
- Inter-Agent Communication → schemas and protocol versioning
- Scalability/Concurrency → scheduling/backpressure policies (later phases)

## Notes and Open Questions (to be resolved in P0.2/P0.3)
- Uniform hybrid-search entry points and metadata filter syntax to expose in bindings
- Scope semantics for session/task in early phases
- Criteria to enable snapshot/rollback features in later phases


