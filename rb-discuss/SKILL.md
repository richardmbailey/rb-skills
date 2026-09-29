---
name: "rb-discuss"
description: "Use when a non-trivial change still has unresolved material requirements, behaviour, interfaces, edge cases, or acceptance criteria that must be discussed before implementation. Do not use once the change is sufficiently agreed for planning or implementation."
---

# /rb:discuss - discuss before coding

## Purpose

Use this when a non-trivial feature or change cannot yet be planned or implemented safely because material requirements remain unresolved.

Do not use it merely because a change is substantial. Once the intended behaviour and acceptance criteria are sufficiently agreed, use `$rb-create-prd` when the user wants a durable product requirements document. Otherwise, use `$rb-create-implementation-plan` for a new top-level plan or the appropriate implementation skill for agreed work.

## Procedure

1. Read `CONTEXT.md` if present, plus relevant ADRs, README files, docs, and tests. If `CONTEXT.md` is missing, note that and continue.
2. Separate what is already agreed from decisions that materially affect behaviour, interfaces, data, compatibility, failure handling, tests, scientific assumptions, or acceptance.
3. Ask one targeted question at a time when answers depend on each other. Bundle independent missing decisions when that reduces delay. Ask only when the answer cannot be recovered safely from the repository and would materially change the result.
4. For multi-LLM-agent systems, also use `$rb-multi-agent-systems` to clarify stack, tools, state, observability, evals, retrieval, and provider routing.
5. For text-processing requests, establish whether acceptance depends on stable syntax or meaning. Clarify expected errors and tolerances; leave the choice among an LLM and other validated semantic methods to implementation unless it is a product constraint.
6. Continue until behaviour, interface, edge cases, failure modes, tests, scientific assumptions, and compatibility are clear.
7. For substantial discovery or planning, update `$rb-working-diary` with durable findings, decisions, and open questions.
8. Record the agreed requirements, accepted risks, remaining questions, and next workflow. Continue when the current request already authorises that work. Do not require a separate confirmation merely to change skills. Create a PRD or top-level plan only when it is part of the authorised task, using `$rb-create-prd` or `$rb-create-implementation-plan` respectively.

## Stop condition

Do not start coding until material ambiguity is resolved or explicitly accepted as a risk.
