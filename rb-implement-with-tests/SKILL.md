---
name: "rb-implement-with-tests"
description: "Use for one bounded agreed change with automated behavioural tests, suitable test levels, executable checks, and review. For plan ownership, use $rb-execute-plan or $rb-sprint."
---

# /rb:implement - implement with tests

## Purpose

Implement one agreed ordinary change in small verified increments. This skill owns the detailed code, test, and task-level review loop; it does not sequence multi-phase work or maintain plan-wide status.

Use `$rb-discuss` first when material behaviour, interface, edge cases, compatibility, or test expectations are unclear. Use `$rb-execute-plan` when the user asks to follow, sequence, continue, or track an existing plan linearly. Use `$rb-sprint` when plan-state ownership includes recurring PRD reconciliation and evidence-driven changes to remaining work. When either plan owner selects one ordinary task, use this skill to implement that task and return evidence; the plan owner updates `[ ]`, `[x]`, and `[v]` status. Use `$rb-tdd-scientific-code` instead when the selected change is scientific, numerical, modelling, simulation, or domain-sensitive enough to need scientific invariants.

## Procedure

1. Confirm the one agreed requirement, selected plan task, or issue. If the request contains several tasks that need sequencing or requires plan-state tracking, route to `$rb-execute-plan` for linear delivery or `$rb-sprint` for adaptive delivery before editing.
2. Read `AGENTS.md`, `CONTEXT.md`, relevant docs, surrounding code, existing tests, coverage configuration, and canonical CI or pre-commit commands that define local conventions.
3. Check current worktree state. Preserve user changes and avoid touching unrelated files.
4. Identify the smallest useful behaviour to change and the plausible ways it could fail, including invalid inputs, boundary values, permission or policy denial, missing dependencies, external-service failure, timeout, partial failure, duplicate requests, idempotency, concurrency, rollback, and corrupted responses where relevant.
5. If the change handles text, classify the text operation before designing the code:
   - Use deterministic parsing for syntax-bound tasks with stable structure, such as JSON/YAML/XML/CSV parsing, frontmatter fields, exact delimiters, known IDs, line-oriented logs, file paths, URLs, or protocol formats.
   - Use structured parsers or existing libraries for structured formats before considering regex.
   - Invoke an LLM for semantic tasks that require meaning, intent, relevance, classification, summarisation, ambiguity resolution, rubric judgment, natural-language extraction, entity/claim matching, or deciding whether two differently worded passages mean the same thing.
   - Do not replace semantic understanding with elaborate regexes, keyword lists, brittle heuristics, or ad hoc string scoring unless the human explicitly accepts that limitation.
   - When using an LLM, keep deterministic pre/post-processing around it: bounded input selection, typed output schema, validation, retries/fallbacks, fixtures/evals where practical, and visible failure if the LLM path is unavailable.
6. Select the test level from the changed behaviour and likely failure boundary:
   - unit or property tests for pure logic, local transformations, branching, and invariants;
   - component or integration tests for database, filesystem, network, queue, process, framework, or service boundaries;
   - contract tests for public APIs, schemas, events, tool interfaces, and compatibility promises;
   - migration tests for existing data, upgrade paths, rollback, and partial failure;
   - end-to-end or workflow tests for critical multi-component user paths;
   - smoke, performance, security, or concurrency tests when those risks are material.
7. Add or update an automated test that exercises the changed behaviour by default. Include at least one relevant negative, boundary, or failure-path case when the change adds a decision, validation rule, external interaction, or side effect. If an automated test is genuinely infeasible, document why, define the best executable or manual verification before editing, and state the regression risk that remains.
8. Run the focused test or baseline check before editing when possible. For bug fixes, preserve evidence that the regression test fails against the defective behaviour.
9. Implement the smallest change that should pass the test, following existing patterns and helper APIs.
10. Run the focused test again and confirm the intended failure path as well as the happy path where relevant.
11. Run broader tests when the change touches shared behaviour, public interfaces, migrations, persistence, build configuration, external integrations, or user-facing workflows.
12. Inspect coverage tooling when the repository already uses it. Ensure the changed branches and behaviours are exercised, use diff coverage when available, and do not reduce established thresholds without explicit approval. Do not introduce a universal percentage target where the project has none.
13. Refactor only while keeping checks green and only within the requested scope.
14. Update `$rb-working-diary` only when the implementation is long-running, context-heavy, or part of accumulated project work that needs cross-session continuity.
15. Repeat in small increments until the requested change is complete.
16. Run the closest available repository CI-equivalent command before completion: the configured test/lint/type/build/pre-commit workflow, or the largest relevant affordable subset when the full suite is impractical. Record exactly what was omitted and why.
17. Run a final review over the diff, tests, docs, and behaviour. Use `$rb-review-pr-or-diff` for substantial, risky, or cross-cutting changes; for small changes, perform the same review discipline inline.
18. Fix actionable review findings, rerun the relevant focused, failure-path, broader, and CI-equivalent checks, and re-review when findings were material.
19. Do not call the implementation complete until no blocking review findings remain, or the human explicitly accepts the residual risk.

## Test Integrity Rules

- Do not delete, skip, quarantine, or weaken a failing test merely to make the suite green.
- Do not weaken an assertion, fixture, coverage threshold, type check, or expected error without explaining why the previous expectation was incorrect and obtaining approval when behaviour changes.
- Do not rerun an intermittent test until it happens to pass. Treat flakiness as a defect; preserve the seed, timing, ordering, environment, and failing output where relevant, then diagnose it.
- Prefer tests that assert externally meaningful behaviour over tests coupled to private implementation details.
- Use mocks or stubs at genuine boundaries, not to bypass the behaviour being tested. Keep at least one realistic integration path for important boundaries where practical.
- A successful lint, import, build, or smoke check does not replace a behavioural test when a plausible regression in the changed behaviour could otherwise escape.

## Required Behaviour

- Do not skip clarification when behaviour is still ambiguous.
- Do not create, resequence, or mark a multi-phase plan complete. Return implementation and verification evidence to `$rb-execute-plan` or `$rb-sprint` when it owns the surrounding plan.
- Do not claim success without running or explicitly naming the automated test and CI-equivalent check that could not be run.
- Keep edits scoped to the requested behaviour unless a wider change is necessary and explained.
- Do not introduce dependencies, migrations, destructive operations, secret handling changes, or broad architecture changes without explicit approval.
- Do not rewrite working user changes; work with them or ask if they block the task.
- Prefer the repository's existing style, tests, frameworks, and abstractions over new patterns.
- For text-heavy code, keep a clear boundary between deterministic structure handling and semantic LLM judgment.
- Do not build complex regex/string heuristics for tasks whose acceptance criteria depend on understanding the text.
- Do not skip the final review+fix loop unless the human explicitly asks to stop before review.

## Output

- the selected task or requirement completed and what changed
- changed behaviour, plausible failure modes, and selected test level
- automated tests added or updated, including negative or boundary coverage
- focused, broader, coverage, and CI-equivalent checks run with exact outcomes
- review+fix findings, fixes applied, and checks rerun
- checks not run, why they were not run, and the resulting regression risk
- residual risks or follow-up work
