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
2. Decide the capability scaling shape before choosing frameworks:
   - Prefer deterministic code or a typed tool when the operation has stable inputs/outputs, does not require judgment, can be unit-tested conventionally, and does not need conversation state.
   - For text operations, treat structure and semantics separately: parse stable syntax deterministically, but use an LLM-backed capability when the task depends on meaning, intent, relevance, classification, summarisation, ambiguity resolution, rubric judgment, natural-language extraction, entity/claim matching, or semantic equivalence.
   - Do not let a "deterministic tool" become a pile of complex regexes, keyword lists, or fuzzy string heuristics that are really attempting semantic understanding.
   - Embed a capability inside an existing agent when it is tightly coupled to that agent's local context, state, or tool sequence, and splitting it would require passing most of the parent context anyway.
   - Split a capability into a new agent when it is reusable across workflows, can accept a small typed input, can produce a typed output, owns a distinct tool/state/eval surface, or would otherwise add noisy tools and context to a monolithic agent.
   - Add an orchestration layer only when multiple independent agents need sequencing, routing, arbitration, merging, retries, cancellation, or human checkpoints.
   - Reject a new agent if it mostly proxies every decision back to the parent, needs the parent's full context to work, has no independent success criteria, or adds model-call latency without reducing context noise or failure blast radius.
   - Record the expected effect on cost, latency, reliability, and context size whenever adding tools to an agent or splitting work across agents.
3. Choose the primary stack:
   - Existing system: keep the current framework unless it creates concrete reliability, maintainability, observability, or product problems.
   - Greenfield provider-independent Python research/prototyping: consider `Pydantic + PydanticAI + FastMCP + Logfire/Evals or Langfuse`; add `LiteLLM` only when provider routing is real; add `Outlines` where constrained local/open-model decoding matters.
   - OpenAI-first production: consider `Pydantic + OpenAI Agents SDK + FastMCP + OpenAI Structured Outputs + tracing/evals`. When implementing concrete OpenAI SDK details, use `$openai-docs` or official docs.
4. Define agent boundaries:
   - Give each agent a clear responsibility, input contract, output contract, state ownership, tool permissions, and failure mode.
   - Do not create an agent when a deterministic function, typed tool call, or normal workflow step is enough.
   - Keep each agent's prompt, retrieved context, and tool list narrow enough that tool choice remains obvious for its responsibility.
   - Make handoffs explicit: who calls whom, what context is passed, what state is persisted, and what is returned.
5. Define structured outputs:
   - Use typed models as the default contract surface in languages/frameworks that support them; Pydantic is a strong Python default.
   - Use OpenAI Structured Outputs in OpenAI-only designs when JSON Schema enforcement is needed.
   - Use Outlines for local/open/constrained generation when strict decoding is genuinely required.
6. Define tools and MCP:
   - Prefer typed tool schemas and FastMCP servers for reusable tool boundaries.
   - Keep tools idempotent where possible, explicit about side effects, and narrow in permissions.
   - Record which tools require human approval, secrets, filesystem access, network access, or external writes.
7. Design failure containment before increasing autonomy:
   - Identify assumptions that could poison the whole run if wrong, such as user intent, target files, retrieved evidence, permissions, external state, or irreversible side effects.
   - Validate high-risk assumptions with cheap checks before handing them to downstream agents or tools; use deterministic checks where possible.
   - Treat sub-agent output as evidence with provenance and confidence, not as automatically trusted state. Preserve enough trace data to see which agent produced which claim, tool result, or decision.
   - Stop, retry, route to an alternate path, or ask for human confirmation when a sub-agent returns low confidence, schema-invalid output, contradictory evidence, or a failed precondition.
   - Put explicit budgets around autonomous loops: maximum model calls, tool calls, retries, wall-clock time, spend, and destructive or externally visible actions.
