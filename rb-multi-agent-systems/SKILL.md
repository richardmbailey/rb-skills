---
name: rb-multi-agent-systems
description: Use when designing, reviewing, or debugging a system with multiple LLM agents or orchestration layers, including agent boundaries, tool permissions, handoffs, shared state, routing, failure containment, observability, evaluation, budgets, and durability. Do not use for a single ordinary LLM call.
---

# /rb:multi-agent-systems - design multi-LLM-agent systems

## Purpose

Use this when shaping, reviewing, or diagnosing systems with multiple LLM agents, agent tools, MCP servers, structured outputs, retrieval, long-running workflows, provider routing, or production observability needs.

## Core stance

Preserve the repository's existing production constraints and framework choices unless evidence supports a change. For new designs, choose one primary agent framework only after defining capability boundaries and operational requirements. Verify version-sensitive implementation details against current official documentation before coding.

## Default orchestration architecture

For non-trivial multi-agent systems, prefer a deterministic state-machine runner unless the workflow is more naturally represented as a simple pipeline or dependency graph.

The runner is the control plane. It owns:

- current workflow state, legal transitions, and terminal conditions
- agent dispatch, handoff execution, and message routing
- authentication and caller identity
- authorization and policy enforcement
- just-in-time tool and capability allocation
- structured input and output validation
- retry, timeout, budget, cancellation, and termination rules
- quality gates and human approval checkpoints
- checkpointing, append-only event logging, tracing, replay, and recovery

Agents perform bounded cognitive work. They may analyse information, generate candidate actions, recommend transitions, or return structured evidence, but they must not directly mutate authoritative workflow state or bypass runner policy.

Treat each agent-returned action, tool call, handoff, or transition as a proposal. Before execution, the runner must check that:

- the transition is legal from the current state
- the calling identity is authenticated where a real trust boundary exists
- the caller is authorized for the requested action
- required preconditions and quality gates have passed
- the requested tools are permitted for the current state, role, and task
- schema, confidence, provenance, and acceptance requirements are satisfied
- retry, cost, time, and side-effect budgets permit continuation

Keep these concerns separate:

- authentication: who is calling
- authorization: what that identity may do
- capability allocation: which tools and actions are exposed for this state and task

For trusted agents inside one process, cryptographic authentication may be omitted. Still preserve explicit caller identity, authorization rules, capability allocation, validation, and audit logging in the runner.

Maintain both a current-state record and an append-only event log. The current state supports execution; the event log supports audit, replay, debugging, evaluation, and recovery. For in-process systems, an in-memory transport may implement the same typed message and task contracts as a future HTTP, JSON-RPC, gRPC, or A2A boundary.

## Runner, A2A, and MCP boundaries

Keep orchestration, agent communication, and capability access conceptually separate:

- The runner governs the workflow, policy, state transitions, permissions, budgets, quality gates, and recovery.
- A2A is an agent-delegation boundary for communicating with an independently deployed, independently owned, or otherwise opaque agent system.
- MCP is a capability boundary for exposing tools, resources, and prompts to the runner or to a bounded agent.

A2A does not replace the runner, and MCP servers should not quietly become orchestration layers. The runner decides whether an agent may be contacted and whether an MCP capability may be used.

For agents in the same process, prefer typed direct calls or an in-memory transport. Preserve A2A-compatible message, task, context, status, and artifact contracts only when future transport substitution or interoperability is useful. Use actual A2A networking when a real deployment, language, framework, team, or organisational boundary justifies it.

Maintain two separate policy surfaces:

- an A2A agent-and-skill allow-list defining which remote agents and advertised skills may be invoked in each workflow state
- an MCP server, tool, resource, and prompt allow-list defining which capabilities may be exposed in each workflow state

Do not expose every discovered A2A agent or every tool returned by MCP discovery to an LLM. Discovery reports what is available; the runner filters that set according to workflow state, role, caller identity, task policy, data sensitivity, approval requirements, and budget.

Prefer these invocation modes:

- deterministic capability calls are selected and executed directly by the runner
- judgement-dependent agent or tool calls are proposed through typed outputs and validated by the runner
- low-risk autonomous loops may let an agent choose among a small, explicitly granted capability set

