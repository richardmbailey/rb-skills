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
inspect repo -> establish pipeline state -> resolve discovery gates -> create product requirements when required -> plan -> implement -> verify -> hand off or complete
```

## Required Behaviour

- Do not write product code during onboarding.
- Ask one question at a time and wait for the human's answer.
- If repository files already answer a question, state the inferred answer and ask the human to confirm or correct it.
- Keep a short `Pipeline State` after each answer using the fields below.
- Do not invent domain assumptions, units, invariants, users, deployment targets, testing expectations, or success criteria.
- Do not mark a pipeline stage complete unless its exit evidence exists or the human explicitly accepts the missing evidence as a risk.
- If the human changes the goal or skips a stage, update `Pipeline State` and record the reason and consequence.
- Before entering a new workflow, obtain explicit approval unless the recorded autonomy decision already authorises that exact transition. Approval for one workflow does not authorise later workflows.

## New Project Pipeline

Use this pipeline to keep a new project moving. Give each stage one status: `not_started`, `in_progress`, `blocked`, `complete`, or `not_required`. Before marking a stage `not_required`, record why its exit evidence is unnecessary for this project.

| Stage | Exit evidence | Next workflow |
| --- | --- | --- |
| 1. Onboarding | Goal, users, project type, constraints, test/CI context, autonomy, and first deliverable are known. | Continue to the applicable discovery gate. |
| 2. Research premise | Any scientific, algorithmic, modelling, or novelty claim that controls product feasibility has been assessed, or this gate is `not required`. | `$rb-research-question-gate` when assessment is required. |
| 3. Requirements discussion | Material behaviour, interfaces, permissions, data rules, failure handling, and acceptance decisions are resolved or recorded as accepted risks, or this gate is `not required`. | `$rb-discuss` when material ambiguity remains. |
| 4. Product requirements | A PRD is `decision-ready`, or the PRD gate is `not required` with a recorded reason. | `$rb-create-prd` when the gate applies. |
| 5. Implementation planning | A top-level plan exists, its route is recorded, and the human has approved it for execution, or a plan is `not required` for one bounded agreed change. | `$rb-create-implementation-plan` or the bounded implementation skill. |
| 6. Implementation | The agreed change or all approved phases are implemented with the selected test levels and recorded evidence. | `$rb-execute-plan`, `$rb-implement-with-tests`, or `$rb-tdd-scientific-code`. |
| 7. Review and release readiness | Review findings are resolved or accepted, affected checks and the CI-equivalent gate are recorded, and rollout or handoff conditions are satisfied. | Inline review+fix or `$rb-review-pr-or-diff`. |
| 8. Completion or continuation | The outcome, residual risks, artifact locations, pipeline state, and exact next action are durable. | `$rb-end-session`, `$rb-working-diary`, or normal completion. |

Set Stage 4 to `in_progress` when the human requests a PRD, when the project creates a new product or service, or when product behaviour, users, permissions, data policy, success measures, or rollout need durable agreement across roles. A PRD is not required merely because a project is new. Set Stage 4 to `not_required` for a narrow bug fix, maintenance task, internal refactor, one-off analysis, or research without a product deliverable. Also set it to `not_required` when an existing authoritative requirements artifact covers the same decisions. Record the artifact or reason instead of silently skipping the stage.

## Pipeline State Record

Use these fields consistently:

```markdown
## Pipeline State

