---
name: "rb-execute-plan"
description: "Use when an existing multi-step implementation plan or phase checklist must be refined, sequenced, tracked, or carried through verified phase work. Own plan state, testing strategy, CI-equivalent checks, and verification gates; use $rb-implement-with-tests for one bounded ordinary code change."
---

# RB Execute Plan

Use this skill to own sequencing, phase artifacts, status, testing strategy, and verification for an existing multi-step plan. It is the orchestration layer around implementation work.

Use `$rb-create-implementation-plan` first when the human has a rough idea, feature request, or product goal and needs the top-level plan. Use `$rb-execute-plan` when an existing plan or phase checklist needs sequencing, refinement, progress tracking, or phase-level verification. For one bounded ordinary code change that does not require plan-state ownership, use `$rb-implement-with-tests` directly.

While executing a plan, use `$rb-implement-with-tests` for each selected ordinary software task and `$rb-tdd-scientific-code` for each selected scientific, numerical, modelling, simulation, or domain-sensitive task. `$rb-execute-plan` remains responsible for selecting tasks, preserving dependencies, ensuring the test levels collectively cover the phase, updating plan status from evidence, and deciding whether phase exit criteria are satisfied.

## Core Defaults

- Prefer a walking-skeleton approach: build the thinnest runnable vertical slice first, then deepen it.
- Prefer vertical slices over horizontal/layer-first phases.
- Keep plan orchestration separate from task implementation. This skill selects tasks, supplies their scope and checks, records returned evidence, and maintains phase state; the selected implementation skill owns the detailed edit, test, and task-level review loop.
- Each implementation increment should preserve a runnable path through user input, core processing, output, validation, and persistence/audit when those concerns apply.
- Use automated behavioural tests by default. Manual verification is an exception that must explain why automation is infeasible and what regression risk remains.
- Choose test levels from the likely failure boundary, not from convenience: unit/property, component/integration, contract, migration, workflow/end-to-end, stochastic, performance, security, or concurrency as applicable.
- Avoid silent fallbacks. Prefer fail-fast or fail-closed behaviour with clear diagnostics.
- Only include degraded modes or fallback-like behaviour when the human explicitly asks for them or when they are deliberate, visible, tested, and auditable product states.
- Preserve the repository's existing language, framework, validation, test, coverage, CI, and deployment conventions unless there is a clear reason to change them.
- For systems with multiple LLM agents, agentic workflows, or orchestration layers, use `$rb-multi-agent-systems` to choose the simplest sufficient control model and resolve agent boundaries, tools, handoffs, state, failure containment, observability, evaluation, budgets, durability, and the orchestration test matrix.
- For text-processing work, separate deterministic handling of stable structure from LLM-backed judgement about natural-language meaning.

## Optional Constrained Route

- Read the plan's `Execution Route` before phase work. A missing route behaves as `standard` for existing plans; `undecided` requires one bounded human choice before product execution; never select `constrained` implicitly.
- Keep the ordinary procedure in this skill for `standard` plans.
- The first-release constrained route cannot execute unit tests, integration tests, builds, linting, type checking, application commands, or other behavioural checks because `exec_argv` and `check` are unavailable. Do not choose or continue the constrained route for a phase whose acceptance depends on executing code. Use `standard`, narrow the phase to criteria fully verifiable by static file-state inspection, or stop until reviewed command capability exists.
- File inspection, hashes, and agent-reported reasoning do not constitute behavioural test evidence. A constrained phase must not be marked `[v]` for runtime behaviour based only on source inspection.
- Before invoking `$rb-create-low-level-plan`, confirm every constrained criterion and verifier check can be compiled as `static_file_state::<description>`. The runtime deterministically rejects untyped requirements and the unsupported modes `executable_test`, `runtime_observation`, and `external_observation`.
- Before entering the constrained pipeline, remind the human that `$rb-create-safe-operation-policy` is available when repository-owned path restrictions are wanted; do not create a policy implicitly. Then invoke the manifest-pinned read-only `doctor` command for the exact requested profile. Supply the four installed generated-schema roots, requested verification modes, and only explicitly named provider/grant facts. `doctor` must not install, repair, remove leases, discover ambient credentials, create authority, or select a fallback. Stop on `not_ready`. If semantic roles are required and grants are absent, use `prepare-run-authority` to create a deterministic preview, show its finite limits, permitted automatic-retry classes, and assurance boundaries, and persist authority only after the human supplies the exact preview-bound confirmation statement. One confirmed preparation is the reusable authority envelope for that one unchanged run; it avoids per-call copy and paste but cannot authorise a different run, provider, model, plan, policy, target set, effect set, permission set, expiry, or budget.
- For a statically verifiable `constrained` phase, keep this skill as route and phase-state owner, but process only the next current phase:
  1. invoke `$rb-create-low-level-plan` to compile the phase and preserve every later phase ID;
  2. invoke `$rb-assess-plan-safety` in a fresh context;
  3. stop for human intervention on `safe: false`; a rejected artifact cannot be relabelled;
  4. hand only an unchanged exact `safe: true` bundle to `$rb-safe-operation`;
  5. accept phase completion only when `$rb-safe-operation` reaches `verified` from coordinator-observed product state plus context-separated agent verifier evidence, and only when every criterion is typed `static_file_state` and genuinely static under the supported capability set; on the current host the separation is instruction-only, not host-proven independence.
