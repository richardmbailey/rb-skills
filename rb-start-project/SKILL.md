---
name: "rb-start-project"
description: "Use when first onboarding a new or poorly understood project and the user needs repository discovery, setup questions, goals, constraints, and workflow routing before coding. For a mature project with diary or handoff context, use $rb-continue-project."
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

Route to the narrowest next workflow supported by the first task:

| First-task signal | Next workflow |
| --- | --- |
| Material behaviour, interface, edge cases, or acceptance criteria are unresolved | `$rb-discuss` |
| A sufficiently understood idea needs its first top-level plan | `$rb-create-implementation-plan` |
| A plan, phase checklist, or issue list already exists and needs execution or verification | `$rb-execute-plan` |
| Ordinary product work is agreed and ready to implement | `$rb-implement-with-tests` |
| Scientific, numerical, modelling, simulation, or domain-sensitive work is agreed | `$rb-tdd-scientific-code` |
| A bug, regression, failing test, or surprising output has an unknown cause | `$rb-diagnose` |
| The user wants neutral orientation to an unfamiliar codebase | `$rb-explain-codebase` |
| The user wants structural critique or a refactoring strategy | `$rb-architecture-review` |
| The user wants defects found in a diff, branch, or pull request | `$rb-review-pr-or-diff` |

Use `$rb-name` syntax in Codex and `/rb-name` syntax in Claude Code. Do not force every project through every workflow. Recommend only the next justified step, ask for approval, and let that workflow route onward when its exit condition is met.

After implementation, require a review+fix cycle before completion: review small changes inline or use `$rb-review-pr-or-diff` for substantial changes, fix actionable findings, rerun affected checks, and re-review until no blocking finding remains or the human accepts the residual risk.

If a named global skill is unavailable, run the equivalent bounded workflow inline and note that skill discovery may need installation or a session reload.

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
