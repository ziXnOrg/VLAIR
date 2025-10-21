# Security Policy

## Using Redaction

To protect sensitive information in logs, artifacts, and analysis details, the orchestrator supports pattern- and field-based redaction.

- Environment variables
  - `VLTAIR_REDACT_PREFIXES`: comma-separated token prefixes to redact (e.g., `sk-,ghp_`).
  - `VLTAIR_REDACT_FIELDS`: comma-separated field paths to redact in artifact payloads (e.g., `log,details,meta.token`).
  - `VLTAIR_REDACT_FIELDS_<KIND>`: per-artifact overrides (KIND uppercased), e.g., `VLTAIR_REDACT_FIELDS_TEST_RESULT=log`.

- CLI flags (apply for the current invocation)
  - `--redact-prefix <prefix>`: repeat to add multiple prefixes; sets `VLTAIR_REDACT_PREFIXES` for the process.
  - `--redact-fields <paths>`: comma-separated field paths; sets `VLTAIR_REDACT_FIELDS`.

Examples:

```bash
# Show current redaction settings
orchestrator --redact-prefix sk- --redact-prefix ghp_ --redact-fields log,meta.token status

# Run a task with redaction configured
orchestrator --redact-prefix sk- --redact-fields details run --file task.json
```

Caveats:
- Prefix redaction is aggressive; choose specific prefixes to avoid over-redacting useful data.
- Field paths are applied recursively on dicts/lists; verify with tests when adding new artifact kinds.
- Redaction replaces content with `<<REDACTED>>`; underlying raw content should not be logged or persisted.
- Always review artifacts for hidden metadata before distribution.

See also:
- `orchestrator/obs/redaction.py` for supported patterns and field-walking behavior.
- `Docs/ImplementationPlan.md` Phase 2 Redaction & Security Hardening.