Treat a remote A2A agent as opaque unless its internal implementation is also under the application's governance. It may use its own runner, agents, and MCP servers internally. The local runner controls the information sent across the boundary, the allowed remote skill, the task budget, and validation of the returned result; it does not assume control of the remote agent's private tools.

Keep application workflow state distinct from delegated A2A task state. A remote task may be working, waiting for input, waiting for authorization, completed, failed, or cancelled, while the local runner remains authoritative about what those states mean for the larger workflow.

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
   - When orchestration is needed, default to a deterministic state-machine runner and justify any less explicit control model.
   - Reject a new agent if it mostly proxies every decision back to the parent, needs the parent's full context to work, has no independent success criteria, or adds model-call latency without reducing context noise or failure blast radius.
   - Record the expected effect on cost, latency, reliability, and context size whenever adding tools to an agent or splitting work across agents.
3. Choose the primary stack only after the preceding decisions. Keep an existing working stack unless it creates a concrete problem. Read `references/framework-selection.md` only when the user needs a greenfield stack recommendation, a framework comparison, or a concrete product choice; verify every version-sensitive recommendation against current official documentation.
4. Define agent boundaries:
   - Give each agent a clear responsibility, input contract, output contract, state ownership, tool permissions, and failure mode.
   - Do not create an agent when a deterministic function, typed tool call, or normal workflow step is enough.
   - Keep each agent's prompt, retrieved context, and tool list narrow enough that tool choice remains obvious for its responsibility.
   - Make handoffs explicit: who calls whom, what context is passed, what state is persisted, and what is returned.
   - Prefer agents returning typed results, evidence, and proposed next actions rather than directly controlling workflow transitions.
5. Define structured outputs:
   - Use typed, validated contracts where the language and framework support them.
   - Decide whether validation occurs after generation or through constrained decoding, and test schema failures explicitly.
   - Represent proposed transitions, requested tools, confidence, provenance, and retryability explicitly when they affect orchestration.
6. Define tools, MCP, and agent communication:
   - Prefer typed tool schemas and narrow reusable MCP server boundaries.
   - Keep tools idempotent where possible, explicit about side effects, and narrow in permissions.
   - Record which tools require human approval, secrets, filesystem access, network access, or external writes.
   - Allocate tools just in time according to workflow state, agent role, caller identity, and task policy rather than exposing the full catalogue by default.
   - Decide explicitly whether each agent boundary uses a direct call, an in-memory transport, or A2A; do not add a network protocol where there is no meaningful boundary.
   - Use A2A for independently deployed or opaque agent systems, not as a substitute for ordinary internal function calls.
   - Maintain separate A2A agent-and-skill and MCP capability allow-lists.
   - Distinguish runner-selected MCP calls, agent-proposed MCP calls, and bounded agent-controlled tool loops.
   - Treat discovered agents, skills, tools, resources, and prompts as candidates that must be filtered by policy before exposure or execution.
7. Design failure containment before increasing autonomy:
   - Identify assumptions that could poison the whole run if wrong, such as user intent, target files, retrieved evidence, permissions, external state, or irreversible side effects.
   - Validate high-risk assumptions with cheap checks before handing them to downstream agents or tools; use deterministic checks where possible.
   - Treat sub-agent output as evidence with provenance and confidence, not as automatically trusted state. Preserve enough trace data to see which agent produced which claim, tool result, or decision.
   - Validate every proposed transition against the current state, transition policy, preconditions, permissions, quality gates, and budgets before committing it.
   - Stop, retry, route to an alternate path, or ask for human confirmation when a sub-agent returns low confidence, schema-invalid output, contradictory evidence, or a failed precondition.
   - Put explicit budgets around autonomous loops: maximum model calls, tool calls, retries, wall-clock time, spend, and destructive or externally visible actions.
