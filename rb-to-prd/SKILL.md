---
name: "rb-to-prd"
description: "Use to turn an idea or rough feature request into a practical PRD with goals, constraints, risks, success criteria, and validation approach."
---

# /rb:to-prd — turn an idea into a practical PRD

## Procedure

1. Restate the idea.
2. Ask clarifying questions if needed.
3. Read `CONTEXT.md` if present; otherwise note the missing project context and continue.
4. If the idea involves multiple LLM agents, also use `$rb-multi-agent-systems` to define stack choice, agent/tool boundaries, state, observability, evals, retrieval, provider routing, and durability requirements.
5. Define goals, non-goals, users, requirements, constraints, assumptions, risks, success criteria, and validation.
6. Update `$rb-working-diary` with durable planning decisions, risks, and open questions when the PRD work is substantial.
7. Produce a PRD using the bundled `assets/PRD.md` structure. Prefer a project-specific PRD template if the human or repository provides one.
