# Simplified Language Patterns

Use these patterns as review aids. Preserve the source's intent and terminology rather than applying them mechanically.

## Requirement record

For each behaviour-changing instruction, recover this information:

| Field | Question |
| --- | --- |
| Actor | Which agent, runner, tool, or human acts? |
| Condition | Which observable fact enables or requires the action? |
| Action | What must, should, or may happen? |
| Object | Which exact tool, field, state, file, or artifact is affected? |
| Result | What observable state or output shows completion? |
| Failure | What happens when the action cannot complete or validation fails? |
| Precedence | Which rule wins if another instruction conflicts? |

Not every simple rule needs all seven fields in its final sentence. The missing fields must not create a material behavioural ambiguity.

## Rewrite patterns

### Put the condition before the action

Ambiguous:

```text
Check the database before answering when appropriate.
```

Controlled:

```text
If the answer depends on database data, query `customer_db` before answering.
Do not answer from memory when database data are required.
```

The rewrite is valid only if dependence on database data is the intended criterion. Otherwise, expose the missing criterion.

### Define tool boundaries

Ambiguous:

```text
Use `lookup_customer` when it might help.
```

Controlled:

```text
Use `lookup_customer` when the task requires customer data that are not present in the conversation.
Do not use `lookup_customer` for public company information.
```

### Name the actor and transition

Ambiguous:

```text
After evaluation, revise if necessary; otherwise return the answer.
```

Controlled:

```text
The evaluator checks the candidate answer against every acceptance criterion.
If one or more criteria fail, the runner sets `state = REVISE`.
If all criteria pass, the runner sets `state = COMPLETE`.
```

### Use a stable handoff schema

When agents exchange a fixed set of facts, prefer fields such as:

```text
CLAIM: <claim under review>
STATUS: SUPPORTED | UNSUPPORTED | CONFLICTING
EVIDENCE: <source identifier and relevant finding>
ACTION: <requested next action>
```

Define field meanings, allowed values, validation failures, and missing-field behaviour in the surrounding contract. Do not use a template as if it were a validated schema when enforcement matters.

### Separate rule, rationale, and example

```text
RULE
Use repository search before answering a question about a file that has not been read during this run.

RATIONALE
The agent must not infer unseen file contents.

EXAMPLE
If the user asks where `RetryPolicy` is defined, search for that symbol before answering.
```

The rationale explains the boundary. It does not add an unstated exception to the rule.

### State precedence

```text
Apply instructions in this order when they conflict:
1. Safety and permission constraints.
2. Explicit user constraints for the current task.
3. The task procedure.
4. Default behaviour.
```

Use the authority order that actually governs the system. Do not invent a generic order when a platform or repository already defines one.

## Review signals

Look closely at:

- vague qualifiers without a local definition;
- conditions placed after long action clauses;
- pronouns with more than one possible referent;
- one sentence that contains several independently testable actions;
- synonyms used for the same canonical entity;
- one term used for different entities;
- passive constructions that hide the responsible actor;
- unquantified temporal or quality terms that control behaviour;
- a `must`, `should`, `may`, or `must not` conflict;
- exceptions contained only in rationale or examples;
- missing failure, denial, retry, or terminal behaviour;
- prose that restates a field schema inconsistently;
- a deterministic-looking checklist that actually requires semantic judgement.

These are diagnostic signals. They are not automatic defects.

## Final semantic checks

1. Can two careful readers derive materially different actions from the same rule?
2. Can each decision be tied to an observable fact or a bounded semantic judgement?
3. Are actor, authority, and side-effect ownership explicit?
4. Does any example contradict or silently broaden a rule?
5. Does the text preserve useful context needed by an LLM to apply the rule reliably?
6. Could a schema or enum enforce stable structure more reliably than prose?
7. Is any missing product or policy decision disguised as a wording problem?