- Stop after the current constrained phase. Use the coordinator stdout handoff for route, run/phase identity, artifact hashes and locations, lifecycle state, event head, verification modes, every remaining phase ID, enforcement limitations, and exact next action. Write that checkpoint to the canonical external `${CODEX_HOME:-~/.codex}/diary/` with `$rb-working-diary`; this is control-plane continuity state. Never mutate a project-local diary or progress file after verification unless it was an assessed product operation.
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
3. Mark a standard-route task `[v]` only after confirming its behaviour with the appropriate automated test level and recording the evidence.
4. If automated testing is genuinely infeasible, document why, define the best executable or manual check, state the residual regression risk, and obtain explicit acceptance before marking `[v]`.
5. A lint, import, build, smoke check, source inspection, or successful command does not replace behavioural coverage when a plausible regression could otherwise escape.
6. Do not declare the phase complete until every task is `[v]`, the phase-level integration and CI-equivalent checks pass, and the phase completion review+fix cycle is done.
7. For multi-phase work, create a separate implementation file for each phase.
8. Keep the main implementation plan as an overview; put the granular task list, verification notes, and phase-specific test plan in the phase file.
9. Granular tasks should be small enough that completion and verification are unambiguous.

## Phase Planning Requirements

When converting an implementation plan into executable phases, or revising phase plans:

1. Identify the walking skeleton before detailed phase planning.
2. Make Phase 1 a runnable end-to-end slice, even if some internals are minimal.
3. Keep horizontal foundation work only as large as the first vertical slice requires.
4. State exit criteria in terms of user-observable workflow and executable validation checks.
5. Include fail-fast diagnostics and negative-path tests for missing dependencies, provider failures, validation errors, unsupported states, policy blocks, timeouts, partial failures, and duplicate side effects where relevant.
6. Record the existing stack, test frameworks, coverage configuration, canonical CI-equivalent command, and project conventions before proposing dependency or framework changes.
7. For systems with multiple LLM agents, agentic workflows, or orchestration layers, record the decisions and test matrix produced by `$rb-multi-agent-systems` rather than repeating control-model or framework selection in this plan.
8. For text-heavy features, identify which steps are deterministic structure handling and which require semantic LLM judgement. Do not plan elaborate regexes or keyword heuristics as substitutes for understanding natural-language meaning.
9. Include automated tests or justified exceptional verification checks for every task, and ensure the phase collectively covers unit/property logic, important integration boundaries, public contracts, migrations, and critical end-to-end paths as applicable.
10. Include coverage of changed branches and behaviours when project tooling supports it; do not lower established thresholds without approval or impose a new universal percentage target without project agreement.
11. For each phase, create or reference a dedicated phase implementation file with:
   - phase goal;
   - scope and non-scope;
   - dependencies;
   - granular `[ ]` task checklist;
   - changed behaviours and failure modes;
   - selected test levels;
   - tests to add or run, including negative and boundary cases;
   - coverage expectations where tooling exists;
   - canonical CI-equivalent command or justified subset;
   - verification checklist;
   - phase exit criteria.

## Execution Requirements

When executing a phase:

