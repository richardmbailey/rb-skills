---
name: "rb-grill-with-docs"
description: "Use before implementing non-trivial features or changes to clarify requirements, read relevant docs, identify ambiguity, and produce an implementation plan."
---

# /rb:grill — clarify before coding

## Purpose

Use this before implementing non-trivial features or changes.

## Procedure

1. Restate the requested change in plain language.
2. Read `CONTEXT.md` if present, plus relevant ADRs, README files, docs, and tests. If `CONTEXT.md` is missing, note that and continue.
3. Identify ambiguous points.
4. Ask targeted questions one at a time.
5. For multi-LLM-agent systems, also use `$rb-multi-agent-systems` to clarify stack, tools, state, observability, evals, retrieval, and provider routing.
6. Continue until behaviour, interface, edge cases, failure modes, tests, scientific assumptions, and compatibility are clear.
7. For substantial discovery or planning, update `$rb-working-diary` with durable findings, decisions, and open questions.
8. Produce a short implementation plan.

## Stop condition

Do not start coding until material ambiguity is resolved or explicitly accepted as a risk.
