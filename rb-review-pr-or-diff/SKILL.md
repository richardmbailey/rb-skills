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
5. For text-handling changes, check that stable syntax uses structured parsing and semantic tasks use a method validated against representative meaning-dependent cases. Flag brittle heuristics when concrete failures or unsupported assumptions threaten correctness. Do not require an LLM solely because another validated semantic method was used. Check model-backed paths for typed outputs, validation, failure handling, and held-out evals where practical.
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
9. Inspect the risks exposed by the diff. Expand into architecture, security, migrations, numerical behaviour, performance, or other concerns only when the changed behaviour creates that failure boundary. Run a focused discriminating check when it can resolve a material uncertainty; do not repeat an unchanged full suite solely to perform a review.
10. Separate definite issues from uncertainties. Do not present speculation as a finding; put uncertain points under questions or residual risk.
11. Use `$rb-working-diary` only when its trigger conditions apply and the human has authorized durable continuity. Do not write diary entries for an isolated one-turn review.
12. Recommend concrete fixes for each finding, but do not apply them unless asked.

## Reuse evidence and limit follow-up review

Review the supplied test results against the actual diff and the conditions in which they ran. Do not rerun a passing suite merely to make it the reviewer's own result. Run a focused check when the available evidence leaves a material question unanswered, when a relevant condition has changed, or when the project explicitly requires independent execution. Explain which of these reasons applies.

A review may cover the complete coherent repair, including its tests and integration implications. After findings are fixed, review the changed parts and any conclusions that the fix could invalidate. Expand the review when the fix exposes a new risk; do not automatically reopen every accepted part of the original diff.

Do not require a separate review package for each routine status check, same-scope session renewal or handoff. Require separate operational assessment when the action changes authority, has uncertain side effects, involves recovery or deployment risks not covered by the code review, or falls under an explicit gate. A code review never substitutes for required fresh authority or cleanup checks.

When no blocking finding or material unanswered question remains within the requested scope, return the verdict and its limits. Do not delay it to produce more review artifacts or repeat an unchanged test inventory.

For a blocking finding, name the affected requirement or explicit gate, the evidence of failure or missing acceptance evidence, and the action that cannot proceed. Keep speculative edge cases and optional improvements separate from blockers. An unrelated defect does not automatically block this change; preserve its evidence and assess whether it affects the requested behaviour or a required gate. Do not turn every uncertainty into a required test.

## Required Behaviour

- Findings come first, ordered by severity.
- Every finding needs a tight file/line reference when possible.
- Explain the user-visible or developer-visible impact, not just style preference.
- Flag missing or wrongly levelled tests when a plausible regression could escape, including failures at component boundaries rather than demanding tests ritualistically.
- Flag test deletion, weakening, flaky rerun-until-green behaviour, unjustified threshold reductions, and mock-only coverage of critical boundaries as correctness risks.
- Do not impose a universal numerical coverage target where the project has none; assess changed behaviours, branches, existing thresholds, and diff coverage where available.
- Judge findings by observable impact and evidence, not by whether the author followed this skill's preferred procedure.
- Say clearly when no actionable issues are found.
- Include checks not run and residual risks.

## Output

Use this shape for a substantial review. For a small review, report the supported findings and verification limits concisely; omit empty sections. Do not manufacture a finding to fill the template.

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
