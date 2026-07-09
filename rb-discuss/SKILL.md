---
name: "rb-discuss"
description: "Use before implementing non-trivial features or changes to discuss requirements, read relevant docs, identify ambiguity, and produce an implementation plan."
---

# /rb:discuss - discuss before coding

## Purpose

Use this before implementing non-trivial features or changes.

## Procedure

1. Restate the requested change in plain language.
2. Read `CONTEXT.md` if present, plus relevant ADRs, README files, docs, and tests. If `CONTEXT.md` is missing, note that and continue.
3. Identify ambiguous points.
4. Ask targeted questions one at a time.
5. For multi-LLM-agent systems, also use `$rb-multi-agent-systems` to clarify stack, tools, state, observability, evals, retrieval, and provider routing.
6. For text-processing requests, clarify whether each text step is syntax-bound or semantic:
   - Syntax-bound means stable structure, exact markers, structured formats, IDs, URLs, logs, or protocol fields, and can usually be deterministic.
   - Semantic means meaning, intent, relevance, classification, summarisation, ambiguity resolution, natural-language extraction, rubric judgment, entity/claim matching, or semantic equivalence, and should usually use an LLM-backed path.
7. Continue until behaviour, interface, edge cases, failure modes, tests, scientific assumptions, and compatibility are clear.
8. For substantial discovery or planning, update `$rb-working-diary` with durable findings, decisions, and open questions.
9. Produce a short implementation plan.

## Stop condition

Do not start coding until material ambiguity is resolved or explicitly accepted as a risk.
