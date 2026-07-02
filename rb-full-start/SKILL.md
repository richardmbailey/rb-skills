---
name: "rb-full-start"
description: "Use when the user asks for rb-full-start, full_start, full installation, full project setup, or wants Codex to prepare a repository end-to-end with RB global skills, project resources, AGENTS.md, CONTEXT.md, visibility checks, and then begin /start onboarding."
---

# RB Full Start

## Purpose

Prepare the current repository for RB Codex work in one pass, then continue into onboarding.

This is the convenient entrypoint for new projects when the human wants everything installed rather than only running `/start`.

## Inputs

- Target repository path. Default to the current working directory.
- Pack root. Discover it from `--pack-root`, `RB_AGENT_SKILLS_PACK`, this script's source-pack ancestors, the current directory or target directory, or a sibling `_rb-agent-skills` directory.
- Optional tool files: install `CODEX.md`, `CLAUDE.md`, or Cursor rules only when the human asks.

## Procedure

1. Confirm the target path is the repository the human wants to prepare. If uncertain, ask before installing.
2. Run the bundled script:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-full-start/scripts/full_start.py" --target "$PWD"
   ```

   If the script cannot find the source pack, pass it explicitly or set `RB_AGENT_SKILLS_PACK`:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-full-start/scripts/full_start.py" --target "$PWD" --pack-root /path/to/_rb-agent-skills
   ```

   If working from this pack source directory before the skill is installed globally, run:

   ```bash
   python3 skills/rb-full-start/scripts/full_start.py --target "$PWD"
   ```

3. If the human asks for optional tool files, add `--codex`, `--claude`, or `--cursor`.
4. Read the script output. It should:
   - install canonical skills from the pack `skills/` directory into `${CODEX_HOME:-~/.codex}/skills`;
   - install project resources into the target repository;
   - verify skill source and active visibility;
   - confirm `.rb-agent/skills` was not created.
5. If installation succeeds, continue into `/start` or `$rb-start-project` onboarding in the target repository.

## Required behaviour

- Do not install into a target path unless it is clear which existing repository should be prepared.
- Do not create a missing target directory silently; ask the human to create or identify the repository first.
- Do not create or preserve project-local skills; skills have one source of truth in the pack `skills/` directory and are installed globally.
- If the pack root cannot be found, ask the human for the path to `_rb-agent-skills` or set `RB_AGENT_SKILLS_PACK`.
- If a command fails, report the failed command and do not pretend onboarding completed.

## Output

- global skill installation status;
- project resource installation status;
- visibility audit result;
- next onboarding action, usually `/start`.
