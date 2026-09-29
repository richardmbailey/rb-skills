# Evidence and authority for a plan change

Read when a plan change, unresolved governed decision, or blocker is proposed.

First classify the proposed response to the evidence:

- **Execution refinement:** a local implementation detail changes without altering product behaviour, public contracts, phase intent, dependencies, risk, or acceptance evidence.
- **Plan adaptation:** remaining tasks or phases are split, combined, reordered, added, superseded, or given a different technical approach while the approved product intent and material risk boundary remain unchanged.
- **Governed technical decision:** the proposal adds a production dependency, replaces an established framework or service, changes architecture boundaries, introduces a migration, changes compatibility or rollback, changes external side effects, or changes a recorded security, privacy, cost, performance, operations, or delivery-risk commitment.
- **Product decision:** the proposal changes requirements, user-visible behaviour, scope, non-goals, users, permissions, data policy, success measures, acceptance evidence, rollout authority, or accepted product risk.
- **Blocker:** required evidence, authority, environment, dependency, or a credible implementation route is absent.

For a proposed plan change, unresolved governed decision, or blocker, create one gate record with these fields:

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

For `NO_CHANGE`, use the compact checkpoint in the skill. Do not populate unused change fields or invent an affected item, contradiction, or unchanged consequence.

Set `PLAN_CHANGE_GATE: REPLAN` only when all of these conditions are established:

1. `PLAN_STATE` identifies the exact plan state under review. `EVIDENCE` names new externally grounded evidence or evidence that became newly relevant after the current plan or last plan change. Agent preference, reflection, generic best practice, novelty, stylistic consistency, and a speculative future risk are not evidence.
2. `AFFECTED_PLAN_ITEM` identifies an exact current plan item. `CONTRADICTION` explains how the evidence contradicts, invalidates, blocks, already satisfies, or makes that item obsolete. An alternative that merely appears cleaner, more elegant, or equally viable does not pass.
3. `UNCHANGED_CONSEQUENCE` identifies a concrete problem with preserving the item: failure to satisfy a named requirement or constraint, an invalid dependency or order, duplicated or already completed work, work shown to be non-executable, or a missing verification path. A possible improvement without one of these consequences does not pass.
4. `SMALLEST_RESPONSE` shows that an execution refinement cannot resolve the problem and that the proposed plan delta is the smallest adequate response.
5. `AUTHORITY` confirms that the delta remains within the approved product and risk boundaries. `VERIFICATION_IMPACT` identifies every affected acceptance or verification commitment.

If any required field is missing, unsupported, or uncertain, do not return `REPLAN`:

- Return `NO_CHANGE` when the current plan remains supported. Preserve it and continue to sprint selection.
- Return `AWAITING_HUMAN_DECISION` when a governed technical decision or product decision still needs authority or material clarification. Do not edit the governed artifact or begin affected implementation.
- Return `BLOCKED` when a credible concern makes affected work unsafe or unsound to continue but the evidence, authority, environment, dependency, or implementation route is insufficient to choose a delta.

Use the same result when the same `EVIDENCE` is reviewed against the same `PLAN_STATE`. Evidence already reflected in the current plan does not justify another change. Record `NO_CHANGE` unless new evidence or a changed plan state changes the gate result.

Invocation of `$rb-sprint` authorises execution refinements under `NO_CHANGE` because they do not edit the plan. It authorises plan adaptations only after the gate returns `REPLAN` within the approved product and risk boundaries. A governed technical decision or product decision requires explicit human approval, which may already be supplied by the current request. Record an authorised requirements change before evaluating its plan delta. Existing authority does not bypass platform permissions or exact constrained-runtime confirmations. If the decision authority is absent or unclear, return `AWAITING_HUMAN_DECISION`. Route product decisions through `$rb-discuss` or `$rb-create-prd` according to whether the project needs discussion or a durable requirements change.
