---
name: "rb-project-language"
description: "Use when a project needs shared vocabulary or CONTEXT.md updated with domain terms, acronyms, units, invariants, assumptions, or modelling concepts. Do not use for general repository orientation without a terminology or domain-context need."
---

# RB Project Language

## Purpose

Use this to build or update `CONTEXT.md`, especially in scientific, modelling, or domain-heavy code.

This skill owns the shared vocabulary and domain-context artifact. It may document established agent roles, tools, states, and handoffs, but it does not design or review an orchestration architecture.

## Procedure

1. Inspect docs and source code.
2. Extract domain terms, variables, units, and recurring concepts.
3. Identify ambiguous or overloaded terms.
4. Ask the human one question at a time to resolve important ambiguity.
5. If the project includes multiple LLM agents, capture established agent roles, tool boundaries, handoffs, states, structured outputs, retrieval, observability, evaluation, and provider-routing terms. Do not select `$rb-multi-agent-systems` merely because the project has multiple agents. Use `$rb-multi-agent-systems` when the human also asks to design, review, or debug the orchestration architecture.
6. Update `$rb-working-diary` with durable vocabulary and context decisions when the work is substantial.
7. Update or draft `CONTEXT.md`.

## Capture for scientific code

- state variables
- parameters
- units
- dimensions
- coordinate systems
- sign conventions
- boundary conditions
- forcing terms
- source and sink terms
- stochastic assumptions
- random seed policy
- conservation or balance laws
- benchmark cases
- observation operators
- calibration and validation assumptions
- data provenance
- trusted outputs
