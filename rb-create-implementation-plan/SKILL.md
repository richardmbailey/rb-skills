---
name: "rb-create-implementation-plan"
description: "Use to turn an idea or rough feature request into a practical implementation plan with goals, constraints, phased work, risks, success criteria, and validation approach."
---

# /rb:create-implementation-plan - turn an idea into a practical implementation plan

## Procedure

1. Restate the idea.
2. Ask clarifying questions if needed.
3. Read `CONTEXT.md` if present; otherwise note the missing project context and continue.
4. If the idea involves multiple LLM agents, also use `$rb-multi-agent-systems` to define stack choice, agent/tool boundaries, state, observability, evals, retrieval, provider routing, and durability requirements.
5. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, implementation phases, and validation.
6. When the plan needs granular phase checklists, walking-skeleton sequencing, execution tracking, or verification gates, also use `$rb-execute-plan` for the phase-level plan.
7. Update `$rb-working-diary` with durable planning decisions, risks, and open questions when the implementation-planning work is substantial.
8. Produce an implementation plan using the bundled `assets/IMPLEMENTATION_PLAN.md` structure. Prefer a project-specific planning template if the human or repository provides one.
