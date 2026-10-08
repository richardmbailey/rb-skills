---
name: "rb-sprint"
description: "Use for adaptive delivery of an existing plan through PRD-aligned sprints, evidence-backed replanning, tests, and review. Do not use for initial planning, linear execution, or one bounded change."
---

# RB Sprint

Use this skill to deliver an existing multi-step implementation plan through an adaptive review, plan, build, verify, and replan loop. The product requirements define the intended outcome. The implementation plan is a changeable technical strategy for reaching it.

Use `$rb-create-implementation-plan` first when no top-level plan exists. Use `$rb-create-prd` when the project needs an authoritative product requirements document or when product decisions must change. Use `$rb-execute-plan` when the human wants the approved plan followed linearly without recurring PRD reconciliation or plan restructuring. For one bounded ordinary change without plan-state ownership, use `$rb-implement-with-tests` directly.

This skill owns sprint selection, PRD alignment, implementation-plan changes, sprint records, phase and task status, testing strategy, CI-equivalent checks, review gates, and the transition to the next sprint. Use `$rb-implement-with-tests` for each selected ordinary software task and `$rb-tdd-scientific-code` for each selected scientific, numerical, modelling, simulation, stochastic, or domain-sensitive task.

## Required Inputs

Before starting the first sprint, locate or obtain:

- an authoritative PRD or equivalent requirements artifact, including its decision or approval status;
- the current top-level implementation plan and any phase files;
- stable requirement and phase identifiers where the source artifacts provide them;
- the current repository and implementation state;
- the test architecture, coverage conventions, and canonical CI-equivalent command;
- recorded decision authority, constraints, accepted risks, and rollout or rollback boundaries;
- existing sprint, diary, handoff, decision, and plan-change records.

If no authoritative requirements artifact exists, do not infer product intent from the implementation plan. Use `$rb-discuss` for consequential requirements that need the user's judgement, or `$rb-create-prd` when durable product requirements are needed. Investigate technical unknowns within the sprint; preserve settled or delegated choices. If the implementation plan is missing, use `$rb-create-implementation-plan`.

Apply the artifacts in this order when they conflict:

1. applicable higher-priority instructions and current authorised human decisions;
2. the authoritative PRD or equivalent requirements artifact;
3. the approved implementation plan;
4. the current sprint record.

The repository implementation and test results describe observed state. They provide evidence for changing a plan, but they do not override an approved requirement. A lower-level artifact must not silently change a higher-level artifact. A current instruction from an authorised decision-maker can change the product baseline. Record that decision and update the affected requirements before adapting the plan; do not ask for the same approval again. If authority or material consequences remain unresolved, ask only about that gap.

## Core Defaults

- Prefer a walking-skeleton approach and vertical slices that produce runnable, user-observable progress.
- Treat tests, reviews, experiments, failures, repository inspection, and operational observations as evidence. Agent reflection without supporting evidence does not justify a plan change or prove progress.
- Preserve the current plan by default. Replan only after the plan-change gate returns `REPLAN` from complete recorded evidence.
- Keep the PRD or equivalent requirements artifact authoritative for product intent. Do not silently change requirements, scope, acceptance evidence, success measures, users, permissions, data policy, rollout, or accepted risk.
- Preserve completed work and decision history. Revise remaining work rather than rewriting earlier `[x]` or `[v]` entries as if they never existed.
- Use automated behavioural tests by default. A lint, import, build, smoke check, source inspection, or successful command does not replace behavioural coverage when a plausible regression could escape.
- Choose test levels from the likely failure boundary: unit or property, component or integration, contract, migration, workflow or end-to-end, stochastic, performance, security, concurrency, or recovery as applicable.
- Avoid silent fallbacks. A degraded mode must be deliberate, visible, tested, auditable, and within the approved product requirements.
- Preserve repository language, framework, dependency, testing, coverage, CI, and deployment conventions unless evidence supports a change within the authorised boundary.
- For systems with multiple LLM agents, agentic workflows, or orchestration layers, use `$rb-multi-agent-systems` to define the control model, agent and tool boundaries, state, handoffs, failure containment, observability, evaluation, budgets, durability, and orchestration test matrix.
- For text-processing work, separate deterministic handling of stable syntax from validated semantic methods for natural-language meaning.

## Adaptive Workflow State

Use these states and transitions:

```text
review -- NO_CHANGE ------------------------> sprint_ready -> building -> verifying -> review
   |
   +-- REPLAN -----------------------------> replan -> sprint_ready
   +-- AWAITING_HUMAN_DECISION ------------> awaiting_human_decision
   +-- BLOCKED ----------------------------> blocked
   +-- all completion conditions satisfied -> complete
```

The sprint record is the current-state artifact. The implementation plan and its change log preserve delivery strategy and history. The working diary preserves cross-session continuity when the work is long-running.

