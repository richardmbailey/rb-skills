---
name: rb-multi-agent-systems
description: Use to design, review, or debug multi-LLM-agent systems, especially when choosing agent frameworks, tool/MCP architecture, structured outputs, tracing/evals, retrieval, provider routing, durability, or production/research stack tradeoffs involving PydanticAI, OpenAI Agents SDK, FastMCP, LiteLLM, LangGraph, Temporal, DBOS, Restate, LlamaIndex, Langfuse, Logfire, Outlines, or DSPy.
---

# /rb:multi-agent-systems - design multi-LLM-agent systems

## Purpose

Use this when shaping, reviewing, or diagnosing systems with multiple LLM agents, agent tools, MCP servers, structured outputs, retrieval, long-running workflows, provider routing, or production observability needs.

## Core stance

Preserve the repository's existing production constraints and framework choices unless there is a clear reason to change them. For new designs, choose one primary agent framework. Prefer PydanticAI as a greenfield provider-independent Python option; treat the OpenAI Agents SDK as an OpenAI-native runtime, not as a second equal framework mixed deeply into the same architecture. When implementation depends on current SDK behavior, verify against official docs before coding.

## Workflow

1. Classify the system:
   - existing stack vs greenfield design
   - provider-independent research/prototyping vs OpenAI-first production
   - simple request-response vs long-running, stateful, interruptible workflows
   - retrieval-heavy vs tool/workflow-heavy
   - single-provider vs real multi-provider routing
   - hosted/cloud models vs local/open models needing constrained decoding
2. Choose the primary stack:
   - Existing system: keep the current framework unless it creates concrete reliability, maintainability, observability, or product problems.
   - Greenfield provider-independent Python research/prototyping: consider `Pydantic + PydanticAI + FastMCP + Logfire/Evals or Langfuse`; add `LiteLLM` only when provider routing is real; add `Outlines` where constrained local/open-model decoding matters.
   - OpenAI-first production: consider `Pydantic + OpenAI Agents SDK + FastMCP + OpenAI Structured Outputs + tracing/evals`. When implementing concrete OpenAI SDK details, use `$openai-docs` or official docs.
3. Define agent boundaries:
   - Give each agent a clear responsibility, input contract, output contract, state ownership, tool permissions, and failure mode.
   - Do not create an agent when a deterministic function, typed tool call, or normal workflow step is enough.
   - Make handoffs explicit: who calls whom, what context is passed, what state is persisted, and what is returned.
4. Define structured outputs:
   - Use typed models as the default contract surface in languages/frameworks that support them; Pydantic is a strong Python default.
   - Use OpenAI Structured Outputs in OpenAI-only designs when JSON Schema enforcement is needed.
   - Use Outlines for local/open/constrained generation when strict decoding is genuinely required.
5. Define tools and MCP:
   - Prefer typed tool schemas and FastMCP servers for reusable tool boundaries.
   - Keep tools idempotent where possible, explicit about side effects, and narrow in permissions.
   - Record which tools require human approval, secrets, filesystem access, network access, or external writes.
6. Add observability and evals before the system becomes non-trivial:
   - Pick Pydantic Logfire/Evals, Langfuse, or the repository's existing tracing/eval stack.
   - Trace prompts, model calls, tool calls, handoffs, retrieved context, costs, latency, errors, and final decisions.
   - Favour tools that emit or can export OpenTelemetry-compatible traces, while treating GenAI semantic conventions as evolving.
7. Add durability only when the workflow needs it:
   - Use LangGraph when agent control flow is naturally a graph/state machine with persistence, streaming, human-in-the-loop, or resumability.
   - Use Temporal, DBOS, or Restate when production workflows need retries, durable execution, scheduled jobs, resumability, or must not silently die overnight.
8. Add retrieval/document infrastructure when agents work over papers, reports, notes, PDFs, codebases, or lab documentation:
   - Use LlamaIndex for retrieval and data plumbing when it saves work.
   - Otherwise use a simple custom layer with Postgres/pgvector or Qdrant plus typed models.
   - Do not adopt a whole agent framework just to get retrieval.
9. Add provider routing and cost control only when needed:
   - Use LiteLLM when switching across OpenAI, Anthropic, Gemini, local models, Azure, Bedrock, Groq, or similar providers is a real requirement.
   - Use the gateway as the place for routing, keys, logging, budget controls, fallback policy, and reproducibility across providers.
10. Add prompt/program optimisation only when there are examples and metrics:
   - Use DSPy for repeatable subtasks such as extraction, classification, routing, scoring, or RAG answer synthesis.
   - Do not use DSPy as the base agent runtime by default.
11. Update `$rb-working-diary` with durable architecture decisions, rejected alternatives, observability/eval commitments, and open risks when the work is substantial.

## Recommended default

For greenfield provider-independent Python agent systems, start by considering `PydanticAI + FastMCP + Logfire/Evals`. Do not override an existing working stack without evidence.

Add Outlines only where constrained decoding matters. Add LiteLLM when provider switching becomes real. Add LangGraph or Temporal/DBOS/Restate when control flow becomes long-running, stateful, resumable, or production-critical. Keep the OpenAI Agents SDK in the toolbox for explicitly OpenAI-native apps.

## Review checklist

- Is there one primary agent framework?
- Are agent responsibilities, contracts, state ownership, and handoffs explicit?
- Could any agent be replaced by deterministic code or a typed tool?
- Are structured outputs enforced and tested?
- Are tool permissions, side effects, approval points, and idempotency clear?
- Are traces and evals present before non-trivial behaviour ships?
- Is retrieval scoped to data plumbing rather than becoming accidental architecture?
- Is provider routing a real need, with cost and fallback behaviour defined?
- Is fallback behavior explicit, tested, and user-visible rather than silently hiding failures?
- Is durable orchestration used only where state, retries, resumability, or scheduling justify it?
- Are OpenTelemetry/export needs captured for portability?

## Output

When applying this skill, produce:

- recommended architecture and primary stack, including whether it preserves or changes the existing stack
- alternatives rejected and why
- agent and tool boundary map
- structured-output contracts
- state, durability, and retry plan
- retrieval plan if relevant
- observability, tracing, eval, cost, and reproducibility plan
- immediate implementation slice and validation checks
