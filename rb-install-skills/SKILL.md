---
name: "rb-install-skills"
description: "Use for the full RB setup workflow: install or verify global skills, prepare AGENTS.md and CONTEXT.md, check visibility, and begin onboarding. For synchronization use $rb-sync-skills-repo; for setup repair use $rb-setup-local-agent-skills."
---

# RB Install Skills

## Purpose

Install or verify the RB skills setup for the current repository in one pass, then continue into onboarding.

This is the setup entrypoint for new projects when the human wants global skills, project resources, and visibility checks prepared before normal start-project onboarding.

## Inputs

- Target repository path. Default to the current working directory.
- Pack root. Discover it from `--pack-root`, `RB_AGENT_SKILLS_PACK`, this script's source-pack ancestors, symlinked global skills, the current directory or target directory, a sibling `rb-skills` directory, or a legacy sibling `_rb-agent-skills` directory.
- Pack layout. The script supports:
  - the current flat `rb-skills` repo layout, where skill folders live directly at repo root and global install uses `rb-sync-skills-repo/scripts/sync_skills_repo.py`;
  - the legacy `_rb-agent-skills` layout, where skills live under `skills/` and project resources are installed by root `scripts/` helpers.
- Agent destination. Default `--agent auto` installs to Codex first when present, otherwise Claude Code. Use `--agent codex` or `--agent claude` to force the global skills target.
- Optional tool files: install `CODEX.md`, `CLAUDE.md`, or Cursor rules only when the human asks.
- Replacement flags: `--force` replaces managed project resource files only. `--replace-skills` backs up and replaces existing installed global skill folders during flat-pack sync.

## Procedure

1. Confirm the target path is the repository the human wants to prepare. If uncertain, ask before installing.
2. Run the bundled script:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-install-skills/scripts/install_skills.py" --target "$PWD"
   ```

   If the script cannot find the source pack, pass it explicitly or set `RB_AGENT_SKILLS_PACK`:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-install-skills/scripts/install_skills.py" --target "$PWD" --pack-root /path/to/rb-skills
   ```

   If working from this flat repo before the skill is installed globally, run:

   ```bash
   python3 rb-install-skills/scripts/install_skills.py --target "$PWD"
   ```

3. If the active agent target is not the default, add `--agent codex` or `--agent claude`.
4. If the human asks for optional tool files, add `--codex`, `--claude`, or `--cursor`. If existing managed project resource files should be overwritten, add `--force`. If existing installed global skill folders should be backed up and replaced, add `--replace-skills` only after confirming that is intended.
5. Read the script output. It should:
   - install or verify global skills under Codex's skills directory or Claude Code's `~/.claude/skills`;
   - for the flat repo layout, install skills by symlink using `$rb-sync-skills-repo`'s bundled script;
   - for the flat repo layout, create minimal `AGENTS.md` and `CONTEXT.md` project resources when missing;
   - for the legacy layout, use the legacy project-resource installer;
   - verify flat-layout installed skills are symlinks back to the selected `rb-skills` repo;
   - confirm `.rb-agent/skills` was not created.
6. If installation succeeds, continue into `$rb-start-project` onboarding in Codex or `/rb-start-project` onboarding in Claude Code.

## Required behaviour

- Do not install into a target path unless it is clear which existing repository should be prepared.
- Do not create a missing target directory silently; ask the human to create or identify the repository first.
- Do not create or preserve project-local skills; skills have one source of truth in the versioned skills pack and are installed globally.
- In the flat `rb-skills` layout, treat the repo root as the source of truth and global skills as symlinks into it.
- Do not use `--force` as permission to replace global skills. Use `--replace-skills` only when the human has agreed to replace existing installed skill folders.
- Do not treat an existing copied skill folder as a successful flat-layout install. If the visibility audit reports existing folders that are not symlinks to the repo, ask before rerunning with `--replace-skills`.
- If the pack root cannot be found, ask the human for the path to `rb-skills` or set `RB_AGENT_SKILLS_PACK`.
- If a command fails, report the failed command and do not pretend onboarding completed.

## Output

- global skill installation status;
- project resource installation status;
- visibility audit result;
- next onboarding action, usually `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.
