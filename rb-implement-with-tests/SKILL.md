---
name: "rb-implement-with-tests"
description: "Use for one bounded agreed change with automated behavioural tests, suitable test levels, executable checks, and review. For plan ownership, use $rb-execute-plan or $rb-sprint."
---

# /rb:implement - implement with tests

## Purpose

Implement one agreed ordinary change in small verified increments. This skill owns the detailed code, test, and task-level review loop; it does not sequence multi-phase work or maintain plan-wide status.

Use `$rb-discuss` first when material behaviour, interface, edge cases, compatibility, or test expectations are unclear. Use `$rb-execute-plan` when the user asks to follow, sequence, continue, or track an existing plan linearly. Use `$rb-sprint` when plan-state ownership includes recurring PRD reconciliation and evidence-driven changes to remaining work. When either plan owner selects one ordinary task, use this skill to implement that task and return evidence; the plan owner updates `[ ]`, `[x]`, and `[v]` status. Use `$rb-tdd-scientific-code` instead when the selected change is scientific, numerical, modelling, simulation, or domain-sensitive enough to need scientific invariants.

## Procedure

1. Establish the agreed requirement from the current request and project context. Do not ask the human to reconfirm a clear instruction. Route to `$rb-execute-plan` or `$rb-sprint` only when the work needs plan-wide sequencing or status ownership; several related edits can still be one bounded change.
2. Read `AGENTS.md`, `CONTEXT.md`, relevant docs, surrounding code, existing tests, coverage configuration, and canonical CI or pre-commit commands that define local conventions.
3. Check current worktree state. Preserve user changes and avoid touching unrelated files.
4. Identify the smallest useful behaviour to change and the plausible ways it could fail, including invalid inputs, boundary values, permission or policy denial, missing dependencies, external-service failure, timeout, partial failure, duplicate requests, idempotency, concurrency, rollback, and corrupted responses where relevant.
5. For text processing, use structured parsers for stable syntax. When correctness depends on meaning, use an LLM or an existing semantic method whose measured behaviour meets the requirement. Do not substitute elaborate regexes or brittle keyword heuristics for semantic understanding. For model-backed paths, bound the inputs, validate typed outputs, test representative errors, and make failure visible. Respect any explicit project choice of technology.
6. Select the test level from the changed behaviour and likely failure boundary:
   - unit or property tests for pure logic, local transformations, branching, and invariants;
   - component or integration tests for database, filesystem, network, queue, process, framework, or service boundaries;
   - contract tests for public APIs, schemas, events, tool interfaces, and compatibility promises;
   - migration tests for existing data, upgrade paths, rollback, and partial failure;
   - end-to-end or workflow tests for critical multi-component user paths;
   - smoke, performance, security, or concurrency tests when those risks are material.
7. Add or update an automated test that exercises the changed behaviour by default. Include at least one relevant negative, boundary, or failure-path case when the change adds a decision, validation rule, external interaction, or side effect. Reuse existing coverage when it already discriminates the change. For prose, formatting, or another change without executable behaviour, use the relevant artifact check rather than inventing a behavioural test. If needed behavioural automation is infeasible, document why, define the best executable or manual verification before editing, and state the remaining regression risk.
8. Run the focused test or baseline check before editing when possible. For bug fixes, preserve evidence that the regression test fails against the defective behaviour.
9. Implement the smallest change that should pass the test, following existing patterns and helper APIs.
10. Run the focused test again and confirm the intended failure path as well as the happy path where relevant.
11. Run broader tests when the change touches shared behaviour, public interfaces, migrations, persistence, build configuration, external integrations, or user-facing workflows.
12. Inspect coverage tooling when the repository already uses it. Ensure the changed branches and behaviours are exercised, use diff coverage when available, and do not reduce established thresholds without explicit approval. Do not introduce a universal percentage target where the project has none.
13. Refactor only while keeping checks green and only within the requested scope.
14. Update `$rb-working-diary` only when the implementation is long-running, context-heavy, or part of accumulated project work that needs cross-session continuity.
15. Repeat in small increments until the requested change is complete.
16. Run the closest available repository CI-equivalent command before completion, or the largest relevant affordable subset when the full suite is impractical. Record omitted checks and why. Reuse passing evidence for unchanged code and environment; rerun when later edits or unresolved failures could invalidate it.
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

- Ask only about unresolved decisions that materially change behaviour, scope, compatibility, authority, or acceptance. Infer routine implementation details from the repository.
- Do not create, resequence, or mark a multi-phase plan complete. Return implementation and verification evidence to `$rb-execute-plan` or `$rb-sprint` when it owns the surrounding plan.
- Do not claim success without running or explicitly naming the automated test and CI-equivalent check that could not be run.
- Keep edits scoped to the requested behaviour unless a wider change is necessary and explained.
- Do not introduce dependencies, migrations, destructive operations, secret handling changes, or broad architecture changes without explicit approval.
- Do not rewrite working user changes; work with them or ask if they block the task.
- Prefer the repository's existing style, tests, frameworks, and abstractions over new patterns.
- Do not skip the final review+fix loop unless the human explicitly asks to stop before review.

## Output

Report the changed behaviour, relevant test and CI-equivalent outcomes, material review findings, and remaining risks. Name omitted checks and their consequences. Scale the explanation to the change; do not repeat an unchanged test inventory or emit empty sections.
