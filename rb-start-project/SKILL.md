---
name: "rb-start-project"
description: "Use when first onboarding a new or poorly understood project and the user needs repository discovery, setup questions, goals, constraints, testing and CI conventions, and workflow routing before coding. For a mature project with diary or handoff context, use $rb-continue-project."
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
- Do not invent domain assumptions, units, invariants, users, deployment targets, testing expectations, or success criteria.
- Before continuing into planning, plan execution, implementation, or review+fix, ask for explicit approval to proceed into the next workflow.

## Repository Inspection

1. Read `AGENTS.md` if present.
2. Use `$rb-working-diary`: check `${CODEX_HOME:-~/.codex}/diary/diary.md` for an existing entry matching the current project path.
3. Check whether `.rb-agent/` project resources exist.
4. Inspect top-level files and obvious build, test, coverage, lint, typing, formatting, packaging, pre-commit, and CI workflow files.
5. Read `README.md`, `CONTEXT.md`, and relevant docs if present.
6. Identify, without changing the repository:
   - focused unit-test commands;
   - integration, contract, migration, end-to-end, benchmark, or scientific-test commands;
   - coverage tooling and existing thresholds;
   - the closest canonical CI-equivalent local command;
   - checks that can run locally versus only in CI;
   - test-data, fixture, external-service, secret, container, hardware, or network requirements.
7. Give a short initial summary:
   - apparent project type;
   - important files found;
   - test levels and check commands discovered;
   - canonical CI-equivalent command or missing equivalent;
   - coverage thresholds and test-environment constraints;
   - missing setup information.

Continue with this global skill. `.rb-agent/` may contain project resources, prompts, templates, or workflows, but reusable skills are installed globally from the versioned `rb-skills` source repo.

## Question Sequence

Ask these in order unless the answer is already clear from the repository:

1. **Goal:** What is the main outcome you want from this project or session?
2. **Audience:** Who uses the code, product, analysis, or outputs?
3. **Current state:** Is this greenfield, existing but unfamiliar, active development, bug fixing, research/prototyping, or maintenance?
4. **First task:** What is the first concrete thing you want help with?
5. **Non-goals:** What should the agent avoid changing or deciding?
6. **Constraints:** What technical, time, dependency, privacy, deployment, or compatibility constraints matter?
7. **Run/check loop:** Which commands install, run, unit-test, integration-test, lint, type-check, format, build, benchmark, or validate the project, and which command best matches CI before completion?
8. **Test expectations:** Which boundaries and critical workflows require integration, contract, migration, end-to-end, stochastic, performance, security, concurrency, or recovery coverage? Are there existing coverage thresholds or flaky tests?
9. **Domain language:** What project-specific terms, units, invariants, assumptions, or trusted outputs should be captured?
10. **Definition of done:** What would make the first task acceptable, including required automated tests and checks?
11. **Autonomy:** Should the agent ask before editing, make focused edits after planning, or proceed through implementation, verification, and review+fix unless blocked?

## Workflow Routing

Route to the narrowest next workflow supported by the first task:

| First-task signal | Next workflow |
| --- | --- |
| Material behaviour, interface, edge cases, failure handling, test expectations, or acceptance criteria are unresolved | `$rb-discuss` |
| A sufficiently understood idea needs its first top-level plan | `$rb-create-implementation-plan` |
| An existing multi-step plan or phase checklist needs sequencing, status tracking, or phase-level verification | `$rb-execute-plan` |
| One bounded ordinary product change is agreed and ready to implement without plan-state ownership | `$rb-implement-with-tests` |
| Scientific, numerical, modelling, simulation, or domain-sensitive work is agreed | `$rb-tdd-scientific-code` |
| A bug, regression, failing test, flaky test, or surprising output has an unknown cause | `$rb-diagnose` |
| The user wants neutral orientation to an unfamiliar codebase | `$rb-explain-codebase` |
| The user wants structural critique or a refactoring strategy | `$rb-architecture-review` |
| The user wants defects found in a diff, branch, or pull request | `$rb-review-pr-or-diff` |

Use `$rb-name` syntax in Codex and `/rb-name` syntax in Claude Code. Do not force every project through every workflow. Recommend only the next justified step, ask for approval, and let that workflow route onward when its exit condition is met.

After implementation, require a review+fix cycle before completion: review small changes inline or use `$rb-review-pr-or-diff` for substantial changes, fix actionable findings, rerun affected focused, failure-path, integration, and CI-equivalent checks, and re-review until no blocking finding remains or the human accepts the residual risk.

If a named global skill is unavailable, run the equivalent bounded workflow inline and note that skill discovery may need installation or a session reload.

## Handoff

At the end of onboarding, provide:

- project summary;
- agreed constraints;
- test levels and test/check commands;
- canonical CI-equivalent command and checks available only remotely;
- coverage thresholds, fixture requirements, and known flaky tests;
- domain/context items to capture;
- first task and definition of done;
- recommended next workflow;
- exact handoff question.

For non-trivial projects, update `$rb-working-diary` with the project path, summary, constraints, testing/CI conventions, and next workflow before handoff.

Ask the handoff question for the route actually selected:

- unresolved feature requirements: `Proceed into the discuss session for the first task now?`
- agreed bounded ordinary change: `Proceed into implementation with tests now?`
- agreed scientific or modelling change: `Proceed into scientific TDD now?`
- existing implementation plan: `Proceed into verified plan execution now?`
- new top-level planning: `Proceed into implementation planning now?`
- unknown-cause bug or flaky test: `Proceed into diagnosis now?`

Do not route an agreed task through `$rb-discuss` merely because it is substantial.
