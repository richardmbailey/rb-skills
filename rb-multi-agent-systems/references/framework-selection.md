# Framework Selection Reference

Read this reference only when a multi-agent task requires a concrete greenfield
stack recommendation, framework comparison, or product choice. The main skill
defines the architectural decisions that must come first.

Every named product and SDK is version-sensitive. Check current official documentation before recommending APIs, compatibility, hosting behaviour, or production guarantees.

## Primary Agent Runtime

- Preserve an existing working runtime unless evidence shows a reliability,
  maintainability, observability, or product problem.
- For owned Python agents, prefer PydanticAI as the primary runtime when it fits
  the repository's requirements and conventions.
- For explicitly OpenAI-native production applications, compare the OpenAI Agents SDK and use current official OpenAI documentation for implementation details.
- Choose one primary agent runtime. Do not combine two full agent frameworks as
  equal orchestration layers without a specific interoperability reason.
- Do not treat A2A as an alternative agent runtime. Use it as a protocol adapter
  when an independently deployed or opaque agent boundary requires interoperability.
- Prefer direct PydanticAI calls or programmatic hand-offs for agents owned by
  the same Python application; add A2A only at a real process, framework, team,
  language, or organisational boundary.

## Typed Contracts And Tools

- Pydantic is a useful Python option for typed contracts and validation.
- FastMCP is a useful option for reusable MCP server boundaries.
- OpenAI Structured Outputs can enforce JSON Schema in OpenAI-only designs.
- Outlines can provide constrained decoding for supported local or open models.

Choose these only when they fit the existing language, deployment target, and
failure model.

## Observability And Evaluation

- Prefer an existing tracing and evaluation stack.
- Pydantic Logfire/Evals and Langfuse are options when their current feature
  sets cover prompts, model calls, tools, handoffs, retrieval, costs, latency,
  errors, and final decisions.
- Prefer OpenTelemetry-compatible export when portability matters, while
  treating GenAI semantic conventions as evolving.

## Durable Orchestration

- Prefer an explicit runner and state model in the primary application stack for ordinary state-machine orchestration.
- Temporal, DBOS, and Restate are candidates when production workflows need
  durable execution, schedules, retries, resumability, or crash survival.

Select durability from operational semantics, not from the presence of an LLM.

## Retrieval, Provider Routing, And Optimisation

- LlamaIndex can reduce retrieval and document-plumbing work; a simpler custom
  layer with Postgres/pgvector or Qdrant may be more appropriate for a narrow
  retrieval surface.
- LiteLLM can centralize genuine multi-provider routing, keys, logging, budgets,
  and fallback policy. Do not add it for hypothetical provider portability.
- DSPy can optimize bounded, repeatable prompt programs when representative
  examples, metrics, and held-out evaluation exist. It is not a default agent
  runtime.

For each product choice, record the requirement it satisfies, alternatives
rejected, operational cost, lock-in, and the official documentation consulted.
