---
name: "rb-setup-local-agent-skills"
description: "Use to verify or repair RB global skill installation and project resource setup, including AGENTS.md, CONTEXT.md, .rb-agent prompts/templates/workflows, and Codex skill discovery. For normal project onboarding, use $rb-start-project."
---

# /rb:setup - verify RB Codex workflow setup

## Purpose

Use this skill when the RB workflow setup itself may be missing, stale, or confusing. For ordinary project onboarding, use `$rb-start-project` or `/start`.

## Procedure

1. Confirm the active Codex skills path. Default to `$CODEX_HOME/skills`, or `~/.codex/skills` when `CODEX_HOME` is unset.
2. Locate the canonical `_rb-agent-skills` source pack when possible. Prefer `RB_AGENT_SKILLS_PACK`, the current directory or its parents, or a sibling `_rb-agent-skills` directory.
3. Check that the expected global `rb-*` skills exist, especially `$rb-start-project`, `$rb-working-diary`, `$rb-grill-with-docs`, `$rb-implement-with-tests`, `$rb-diagnose`, `$rb-project-language`, and `$rb-review-pr-or-diff`.
4. If the pack source is available, run or recommend:

   ```bash
   python3 scripts/verify_pack.py
   python3 scripts/audit_skill_visibility.py
   ```

5. Treat non-RB skills in the active Codex skills directory as informational unless they conflict with RB skill names or discovery.
6. Read `AGENTS.md` if present; otherwise note the absence and continue.
7. Check whether `.rb-agent/` exists. It should contain project resources such as prompts, templates, and workflows, not skills.
8. Look for `CONTEXT.md`. If it exists, read it. If not, note the missing project context and propose creating it.
9. Identify likely entry points, tests, docs, scripts, notebooks, and configuration files.
10. Identify how to run tests or checks.
11. Use `$rb-working-diary`: check `${CODEX_HOME:-~/.codex}/diary/diary.md` for an existing entry matching the current project path.
12. Recommend `/start` for normal onboarding once setup is healthy.

## Required behaviour

Do not write code during setup unless the human explicitly asks.
Do not run destructive commands.
Do not infer scientific assumptions silently.
Do not flag unrelated non-RB personal skills as setup failures unless they break RB skill discovery.

## Output

- canonical pack source status
- global RB skill installation status
- project resource status
- important files/directories
- test/check commands found
- missing setup information
- recommended next setup or onboarding action
