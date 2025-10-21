# P2-2.2 — CodeGenAgent Workflow and Prompts

## Determinism
- Temperature=0, fixed seeds (when LLM used later), stable formatting.
- Content derived from task payload (action/target) to keep tests deterministic.

## Minimal Prompt Skeleton (future)
- System: You are a code generation agent. Follow project coding standards and minimize change surface.
- Instructions:
  - Modify or create file `{target}` according to `{goal}`.
  - Output unified diff OR full file content when small.
  - Respect 2-space indent, 100-col limit; no tabs.
- Constraints: No external side effects; produce compilable code.

## Output Contract (payload)
- payload.delta.doc: { path, content }
- artifacts[diff_summary]: { files_changed, insertions, deletions }

## Next
- Expand with language-specific templates and guardrails.