- Current stage: <1-8 and canonical stage name>
- Stage status: <not_started | in_progress | blocked | complete | not_required>
- Completed stages and evidence: <artifact paths, decisions, or check results>
- Not-required stages and reasons: <stage and reason>
- Active artifact: <path, status, and approval state>
- PRD: <required | not_required | decision-ready | approved, plus path or reason>
- Blocking decisions: <decision, owner, and effect>
- Approved transition: <exact next workflow or none>
- Next gate: <required exit evidence>
- Recommended next workflow: <$rb-name>
- Expected successor: <later workflow or completion condition>
```

`$rb-start-project` owns this record during onboarding. The active downstream workflow owns it after handoff. Update the durable diary record before each cross-session handoff or change of pipeline stage. `$rb-continue-project` restores the record. Do not rely on conversation memory as the only pipeline record.

## Repository Inspection

1. Read `AGENTS.md` if present.
2. Use `$rb-working-diary`: check `${CODEX_HOME:-~/.codex}/diary/diary.md` for an existing entry matching the current project path.
3. Check whether `.rb-agent/` project resources exist.
4. Inspect top-level files and obvious build, test, coverage, lint, typing, formatting, packaging, pre-commit, and CI workflow files.
5. Read `README.md`, `CONTEXT.md`, and relevant docs if present. Look for product briefs, research, PRDs, roadmaps, architecture decisions, implementation plans, issue trackers, and handoff records that establish a completed pipeline gate.
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
   - existing lifecycle artifacts and the pipeline gates they satisfy;
   - missing setup information.

Continue with this global skill. `.rb-agent/` may contain project resources, prompts, templates, or workflows, but reusable skills are installed globally from the versioned `rb-skills` source repo.

## Question Sequence

Ask these in order unless the answer is already clear from the repository. Stop the onboarding questions when the known facts are sufficient to choose and persist the next pipeline stage. Leave stage-specific detail to the workflow that owns that stage.

1. **Goal:** What is the main outcome you want from this project or session?
2. **Audience:** Who uses the code, product, analysis, or outputs?
3. **Current state:** Is this greenfield, existing but unfamiliar, active development, bug fixing, research/prototyping, or maintenance?
4. **Evidence and premise:** Which user research, operational evidence, scientific premise, policy, or stakeholder decision supports the project?
5. **Product-requirements gate:** Will this create a product, service, or substantial user-facing capability? Does an authoritative PRD or equivalent requirements artifact already exist?
6. **Decision ownership:** Who owns product decisions, technical decisions, approvals, and acceptance?
7. **First task:** What is the first concrete thing you want help with?
8. **Non-goals:** What should the agent avoid changing or deciding?
9. **Constraints:** What technical, time, dependency, privacy, deployment, or compatibility constraints matter?
10. **Run/check loop:** Which commands install, run, unit-test, integration-test, lint, type-check, format, build, benchmark, or validate the project, and which command best matches CI before completion?
11. **Test expectations:** Which boundaries and critical workflows require integration, contract, migration, end-to-end, stochastic, performance, security, concurrency, or recovery coverage? Are there existing coverage thresholds or flaky tests?
12. **Domain language:** What project-specific terms, units, invariants, assumptions, or trusted outputs should be captured?
13. **Definition of done:** What would make the first deliverable acceptable, including required automated tests and checks?
14. **Autonomy:** Which exact pipeline transitions, if any, may proceed without another confirmation? Stop at every material decision or permission boundary.

## Workflow Routing

Route to the narrowest next workflow supported by the first task:

| First-task signal | Next workflow |
| --- | --- |
| A research, scientific, modelling, algorithmic, or novelty premise must be assessed before product requirements are credible | `$rb-research-question-gate` |
| Material behaviour, interface, edge cases, failure handling, test expectations, or acceptance criteria are unresolved | `$rb-discuss` |
| The product or feature needs a durable requirements document before implementation planning | `$rb-create-prd` |
| A PRD or equivalent requirements artifact is decision-ready and needs its first top-level implementation plan | `$rb-create-implementation-plan` |
| A sufficiently understood idea needs its first top-level plan | `$rb-create-implementation-plan` |
| An existing multi-step plan or phase checklist needs sequencing, status tracking, or phase-level verification | `$rb-execute-plan` |
| One bounded ordinary product change is agreed and ready to implement without plan-state ownership | `$rb-implement-with-tests` |
| Scientific, numerical, modelling, simulation, or domain-sensitive work is agreed | `$rb-tdd-scientific-code` |
| A bug, regression, failing test, flaky test, or surprising output has an unknown cause | `$rb-diagnose` |
| The user wants neutral orientation to an unfamiliar codebase | `$rb-explain-codebase` |
| The user wants structural critique or a refactoring strategy | `$rb-architecture-review` |
| The user wants defects found in a diff, branch, or pull request | `$rb-review-pr-or-diff` |

Use `$rb-name` syntax in Codex and `/rb-name` syntax in Claude Code. Do not force every project through every workflow. Recommend the next workflow and show the later expected stages. Obtain approval as defined above, then hand off. Before the handoff, persist `Pipeline State` so the next session can recover the current stage and expected successor.

After implementation, require a review+fix cycle before completion: review small changes inline or use `$rb-review-pr-or-diff` for substantial changes, fix actionable findings, rerun affected focused, failure-path, integration, and CI-equivalent checks, and re-review until no blocking finding remains or the human accepts the residual risk.

If a named global skill is unavailable, run the equivalent bounded workflow inline and note that skill discovery may need installation or a session reload.

## Handoff

At the end of onboarding, provide:

- current pipeline stage and completed or `not required` gates;
- PRD applicability, status, and path or the recorded reason it is not required;
- active lifecycle artifacts and their approval status;
- project summary;
- agreed constraints;
- test levels and test/check commands;
- canonical CI-equivalent command and checks available only remotely;
- coverage thresholds, fixture requirements, and known flaky tests;
- domain/context items to capture;
- first task and definition of done;
- recommended next workflow;
- the expected workflow after that stage completes;
- exact handoff question.

If the project is expected to continue beyond the current turn, update `$rb-working-diary` before handoff. Store the `Pipeline State` fields, project path, constraints, and testing/CI conventions. This record lets `$rb-continue-project` resume the pipeline instead of restarting onboarding or guessing the next stage.

Ask the handoff question for the route actually selected:

- unresolved feature requirements: `Proceed into the discuss session for the first task now?`
- research premise: `Proceed into the research-question gate now?`
- product requirements document: `Proceed into PRD creation now?`
- agreed bounded ordinary change: `Proceed into implementation with tests now?`
- agreed scientific or modelling change: `Proceed into scientific TDD now?`
- existing implementation plan: `Proceed into verified plan execution now?`
- new top-level planning: `Proceed into implementation planning now?`
- unknown-cause bug or flaky test: `Proceed into diagnosis now?`

Do not route an agreed task through `$rb-discuss` merely because it is substantial.
