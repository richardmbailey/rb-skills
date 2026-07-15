---
name: "rb-execute-plan"
description: "Use when an implementation plan, phase checklist, issue list, or agreed direction already exists and must be executed, refined, reviewed, or tracked through implementation and verification. Do not use to create the initial top-level plan from a rough idea."
---

# RB Execute Plan

Use this skill for turning an existing implementation plan into executable, verified phase work.

Use `$rb-create-implementation-plan` first when the human has a rough idea, feature request, or product goal and needs the top-level plan. Use `$rb-execute-plan` when there is already a plan, phase, issue list, checklist, or agreed direction that needs to become concrete tasks, implementation progress, verification gates, or a plan review.

## Core Defaults

- Prefer a walking-skeleton approach: build the thinnest runnable vertical slice first, then deepen it.
- Prefer vertical slices over horizontal/layer-first phases.
- Each implementation increment should preserve a runnable path through user input, core processing, output, validation, and persistence/audit when those concerns apply.
- Avoid silent fallbacks. Prefer fail-fast or fail-closed behavior with clear diagnostics.
- Only include degraded modes or fallback-like behavior when the human explicitly asks for them or when they are deliberate, visible, and auditable product states.
- Preserve the repository's existing language, framework, validation, test, and deployment conventions unless there is a clear reason to change them.
- For multi-agent architecture, use `$rb-multi-agent-systems` to resolve agent boundaries, tools, handoffs, state, failure containment, observability, evaluation, budgets, and durability.
- For text-processing work, separate deterministic handling of stable structure from LLM-backed judgment about natural-language meaning.

## Phase Checklist Convention

Every explicit implementation phase plan must use task checkboxes:

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Rules:

1. Mark a task `[x]` only after completing the implementation work.
2. After all tasks in the phase are `[x]`, run a second verification pass over every task.
3. Mark a task `[v]` only after confirming its behavior with a relevant automated test or explicit verification check.
4. If a task has no verification path, add a test/check or document why the best available check is manual before marking it `[v]`.
5. Do not declare the phase complete until every task is `[v]` and the phase completion review+fix cycle is done.
6. For multi-phase work, create a separate implementation file for each phase.
7. Keep the main implementation plan as an overview; put the granular task list, verification notes, and phase-specific test plan in the phase file.
8. Granular tasks should be small enough that completion and verification are unambiguous.

## Phase Planning Requirements

When converting an implementation plan into executable phases, or revising phase plans:

1. Identify the walking skeleton before detailed phase planning.
2. Make Phase 1 a runnable end-to-end slice, even if some internals are minimal.
3. Keep horizontal foundation work only as large as the first vertical slice requires.
4. State exit criteria in terms of user-observable workflow and validation checks.
5. Include fail-fast diagnostics for missing dependencies, provider failures, validation errors, unsupported states, and policy blocks.
6. Record the existing stack and project conventions before proposing dependency or framework changes.
7. For multi-agent systems, record the decisions produced by `$rb-multi-agent-systems` rather than repeating framework selection in this plan.
8. For text-heavy features, identify which steps are deterministic structure handling and which require semantic LLM judgment. Do not plan elaborate regexes or keyword heuristics as substitutes for understanding natural-language meaning.
9. Include tests or verification checks for every task.
10. For each phase, create or reference a dedicated phase implementation file with:
   - phase goal
   - scope and non-scope
   - dependencies
   - granular `[ ]` task checklist
   - verification checklist
   - tests to add or run
   - phase exit criteria

## Execution Requirements

When executing a phase:

1. Work through `[ ]` tasks in order unless a dependency requires reordering.
2. Update each completed task from `[ ]` to `[x]`.
3. Run the relevant test/check loop as tasks are completed.
4. When all tasks are `[x]`, verify every task again with recorded tests or checks.
5. Add missing tests/checks before marking unverified work verified.
6. Update verified tasks from `[x]` to `[v]`.
7. Report any task that cannot be verified, with the diagnostic and next fix.
8. After every task is `[v]`, complete the review+fix gate below and record its outcome in the phase notes.

## Phase Completion Review

Before marking a phase complete:

- Review the implemented change for bugs, regressions, missing tests, architecture drift, hidden fallback behavior, documentation gaps, and unresolved plan assumptions.
- Use `$rb-review-pr-or-diff` for substantial, high-risk, or cross-cutting diffs; for small phases, perform the same review discipline inline.
- Fix actionable findings before completion whenever they are in scope.
- Rerun focused and broader checks affected by the fixes.
- Record any deferred finding, skipped check, or accepted residual risk in the phase notes and final output.

## Review Requirements

When reviewing an existing implementation plan:

- Check whether Phase 1 is truly vertical and runnable.
- Flag horizontal phases that build isolated layers without user-visible workflow progress.
- Flag fallback paths that may hide defects.
- Flag stack or dependency changes that ignore existing repo conventions.
- For multi-LLM-agent plans, confirm `$rb-multi-agent-systems` concerns are addressed explicitly.
- For text-processing plans, flag semantic tasks implemented only with brittle regex, keyword matching, or ad hoc string scoring.
- Flag tasks without test or verification coverage.
- Check whether task status uses `[ ]`, `[x]`, and `[v]` correctly.
- Confirm no phase is marked complete unless all tasks are `[v]`.

## Output

- walking skeleton summary
- proposed phases with `[ ]` task lists
- task status updates using `[ ]`, `[x]`, and `[v]` when executing a phase
- review+fix findings, fixes applied, checks rerun, and accepted residual risks
- stack/dependency assumptions and which are existing vs proposed
- text-processing split, where relevant: deterministic parsing vs semantic LLM calls
- verification plan and phase exit criteria
- risks, open questions, and decisions needed from the human
