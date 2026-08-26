---
name: rb-multi-agent-systems
description: Use when designing, reviewing, or debugging systems with multiple LLM agents, agent-to-agent delegation, or orchestration layers. Covers boundaries, handoffs, state, permissions, failure containment, testing, budgets, and durability. Do not use merely because one agent uses tools, MCP, retrieval, or structured output.
---

# /rb:multi-agent-systems - design multi-LLM-agent systems

## Purpose

Use this when shaping, reviewing, or diagnosing systems with multiple LLM agents, agent-to-agent delegation, or an orchestration layer that coordinates agent work. Do not select this skill for a single-agent system merely because that agent uses tools, MCP, retrieval, structured outputs, provider routing, durable execution, or observability. Use the skill that owns that component instead.

## Modes

- For design, follow the workflow and produce only the sections needed for the requested design decision.
- For review, assess the existing architecture against the relevant rules without forcing a replacement design.
- For diagnosis, localise the failure across agents, runner state, handoffs, permissions, budgets, or recovery. Do not broaden the task into a full architecture review.

## Core stance

Preserve the repository's existing production constraints and framework choices unless evidence supports a change. For new designs, choose one primary agent framework only after defining capability boundaries and operational requirements. Verify version-sensitive implementation details against current official documentation before coding.

## Architecture escalation

Use the simplest architecture that can express the required behaviour. Escalate workflow control only as requirements demand:

1. Use a state machine for predictable processes whose transitions can be specified in advance.
2. Use an extended state machine when decisions require bounded contextual data but the control flow can remain explicit.
3. Use a dynamic stateful workflow orchestrator only when planning, adaptation, or coordination cannot be expressed clearly by the simpler models.

Choose control-flow complexity and runtime durability independently. A predictable state machine may still need persistence, crash recovery, scheduling, or durable retries.

As control-flow complexity and autonomy increase, strengthen validation, execution limits, permissions, human checkpoints, testing, and auditability. Logging and tracing improve visibility and provide audit evidence, but they do not enforce permissions, constrain behaviour, or control risk by themselves.

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

## Runner, A2A, MCP, and agent-runtime boundaries

Keep orchestration, agent execution, agent communication, and capability access conceptually separate:

- The runner governs the workflow, policy, state transitions, permissions, budgets, quality gates, and recovery.
- An agent runtime such as PydanticAI implements and executes owned agents, including model calls, typed dependencies, structured outputs, tools, retries, and local delegation.
- A2A is an agent-delegation boundary for communicating with an independently deployed, independently owned, or otherwise opaque agent system.
- MCP is a capability boundary for exposing tools, resources, and prompts to the runner or to a bounded agent.

Do not treat PydanticAI and A2A as competing alternatives. PydanticAI is an implementation/runtime choice; A2A is a protocol/transport choice. A PydanticAI agent may be called directly inside the application or exposed behind an A2A server when a real external boundary exists.

For owned Python agents, prefer direct PydanticAI calls or programmatic hand-offs when PydanticAI fits the repository's requirements. Use actual A2A networking only when independent deployment, language, framework, team, organisational ownership, opacity, or interoperability justifies the additional protocol boundary.

A2A does not replace the runner, and MCP servers should not quietly become orchestration layers. The runner decides whether an agent may be contacted and whether an MCP capability may be used.

For agents in the same process, prefer typed direct calls or an in-memory transport. Preserve A2A-compatible message, task, context, status, and artifact contracts only when future transport substitution or interoperability is useful. Keep one logical runner dispatch interface where useful, but implement distinct in-process and A2A transports rather than pretending their failure and trust models are identical.

Maintain two separate policy surfaces:

- an A2A agent-and-skill allow-list defining which remote agents and advertised skills may be invoked in each workflow state
- an MCP server, tool, resource, and prompt allow-list defining which capabilities may be exposed in each workflow state

Do not expose every discovered A2A agent or every tool returned by MCP discovery to an LLM. Discovery reports what is available; the runner filters that set according to workflow state, role, caller identity, task policy, data sensitivity, approval requirements, and budget.

Prefer these invocation modes:

- deterministic capability calls are selected and executed directly by the runner
- judgement-dependent agent or tool calls are proposed through typed outputs and validated by the runner
- low-risk autonomous loops may let an agent choose among a small, explicitly granted capability set

Treat a remote A2A agent as opaque unless its internal implementation is also under the application's governance. It may use PydanticAI or another runtime, its own runner, agents, and MCP servers internally. The local runner controls the information sent across the boundary, the allowed remote skill, the task budget, and validation of the returned result; it does not assume control of the remote agent's private tools.

Keep application workflow state distinct from delegated A2A task state. A remote task may be working, waiting for input, waiting for authorization, completed, failed, or cancelled, while the local runner remains authoritative about what those states mean for the larger workflow.

