---
name: "rb-architecture-review"
description: "Use when the user wants an architectural critique of a codebase, including boundaries, coupling, duplication, hidden assumptions, and improvement opportunities. For neutral orientation to an unfamiliar repository, use $rb-explain-codebase."
---

# /rb:architecture - architecture review

## Purpose

Inspect the codebase for structural problems and opportunities for clearer boundaries.

## Procedure

1. Read `AGENTS.md` and `CONTEXT.md` if present; otherwise note missing project context and continue.
2. Inspect repository structure.
3. Identify major modules and responsibilities.
4. Look for shallow modules, unclear names, duplication, implicit dependencies, hidden scientific assumptions, poor test seams, circular imports, scattered configuration, unnecessary coupling, and ownership gaps.
5. Identify candidate deeper modules with simple interfaces and testable contracts only when the evidence supports a change.
6. Check whether proposed architecture changes preserve current behavior, public APIs, data contracts, deployment constraints, and user workflows.
7. If the architecture includes multiple LLM agents, agentic state machines, or stateful orchestration layers, also use `$rb-multi-agent-systems`.
8. Use `$rb-working-diary` only when its trigger conditions apply and the human has authorized durable continuity. Do not write diary entries for an isolated one-turn review.
9. If actionable risks exist, produce a prioritised refactoring plan. If no actionable architecture risks are supported by evidence, say so and omit the plan.

## Required behaviour

- Do not refactor immediately unless asked.
- Distinguish architecture risks from stylistic preferences.
- Do not invent risks or refactoring work to fill the requested output shape.
- Prefer the simplest architecture that expresses the required behaviour; require evidence before escalating from explicit state machines to dynamic planning or orchestration.
- Prefer incremental refactors with tests over large rewrites.
- Preserve existing project conventions unless a proposed change has a clear payoff.

## Output

- current architecture map: major modules, responsibilities, data/control flow
- top risks, prioritized by impact and likelihood, or a clear statement that no actionable risks were found
- proposed refactoring sequence with small safe increments, only when actionable work exists
- tests/checks needed to protect each proposed refactor
- tradeoffs, non-goals, and open questions