8. Add observability and evals before the system becomes non-trivial:
   - Pick Pydantic Logfire/Evals, Langfuse, or the repository's existing tracing/eval stack.
   - Trace prompts, model calls, tool calls, handoffs, retrieved context, costs, latency, errors, and final decisions.
   - Favour tools that emit or can export OpenTelemetry-compatible traces, while treating GenAI semantic conventions as evolving.
9. Add durability only when the workflow needs it:
   - Use LangGraph when agent control flow is naturally a graph/state machine with persistence, streaming, human-in-the-loop, or resumability.
   - Use Temporal, DBOS, or Restate when production workflows need retries, durable execution, scheduled jobs, resumability, or must not silently die overnight.
10. Add retrieval/document infrastructure when agents work over papers, reports, notes, PDFs, codebases, or lab documentation:
   - Use LlamaIndex for retrieval and data plumbing when it saves work.
   - Otherwise use a simple custom layer with Postgres/pgvector or Qdrant plus typed models.
   - Do not adopt a whole agent framework just to get retrieval.
11. Add provider routing and cost control only when needed:
   - Use LiteLLM when switching across OpenAI, Anthropic, Gemini, local models, Azure, Bedrock, Groq, or similar providers is a real requirement.
   - Use the gateway as the place for routing, keys, logging, budget controls, fallback policy, and reproducibility across providers.
12. Add prompt/program optimisation only when there are examples and metrics:
   - Use DSPy for repeatable subtasks such as extraction, classification, routing, scoring, or RAG answer synthesis.
   - Do not use DSPy as the base agent runtime by default.
13. Update `$rb-working-diary` with durable architecture decisions, rejected alternatives, observability/eval commitments, and open risks when the work is substantial.

## Recommended default

For greenfield provider-independent Python agent systems, start by considering `PydanticAI + FastMCP + Logfire/Evals`. Do not override an existing working stack without evidence.

Add Outlines only where constrained decoding matters. Add LiteLLM when provider switching becomes real. Add LangGraph or Temporal/DBOS/Restate when control flow becomes long-running, stateful, resumable, or production-critical. Keep the OpenAI Agents SDK in the toolbox for explicitly OpenAI-native apps.

## Review checklist

- Is there one primary agent framework?
- Has each new capability been classified as deterministic code/tool, embedded capability, split agent, or orchestration concern?
- For text-heavy capabilities, is semantic understanding handled by an LLM-backed path rather than brittle regex/string heuristics?
- Are agent responsibilities, contracts, state ownership, and handoffs explicit?
- Is each agent's context and tool surface bounded enough that tool choice remains reliable?
- Could any agent be replaced by deterministic code or a typed tool?
- Are structured outputs enforced and tested?
- Are tool permissions, side effects, approval points, and idempotency clear?
- Can one bad premise poison downstream work, and if so where is the validation gate?
- Are sub-agent outputs treated with provenance/confidence rather than blindly becoming shared truth?
- Are traces and evals present before non-trivial behaviour ships?
- Is retrieval scoped to data plumbing rather than becoming accidental architecture?
- Is provider routing a real need, with cost and fallback behaviour defined?
- Are cost, latency, and reliability impacts estimated before adding new model calls, agents, or tools?
- Is fallback behavior explicit, tested, and user-visible rather than silently hiding failures?
- Is durable orchestration used only where state, retries, resumability, or scheduling justify it?
- Are OpenTelemetry/export needs captured for portability?

## Output

When applying this skill, produce:

- recommended architecture and primary stack, including whether it preserves or changes the existing stack
- alternatives rejected and why
- capability scaling decision table: deterministic tool vs embedded capability vs split agent vs orchestration layer
- text-operation classification where relevant: deterministic structure parsing vs semantic LLM judgment
- agent and tool boundary map
- structured-output contracts
- state, durability, retry, and failure-containment plan
- high-risk assumptions and validation gates
- retrieval plan if relevant
- observability, tracing, eval, cost, and reproducibility plan
- immediate implementation slice and validation checks
