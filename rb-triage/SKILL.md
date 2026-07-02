---
name: "rb-triage"
description: "Use to classify and prioritize tasks by type, urgency, importance, risk, dependency, effort, uncertainty, and validity implications."
---

# /rb:triage - classify and prioritise tasks

## Procedure

1. Collect the task list, source, constraints, deadlines, and known dependencies.
2. Classify each item by type, urgency, importance, risk, dependency, effort, uncertainty, and scientific-validity or product-validity implications.
3. Identify blockers, duplicates, tasks that need clarification, and tasks that should be split.
4. Recommend the next action and matching RB skill for each high-priority item.
5. For substantial triage, update `$rb-working-diary` with durable prioritisation decisions, risks, and next actions.

## Required Behaviour

- Do not treat urgency as importance.
- Do not bury high-risk unknowns under easy low-value tasks.
- Mark confidence explicitly when prioritisation depends on assumptions.

## Output

Output a prioritised list or table with:

- priority
- task
- type
- urgency / importance
- risk
- dependencies or blockers
- effort estimate
- confidence
- recommended next action and RB skill
