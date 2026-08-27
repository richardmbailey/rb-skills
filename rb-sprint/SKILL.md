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

If no authoritative requirements artifact exists, do not infer product intent from the implementation plan. Use `$rb-discuss` for unresolved behaviour or `$rb-create-prd` when durable product requirements are needed. If the implementation plan is missing, use `$rb-create-implementation-plan`.

Apply the artifacts in this order when they conflict:

1. repository and current human instructions;
2. the authoritative PRD or equivalent requirements artifact;
3. the approved implementation plan;
4. the current sprint record.

The repository implementation and test results describe observed state. They provide evidence for changing a plan, but they do not override an approved requirement. A lower-level artifact must not silently change a higher-level artifact.

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
- For text-processing work, separate deterministic handling of stable syntax from LLM-backed judgement about natural-language meaning.

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

1. Read the authoritative requirements, current implementation plan, active phase files, latest sprint record, relevant diary or handoff, repository instructions, Git state, implementation, and test evidence.
2. Compare the implemented system and remaining plan with the applicable product requirements and acceptance evidence.
3. Identify requirements that are satisfied, partially satisfied, not started, blocked, contradicted, or no longer covered by the remaining plan.
4. Identify new evidence, invalidated assumptions, failed checks, architecture drift, emerging risks, duplicated work, obsolete tasks, and missing verification.
5. State whether the current plan remains suitable before selecting more implementation work.

Do not perform a ceremonial rewrite when the evidence supports the current plan. Record `NO_CHANGE` and proceed directly to sprint selection. The end of a sprint, the availability of a different design, or a general desire to improve the plan does not by itself justify `REPLAN`.

### 2. Apply the plan-change gate

The plan-change gate has four possible results: `NO_CHANGE`, `REPLAN`, `AWAITING_HUMAN_DECISION`, or `BLOCKED`. Start every review with `NO_CHANGE`. Do not edit the implementation plan before the gate result is recorded.

First classify the proposed response to the evidence:

- **Execution refinement:** a local implementation detail changes without altering product behaviour, public contracts, phase intent, dependencies, risk, or acceptance evidence.
- **Plan adaptation:** remaining tasks or phases are split, combined, reordered, added, superseded, or given a different technical approach while the approved product intent and material risk boundary remain unchanged.
- **Governed technical decision:** the proposal adds a production dependency, replaces an established framework or service, changes architecture boundaries, introduces a migration, changes compatibility or rollback, changes external side effects, or changes a recorded security, privacy, cost, performance, operations, or delivery-risk commitment.
- **Product decision:** the proposal changes requirements, user-visible behaviour, scope, non-goals, users, permissions, data policy, success measures, acceptance evidence, rollout authority, or accepted product risk.
- **Blocker:** required evidence, authority, environment, dependency, or a credible implementation route is absent.

Then create one gate record with these fields:

```text
PLAN_CHANGE_GATE: NO_CHANGE | REPLAN | AWAITING_HUMAN_DECISION | BLOCKED
PLAN_STATE: <implementation-plan path and current revision or sprint-checkpoint identifier>
CHANGE_CLASS: none | execution_refinement | plan_adaptation | governed_technical_decision | product_decision | blocker
EVIDENCE: <one or more exact tests, reviews, experiments, repository observations, operational observations, or explicit human statements; or none_new>
AFFECTED_PLAN_ITEM: <stable task, phase, assumption, dependency, constraint, risk, or verification identifier>
CONTRADICTION: <how the evidence invalidates, blocks, satisfies, or makes that item obsolete>
UNCHANGED_CONSEQUENCE: <specific requirement, constraint, dependency, ordering, duplication, executability, or verification problem caused by preserving it>
SMALLEST_RESPONSE: <why local execution refinement is sufficient, or why the smallest adequate response requires a plan delta>
AUTHORITY: <within existing authority | explicit approval required | authority unavailable>
VERIFICATION_IMPACT: <tests, checks, exit criteria, coverage, rollout, or rollback affected>
```

For `NO_CHANGE`, set `CHANGE_CLASS: none` or `execution_refinement`, use `EVIDENCE: none_new` when no new evidence exists, and set unsupported change fields to `none`. Do not invent an affected item, contradiction, or unchanged consequence to make the record appear complete.

Set `PLAN_CHANGE_GATE: REPLAN` only when all of these conditions are established:

