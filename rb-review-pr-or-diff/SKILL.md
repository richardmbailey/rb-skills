---
name: "rb-review-pr-or-diff"
description: "Use when the user wants defects and risks found in a pull request or diff, including regressions, missing tests, and concrete fixes, with severity and file references. For a teaching-oriented change explanation, use $rb-explain-diff."
---

# /rb:review - review a PR or diff

## Purpose

Review changes for actionable defects, regressions, missing tests, and maintainability risks. Default to review only; do not edit code unless the human explicitly asks for fixes.

## Procedure

1. Inspect the diff or PR scope, including added, modified, deleted, and generated files.
2. Read relevant surrounding code, tests, configuration, migrations, and public interfaces touched by the change.
3. Read `AGENTS.md` and `CONTEXT.md` when present and relevant, especially for domain logic, scientific assumptions, deployment, or project-specific rules.
4. If the diff affects a multi-LLM-agent system, also use `$rb-multi-agent-systems` to review agent boundaries, tool permissions, handoffs, state, structured outputs, tracing, evals, retrieval, provider routing, and durability.
5. For text-handling changes, check whether the code separates deterministic structure parsing from semantic understanding:
   - Deterministic parsing is appropriate for stable syntax, exact delimiters, structured formats, known IDs, file paths, URLs, logs, or protocol fields.
   - LLM calls are appropriate when correctness depends on meaning, intent, relevance, classification, summarisation, ambiguity resolution, natural-language extraction, rubric judgment, entity/claim matching, or semantic equivalence.
   - Flag elaborate regexes, keyword lists, fuzzy string scoring, or brittle heuristics when they are standing in for semantic judgment.
   - Check that LLM-backed semantic paths have typed outputs, validation, failure handling, and tests/fixtures/evals where practical.
6. Check correctness, tests, architecture, naming, maintainability, performance, security/privacy, data migrations, numerical stability, units, reproducibility, compatibility, and failure modes.
7. Separate definite issues from uncertainties. Do not present speculation as a finding; put uncertain points under questions or residual risk.
8. Update `$rb-working-diary` with durable findings and unresolved risks when the review is substantial or likely to continue.
9. Recommend concrete fixes for each finding, but do not apply them unless asked.

## Required Behaviour

- Findings come first, ordered by severity.
- Every finding needs a tight file/line reference when possible.
- Explain the user-visible or developer-visible impact, not just style preference.
- Flag missing tests only when a plausible regression would escape without them.
- Treat over-regexed semantic text handling as a correctness/design risk, not as a style preference.
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
