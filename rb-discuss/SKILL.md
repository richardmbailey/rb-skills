---
name: "rb-discuss"
description: "Interview the user about project goals, outcomes, scope, priorities, or consequential requirements that need their judgement. Use for initial discovery or later decisions; not routine clarification, technical investigation, or resuming agreed work."
---

# RB Discuss

## Purpose

Help the user decide what a project or change should achieve. Use a focused interview to clarify intended outcomes, explore trade-offs, and agree the decisions needed for the next action.

## Selection boundary

Use this when the user requests an interview or exploratory discussion, or when a consequential choice needs their judgement and is not already settled or delegated. Examples include intended users, success criteria, scope, acceptable failure behaviour, and scientific comparisons.

Do not use it merely because a change is substantial. A new session, unfinished task, unfamiliar code, or technical uncertainty is not an interview trigger. Investigate recoverable facts and make ordinary implementation choices within existing authority. Handle a routine clarification in the current workflow.

This skill guides a conversation with the user. Do not simulate their answers or use it as an internal reasoning checklist. If reading the context resolves the apparent question, continue the authorised work without an interview.

## Procedure

1. Read the request and relevant existing decisions, handoff, `CONTEXT.md`, docs, or tests. Missing context files do not require creating them. Preserve settled decisions unless the user changes them or new evidence undermines their assumptions; explain the reason before reopening one.
2. Identify the next decision that needs the user's judgement. For initial discovery, establish the intended outcome and who benefits before exploring solutions. Separate user decisions from investigations the agent can perform and risks that do not block the next action.
3. Ask one targeted question at a time when answers depend on each other. Bundle independent missing decisions when that reduces delay. Explain why the answer matters. Explore only what is needed for the next action; do not work through an exhaustive questionnaire.
4. Where meaningful alternatives exist, offer a small set of distinct options with short trade-offs. Recommend an option when the known goals and evidence support it, and explain why. If that context is missing, ask an open question before recommending. Let the user propose another answer or reject the recommendation.
5. Prefer the host's native question tool for clickable options when it is available and permitted for this question. Follow its current schema and mode restrictions; preserve a way for the user to give their own answer. If the tool cannot be used, ask in text, including any applicable options and evidence-supported recommendation. Do not invent buttons or change modes just to obtain them.
6. Wait for the user's answer before taking an action that depends on it. A recommendation, preselected option, unanswered question, or elapsed time is not agreement. Continue independent work only within existing authority. Apply the user's answer, including a custom choice, and ask a follow-up only if it leaves a consequential decision unresolved.
7. Use specialist guidance only for the decision at hand. For multi-LLM-agent design, use `$rb-multi-agent-systems`. For text processing, clarify whether success depends on syntax or meaning and what errors are acceptable; leave technical method choices to implementation unless they are user constraints.
8. Summarise the agreed decisions, accepted risks, and any remaining user choices separately from agent investigations. For substantial discovery, preserve these through `$rb-working-diary`. Stop the interview once the next action is clear. Continue work already authorised; a skill change alone does not require confirmation. Use `$rb-create-prd` or `$rb-create-implementation-plan` only when that deliverable is part of the authorised task.

## Stop condition

Do not implement behaviour that depends on an unanswered user decision. Resume that work when the user decides, delegates the choice, or explicitly accepts the risk. Do not block unrelated authorised work.

Behavioural cases for selection, handoffs, and question delivery are in `evals/eval-plan.json`.
