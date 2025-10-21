# VLTAIR — Agent Orchestration Framework (with Vesper Context Engine)

## Quick Links

- Redaction Policy and Usage: see `SECURITY.md`.
- CLI Redaction Flags: `--redact-prefix`, `--redact-fields` in `cli/orchestrator_cli.py`.
- Structured Query CLI: `orchestrator query` (dry-run via `VLTAIR_TEST_MODE=1`).
- Implementation Plan: `Docs/ImplementationPlan.md` (phased roadmap; acceptance criteria).
- Production Workflow: `Docs/production-agentic-workflow.md`.

## CLI Examples

### Status / Registry
```bash
orchestrator status
orchestrator register --agent CodeGenAgent --cap create,modify
orchestrator update --agent CodeGenAgent --status idle --load 1
```

### Queue Metrics
```bash
orchestrator queue
```

### Run Task
```bash
orchestrator run --file task.json
# task.json example
{ "type": "AgentTask", "id": "t1", "agent": "CodeGenAgent", "payload": {"action": "create", "target": "a.cpp"}, "constraints": {"timeoutMs": 100} }
```

### Structured Query (Context)
```bash
# Dry-run (no Vesper)
VLTAIR_TEST_MODE=1 orchestrator query --text "vector search" --k 5 --mode hybrid --rrf-k 60 --dense-weight 0.6 --sparse-weight 0.4 --rerank-factor 10 --filter-kv type=text

# Real (with Vesper)
orchestrator query --text "coverage hints" --k 10 --mode hybrid --filter-json '{"type":"coverage_hint"}'
```

### Redaction Configuration
```bash
# Pattern-based redaction prefixes
orchestrator status --redact-prefix sk- --redact-prefix ghp_

# Field-based redaction for artifacts
orchestrator status --redact-fields analysis.details --redact-fields test_result.log

# Env-based configuration
set VLTAIR_REDACT_PREFIXES=sk-,ghp_
set VLTAIR_REDACT_FIELDS=analysis.details,test_result.log
```

## References

- Blueprint: `Docs/Blueprint.md`
- Production Workflow: `Docs/production-agentic-workflow.md`
- Implementation Plan: `Docs/ImplementationPlan.md`
- SECURITY: `SECURITY.md`
- CLI: `cli/orchestrator_cli.py`
- Cursor Rules: `.cursor/rules/`

