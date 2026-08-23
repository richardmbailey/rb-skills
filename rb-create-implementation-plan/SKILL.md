---
name: "rb-create-implementation-plan"
description: "Use when an idea or product goal needs a top-level implementation plan with phases, risks, success criteria, testing architecture, validation, and an optional constrained-route reminder. Use $rb-execute-plan for an existing plan."
---

# /rb:create-implementation-plan - turn an idea into a practical implementation plan

Use this to create the first top-level plan for a sufficiently understood idea or goal. If the user needs a durable product requirements document before implementation planning, use `$rb-create-prd` first. If material requirements are still unresolved and no PRD was requested, use `$rb-discuss` first. If a plan, checklist, issue list, or phase already exists and needs execution or progress tracking, use `$rb-execute-plan` instead.

## Procedure

1. Read `CONTEXT.md`, relevant requirements, architecture notes, tests, coverage configuration, CI or pre-commit workflows, and existing plans when present. Note missing context that affects the plan.
2. Confirm only decisions that materially change scope, users, constraints, compatibility, rollout, validation, testing, or success criteria; ask one question at a time when user input is required.
3. For systems with multiple LLM agents, agentic workflows, or orchestration layers, use `$rb-multi-agent-systems` to choose the simplest sufficient control model and define agent and tool boundaries, state, handoffs, failure containment, observability, evaluation, budgets, durability, and the required orchestration test matrix before choosing phases.
4. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, implementation phases, rollout or rollback where relevant, and validation.
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
6. Produce the durable top-level plan using `assets/IMPLEMENTATION_PLAN.md` or a project-specific template supplied by the repository or human.
7. At the point the implementation plan is created, remind the human that an optional constrained route is available for higher-assurance work. Present exactly these plan-wide choices without choosing for them:
   - `standard`: `$rb-execute-plan` uses its ordinary verified phase workflow and can run the repository's executable tests and CI-equivalent checks;
   - `constrained`: the constrained static-only route compiles each current phase with `$rb-create-low-level-plan`, assesses it with `$rb-assess-plan-safety`, and permits only an unchanged `safe: true` bundle to run through `$rb-safe-operation`; the first-release constrained capability set cannot execute tests, builds, linting, typing, or application commands, so do not select it for phases whose acceptance depends on runtime behaviour;
   - `undecided`: preserve the choice for later and do not enter the constrained pipeline.
8. When `constrained` is selected, flag that low-level success criteria and verifier checks must compile to the closed `<mode>::<description>` syntax and that the first release accepts only `static_file_state::<description>`. Runtime-dependent phases must remain on or return to `standard`.
9. Record the selected value in `Execution Route`. If the human does not choose, record `undecided`; never infer `constrained` from risk, complexity, or safety language.
10. When `constrained` is selected or left as an option, also remind the human that repository-owned path restrictions are optional. `$rb-create-safe-operation-policy` can translate ordinary language such as “do not read or write x.txt” into a previewed, confirmed fixed policy. Do not invent or persist a policy from safety-related subject matter alone.
11. Route an approved plan to `$rb-execute-plan` when it needs granular phase checklists, walking-skeleton sequencing, test-level selection, execution tracking, CI-equivalent checks, or verification gates.
12. Update `$rb-working-diary` when the planning decisions need cross-session continuity. Include the route value, current phase, every later phase ID, artifact links, test strategy, constrained verification-mode limitation, and exact next action when the constrained route is selected.