8. Add observability and evals before the system becomes non-trivial:
   - Prefer the repository's existing tracing and evaluation stack unless it cannot capture the required events.
   - Trace prompts, model calls, tool calls, handoffs, retrieved context, costs, latency, errors, and final decisions.
   - Maintain an append-only workflow event log distinct from the mutable current-state snapshot.
   - Record A2A task identifiers and states, MCP server and capability identifiers, policy decisions, grants, denials, and approval outcomes.
   - Favour tools that emit or can export OpenTelemetry-compatible traces, while treating GenAI semantic conventions as evolving.
9. Add durability only when the workflow needs it:
   - Require durable execution when work must survive process failure, support scheduled or long-running jobs, resume after interruption, or guarantee retry semantics.
   - Checkpoint enough information to resume safely: workflow state, validated inputs, tool results, pending approvals, retry counters, budgets, and idempotency keys for side effects.
   - Persist enough delegated-task state to resume polling, streaming, cancellation, or result retrieval without creating duplicate A2A tasks.
   - Do not add a durability platform to a short request-response path without an operational need.
10. Add retrieval/document infrastructure when agents work over papers, reports, notes, PDFs, codebases, or lab documentation:
   - Do not adopt a whole agent framework just to get retrieval.
   - Define source provenance, chunking, access control, freshness, and answer-grounding checks before choosing the retrieval product.
11. Add provider routing and cost control only when needed:
   - Centralize routing policy, keys, logging, budgets, fallback behaviour, and reproducibility when multiple providers are a real requirement.
12. Add prompt/program optimisation only when there are examples and metrics:
   - Optimize only bounded repeatable subtasks with representative examples, measurable outcomes, and held-out evaluation.
13. Update `$rb-working-diary` with durable architecture decisions, rejected alternatives, observability/eval commitments, and open risks when the work is substantial.

## Review checklist

- Is there one primary agent framework?
- Has each new capability been classified as deterministic code/tool, embedded capability, split agent, or orchestration concern?
- For text-heavy capabilities, is semantic understanding handled by an LLM-backed path rather than brittle regex/string heuristics?
- Is control flow owned by deterministic runner code rather than an LLM?
- Are workflow states, legal transitions, terminal states, and invalid-transition behaviour explicit?
- Are agent-requested actions and transitions treated as proposals rather than authoritative commands?
- Are authentication, authorization, and capability allocation separated?
- Are tools allocated just in time according to state, role, caller identity, and task policy?
- Is each communication boundary explicitly classified as direct call, in-memory transport, or A2A?
- Is A2A limited to boundaries where independent deployment, ownership, opacity, or interoperability justifies it?
- Are A2A agent-and-skill allow-lists distinct from MCP server, tool, resource, and prompt allow-lists?
- Are discovery results filtered before agents see or invoke them?
- Are deterministic MCP calls runner-controlled and judgement-dependent calls represented as validated proposals?
- Are remote A2A task states mapped explicitly into local workflow transitions?
- Are agent responsibilities, contracts, state ownership, and handoffs explicit?
- Is each agent's context and tool surface bounded enough that tool choice remains reliable?
- Could any agent be replaced by deterministic code or a typed tool?
- Are structured outputs enforced and tested?
- Are tool permissions, side effects, approval points, and idempotency clear?
- Are quality gates applied before authoritative state changes and external side effects?
- Can one bad premise poison downstream work, and if so where is the validation gate?
- Are sub-agent outputs treated with provenance/confidence rather than blindly becoming shared truth?
- Is there an append-only event log as well as a current-state snapshot?
- Can execution resume safely from a checkpoint without repeating side effects or duplicating delegated tasks?
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
- runner responsibility map and explicit control-flow ownership
- workflow state and legal-transition map, including terminal and recovery states
- authentication, authorization, and just-in-time capability-allocation plan
- communication-boundary map classifying direct calls, in-memory transports, and A2A boundaries
- separate A2A agent-and-skill and MCP capability allow-lists
- agent and tool boundary map
- structured-output contracts, including proposed actions and transitions where relevant
- state, durability, checkpoint, retry, and failure-containment plan
- high-risk assumptions, quality gates, and human approval points
- retrieval plan if relevant
- append-only event-log, observability, tracing, eval, cost, and reproducibility plan
- immediate implementation slice and validation checks