1. Select the next `[ ]` task in dependency order unless learning value or risk justifies a recorded reordering.
2. Choose the task-level implementation workflow:
   - use `$rb-implement-with-tests` for one bounded ordinary software or product change;
   - use `$rb-tdd-scientific-code` for scientific, numerical, modelling, simulation, stochastic, or domain-sensitive work;
   - use `$rb-discuss` and leave the task `[ ]` when material behaviour remains unresolved.
3. Supply the selected workflow with the task's goal, scope, non-scope, relevant context, changed behaviours, likely failure modes, required test levels, coverage expectations, and CI-equivalent checks. Ask it to implement only that selected task and return its evidence.
4. Update the task from `[ ]` to `[x]` only after the implementation workflow reports that the requested change is complete.
5. Record focused automated-test evidence, negative or boundary coverage, and checks not run, but leave the completed task `[x]` while other phase tasks remain `[ ]`.
6. When every task is `[x]`, run a second verification pass over every task. Confirm or rerun the recorded automated tests, add missing integration or contract coverage, record the evidence, and then update each verified task from `[x]` to `[v]`.
7. Treat flaky tests as defects. Do not rerun until green, skip, quarantine, weaken assertions, or lower thresholds merely to complete the phase; preserve failure seeds, ordering, timing, environment, and outputs for diagnosis.
8. Report any task that cannot be implemented or verified, including the diagnostic, retained status, and next fix.
9. After every task is `[v]`, complete the phase-level integration, CI-equivalent, and review+fix gates below and record their outcome in the phase notes.

## Phase Completion Review

Before marking a standard-route phase complete:

- Treat this as a phase-level integration review in addition to the task-level review performed by the implementation skill.
- Run the closest available repository CI-equivalent command: configured tests, linting, formatting, typing, build/package, pre-commit, migration, and critical workflow checks. If the full suite is impractical, run the largest relevant affordable subset and record exactly what was omitted and why.
- Review the implemented change for bugs, regressions, missing or wrongly levelled tests, architecture drift, hidden fallback behaviour, test weakening, flaky tests, coverage gaps, documentation gaps, and unresolved plan assumptions.
- Confirm that important component boundaries and user workflows are tested, not merely that isolated units pass.
- Use `$rb-review-pr-or-diff` for substantial, high-risk, or cross-cutting diffs; for small phases, perform the same review discipline inline.
- Fix actionable findings before completion whenever they are in scope.
- Rerun focused, failure-path, integration, coverage, and CI-equivalent checks affected by the fixes.
- Record any deferred finding, skipped check, or accepted residual risk in the phase notes and final output.

## Review Requirements

When reviewing an existing implementation plan:

- Check whether Phase 1 is truly vertical and runnable.
- Flag horizontal phases that build isolated layers without user-visible workflow progress.
- Flag fallback paths that may hide defects.
- Flag stack or dependency changes that ignore existing repo conventions.
- For plans involving multiple LLM agents, agentic workflows, or orchestration layers, confirm `$rb-multi-agent-systems` concerns and its test matrix are addressed explicitly.
- For text-processing plans, flag semantic tasks implemented only with brittle regex, keyword matching, or ad hoc string scoring.
- Flag tasks without automated behavioural coverage, an appropriate test level, negative-path consideration, or a justified exception.
- Flag plans that lack integration, contract, migration, or end-to-end tests where the likely failures cross those boundaries.
- Flag plans that lack a canonical CI-equivalent completion gate or quietly reduce existing coverage thresholds.
- Check whether task status uses `[ ]`, `[x]`, and `[v]` correctly.
- Confirm no phase is marked complete unless all tasks are `[v]` and the phase-level checks have passed.

## Output

- walking skeleton summary;
- proposed phases with `[ ]` task lists;
- selected task-level implementation workflow and evidence returned;
- changed behaviours, failure modes, selected test levels, and coverage strategy;
- task status updates using `[ ]`, `[x]`, and `[v]` when executing a phase;
- focused, integration, contract, end-to-end, coverage, and CI-equivalent evidence as applicable;
- review+fix findings, fixes applied, checks rerun, and accepted residual risks;
- stack/dependency assumptions and which are existing vs proposed;
- text-processing split, where relevant: deterministic parsing vs semantic LLM calls;
- verification plan and phase exit criteria;
- constrained-route capability and verification-mode limitations when applicable;
- risks, open questions, and decisions needed from the human.
