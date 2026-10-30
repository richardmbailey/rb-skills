---
name: "rb-working-diary"
description: "Use when long-running or context-heavy work, including accumulated small turns, needs durable decisions, evidence, status, and next actions preserved across compaction, sessions, or handoffs. Do not use for an isolated one-turn task with no accumulated project state."
---

# RB Working Diary

Use this skill to preserve operational memory across compaction and future sessions.

## Canonical Location

Use the Codex diary root:

```text
${CODEX_HOME:-$HOME/.codex}/diary/
```

The global index is:

```text
${CODEX_HOME:-$HOME/.codex}/diary/diary.md
```

Project notes live under:

```text
${CODEX_HOME:-$HOME/.codex}/diary/diary_<project-slug>/
```

Use lowercase ASCII slugs, replacing non-alphanumeric runs with hyphens.

## When To Use

Use the diary when any of these are true:

- the task is long-running, investigative, or likely to span compaction;
- you read many files, run meaningful experiments, or form conclusions future-you should not rediscover;
- a sequence of individually small turns has collectively accumulated substantial decisions, evidence, implementation state, verification results, or unresolved work;
- the user explicitly asks for durable continuity or cross-session notes;
- the repository has an existing diary entry whose state is needed for the current multi-step work.

For isolated one-turn tasks, skip diary reads and writes unless the user explicitly asks for them. Do not treat the immediate request as isolated when the surrounding project or conversation has already accumulated state that future work should not reconstruct.

## Start Of Work

1. Resolve the diary root from `CODEX_HOME`; if unset, use `~/.codex`.
2. Read `diary.md` if it exists.
3. Match the current project by absolute path first, then by project name.
4. If a project diary exists, read only the files relevant to the current task. Start with `handoff.md` when present, then recent entries in `working-diary.md`.
5. If no project diary exists and the task is likely to need continuity, create it and add an index entry.

## Project Diary Files

Create files only as needed:

- `working-diary.md` - dated, compact notes about active work and current state.
- `investigations.md` - durable findings from code reading, experiments, benchmarks, failures, or root-cause work.
- `decisions.md` - decisions made, why they were made, and constraints they rely on.
- `open-questions.md` - unresolved questions, risks, assumptions, and follow-ups.
- `handoff.md` - where future-you should resume.

## What To Write

Write facts and useful synthesis, not a transcript. Keep one authoritative record for each decision or result. Link plans, sprint records, and local handoffs rather than repeating their contents.

Good diary entries include:

- current objective and status;
- important files, symbols, commands, and results;
- hypotheses tested and conclusions;
- decisions and rejected alternatives when they matter;
- known risks, blockers, and unresolved questions;
- exact next steps for future-you;
- changed behaviours and the selected test levels;
- focused, negative/boundary, integration, contract, migration, end-to-end, scientific, or agent-eval evidence as relevant;
- canonical CI-equivalent command and result, coverage status, fixtures/environment, and checks available only remotely;
- checks not run, stale evidence, and residual regression or scientific risk.

In continuity notes, distinguish agreed decisions, pending user choices and the work they block, investigations the agent can perform, and nonblocking risks. Keep recommendations separate from user agreements. Preserve the authorised next action so a new session can continue without reopening settled choices.

For an implementation plan using the optional constrained route, read `references/constrained-continuity.md` before recording its terminal handoff or resuming it. A resume pointer does not authorise execution. Ordinary project notes do not need constrained identities or status overlays.

Do not store secrets, credentials, private tokens, or large raw logs. Link to files or summarise outputs instead.

If another skill or project convention keeps a local progress file, such as `progress.md`, treat that file as project-local task history. Use the working diary for cross-session operational memory: summarise key state, decisions, and where to resume, and link to the project-local file rather than duplicating it.

## Update Rhythm

Update the diary:

- after substantial investigation or an important decision;
- before switching tasks or ending a session;
- before a likely compaction point when useful context is only in chat;
- after verification, especially if tests fail or are not run;
- whenever a CI-equivalent result, selected test level, coverage status, or residual risk materially changes.

Update the matching `Last touched` date in `diary.md` whenever a project diary is changed.

Prefer one compact update at each natural checkpoint over constant logging.

## Record progress without creating another verification cycle

At a natural checkpoint, record the user-visible outcome reached, the current blocker and the next authorised action. Link the existing test result, review or execution receipt that supports each important conclusion. Keep reusable evidence identifiable by its relevant version, data, configuration or environment. Record what would invalidate it when that is not obvious, so a later session can decide whether a rerun is needed.

Preserve failures, incomplete outputs, protected state and recovery boundaries. Summarise their significance and link the retained evidence instead of copying the full history into each entry. A new diary entry does not itself require another test, review or evidence report.

When progress is unexpectedly slow or the user raises efficiency concerns, use available timings to distinguish time spent on tests, model or workflow execution, review, recovery, installation and administration. Mark estimates as estimates, and leave unmeasured costs unknown. Do not invent a percentage breakdown or claim savings without a comparison. Use the existing diary or task record; do not create a separate measurement system unless it is needed for the task.

Measure progress by completed user outcomes and uncertainties resolved. Increasing test counts, review counts, commits or sprint numbers does not by itself show that the requested deliverable is closer to completion.

## Index Entry Shape

Use this shape in `diary.md`:

```markdown
## Projects

- **Project Name** - `/absolute/project/path`
  - Diary: `diary_project-slug/`
  - About: one short sentence.
  - Last touched: YYYY-MM-DD.
```

## Entry Shape

Use this shape for dated entries:

```markdown
## YYYY-MM-DD - Short Title

- Objective:
- Status:
- Findings:
- Decisions:
- Test levels / commands:
- CI / coverage / environment:
- Checks omitted / residual risk:
- Next:
```

Omit empty fields. Keep entries brief enough that future-you can scan them quickly.
