---
name: "rb-start-project"
description: "Use when the user invokes rb-start-project, asks to start a new project, onboard a repository, set up an agent-guided project workflow, run project onboarding, or be guided through setup questions before coding. Works globally from any folder; uses .rb-agent only for project resources when present."
---

# RB Start Project

Use this skill as the global start-project entrypoint for guided project onboarding.

## Invocation

```text
Codex: $rb-start-project
Claude Code: /rb-start-project
```

## Goal

Guide the human from an unstructured new project or unfamiliar repository into a clear first workflow:

```text
inspect repo -> ask setup questions -> summarise answers -> propose context updates -> route through the right planning, execution, implementation, or review+fix workflow
```

## Required Behaviour

- Do not write product code during onboarding.
- Ask one question at a time and wait for the human's answer.
- If repository files already answer a question, state the inferred answer and ask the human to confirm or correct it.
- Keep a short onboarding state after each answer: known facts, unresolved questions, next question.
- Do not invent domain assumptions, units, invariants, users, deployment targets, or success criteria.
- Before continuing into planning, plan execution, implementation, or review+fix, ask for explicit approval to proceed into the next workflow.

## Repository Inspection

1. Read `AGENTS.md` if present.
2. Use `$rb-working-diary`: check `${CODEX_HOME:-~/.codex}/diary/diary.md` for an existing entry matching the current project path.
3. Check whether `.rb-agent/` project resources exist.
4. Inspect top-level files and obvious build/test files.
5. Read `README.md`, `CONTEXT.md`, and relevant docs if present.
6. Give a short initial summary:
   - apparent project type
   - important files found
   - test/check commands discovered
   - missing setup information

Continue with this global skill. `.rb-agent/` may contain project resources, prompts, templates, or workflows, but reusable skills are installed globally from the versioned `rb-skills` source repo.

## Question Sequence

Ask these in order unless the answer is already clear from the repository:

1. **Goal:** What is the main outcome you want from this project or session?
2. **Audience:** Who uses the code, product, analysis, or outputs?
3. **Current state:** Is this greenfield, existing but unfamiliar, active development, bug fixing, research/prototyping, or maintenance?
4. **First task:** What is the first concrete thing you want help with?
5. **Non-goals:** What should the agent avoid changing or deciding?
6. **Constraints:** What technical, time, dependency, privacy, deployment, or compatibility constraints matter?
7. **Run/check loop:** How should the agent install, run, test, lint, benchmark, or validate work?
8. **Domain language:** What project-specific terms, units, invariants, assumptions, or trusted outputs should be captured?
9. **Definition of done:** What would make the first task acceptable?
10. **Autonomy:** Should the agent ask before editing, make focused edits after planning, or proceed through implementation, verification, and review+fix unless blocked?

## Workflow Routing

Choose the next workflow from the first task:

- New feature or meaningful product/code change: clarify requirements first, create or confirm the implementation plan for non-trivial work, use `$rb-execute-plan` when the plan needs granular phases or verification gates, then use `$rb-implement-with-tests` after plan approval, ending with review+fix.
- Scientific, numerical, modelling, simulation, or domain-sensitive change: clarify requirements first, create or confirm the implementation plan for non-trivial work, use `$rb-execute-plan` when the plan needs granular phases or verification gates, then use `$rb-tdd-scientific-code` after plan approval, ending with review+fix.
- Bug, regression, failing test, or surprising output: diagnose before proposing a fix.
- Vague idea, product direction, or planning request: create an implementation plan, then use `$rb-execute-plan` if the human wants to turn the approved plan into executable phase work, and optionally split into issues.
- Unfamiliar existing codebase with no immediate change request: explain the codebase structure.
- Structural concerns, boundaries, maintainability, or refactoring strategy: architecture review.
- Review requested for a diff, branch, or PR: review.

Name the matching global RB skill. Use `$rb-name` syntax in Codex and `/rb-name` syntax in Claude Code:

- ordinary implementation: `$rb-discuss`, then `$rb-create-implementation-plan` for non-trivial work, then `$rb-execute-plan` when phase execution or verification gates are needed, then `$rb-implement-with-tests`, then review+fix
- scientific implementation: `$rb-discuss`, then `$rb-create-implementation-plan` for non-trivial work, then `$rb-execute-plan` when phase execution or verification gates are needed, then `$rb-tdd-scientific-code`, then review+fix
- bug work: `$rb-diagnose`
- planning: `$rb-create-implementation-plan`, then `$rb-execute-plan` if the plan is ready to execute, then optionally `$rb-create-issues`
- unfamiliar codebase: `$rb-explain-codebase`
- architecture: `$rb-architecture-review`
- review: `$rb-review-pr-or-diff`

## Guided Implementation Sequence

For non-trivial feature or project work, guide the human through this sequence unless the repository or human request clearly calls for a shorter route:

```text
$rb-discuss -> $rb-create-implementation-plan -> $rb-execute-plan -> implementation skill -> review+fix
```

Use `$rb-execute-plan` as the bridge between approved planning and coding when the work needs phase checklists, walking-skeleton sequencing, task status updates, or verification gates. Skip it for small, well-scoped changes where `$rb-discuss` can produce a sufficient short plan and the human approves moving directly to implementation.

After implementation, run a review+fix cycle before treating the work as complete: self-review small changes inline or use `$rb-review-pr-or-diff` for substantial diffs, fix actionable findings, rerun relevant checks, and re-review until no blocking findings remain or remaining risks are explicitly accepted.

If a named global skill is not available in the current session, run the equivalent workflow inline and note that the global skills may need to be installed or the session reloaded.

## Handoff

At the end of onboarding, provide:

- project summary
- agreed constraints
- test/check commands
- domain/context items to capture
- first task and definition of done
- recommended next workflow
- exact handoff question

For non-trivial projects, update `$rb-working-diary` with the project path, summary, constraints, and next workflow before handoff.

For feature work, ask:

```text
Proceed into the discuss session for the first task now? After requirements are resolved, I will continue into implementation planning, plan execution, implementation, and review+fix only after you approve each step.
```

For bug work, ask:

```text
Proceed into diagnosis now?
```

For planning work, ask:

```text
Proceed into implementation planning now? Once the plan is approved, I can use $rb-execute-plan to turn it into verified phase work.
```

## Inline Discuss Fallback

If the human approves feature-work handoff and `$rb-discuss` is not available:

1. Restate the requested change.
2. Identify ambiguous behavior, interface, edge cases, failure modes, compatibility constraints, and tests.
3. Ask targeted questions one at a time.
4. Stop before coding.
5. Produce a short implementation plan and ask for approval before implementation edits.
