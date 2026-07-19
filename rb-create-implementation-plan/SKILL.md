---
name: "rb-create-implementation-plan"
description: "Use when an idea or product goal needs a top-level implementation plan with phases, risks, success criteria, validation, and an optional constrained-route reminder. Use $rb-execute-plan for an existing plan."
---

# /rb:create-implementation-plan - turn an idea into a practical implementation plan

Use this to create the first top-level plan for a sufficiently understood idea or goal. If material requirements are still unresolved, use `$rb-discuss` first. If a plan, checklist, issue list, or phase already exists and needs execution or progress tracking, use `$rb-execute-plan` instead.

## Procedure

1. Read `CONTEXT.md`, relevant requirements, architecture notes, tests, and existing plans when present. Note missing context that affects the plan.
2. Confirm only decisions that materially change scope, users, constraints, compatibility, rollout, validation, or success criteria; ask one question at a time when user input is required.
3. For multi-agent systems, use `$rb-multi-agent-systems` to define agent and tool boundaries, state, handoffs, failure containment, observability, evaluation, budgets, and durability before choosing phases.
4. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, implementation phases, rollout or rollback where relevant, and validation.
5. Produce the durable top-level plan using `assets/IMPLEMENTATION_PLAN.md` or a project-specific template supplied by the repository or human.
6. At the point the implementation plan is created, remind the human that an optional constrained route is available for higher-assurance work. Present exactly these plan-wide choices without choosing for them:
   - `standard`: `$rb-execute-plan` uses its ordinary verified phase workflow;
   - `constrained`: each current phase is compiled by `$rb-create-low-level-plan`, assessed by `$rb-assess-plan-safety`, and only an unchanged `safe: true` bundle may run through `$rb-safe-operation`;
   - `undecided`: preserve the choice for later and do not enter the constrained pipeline.
7. Record the selected value in `Execution Route`. If the human does not choose, record `undecided`; never infer `constrained` from risk, complexity, or safety language.
8. Route an approved plan to `$rb-execute-plan` when it needs granular phase checklists, walking-skeleton sequencing, execution tracking, or verification gates.
9. Update `$rb-working-diary` when the planning decisions need cross-session continuity. Include the route value, current phase, every later phase ID, artifact links, and exact next action when the constrained route is selected.