1. `PLAN_STATE` identifies the exact plan state under review. `EVIDENCE` names new externally grounded evidence or evidence that became newly relevant after the current plan or last plan change. Agent preference, reflection, generic best practice, novelty, stylistic consistency, and a speculative future risk are not evidence.
2. `AFFECTED_PLAN_ITEM` identifies an exact current plan item. `CONTRADICTION` explains how the evidence contradicts, invalidates, blocks, already satisfies, or makes that item obsolete. An alternative that merely appears cleaner, more elegant, or equally viable does not pass.
3. `UNCHANGED_CONSEQUENCE` identifies a concrete problem with preserving the item: failure to satisfy a named requirement or constraint, an invalid dependency or order, duplicated or already completed work, work shown to be non-executable, or a missing verification path. A possible improvement without one of these consequences does not pass.
4. `SMALLEST_RESPONSE` shows that an execution refinement cannot resolve the problem and that the proposed plan delta is the smallest adequate response.
5. `AUTHORITY` confirms that the delta remains within the approved product and risk boundaries. `VERIFICATION_IMPACT` identifies every affected acceptance or verification commitment.

If any required field is missing, unsupported, or uncertain, do not return `REPLAN`:

- Return `NO_CHANGE` when the current plan remains supported. Preserve it and continue to sprint selection.
- Return `AWAITING_HUMAN_DECISION` when the evidence supports a governed technical decision or product decision. Do not edit the governed artifact or begin affected implementation.
- Return `BLOCKED` when a credible concern makes affected work unsafe or unsound to continue but the evidence, authority, environment, dependency, or implementation route is insufficient to choose a delta.

Use the same result when the same `EVIDENCE` is reviewed against the same `PLAN_STATE`. Evidence already reflected in the current plan does not justify another change. Record `NO_CHANGE` unless new evidence or a changed plan state changes the gate result.

Invocation of `$rb-sprint` authorises execution refinements under `NO_CHANGE` because they do not edit the plan. It authorises plan adaptations only after the gate returns `REPLAN` within the approved product and risk boundaries. A governed technical decision or product decision requires explicit human approval. If the decision authority is absent or unclear, return `AWAITING_HUMAN_DECISION`. Route product decisions through `$rb-discuss` or `$rb-create-prd` according to whether the project needs discussion or a durable requirements change.

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
- the complete plan-change gate record and result;
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
2. Confirm or rerun focused behavioural tests. Add missing integration, contract, migration, end-to-end, negative, boundary, concurrency, recovery, scientific, or agent-eval coverage where the likely failure crosses those boundaries.
3. Mark a task `[v]` only after the appropriate automated evidence passes. If automation is genuinely infeasible, record why, define the best executable or manual check, state the residual regression risk, and obtain explicit acceptance before `[v]`.
4. Run the closest available repository CI-equivalent command or the largest relevant affordable subset. Record every omitted check, its reason, and the residual risk.
5. Review the complete sprint diff for defects, regressions, architecture drift, hidden fallback behaviour, test weakening, coverage gaps, documentation gaps, and unresolved assumptions. Use `$rb-review-pr-or-diff` for substantial, high-risk, or cross-cutting changes.
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

- Read the implementation plan's `Execution Route`. A missing route behaves as `standard`; `undecided` requires one bounded human choice; never select `constrained` implicitly.
- The first-release constrained route accepts only unchanged, statically verifiable phases whose requirements and checks use `static_file_state::<description>`. It cannot execute tests, builds, linting, type checking, application commands, or other runtime-dependent acceptance checks.
- Before constrained work, follow the readiness, compilation, independent assessment, unchanged-bundle execution, verification, checkpoint, and phase-status rules in `$rb-execute-plan`. A sprint does not relax those gates.
- Treat one verified constrained phase as one sprint increment. Perform adaptive review only before a phase is compiled or after it reaches verified and the coordinator handoff is recorded.
- Any proposed change to the current compiled or assessed phase invalidates that constrained continuation. Do not edit, relabel, or execute the bundle. Stop for a new approved plan and route decision, then compile and assess the changed phase as a new bundle if `constrained` remains selected.
- A plan change after a rejected or incomplete constrained run does not make that run executable. Preserve its hashes, lifecycle state, evidence, and required human decision in the canonical external working-diary checkpoint.

## Continuity

Use `$rb-working-diary` when the sprint cycle spans sessions, produces substantial evidence or decisions, or changes the active implementation plan. Record the authoritative PRD and plan paths, current sprint state, requirement coverage, accepted plan deltas, test and CI evidence, unresolved decisions, route, and exact next action. A diary record preserves context; it does not grant authority for another sprint or a governed decision.

## Output

At every sprint checkpoint, return:

- current sprint ID and state;
- PRD or requirements alignment, including satisfied and uncovered requirement IDs;
- evidence reviewed and assumptions changed;
- the complete plan-change gate record, including its `NO_CHANGE`, `REPLAN`, `AWAITING_HUMAN_DECISION`, or `BLOCKED` result;
- accepted and proposed plan deltas with authority status;
- sprint goal, tasks, and `[ ]`, `[x]`, or `[v]` status;
- focused, integration, contract, end-to-end, coverage, CI-equivalent, and review evidence as applicable;
- checks not run and residual risks;
- blockers or decisions required from the human;
- next state and exact next action.