Do not begin `building` until the sprint is `sprint_ready`. Do not begin another sprint until the preceding sprint reaches `review` with verification evidence or an explicit blocked outcome.

## Sprint Loop

### 1. Review the baseline and current state

At the start of every sprint, and immediately after a material discovery:

1. Establish the authoritative requirements, current plan, active sprint, repository instructions, Git state, and relevant test evidence. On later checkpoints, inspect changes and affected dependencies; do not reread unchanged artifacts already available in context.
2. Compare the implemented system and remaining plan with the applicable product requirements and acceptance evidence.
3. Identify requirements that are satisfied, partially satisfied, not started, blocked, contradicted, or no longer covered by the remaining plan.
4. Identify new evidence, invalidated assumptions, failed checks, architecture drift, emerging risks, duplicated work, obsolete tasks, and missing verification.
5. State whether the current plan remains suitable before selecting more implementation work.

Do not perform a ceremonial rewrite when the evidence supports the current plan. Record `NO_CHANGE` and proceed directly to sprint selection. The end of a sprint, the availability of a different design, or a general desire to improve the plan does not by itself justify `REPLAN`.

### 2. Apply the plan-change gate

The plan-change gate has four possible results: `NO_CHANGE`, `REPLAN`, `AWAITING_HUMAN_DECISION`, or `BLOCKED`. Start every review with `NO_CHANGE`. Do not edit the implementation plan before the gate result is recorded.

If evidence still supports the current plan, record only `NO_CHANGE`, the plan revision or checkpoint, the evidence checked (or `none_new`), and the next increment. Do not create empty change fields or a separate change-log entry.

For a proposed change, unresolved governed decision, or blocker, read `references/plan-change-gate.md` before editing. `REPLAN` requires the exact plan state, new grounded evidence, affected item, concrete problem with preserving it, smallest adequate response, authority, and verification impact. Preference, novelty, or speculative risk alone does not justify a change. Missing authority returns `AWAITING_HUMAN_DECISION`; insufficient evidence that prevents sound continuation returns `BLOCKED`.

Existing explicit authority counts. A new authorised product decision must be recorded in the requirements before adapting the plan. Do not treat an old PRD as overriding that decision, or infer permission for unrelated consequences.

### 3. Refactor the remaining plan

Only when `PLAN_CHANGE_GATE: REPLAN`, refactor the remaining plan:

1. Record the evidence and the assumption or dependency it changes.
2. Name the affected requirement IDs, phase IDs, tests, risks, and rollout or rollback commitments.
3. Record the previous plan, revised plan, rationale, authority, and verification impact in a `Plan Change Log`.
4. Preserve stable identifiers when their meaning remains the same. Give materially new work a new identifier.
5. Do not alter completed `[x]` or `[v]` history. Record obsolete remaining work as superseded and link it to the replacement rather than erasing it.
6. Recheck dependency order, walking-skeleton integrity, phase exit criteria, test levels, coverage expectations, and the canonical CI-equivalent gate.
7. Do not delete or weaken a test, assertion, acceptance criterion, coverage threshold, or failure-path check merely because the implementation made it difficult to satisfy.

Do not create a `Plan Change Log` entry for `NO_CHANGE`; record that gate result in the sprint record. For `AWAITING_HUMAN_DECISION` or `BLOCKED`, record the proposed delta and its consequences without editing the plan. Name the decision or condition that would permit another review.

### 4. Select the sprint

Select one coherent vertical increment from the current plan. Use the next work in dependency order unless risk reduction or learning value justifies a recorded reordering.

Create or update one sprint record using the project's existing convention. If none exists, create `SPRINT-<stable-id>.md` next to the implementation plan. Do not create a new tracking hierarchy only to imitate a project-management ceremony.

The sprint record must contain:

- sprint ID, state, goal, and applicable requirement and phase IDs;
- reviewed product baseline and implementation-plan paths;
- evidence and plan deltas considered at sprint entry;
- the compact `NO_CHANGE` checkpoint or a link to the full change/decision/blocker record;
- scope, non-scope, dependencies, and expected learning;
- bounded `[ ]` task checklist;
- changed behaviours and likely failure modes;
- selected test levels, tests to add or run, coverage expectations, and CI-equivalent command;
- verification and review checklist;
- sprint exit criteria and conditions that require an immediate review checkpoint.

A sprint must be small enough that its implementation, behavioural verification, integration checks, and review can reach one evidence-backed outcome before unrelated work begins. Do not use an arbitrary task count or simulated calendar duration as the boundary.

### 5. Build the sprint

For each selected task:

