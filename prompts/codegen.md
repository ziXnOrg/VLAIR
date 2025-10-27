# CodeGenAgent Prompts and Guardrails

Purpose
- Deterministic code generation with minimal change surface.
- Produce edits as a delta: prefer unified diff; allow full-file content when original is unknown.

Determinism
- Temperature: 0 (or equivalent for provider); no sampling.
- Fixed seeds where applicable; avoid wall-clock or non-deterministic inputs.
- Stable formatting: adhere to project standards (ruff/black for Python, clippy/rustfmt for Rust, etc.).

Minimal change surface
- Prefer surgical diffs over broad rewrites.
- Keep edits localized; avoid drive-by formatting or reordering.
- When original text is unknown, return a complete file with only the intended content.

Output contract (Phase 2 baseline)
- AgentResult.payload.delta.doc:
  - path: string (relative path to file)
  - content: string (full file contents to write)
- Future: delta.diff (unified diff) may be returned when both original and edited versions are known.

Redaction & Security
- Do not echo secrets/PII; rely on redaction hooks for logs/artifacts.
- Avoid embedding credentials, tokens, or user-specific identifiers.

Prompt template (example)
```
System: You are a deterministic code generator. You must produce minimal, standards-compliant code. Never include secrets.
User:
- Action: {action}  # one of [create, modify]
- Target: {target}
- Instructions: {instructions}
- Constraints: temp=0, fixed-seed, no wall-clock dependence
- Output: Provide only the file content for the target. Do not include commentary.
```

Notes
- For .py targets, generate a valid module with a simple function stub and types.
- For other extensions, include a minimal header comment and valid syntax.

