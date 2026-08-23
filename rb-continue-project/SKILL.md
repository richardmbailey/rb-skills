---
name: "rb-continue-project"
description: "Use when resuming a mature project from existing instructions, diary, handoff, and Git state, with a quick orientation before editing. Do not use for first onboarding. If the deliverable could instead be a standalone status artifact, clarify."
---

# RB Continue Project

## Purpose

Continue work in an existing or mature repository without losing prior context.

Use this when the human wants continuity from durable project context rather than first-time onboarding.

## Inputs

- Target repository path. Default to the current working directory.
- Optional current task from the human.
- Existing project context such as `AGENTS.md`, `CONTEXT.md`, README/docs, working diary files, handoff notes, plans, and git state.

## Procedure

1. Confirm the current working directory is the repository to continue. If uncertain, ask before proceeding.
2. Read repository-level agent instructions first:
   - `AGENTS.md` when present;
   - tool-specific instructions only when relevant to the current session.
3. Use `$rb-working-diary`:
   - read `${CODEX_HOME:-~/.codex}/diary/diary.md`;
   - match the current project by absolute path first, then by project name;
   - if a project diary exists, read `handoff.md` first when present, then recent `working-diary.md`;
   - read `decisions.md`, `open-questions.md`, or `investigations.md` only when the current task needs them.
4. Read project context files that explain the codebase:
   - `CONTEXT.md` when present;
   - `README.md` and nearby docs that describe setup, architecture, tests, or current work;
   - active implementation plans, issue notes, or project-local handoff files if clearly relevant.
5. Inspect read-only repo state:
   - top-level files and build, test, coverage, lint, typing, formatting, packaging, pre-commit, and CI configuration;
   - `git status --short`;
   - current branch;
   - recent commits when useful.
6. Recover the testing context established by prior work:
   - focused unit/property test commands;
   - integration, contract, migration, end-to-end, benchmark, scientific, or agent-eval commands;
   - canonical CI-equivalent command and checks available only remotely;
   - coverage tooling and existing thresholds;
   - fixture, service, secret, container, hardware, network, or test-data requirements;
   - known flaky or quarantined tests;
   - checks last run, their dates/context, omitted checks, and residual regression risk.
7. Recover `Pipeline State` when the project began through `$rb-start-project`:
   - current pipeline stage;
   - canonical stage status;
   - completed and `not required` gates with their evidence or reasons;
   - PRD applicability, status, and path;
   - active lifecycle artifacts and approval status;
   - blocking decisions and owners;
   - next gate, recommended skill, and expected successor.
   If the record is absent or stale, reconstruct only what repository and diary evidence supports. Mark every reconstructed or uncertain field.
8. Summarise before editing:
   - what the project is;
   - what prior sessions appear to have been doing;
   - current git/worktree state;
   - relevant test levels, commands, and CI-equivalent gate;
   - unresolved questions, blockers, risks, assumptions, and stale evidence;
   - recovered pipeline stage, completed gates, active artifact, and next gate;
   - recommended next action and matching RB workflow skill.
9. Stop and ask for approval before code edits, destructive commands, dependency changes, migrations, broad refactors, or entry into a pipeline workflow that the recorded autonomy decision did not authorise explicitly.

## Routing

Use the same routing rule as `$rb-start-project`:

- If a research, scientific, modelling, algorithmic, or novelty premise must be assessed before product requirements are credible, recommend `$rb-research-question-gate`.
- If material behaviour, interfaces, edge cases, failure handling, test expectations, or acceptance criteria remain unresolved, recommend `$rb-discuss`.
- If the project needs a durable PRD or an existing PRD must become decision-ready, recommend `$rb-create-prd`.
- If the requirements are sufficiently understood and a new top-level implementation plan is needed, recommend `$rb-create-implementation-plan`.
- If an existing multi-step implementation plan or phase checklist must be continued, refined, or tracked, recommend `$rb-execute-plan`.
- If one bounded ordinary change is already agreed and does not need plan-state ownership, recommend `$rb-implement-with-tests` directly.
- If an agreed change is scientific, numerical, modelling, simulation, stochastic, or domain-sensitive, recommend `$rb-tdd-scientific-code` directly.
- If the next step is a bug, regression, failing or flaky test, or surprising output with an unknown cause, recommend `$rb-diagnose`.
- If the next step is understanding an unfamiliar area, recommend `$rb-explain-codebase`.
- If the next step is structural review, recommend `$rb-architecture-review`.
- If the next step is reviewing changes, recommend `$rb-review-pr-or-diff`.
- If the user explicitly authorises the next workflow, continue with the selected skill.

Do not insert `$rb-discuss` merely because a change is substantial. Use it only when material ambiguity remains.

Before entering the selected workflow, update `Pipeline State` with its canonical stage and status, the exact approved transition, the exit evidence needed from that workflow, and the expected successor. Before a cross-session handoff or stage change, persist the updated record through `$rb-working-diary`.

## Required Behaviour

- Do not treat `/continue_project` or `/continue_session` as built-in slash commands; treat them as invocation phrases for this skill.
- Do not write product code during the continuity pass.
- Do not invent missing project history. State what was found and what is absent.
- Do not load every diary file by default. Start with handoff and recent working-diary entries, then expand only as needed.
- Do not claim tests passed unless they were run in this session or documented in the handoff with dates and context.
- Distinguish passed, failed, not run, unavailable, remote-only, and stale checks.
- Preserve user changes in the worktree. Report them rather than reverting them.

## Output

Provide a concise continuity brief:

```markdown
## Continuity Brief

- Project:
- Prior context:
- Current state:
- Test levels and commands:
- CI-equivalent gate:
- Coverage / fixtures / environment:
- Checks last run and omissions:
- Open questions / risks:
- Pipeline stage / status / completed evidence:
- PRD status / active artifact:
- Next gate / expected successor:
- Recommended next step:
```

Then ask whether to proceed with the recommended workflow.
