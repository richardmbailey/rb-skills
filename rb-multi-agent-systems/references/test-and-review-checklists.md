# Multi-agent completion checklists

Use this reference only for a formal architecture review, a complete testing strategy, or a detailed implementation-plan handoff. Select the applicable items. Do not force every item into a smaller design, review, or diagnosis.

## Required test matrix

For a non-trivial runner or multi-agent workflow, include the applicable coverage:

- state-machine unit tests for every legal transition and every illegal-transition rejection;
- terminal, cancellation, timeout, retry, and budget-exhaustion tests;
- structured-output schema success and failure tests;
- authentication, authorization, approval, and just-in-time capability-allocation denial tests;
- tool allow-list, side-effect, and idempotency tests;
- deterministic runner tests using agent stubs and tool doubles;
- integration tests for agent-runtime, MCP, persistence, queues, files, databases, and external-service boundaries;
- A2A contract tests for task creation, status mapping, artifacts, input requests, cancellation, failure, and duplicate suppression;
- checkpoint, crash-recovery, replay, and event-log consistency tests;
- retrieval provenance, access-control, stale-data, and answer-grounding tests where retrieval is used;
- held-out agent evals with repeated trials for semantic quality, tool selection, refusal or escalation, adversarial inputs, and distribution shift;
- end-to-end tests for critical user workflows and high-consequence side effects;
- observability assertions that confirm traces and events contain required identities, decisions, denials, costs, and error states without leaking secrets.

## Review checklist

- Does the system need multiple agents, or would deterministic code, a typed tool, or one bounded agent be sufficient?
- Is workflow control as simple as the required behaviour allows?
- Does deterministic runner code own authoritative state and legal transitions?
- Are agent actions and transitions proposals that runner policy validates?
- Are agent responsibilities, typed contracts, state ownership, context, tools, and handoffs explicit and narrow?
- Are authentication, authorization, and capability allocation separate?
- Are permissions, approvals, budgets, timeouts, cancellation, and side effects enforced and tested?
- Is the agent runtime separate from the communication protocol?
- Is each boundary classified as a direct call, in-memory transport, or A2A, with A2A limited to a real interoperability boundary?
- Are A2A agent-and-skill allow-lists separate from MCP capability allow-lists?
- Are discovery results filtered before an agent can see or invoke them?
- Are malformed outputs, low confidence, contradictory evidence, invalid transitions, and failed preconditions contained?
- Is there an append-only event log as well as current state?
- Can checkpoint recovery avoid duplicate tasks and side effects?
- Do deterministic tests, integration and contract tests, held-out evals, recovery tests, and end-to-end checks cover the relevant failure boundaries?
- Are fallback behaviour, cost, latency, provider routing, retrieval, durability, tracing, and secret handling explicit where they apply?

## Output fields

Choose only the fields needed for the task:

- current or recommended architecture and whether the existing stack changes;
- alternatives rejected and the evidence for rejection;
- workflow-control choice and state-transition map;
- capability decision: deterministic tool vs embedded capability vs split agent vs orchestration layer;
- runner, agent, tool, MCP, and communication-boundary map;
- structured contracts, policy checks, permissions, budgets, and approval points;
- state, retry, checkpoint, recovery, failure-containment, and durability plan;
- required deterministic tests, integration or contract tests, recovery tests, held-out evals, and end-to-end checks;
- event logging, tracing, evaluation, cost, and reproducibility plan;
- immediate implementation slice and validation checks.
