---
name: "rb-execute-plan"
description: "Use when an existing multi-step implementation plan or phase checklist must be refined, sequenced, tracked, or carried through verified phase work. Own plan state and verification gates; use $rb-implement-with-tests for one bounded ordinary code change."
---

# RB Execute Plan

Use this skill to own sequencing, phase artifacts, status, and verification for an existing multi-step plan. It is the orchestration layer around implementation work.

Use `$rb-create-implementation-plan` first when the human has a rough idea, feature request, or product goal and needs the top-level plan. Use `$rb-execute-plan` when an existing plan or phase checklist needs sequencing, refinement, progress tracking, or phase-level verification. For one bounded ordinary code change that does not require plan-state ownership, use `$rb-implement-with-tests` directly.

While executing a plan, use `$rb-implement-with-tests` for each selected ordinary software task and `$rb-tdd-scientific-code` for each selected scientific, numerical, modelling, simulation, or domain-sensitive task. `$rb-execute-plan` remains responsible for selecting tasks, preserving dependencies, updating plan status from evidence, and deciding whether phase exit criteria are satisfied.

## Core Defaults

- Prefer a walking-skeleton approach: build the thinnest runnable vertical slice first, then deepen it.
- Prefer vertical slices over horizontal/layer-first phases.
- Keep plan orchestration separate from task implementation. This skill selects tasks, supplies their scope and checks, records returned evidence, and maintains phase state; the selected implementation skill owns the detailed edit, test, and task-level review loop.
- Each implementation increment should preserve a runnable path through user input, core processing, output, validation, and persistence/audit when those concerns apply.
- Avoid silent fallbacks. Prefer fail-fast or fail-closed behavior with clear diagnostics.
- Only include degraded modes or fallback-like behavior when the human explicitly asks for them or when they are deliberate, visible, and auditable product states.
- Preserve the repository's existing language, framework, validation, test, and deployment conventions unless there is a clear reason to change them.
- For multi-agent architecture, use `$rb-multi-agent-systems` to resolve agent boundaries, tools, handoffs, state, failure containment, observability, evaluation, budgets, and durability.
- For text-processing work, separate deterministic handling of stable structure from LLM-backed judgment about natural-language meaning.

## Optional Constrained Route

- Read the plan's `Execution Route` before phase work. A missing route behaves as `standard` for existing plans; `undecided` requires one bounded human choice before product execution; never select `constrained` implicitly.
- Keep the ordinary procedure in this skill for `standard` plans.
- For `constrained`, keep this skill as route and phase-state owner, but process only the next current phase:
  1. invoke `$rb-create-low-level-plan` to compile the phase and preserve every later phase ID;
  2. invoke `$rb-assess-plan-safety` in a fresh context;
  3. stop for human intervention on `safe: false`; a rejected artifact cannot be relabelled;
  4. hand only an unchanged exact `safe: true` bundle to `$rb-safe-operation`;
  5. accept phase completion only when `$rb-safe-operation` reaches `verified` from coordinator-observed product state plus context-separated agent verifier evidence; on the current host the separation is instruction-only, not host-proven independence.
- Stop after the current constrained phase. Use the coordinator stdout handoff for route, run/phase identity, artifact hashes and locations, lifecycle state, event head, every remaining phase ID, enforcement limitations, and exact next action. Write that checkpoint to the canonical external `${CODEX_HOME:-~/.codex}/diary/` with `$rb-working-diary`; this is control-plane continuity state. Never mutate a project-local diary or progress file after verification unless it was an assessed product operation.
- On the constrained route, treat the external diary checkpoint as the authoritative phase-status overlay: record the completed phase as `[v]` only after the coordinator reaches `verified`, while leaving the repository plan unchanged. The next phase is the first ID in the verified handoff's ordered `remaining_phase_ids`, cross-checked against the unchanged authoritative plan. Do not infer constrained progress from stale repository checkboxes or make an unassessed post-verification checklist edit.
- Leaving the constrained pipeline requires an explicit human choice recorded by `$rb-working-diary` in the canonical external `${CODEX_HOME:-~/.codex}/diary/` checkpoint, including the rejected run/bundle hash, `leave_constrained_pipeline`, the resulting route, and the exact next action. This first-release record is instruction-only continuity evidence, not a runtime-authenticated or resumable `HumanIntervention` artifact. It does not make a rejected assessment executable; subsequent standard execution is a separately authorised workflow choice.

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

1. Select the next `[ ]` task in dependency order unless learning value or risk justifies a recorded reordering.
2. Choose the task-level implementation workflow:
   - use `$rb-implement-with-tests` for one bounded ordinary software or product change;
   - use `$rb-tdd-scientific-code` for scientific, numerical, modelling, simulation, stochastic, or domain-sensitive work;
   - use `$rb-discuss` and leave the task `[ ]` when material behaviour remains unresolved.
3. Supply the selected workflow with the task's goal, scope, non-scope, relevant context, and required tests or checks. Ask it to implement only that selected task and return its evidence.
4. Update the task from `[ ]` to `[x]` only after the implementation workflow reports that the requested change is complete.
5. Record the implementation workflow's focused test or check evidence, but leave the completed task `[x]` while other phase tasks remain `[ ]`.
6. When every task is `[x]`, run a second verification pass over every task. Confirm or rerun the recorded automated test or explicit check, add a missing check where needed, record the evidence, and then update each verified task from `[x]` to `[v]`.
7. Report any task that cannot be implemented or verified, including the diagnostic, retained status, and next fix.
8. After every task is `[v]`, complete the phase-level review+fix gate below and record its outcome in the phase notes.

## Phase Completion Review

Before marking a phase complete:

- Treat this as a phase-level integration review in addition to the task-level review performed by the implementation skill.
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
- selected task-level implementation workflow and evidence returned
- task status updates using `[ ]`, `[x]`, and `[v]` when executing a phase
- review+fix findings, fixes applied, checks rerun, and accepted residual risks
- stack/dependency assumptions and which are existing vs proposed
- text-processing split, where relevant: deterministic parsing vs semantic LLM calls
- verification plan and phase exit criteria
- risks, open questions, and decisions needed from the human