1. Use `$rb-implement-with-tests` for one bounded ordinary change or `$rb-tdd-scientific-code` for scientific or domain-sensitive work.
2. Supply the task goal, scope, non-scope, applicable requirements, relevant evidence, changed behaviour, failure modes, selected test levels, coverage expectations, and CI-equivalent checks.
3. Mark the task `[x]` only after implementation is complete. Leave it `[x]` until the separate sprint verification pass confirms the required behaviour.
4. If implementation reveals material new evidence, finish or safely stop the current bounded operation, record the evidence, and return to `review` before starting affected work.
5. Leave unresolved or blocked work `[ ]` and record the exact blocker.

### 6. Verify and review the sprint

After every sprint task is `[x]`:

1. Run a separate verification pass over every task and applicable product requirement.
2. Reuse focused evidence for unchanged code and environment. Rerun affected checks and add missing coverage where the combined change exposes a new failure boundary.
3. Confirm the appropriate automated evidence passes; retain `[x]` until the review below also passes. If automation is genuinely infeasible, record why, define the best executable or manual check, state the residual regression risk, and obtain explicit acceptance before `[v]`.
4. Run the closest available repository CI-equivalent command or the largest relevant affordable subset. Record every omitted check, its reason, and the residual risk.
5. Review the complete sprint diff for defects, integration gaps, scope drift, hidden fallbacks, and test weakening. Require independent sub-agent review for substantial, high-risk, or cross-cutting changes, or existing explicit gates; use `$rb-review-pr-or-diff` for that review. A small local change without such a gate may be reviewed inline. If required review cannot run, retain `[x]` and report the blocker. Mark `[v]` only after required review as well as tests passes.
6. Fix actionable findings, rerun affected checks, and re-review before accepting the sprint.
7. Treat flaky tests as defects. Do not rerun until green, skip, quarantine, weaken assertions, or lower thresholds merely to finish the sprint.

### 7. Close the sprint and choose the next transition

Return to `review` and record:

- delivered behaviour and affected requirement IDs;
- task, integration, coverage, CI-equivalent, and review evidence;
- new evidence and assumptions confirmed or invalidated;
- product-requirement coverage and remaining gaps;
- the plan-change gate result and plan deltas made or proposed;
- defects, omissions, blockers, and residual risks;
- the next state: `replan`, `sprint_ready`, `awaiting_human_decision`, `blocked`, or `complete`.

Set the project to `complete` only when every in-scope requirement has current acceptance evidence, every approved deferral is recorded, all required plan work is verified, the CI-equivalent and final review gates have passed, and rollout, rollback, documentation, operational handoff, and residual-risk conditions are satisfied where applicable.

Complete one sprint and its review checkpoint before beginning another. Continue automatically only when the human's recorded authority covers another sprint and no governed decision is pending. If either condition is false, hand the checkpoint to the human before continuing.

## Checklist Convention

Use these task states in sprint and phase files:

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Do not declare a sprint or phase complete until every required task is `[v]`, the applicable product requirements are reconciled, phase or sprint integration and CI-equivalent checks pass, and the review+fix cycle is complete.

## Optional Constrained Route

- Read the implementation plan's `Execution Route`. A missing route behaves as `standard`; `undecided` also uses `standard`; never select `constrained` implicitly.
- The first-release constrained route accepts only unchanged, statically verifiable phases whose requirements and checks use `static_file_state::<description>`. It cannot execute tests, builds, linting, type checking, application commands, or other runtime-dependent acceptance checks.
- Before constrained work, read and follow `$rb-execute-plan` and its `references/constrained-execution.md` for readiness, compilation, assessment, unchanged-bundle execution, verification, and phase-status rules. A sprint does not relax those gates.
- Treat one verified constrained phase as one sprint increment. Perform adaptive review only before a phase is compiled or after it reaches verified and the coordinator handoff is recorded.
- Any proposed change to the current compiled or assessed phase invalidates that constrained continuation. Do not edit, relabel, or execute the bundle. Stop for a new approved plan and route decision, then compile and assess the changed phase as a new bundle if `constrained` remains selected.
- A plan change after a rejected or incomplete constrained run does not make that run executable. Preserve its hashes, lifecycle state, evidence, and required human decision in the canonical external working-diary checkpoint.

## Continuity

Use `$rb-working-diary` when the sprint cycle spans sessions, produces substantial evidence or decisions, or changes the active implementation plan. Record the authoritative PRD and plan paths, current sprint state, requirement coverage, accepted plan deltas, test and CI evidence, unresolved decisions, route, and exact next action. A diary record preserves context; it does not grant authority for another sprint or a governed decision.

## Output

At a checkpoint, report the delivered behaviour, requirements coverage, verification/review outcomes, material risks or decisions, and next action. Link the sprint record. For `NO_CHANGE`, include only the compact checkpoint; for other gate results, link the full record and explain its consequence. Do not reproduce unchanged inventories or empty fields.
