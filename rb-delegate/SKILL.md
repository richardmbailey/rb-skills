---
name: rb-delegate
description: Use for substantial Codex tasks when bounded, independently verifiable subtasks can be delegated to cheaper sub-agents without transferring final integration or completion judgement. Do not use for simple tasks, tightly coupled work, or multi-agent system design.
---

# RB Delegate

Use sub-agents to reduce expensive parent-model work while preserving the quality and accountability of the final result. Optimise total cost, the amount of context processed by the parent, latency, and rework together. Do not claim a saving merely because a smaller model was used.

This is a Codex-specific execution skill because it depends on Codex sub-agent controls and named model tiers. It supplements the skill that owns the task. It does not replace implementation, research, review, planning, or other task-specific workflows.

## Selection boundary

Select this skill automatically only when the overall task is substantial and at least one candidate subtask satisfies every condition below:

- The parent can state a bounded objective, input scope, deliverable, and acceptance criteria.
- The subtask needs only a small context packet or a narrow set of files or sources.
- The result can be checked independently from the sub-agent's own conclusion.
- The subtask does not own final synthesis, task completion, or an unresolved user or product decision.
- The expected saving or useful parallel progress is greater than the cost of briefing, waiting, reviewing, and possible rework.

Do not select this skill:

- for a simple request that the parent can complete more cheaply than it can delegate and verify;
- when a subtask needs most of the parent's conversation or codebase context;
- when the work is tightly coupled and must be judged continuously as it develops;
- when the user prohibits delegation or requests a specific execution model;
- merely because the request mentions agents, models, tokens, or cost;
- to design, review, or debug a multi-agent product or orchestration architecture; use `$rb-multi-agent-systems` for that work.

Explicit invocation of `$rb-delegate` requires the parent to assess delegation, but it does not require the parent to create a poor delegation boundary. If no candidate meets the criteria, the parent completes the work directly and briefly explains why.

Apply instructions in this order when they conflict:

1. System, developer, platform, safety, and permission constraints.
2. The user's explicit instructions for the current task.
3. The skill that owns the requested task.
4. This skill's delegation defaults.

Available collaboration tools, model availability, and concurrency limits may further restrict delegation.

## Ownership

The parent agent owns:

- understanding the user's complete request;
- selecting and scoping delegated work;
- decisions that affect the whole task;
- resolving conflicts between results;
- inspecting returned evidence and changed artifacts;
- running or reviewing the final relevant checks;
- deciding whether the user's task is complete;
- writing the final answer.

A sub-agent owns only the task packet it receives. Its completion message is a proposed result, not proof that the overall task is complete.

## Choose the execution path

Before delegating, prefer deterministic code or a direct tool call when stable inputs and outputs make model judgement unnecessary.

Use `gpt-5.6-luna` with `reasoning_effort: max` for a well-defined, discrete subtask that requires limited judgement. Suitable work includes:

- locating files, symbols, tests, or source passages within a bounded scope;
- extracting or classifying information into a stated structure;
- summarising a small supplied source set;
- making a narrow mechanical edit with explicit acceptance criteria;
- adding an isolated test from an already-defined behaviour;
- running focused checks and returning the exact evidence;
- checking a bounded artifact against a concrete checklist.

Use `gpt-6-astra` with `reasoning_effort: medium` when an independently scoped subtask genuinely needs high intelligence. Suitable work includes:

- difficult mathematical or scientific reasoning;
- synthesis across a large but bounded source or file set;
- a substantial coding unit that requires reasoning across several components;
- a difficult review or investigation that requires evolving judgement.

Keep the work with the parent when it requires the parent's broad context, final synthesis, cross-cutting trade-offs, or continuous integration judgement. Do not move work to Astra merely because it is large; first confirm that it has an independent boundary and acceptance test.

If the selected model or reasoning level is unavailable, use another model only when the platform identifies it as a permitted lower-cost option and the delegation case still holds. Do not infer relative price from a model name. Otherwise, keep the work with the parent. Report a fallback only when it materially affects confidence, cost, or completion.

## Prepare the task packet

Send the smallest self-contained packet that allows the sub-agent to succeed. Include:

1. `Objective`: one bounded outcome.
2. `Scope`: exact files, directories, sources, or questions the agent may inspect or change.
3. `Context`: only the facts and decisions required for this subtask.
4. `Constraints`: relevant repository instructions, permissions, prohibitions, and compatibility requirements.
5. `Deliverable`: the artifact, findings, patch, or evidence to return.
6. `Acceptance`: observable checks the parent will use.
7. `Failure return`: what uncertainty, missing input, conflict, or failed check the agent must report.

For routine Luna delegation, use `fork_turns: "none"` and provide the task packet explicitly. Use a small positive `fork_turns` value only when recent conversation turns are necessary and reproducing their relevant content would be less efficient. Do not use `fork_turns: "all"` for routine bounded delegation.

Tell each sub-agent not to create further sub-agents unless the parent explicitly authorises nested delegation for that task.

## Dispatch and coordination

1. Identify candidate subtasks only after understanding the overall goal and current constraints.
2. Delegate only independent work. Assign non-overlapping write scopes when agents share a filesystem.
3. Use available concurrency for work that can progress independently. Do not create agents merely to fill every slot.
4. Do not send duplicate work to several agents unless comparative evaluation or the consequences of error justify the extra cost.
5. Keep external writes, destructive operations, approvals, and other high-consequence actions with the parent. A sub-agent may perform bounded read-only preparation when permitted.
6. While sub-agents work, the parent should continue useful non-overlapping work when doing so will not create conflicting edits or conclusions.

## Review and escalation

For every returned result, the parent must:

1. Compare the result with the task packet and acceptance criteria.
2. Inspect the actual files, diff, sources, calculations, or command output that support it.
3. Check assumptions and integration points that the sub-agent could not see.
4. Run or review the relevant deterministic checks when they are available.
5. Reject, repair, or escalate incomplete, unsupported, contradictory, or out-of-scope work.

If a Luna result fails because the packet omitted a bounded fact, correct the packet and retry once. If the work instead requires broader context or more judgement than expected, stop repeated Luna retries. Move the subtask to Astra Medium or return it to the parent.

If an Astra result still requires broad parent context, a user decision, unavailable authority, or resolution of conflicting evidence, return control to the parent. Do not let model escalation silently broaden the requested task or its permissions.

## Completion

The parent may mark the task complete only after it has integrated the accepted sub-agent work and verified the overall result against the user's request. The final response must remain self-contained. Mention delegation details only when the user asks, or when model fallback, omitted verification, cost, or uncertainty materially affects the result.

When usage data is available, record enough information to evaluate the routing policy: assigned model, reasoning level, input and output tokens, latency, retries, verification effort, and whether the parent accepted the first result. Use these measurements to revise the policy instead of assuming that smaller-model delegation always saves resources.
