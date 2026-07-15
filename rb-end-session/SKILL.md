---
name: "rb-end-session"
description: "Use when the user wants to pause or close the current work, prepare durable continuity notes, or create a handoff brief for another agent session. For an ongoing project status report, use $rb-where-are-we."
---

# RB End Session

Use this skill to close one working session cleanly and prepare a new agent/session to continue without guessing.

## Core Workflow

1. Inspect current state:
   - run `git status --short`;
   - identify the current branch with `git branch --show-current`;
   - if useful, list recent commits with `git log --oneline -5`;
   - check for active phase/plan files, TODOs, or handoff notes.
2. Summarize the work:
   - current goal;
   - what changed in this session;
   - files edited or important files to read first;
   - commands/tests run and exact results;
   - uncommitted changes, if any;
   - blockers, risks, and known caveats;
   - next recommended task.
3. Create or update a project-local handoff file if the user asks for a durable handoff. Prefer:
   - `docs/end-session.md` for documented project work;
   - `AGENT_BRIEF.md` if the project already uses that convention;
   - an existing project-local handoff path when the project already uses one;
   - `.rb-agent/templates/AGENT_BRIEF.md` as a template when present.
4. Use `$rb-working-diary` for durable continuity when the session had meaningful investigation, decisions, unresolved risks, or compaction-prone context. Update `handoff.md` and, when helpful, `working-diary.md`.
5. Provide a paste-ready prompt for the next session.
6. If the user explicitly asks to end/archive the thread, use the available thread archive tool after the handoff is complete; in Codex desktop, prefer `set_thread_archived` over raw archive directives.

## Handoff Brief Shape

Use this structure unless the project already has a stronger convention:

```markdown
# RB End Session Brief

## Current Goal

## Current Status

## Recent Changes

## Files To Read First

## Commands And Results

## Git State

## Constraints And Project Rules

## Risks Or Caveats

## Next Recommended Step

## Prompt For Next Session
```

## Rules

- Do not hide uncommitted changes. Call them out clearly.
- Do not claim tests passed unless they were run in this session or the user explicitly provided that fact.
- Keep the next-session prompt short enough to paste, but include the exact repo path and immediate next task.
- Preserve project-specific workflow rules, especially phase checklist status, required test commands, security constraints, and no-fallback rules.
- Prefer a durable file when the context is large or the user is about to start a new session.
- Prefer the working diary for cross-session operational memory that should outlive the current repository checkout or chat thread.
