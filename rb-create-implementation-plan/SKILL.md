---
name: "rb-create-implementation-plan"
description: "Use when an idea, rough feature request, or product goal needs a new top-level implementation plan covering goals, constraints, phases, risks, success criteria, and validation. Do not use to carry out or track an existing plan; use $rb-execute-plan."
---

# /rb:create-implementation-plan - turn an idea into a practical implementation plan

Use this to create the first top-level plan for a sufficiently understood idea or goal. If material requirements are still unresolved, use `$rb-discuss` first. If a plan, checklist, issue list, or phase already exists and needs execution or progress tracking, use `$rb-execute-plan` instead.

## Procedure

1. Read `CONTEXT.md`, relevant requirements, architecture notes, tests, and existing plans when present. Note missing context that affects the plan.
2. Confirm only decisions that materially change scope, users, constraints, compatibility, rollout, validation, or success criteria; ask one question at a time when user input is required.
3. For multi-agent systems, use `$rb-multi-agent-systems` to define agent and tool boundaries, state, handoffs, failure containment, observability, evaluation, budgets, and durability before choosing phases.
4. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, implementation phases, rollout or rollback where relevant, and validation.
5. Produce the durable top-level plan using `assets/IMPLEMENTATION_PLAN.md` or a project-specific template supplied by the repository or human.
6. Route an approved plan to `$rb-execute-plan` when it needs granular phase checklists, walking-skeleton sequencing, execution tracking, or verification gates.
7. Update `$rb-working-diary` only when the planning decisions need cross-session continuity.
