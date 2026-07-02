---
name: "rb-architecture-review"
description: "Use to inspect a codebase for architecture problems, unclear boundaries, duplication, hidden assumptions, and improvement opportunities."
---

# /rb:architecture - architecture review

## Purpose

Inspect the codebase for structural problems and opportunities for clearer boundaries.

## Procedure

1. Read `AGENTS.md` and `CONTEXT.md` if present; otherwise note missing project context and continue.
2. Inspect repository structure.
3. Identify major modules and responsibilities.
4. Look for shallow modules, unclear names, duplication, implicit dependencies, hidden scientific assumptions, poor test seams, circular imports, scattered configuration, unnecessary coupling, and ownership gaps.
5. Identify candidate deeper modules with simple interfaces and testable contracts.
6. Check whether proposed architecture changes preserve current behavior, public APIs, data contracts, deployment constraints, and user workflows.
7. If the architecture includes multiple LLM agents, also use `$rb-multi-agent-systems`.
8. Update `$rb-working-diary` with durable architecture findings, decisions, and follow-up risks when the review is substantial.
9. Produce a prioritised refactoring plan.

## Required behaviour

- Do not refactor immediately unless asked.
- Distinguish architecture risks from stylistic preferences.
- Prefer incremental refactors with tests over large rewrites.
- Preserve existing project conventions unless a proposed change has a clear payoff.

## Output

- current architecture map: major modules, responsibilities, data/control flow
- top risks, prioritized by impact and likelihood
- proposed refactoring sequence with small safe increments
- tests/checks needed to protect each refactor
- tradeoffs, non-goals, and open questions
