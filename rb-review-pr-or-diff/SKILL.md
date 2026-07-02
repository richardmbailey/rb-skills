---
name: "rb-review-pr-or-diff"
description: "Use to review a pull request or diff for bugs, regressions, missing tests, architecture issues, and concrete fixes. Findings should lead, with severity and file/line references."
---

# /rb:review - review a PR or diff

## Purpose

Review changes for actionable defects, regressions, missing tests, and maintainability risks. Default to review only; do not edit code unless the human explicitly asks for fixes.

## Procedure

1. Inspect the diff or PR scope, including added, modified, deleted, and generated files.
2. Read relevant surrounding code, tests, configuration, migrations, and public interfaces touched by the change.
3. Read `AGENTS.md` and `CONTEXT.md` when present and relevant, especially for domain logic, scientific assumptions, deployment, or project-specific rules.
4. If the diff affects a multi-LLM-agent system, also use `$rb-multi-agent-systems` to review agent boundaries, tool permissions, handoffs, state, structured outputs, tracing, evals, retrieval, provider routing, and durability.
5. Check correctness, tests, architecture, naming, maintainability, performance, security/privacy, data migrations, numerical stability, units, reproducibility, compatibility, and failure modes.
6. Separate definite issues from uncertainties. Do not present speculation as a finding; put uncertain points under questions or residual risk.
7. Update `$rb-working-diary` with durable findings and unresolved risks when the review is substantial or likely to continue.
8. Recommend concrete fixes for each finding, but do not apply them unless asked.

## Required Behaviour

- Findings come first, ordered by severity.
- Every finding needs a tight file/line reference when possible.
- Explain the user-visible or developer-visible impact, not just style preference.
- Flag missing tests only when a plausible regression would escape without them.
- Say clearly when no actionable issues are found.
- Include checks not run and residual risks.

## Output

Use this shape:

```markdown
## Findings

- [P1] Short issue title
  File: path:line
  Impact: what breaks or what risk escapes.
  Fix: concrete fix direction.

## Questions / Assumptions

- ...

## Tests / Gaps

- Tests reviewed or not run.
- Missing coverage or residual risk.

## Summary

Brief change summary only after findings.
```

Severity guide:

- `P0`: must fix immediately; data loss, security issue, or complete breakage.
- `P1`: likely bug or serious regression.
- `P2`: correctness, maintainability, or test gap that should be fixed.
- `P3`: minor improvement or cleanup.
