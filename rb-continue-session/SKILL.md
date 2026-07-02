---
name: "rb-continue-session"
description: "Use when the user asks for /continue_session, continue_session, rb-continue-session, $rb-continue-session, resume this repo, continue from the working diary, continue from the latest handoff, or wants a new session in a mature codebase to orient from existing project instructions, diary notes, handoff notes, git state, and then summarise before editing."
---

# RB Continue Session

## Purpose

Resume work in an existing or mature repository without losing prior context.

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
   - top-level files and obvious build/test configuration;
   - `git status --short`;
   - current branch;
   - recent commits when useful.
6. Summarise before editing:
   - what the project is;
   - what prior sessions appear to have been doing;
   - current git/worktree state;
   - relevant commands for running, testing, linting, or validating;
   - unresolved questions, blockers, risks, and assumptions;
   - recommended next action and matching RB workflow skill.
7. Stop and ask for approval before code edits, destructive commands, dependency changes, migrations, or broad refactors.

## Routing

- If the next step is ordinary feature or product work, recommend `$rb-clarify` before `$rb-implement-with-tests`.
- If the next step is scientific, numerical, modelling, simulation, or domain-sensitive work, recommend `$rb-clarify` before `$rb-tdd-scientific-code`.
- If the next step is a bug, regression, failing test, or surprising output, recommend `$rb-diagnose`.
- If the next step is understanding an unfamiliar area, recommend `$rb-zoom-out`.
- If the next step is structural review, recommend `$rb-architecture-review`.
- If the next step is reviewing changes, recommend `$rb-review-pr-or-diff`.
- If the user explicitly authorises the next workflow, continue with the selected skill.

## Required Behaviour

- Do not treat `/continue_session` as a built-in slash command; treat it as an invocation phrase for this skill.
- Do not write product code during the continuity pass.
- Do not invent missing project history. State what was found and what is absent.
- Do not load every diary file by default. Start with handoff and recent working-diary entries, then expand only as needed.
- Do not claim tests passed unless they were run in this session or documented in the handoff with dates/context.
- Preserve user changes in the worktree. Report them rather than reverting them.

## Output

Provide a concise continuity brief:

```markdown
## Continuity Brief

- Project:
- Prior context:
- Current state:
- Commands/checks:
- Open questions/risks:
- Recommended next step:
```

Then ask whether to proceed with the recommended workflow.
