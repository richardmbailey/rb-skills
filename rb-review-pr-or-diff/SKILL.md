---
name: "rb-review-pr-or-diff"
description: "Use when the user wants defects and risks found in a pull request or diff, including regressions, missing or wrongly levelled tests, flaky or weakened tests, and concrete fixes, with severity and file references. For a teaching-oriented change explanation, use $rb-explain-diff."
---

# /rb:review - review a PR or diff

## Purpose

Review changes for actionable defects, regressions, missing or inadequate tests, and maintainability risks. Default to review only; do not edit code unless the human explicitly asks for fixes.

## Procedure

1. Inspect the diff or PR scope, including added, modified, deleted, and generated files.
2. Read relevant surrounding code, tests, coverage configuration, CI workflows, migrations, and public interfaces touched by the change.
3. Read `AGENTS.md` and `CONTEXT.md` when present and relevant, especially for domain logic, scientific assumptions, deployment, testing conventions, or project-specific rules.
4. If the diff affects multiple LLM agents, an agentic workflow, or an orchestration layer, also use `$rb-multi-agent-systems` to review whether the control model is the simplest sufficient architecture, along with agent boundaries, tool permissions, handoffs, state, structured outputs, tracing, evals, retrieval, provider routing, durability, and the required test matrix.
5. For text-handling changes, check whether the code separates deterministic structure parsing from semantic understanding:
   - Deterministic parsing is appropriate for stable syntax, exact delimiters, structured formats, known IDs, file paths, URLs, logs, or protocol fields.
   - LLM calls are appropriate when correctness depends on meaning, intent, relevance, classification, summarisation, ambiguity resolution, natural-language extraction, rubric judgment, entity/claim matching, or semantic equivalence.
   - Flag elaborate regexes, keyword lists, fuzzy string scoring, or brittle heuristics when they are standing in for semantic judgment.
   - Check that LLM-backed semantic paths have typed outputs, validation, failure handling, deterministic fixtures, and held-out evals where practical.
6. Review the testing strategy against the likely regression boundary:
   - unit or property tests for local logic and invariants;
   - integration tests for database, filesystem, network, queue, framework, solver, process, or service boundaries;
   - contract tests for public APIs, schemas, events, tools, and compatibility;
   - migration and rollback tests for existing data or state changes;
   - end-to-end tests for critical user or operational workflows;
   - stochastic, performance, security, concurrency, recovery, and multi-agent evals where those risks are material.
7. Check that new decisions, validation rules, external interactions, and side effects include relevant negative, boundary, timeout, permission-denial, partial-failure, duplicate, idempotency, rollback, or corrupted-response cases.
8. Check test integrity:
   - no deleted, skipped, quarantined, or weakened test merely to make the suite green;
   - no unjustified assertion, tolerance, seed, fixture, type-check, or coverage-threshold weakening;
   - no repeated rerun-until-green treatment of an intermittent failure;
   - mocks do not bypass the behaviour supposedly under test;
   - important integration paths are not represented only by isolated mocks.
9. Check correctness, architecture, naming, maintainability, performance, security/privacy, data migrations, numerical stability, units, reproducibility, compatibility, coverage of changed branches, CI-equivalent checks, and failure modes.
10. Separate definite issues from uncertainties. Do not present speculation as a finding; put uncertain points under questions or residual risk.
11. Update `$rb-working-diary` with durable findings and unresolved risks when the review is substantial or likely to continue.
12. Recommend concrete fixes for each finding, but do not apply them unless asked.

## Required Behaviour

- Findings come first, ordered by severity.
- Every finding needs a tight file/line reference when possible.
- Explain the user-visible or developer-visible impact, not just style preference.
- Flag missing or wrongly levelled tests when a plausible regression could escape, including failures at component boundaries rather than demanding tests ritualistically.
- Flag test deletion, weakening, flaky rerun-until-green behaviour, unjustified threshold reductions, and mock-only coverage of critical boundaries as correctness risks.
- Do not impose a universal numerical coverage target where the project has none; assess changed behaviours, branches, existing thresholds, and diff coverage where available.
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

- Test levels reviewed and whether they match the likely failure boundaries.
- Negative, integration, contract, migration, end-to-end, scientific, or agent-eval gaps.
- Coverage, flaky-test, weakened-test, CI, or checks-not-run risks.

## Summary

Brief change summary only after findings.
```

Severity guide:

- `P0`: must fix immediately; data loss, security issue, or complete breakage.
- `P1`: likely bug or serious regression.
- `P2`: correctness, maintainability, or test gap that should be fixed.
- `P3`: minor improvement or cleanup.
