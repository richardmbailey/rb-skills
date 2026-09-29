---
name: rb-multi-agent-systems
description: Use when designing, reviewing, or debugging systems with multiple LLM agents, agent-to-agent delegation, or orchestration layers. Covers boundaries, handoffs, state, permissions, failure containment, testing, budgets, and durability. Do not use merely because one agent uses tools, MCP, retrieval, or structured output.
---

# RB Multi-Agent Systems

Design, review, or diagnose systems that coordinate multiple LLM agents. Do not select this skill for a single-agent system merely because it uses tools, MCP, retrieval, structured outputs, provider routing, or durable execution.

## Modes

For design, resolve the requested architecture decision. For review, assess supported risks without forcing a replacement design. For diagnosis, localise the failure and do not expand into an unrelated architecture redesign. Preserve an existing working stack unless evidence supports changing it.

## Architecture choices

Use the simplest architecture that can express the required behaviour. Choose among deterministic tool vs embedded capability vs split agent vs orchestration layer:

- Use a function or typed tool for stable operations that do not need semantic judgement or conversation state.
- Keep a capability in the existing agent when it needs most of that agent's context.
- Split an agent only when it has a bounded responsibility, small input, independently checkable output, and a useful separate tool/state/evaluation boundary.
- Use a pipeline or dependency graph when it expresses the coordination clearly. For non-trivial multi-agent systems, prefer a deterministic state-machine runner when explicit states and transitions are needed. Use an extended state machine for bounded contextual decisions; justify a dynamic stateful workflow orchestrator only when the simpler models cannot express the requirement.

Choose control-flow complexity and runtime durability independently. Persistence, scheduling, crash recovery, and durable retries are requirements to establish, not automatic consequences of adding agents. Record the expected effect of a new agent on cost, latency, context size, and failure containment; validate those expectations with measurements.

Use structured parsers for stable syntax. For meaning-dependent operations, use an LLM or an existing semantic method validated against the acceptance criteria. Do not build brittle keyword or regex substitutes for understanding language.

## Ownership and enforcement

The runner owns authoritative workflow state, legal transitions, dispatch, permissions, capability allocation, validation, budgets, and terminal conditions. Agents return evidence and proposed actions or transitions. Validate proposals against current state, authority, schemas, quality gates, and available budgets before committing them.

Give every agent a responsibility, input/output contract, state ownership, allowed tools, and failure response. Keep its context and tool list narrow. Reject a new agent that mainly relays decisions to its parent, needs the parent's full context, or has no independent success criterion.

Use explicit caller identity even within one process. Require authentication across real trust boundaries. Allocate only the tools needed for the current role and task. Treat discovered agents and tools as candidates, not grants of authority.

Logging and tracing provide evidence; they do not enforce permissions, constrain behaviour, or control risk by themselves. Keep current state and an append-only event log when audit, replay, or recovery is required; short in-process work may use in-memory state and traces without adding a persistence platform.

## Workflow

1. Establish the requested behaviour, existing stack, trust boundaries, side effects, expected duration, and acceptance evidence. Ask only for unresolved decisions that affect those requirements.
2. Choose the simplest control model and define bounded agents and typed handoffs. Separate deterministic validation from semantic judgements; do not treat a model's confidence as proof.
3. Establish relevant boundaries before choosing products. Read `references/agent-boundaries.md` when runtime, A2A transport, or MCP capabilities need design or review. Do not treat PydanticAI and A2A as competing alternatives. Where both protocols exist, maintain separate A2A agent-and-skill and MCP capability allow-lists; do not add unused policy surfaces.
4. Read `references/framework-selection.md` only for a concrete framework or product decision. Check version-sensitive implementation details against current official documentation. Prefer direct typed calls for owned in-process agents; add networking only for a real deployment, ownership, language, or interoperability boundary.
5. Define failure containment: schema rejection, conflicting evidence, unavailable tools, permission denial, cancellation, retry, and partial side effects as applicable. Put finite limits around maximum model calls, tool calls, retries, wall-clock time, spend, and externally visible actions. Preserve explicit human checkpoints. A fallback must be visible, bounded, and tested.
6. Define tests at the actual failure boundaries. Use deterministic stubs and fake clocks for runner transitions, permissions, budgets, and retries. Use integration/contract tests for real tool and transport boundaries. Use held-out agent evals for semantic decisions. Neither software tests nor model evals substitutes for the other.
7. Add durability only when work must survive interruption or delayed continuation. Then define checkpoints, idempotency keys, pending approvals, remaining budgets, replay, and recovery tests that prove side effects are not duplicated.
8. Capture the evidence needed to debug outcomes: model/tool calls, handoffs, policy decisions, errors, latency, and cost. Respect data policy when retaining prompts and retrieved material. Add retrieval or provider-routing infrastructure only when the requirements call for it.
9. Review whether every proposed component and gate addresses a concrete requirement. Use `$rb-working-diary` only when the work needs authorised durable continuity; do not write diary entries for an isolated review or diagnosis.

## Completion material

Read `references/test-and-review-checklists.md` for a formal architecture review, detailed testing strategy, or implementation handoff. Select only applicable rows. Report the chosen boundaries, consequential tradeoffs, supporting evidence, tests/evals needed or run, and unresolved risks. Distinguish proposed architecture from implemented or validated behaviour; do not invent components or findings to complete a template.
