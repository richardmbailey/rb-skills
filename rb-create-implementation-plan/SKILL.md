---
name: "rb-create-implementation-plan"
description: "Use to create the first top-level implementation plan with phases, risks, success criteria, testing architecture, validation, and optional constrained route. For existing plans, use $rb-execute-plan or $rb-sprint."
---

# /rb:create-implementation-plan - turn an idea into a practical implementation plan

Use this to create the first top-level plan for a sufficiently understood idea or goal. If the user needs a durable product requirements document before implementation planning, use `$rb-create-prd` first. If material requirements are still unresolved and no PRD was requested, use `$rb-discuss` first. If a plan, checklist, issue list, or phase already exists, use `$rb-execute-plan` for linear execution or `$rb-sprint` for adaptive delivery instead.

## Task Status Convention

Every implementation plan created by this skill must use these exact task states:

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Prefix every actionable implementation task in every phase with one of these states. Set newly planned work to `[ ]`. Do not mark new work `[x]` or `[v]` merely because the plan describes it. Use `[x]` only for work that is already implemented and has supporting evidence. Use `[v]` only for work that has satisfied the selected delivery workflow's verification gate. Record whether independent review is required by the selected workflow, the change's risk, or an existing project gate.

Include the three-state legend in the generated plan. Apply the convention when using the bundled template, a project-specific template, or a human-supplied template. Headings, goals, non-goals, explanatory notes, risks, and success criteria do not need task states unless they are also actionable implementation tasks.

## Procedure

1. Read `CONTEXT.md`, relevant requirements, architecture notes, tests, coverage configuration, CI or pre-commit workflows, and existing plans when present. Note missing context that affects the plan.
2. Resolve only missing decisions that materially change scope, users, constraints, compatibility, rollout, validation, testing, or success criteria. Use known answers and existing authority; bundle independent questions when that reduces delay.
3. For systems with multiple LLM agents, agentic workflows, or orchestration layers, use `$rb-multi-agent-systems` to choose the simplest sufficient control model and define agent and tool boundaries, state, handoffs, failure containment, observability, evaluation, budgets, durability, and the required orchestration test matrix before choosing phases.
4. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, implementation phases, rollout or rollback where relevant, and validation. Give every phase a goal, dependencies, a status-marked task list, verification checks, and exit criteria.
5. Define the testing architecture at the top level before implementation details harden:
   - unit or property tests for local logic and invariants;
   - component and integration boundaries such as databases, files, queues, networks, frameworks, solvers, and external services;
   - contract tests for public APIs, schemas, events, tools, and compatibility promises;
   - migration and rollback tests where existing data or state changes;
   - end-to-end tests for critical user or operational workflows;
   - scientific, stochastic, performance, security, concurrency, and recovery checks where those risks are material;
   - fixture and test-data strategy, including trusted provenance and secret-free representative data;
   - coverage expectations based on changed behaviours and existing project thresholds rather than a new arbitrary percentage;
   - the canonical CI-equivalent completion command and any release or rollback validation.
6. Produce the durable top-level plan using `assets/IMPLEMENTATION_PLAN.md` or a project-specific template supplied by the repository or human. Include the three-state legend and prefix every actionable implementation task with `[ ]`, `[x]`, or `[v]`; do not emit an unmarked implementation task list. Omit irrelevant template sections and reuse existing requirements and test records by reference.
7. Record `Execution Route: standard` unless the human explicitly selects `constrained` or asks to leave the route `undecided`. A missing or `undecided` route uses standard execution. Do not interrupt ordinary planning to present an unused specialist route; never infer `constrained` from risk or safety language.
8. Only when constrained execution is requested or being compared, read `references/constrained-route.md`. It describes the constrained static-only route, its optional path policy, and why it cannot execute tests, builds, linting, typing, or application commands.
9. Route an approved plan to `$rb-execute-plan` when the human wants linear phase execution. Route it to `$rb-sprint` when the human wants repeated bounded delivery increments with PRD reconciliation and evidence-driven changes to remaining plan work. Both workflows own granular task selection, testing strategy, execution tracking, CI-equivalent checks, and verification gates.
10. Update `$rb-working-diary` when the planning decisions need cross-session continuity. Include the route value, current phase, every later phase ID, artifact links, test strategy, constrained verification-mode limitation, and exact next action when the constrained route is selected.

Continue into already-authorised execution after the plan is ready. Ask for approval only when required by an explicit review gate or a material decision beyond the existing request.

## Completion Check

Before handing off a newly created plan, confirm that:

- the plan contains the exact `[ ]` planned, `[x]` implemented, and `[v]` verified legend;
- every actionable implementation task in every phase has exactly one state marker;
- every newly planned task is `[ ]`;
- any carried-forward `[x]` or `[v]` state cites the evidence that justifies it;
- the plan names the delivery workflow that owns later state transitions and verification.
