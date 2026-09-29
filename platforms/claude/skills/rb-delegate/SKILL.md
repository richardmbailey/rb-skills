---
name: rb-delegate
description: Use alongside a substantial Claude Code task when independently verifiable subtasks justify delegation. Ask for the subagent model unless the user already selected one. Keep final integration and completion with the parent. Do not use for multi-agent product design.
---

# RB Delegate for Claude Code

Delegate only when a bounded subtask can make useful independent progress and its result can be checked. This skill supplements the task's implementation, research, or review workflow. It does not replace that workflow or design a multi-agent product; use `/rb-multi-agent-systems` for architecture work.

## Decide whether delegation helps

Keep simple work, closely coupled decisions, final synthesis, and integration with the parent. Before creating a subagent, identify its objective, exact scope, required context, deliverable, and observable acceptance check. Compare that benefit with briefing, waiting, and review effort. An explicit request to assess delegation does not require an unsuitable subtask.

## Obtain the model choice

1. Check the current request and recorded user choice for an applicable subagent model. Reuse a choice whose scope covers this task. A platform default or a model named by another skill is not a user choice.
2. If no choice exists, ask: “Which model should I use for the subagents for this task? You can name a model available in your Claude Code setup, or authorise inheriting this chat's model.” Do not preselect a model or launch subagents while the answer is pending. Continue independent parent work when useful.
3. Record the answer and scope in the task context. A single choice covers the task's subtasks unless the user limits it or names different models for different roles. Do not ask again for each dispatch. Persist it only in an already-authorised handoff or diary when continuity needs it; do not turn a task choice into a permanent preference.
4. Configure the native subagent with the exact supported user choice. Use `inherit` only when the user explicitly selected inheritance. Verify that the available interface can honour it. Do not set an effort level unless the user or applicable project policy specifies one.
5. If the selected model is unavailable, inaccessible, or cannot be enforced through the current interface, report that condition and ask for another choice or permission to keep the work with the parent. Do not silently substitute a model or claim the failed dispatch ran.

If no suitable delegation exists, complete the work in the parent without asking a model question. If an independent reviewer is mandatory, parent implementation work does not satisfy that review: keep the verification gate open until the required review occurs.

## Prepare and dispatch

Give each subagent a self-contained packet containing:

- Objective and exact read/write scope.
- Relevant requirements, constraints, and evidence.
- Expected artifact and acceptance checks.
- Failure conditions to report, including unavailable inputs or authority.
- The approved model choice and a prohibition on further delegation unless explicitly authorised.

Use Claude's native subagent controls and current available capabilities. Do not copy Codex tool names or `fork_turns` parameters. Provide necessary context explicitly rather than assuming the subagent received the parent conversation. Assign non-overlapping write scopes. Keep external writes, destructive actions, approvals, and unresolved product decisions with the parent.

## Verify and finish

Inspect the returned artifact and evidence. Run or review the relevant checks, assess integration and assumptions, and repair or reject incomplete results. An independent reviewer must not be the agent that implemented the change. Keep required review gates when tools are unavailable; do not replace them with self-review.

The parent owns the final answer and completion judgement. Report material missing checks or model fallbacks honestly. Where usage is available, compare total cost and accepted outcomes, including briefing, retries, and parent review. Do not infer price or quality from a model name.