## Workflow

1. Classify the system:
   - existing stack vs greenfield design
   - provider-independent research/prototyping vs OpenAI-first production
   - simple request-response vs long-running, stateful, interruptible workflows
   - retrieval-heavy vs tool/workflow-heavy
   - single-provider vs real multi-provider routing
   - hosted/cloud models vs local/open models needing constrained decoding
2. Decide the capability scaling shape before choosing frameworks: deterministic tool vs embedded capability vs split agent vs orchestration layer.
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
   - Choose the agent runtime independently from the communication protocol.
   - For owned Python agents, prefer PydanticAI when it fits the repository's requirements and conventions.
   - Do not add A2A merely because a system contains multiple agents; add it only where the communication boundary warrants protocol interoperability.
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
   - Decide explicitly whether each agent boundary uses a direct runtime call, an in-memory transport, or A2A; do not add a network protocol where there is no meaningful boundary.
   - Prefer direct PydanticAI calls or programmatic hand-offs for owned in-process agents when PydanticAI is the selected runtime.
   - Use A2A for independently deployed or opaque agent systems, not as a substitute for ordinary internal agent-runtime calls.
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
8. Define the testing strategy before non-trivial behaviour ships:
   - Separate deterministic software tests from model-behaviour evals; neither replaces the other.
   - Use deterministic agent stubs, fake clocks, seeded model adapters, and controlled tool doubles to test runner behaviour without relying on live model variability.
   - Cover every legal state transition, rejection of illegal transitions, terminal states, invalid structured outputs, permission denials, missing approvals, retry and timeout paths, cancellation, budget exhaustion, idempotency, duplicate suppression, checkpoint/recovery, event-log replay, and side-effect failure where applicable.
   - Add integration and contract tests for direct runtime calls, in-memory transports, A2A task/status/artifact mapping, MCP schemas and allow-lists, authentication/authorization boundaries, and external-service failure behaviour.
   - Use held-out behavioural evals for judgement-dependent agents, including malformed, adversarial, ambiguous, low-confidence, contradictory, and tool-misuse cases. Track repeated trials where nondeterminism matters.
   - Test fallback behaviour explicitly and confirm it is visible, bounded, and does not silently convert failure into success.
   - Run recovery tests from realistic checkpoints and prove side effects are not duplicated during replay or retry.
9. Add observability and evals before the system becomes non-trivial:
   - Prefer the repository's existing tracing and evaluation stack unless it cannot capture the required events.
   - Trace prompts, model calls, tool calls, handoffs, retrieved context, costs, latency, errors, and final decisions.
   - Maintain an append-only workflow event log distinct from the mutable current-state snapshot.
   - Record agent-runtime invocations, A2A task identifiers and states, MCP server and capability identifiers, policy decisions, grants, denials, and approval outcomes.
   - Favour tools that emit or can export OpenTelemetry-compatible traces, while treating GenAI semantic conventions as evolving.
10. Add durability only when the workflow needs it:
   - Require durable execution when work must survive process failure, support scheduled or long-running jobs, resume after interruption, or guarantee retry semantics.
   - Checkpoint enough information to resume safely: workflow state, validated inputs, tool results, pending approvals, retry counters, budgets, and idempotency keys for side effects.
   - Persist enough delegated-task state to resume polling, streaming, cancellation, or result retrieval without creating duplicate A2A tasks.
   - Do not add a durability platform to a short request-response path without an operational need.
11. Add retrieval/document infrastructure when agents work over papers, reports, notes, PDFs, codebases, or lab documentation:
   - Do not adopt a whole agent framework just to get retrieval.
   - Define source provenance, chunking, access control, freshness, and answer-grounding checks before choosing the retrieval product.
12. Add provider routing and cost control only when needed:
   - Centralize routing policy, keys, logging, budgets, fallback behaviour, and reproducibility when multiple providers are a real requirement.
13. Add prompt/program optimisation only when there are examples and metrics:
   - Optimize only bounded repeatable subtasks with representative examples, measurable outcomes, and held-out evaluation.
14. Use `$rb-working-diary` only when its trigger conditions apply and the human has authorized durable continuity. Record durable architecture decisions, rejected alternatives, testing/eval commitments, observability commitments, and open risks. Do not write diary entries for an isolated one-turn review or diagnosis.

## Completion material

Read `references/test-and-review-checklists.md` only when the task needs a formal architecture review, a complete testing strategy, or a detailed implementation-plan handoff. It contains the full review checklist, the required test matrix for a non-trivial runner, and the available output fields. Select only the rows and fields that apply; do not manufacture components, risks, or deliverables to complete the template.
