---
name: "rb-to-issues"
description: "Use to split a PRD or implementation plan into ordered issues with scope, acceptance criteria, tests, risks, and dependencies."
---

# /rb:to-issues - split a PRD into issues

## Procedure

1. Read the PRD, implementation plan, and relevant project context.
2. Identify dependencies, risks, unknowns, and the smallest useful vertical slices.
3. If the PRD or plan involves multiple LLM agents, also use `$rb-multi-agent-systems` so agent boundaries, tools, handoffs, state, observability, evals, retrieval, provider routing, and durability become explicit issue scope where needed.
4. Split work into small vertical slices. Avoid issues that only build isolated layers unless they unblock a specific runnable slice.
5. Give each issue a title, motivation, scope, non-scope, acceptance criteria, tests/checks, risks, dependencies, and rollback or follow-up notes when relevant.
6. Update `$rb-working-diary` with durable issue-splitting decisions and sequencing risks when the plan is substantial.
7. Order issues by dependency, risk, and learning value.

## Required Behaviour

- Do not create issues that are too broad to verify in one reviewable change.
- Do not hide open product or technical questions inside implementation issues; call them out explicitly.
- Preserve the PRD's non-goals and constraints.

## Output

Use this shape for each issue:

```markdown
## Issue N: Title

- Goal:
- Motivation:
- Scope:
- Non-scope:
- Acceptance criteria:
- Tests/checks:
- Dependencies:
- Risks/open questions:
- Suggested order/rationale:
```
