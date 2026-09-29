---
name: "rb-execute-plan"
description: "Use for linear execution of existing plans under standard conditions by default, with automated behavioural tests, risk-based review, CI-equivalent checks, and verified tasks. Use $rb-sprint for recurring PRD alignment or replanning."
---

# RB Execute Plan

Own sequencing, phase status, and completion evidence for an existing multi-step plan. Use `$rb-create-implementation-plan` for a new plan, `$rb-sprint` for authorised recurring PRD reconciliation and replanning, and `$rb-implement-with-tests` directly for one bounded change.

## Authority and route

- Execute under the `standard` route unless the human explicitly specifies another route in the current request or approved plan. Treat a missing or `undecided` route as `standard`. Never infer `constrained` from risk, complexity, or safety language.
- Continue through the work covered by the current request or recorded authority. Ask only for a missing material decision, an explicitly required approval, or work beyond that authority.
- Follow the approved phase and task order. Make a local ordering correction only when a dependency or executable verification requirement makes the next task impossible; record the evidence. Preference or learning value alone does not justify reordering this linear plan.
- If the strategy is no longer credible, stop affected work and report the evidence. Enter `$rb-sprint` only when adaptive work is authorised. Do not silently alter product scope, architecture commitments, acceptance, permissions, migrations, rollout, or accepted risk.
- If `constrained` is selected, read `references/constrained-execution.md` before any phase work and follow that procedure instead of the standard loop below. It is static-only, cannot run behavioural checks, and retains exact authority, assessment, independent review, and checkpoint requirements.

## Prepare the next phase

1. Read the approved plan, repository instructions, relevant requirements, worktree state, and current verification evidence. Preserve unrelated user changes.
2. Prefer a walking-skeleton approach: a thin runnable vertical slice before deeper implementation. Apply this when making an incomplete phase executable; do not redesign an already approved sequence to enforce a preference.
3. Reuse existing phase files or checklists. Create a separate phase file only when detail would make the overview difficult to use. Record the goal, scope, dependencies, actionable tasks, acceptance criteria, and relevant test/CI commands once.
4. For multi-agent architecture decisions, use `$rb-multi-agent-systems`. For text processing, distinguish structured parsing from validated semantic methods; do not substitute brittle heuristics for meaning-dependent acceptance.
5. Select tests at the failure boundary: local logic, component interaction, public contract, migration, critical workflow, or scientific/stochastic behaviour as relevant. Include negative and failure cases for changed decisions and side effects. Preserve existing coverage thresholds; do not impose a new arbitrary percentage.
6. Establish the review requirement before implementation. Require an independent sub-agent review for substantial, high-risk, or cross-cutting changes, or when the approved plan or repository explicitly requires one. Examples include security/permission changes, migrations, public-contract changes, and changes spanning independently owned components. For a small local change without such a gate, inline review is sufficient. Record which applies and why.

## Task states

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Mark `[x]` after inspecting the completed implementation. Mark `[v]` only after the applicable behavioural evidence and review pass. If independent review is required, mark `[v]` only after an independent sub-agent returns a favourable verdict for that task; the reviewer must not have implemented it. If that reviewer is unavailable, preserve `[x]` and report the blocker rather than lowering the gate.

If needed behavioural automation is infeasible, record the reason, alternative check, and residual risk; obtain explicit acceptance of that exception before `[v]`. Non-executable artifact changes use relevant artifact checks rather than invented behavioural tests. A successful lint, import, build, smoke check, or source inspection does not establish runtime behaviour.

## Standard execution loop

1. Select the next task in the approved order. Supply its scope, acceptance, relevant context, and required evidence to `$rb-implement-with-tests` or `$rb-tdd-scientific-code`. The implementation skill owns editing, focused testing, and task-level review; this skill owns plan status.
2. Inspect the returned changes and evidence. Record `[x]`, test outcomes, and unresolved findings. Do not accept a completion statement without its supporting artifact or result.
3. Review the phase's combined behaviour when its tasks are implemented. Reuse current passing task evidence; rerun only when later edits, changed fixtures/environment, or unresolved failures can invalidate it. Add missing integration or contract checks where the combined change exposes a new failure boundary.
4. Run the closest available repository CI-equivalent command, or the largest relevant affordable subset. Record omitted checks, their reasons, and residual risk. Do not repeat an unchanged successful suite just to create another checkpoint.
5. Review the complete diff for actionable defects, integration gaps, scope drift, hidden fallbacks, and test weakening. For required independent review, give a fresh reviewer the requirements, scoped diff, test evidence, and known limits. One review may cover the phase and return task-specific verdicts; do not require separate agents for each task.
6. Fix in-scope findings, rerun affected checks, and re-review material fixes. If a fix changes a verified task, return that task to `[x]` until its affected evidence and required review pass again. Retain failures and their diagnostics; do not weaken tests or rerun intermittent failures until green.
7. Mark supported tasks `[v]`. Complete the phase only when every required task is `[v]`, exit criteria are met, and applicable integration, CI-equivalent, and review gates pass. Preserve explicit release and deployment approvals.
8. Continue to the next authorised phase. At meaningful checkpoints, use `$rb-working-diary` when the work needs continuity. Record evidence and next action without copying the whole plan.

## Output

Report delivered behaviour, phase/task status, verification and review outcomes, omitted checks, residual risks, and the next action. Link detailed evidence instead of reproducing it. Do not invent findings, artifacts, or approvals to fill a template.
