# Agent communication and capability boundaries

Read only when the design includes remote agent delegation, MCP capabilities, or a decision about runtime versus transport. Apply only the boundaries that exist.

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

When both A2A and MCP boundaries exist, maintain two separate policy surfaces:

- an A2A agent-and-skill allow-list defining which remote agents and advertised skills may be invoked in each workflow state
- an MCP server, tool, resource, and prompt allow-list defining which capabilities may be exposed in each workflow state

Do not expose every discovered A2A agent or every tool returned by MCP discovery to an LLM. Discovery reports what is available; the runner filters that set according to workflow state, role, caller identity, task policy, data sensitivity, approval requirements, and budget.

Prefer these invocation modes:

- deterministic capability calls are selected and executed directly by the runner
- judgement-dependent agent or tool calls are proposed through typed outputs and validated by the runner
- low-risk autonomous loops may let an agent choose among a small, explicitly granted capability set

Treat a remote A2A agent as opaque unless its internal implementation is also under the application's governance. It may use PydanticAI or another runtime, its own runner, agents, and MCP servers internally. The local runner controls the information sent across the boundary, the allowed remote skill, the task budget, and validation of the returned result; it does not assume control of the remote agent's private tools.

Keep application workflow state distinct from delegated A2A task state. A remote task may be working, waiting for input, waiting for authorization, completed, failed, or cancelled, while the local runner remains authoritative about what those states mean for the larger workflow.
