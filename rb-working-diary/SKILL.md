---
name: "rb-working-diary"
description: "Use when long-running or context-heavy work, including accumulated small turns, needs durable decisions, evidence, status, and next actions preserved across compaction, sessions, or handoffs. Do not use for an isolated one-turn task with no accumulated project state."
---

# RB Working Diary

Use this skill to preserve operational memory across compaction and future sessions.

## Canonical Location

Use the Codex diary root:

```text
${CODEX_HOME:-~/.codex}/diary/
```

The global index is:

```text
${CODEX_HOME:-~/.codex}/diary/diary.md
```

Project notes live under:

```text
${CODEX_HOME:-~/.codex}/diary/diary_<project-slug>/
```

Use lowercase ASCII slugs, replacing non-alphanumeric runs with hyphens.

## When To Use

Use the diary when any of these are true:

- the task is long-running, investigative, or likely to span compaction;
- you read many files, run meaningful experiments, or form conclusions future-you should not rediscover;
- a sequence of individually small turns has collectively accumulated substantial
  decisions, evidence, implementation state, verification results, or unresolved work;
- the user explicitly asks for durable continuity or cross-session notes;
- the repository has an existing diary entry whose state is needed for the current multi-step work.

For isolated one-turn tasks, skip diary reads and writes unless the user explicitly asks
for them. Do not treat the immediate request as isolated when the surrounding project or
conversation has already accumulated state that future work should not reconstruct.

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

Write facts and useful synthesis, not a transcript.

Good diary entries include:

- current objective and status;
- important files, symbols, commands, and results;
- hypotheses tested and conclusions;
- decisions and rejected alternatives when they matter;
- known risks, blockers, and unresolved questions;
- exact next steps for future-you.

Do not store secrets, credentials, private tokens, or large raw logs. Link to files or summarize outputs instead.

If another skill or project convention keeps a local progress file, such as `progress.md`, treat that file as project-local task history. Use the working diary for cross-session operational memory: summarize key state, decisions, and where to resume, and link to the project-local file rather than duplicating it.

## Update Rhythm

Update the diary:

- after substantial investigation or an important decision;
- before switching tasks or ending a session;
- before a likely compaction point when useful context is only in chat;
- after verification, especially if tests fail or are not run.
- Update the matching `Last touched` date in `diary.md` whenever a project diary
  is changed.

Prefer one compact update at each natural checkpoint over constant logging.

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
- Commands/checks:
- Next:
```

Omit empty fields. Keep entries brief enough that future-you can scan them quickly.
