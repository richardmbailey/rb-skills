---
name: "rb-install-skills"
description: "Use for the full RB setup workflow: install or verify global skills, prepare AGENTS.md and CONTEXT.md, check visibility, and begin onboarding. For synchronization use $rb-sync-skills-repo; for setup repair use $rb-setup-local-agent-skills."
---

# RB Install Skills

## Purpose

Install or verify the RB skills setup for the current repository. Continue into onboarding when the user has requested it.

This is the setup entrypoint for new projects when the human wants global skills, project resources, and visibility checks prepared before normal start-project onboarding.

## Inputs

- Target repository path. Default to the current working directory.
- Pack root. Discover it from `--pack-root`, `RB_AGENT_SKILLS_PACK`, this script's source-pack ancestors, symlinked global skills, the current directory or target directory, a sibling `rb-skills` directory, or a legacy sibling `_rb-agent-skills` directory.
- Pack layout. The script supports:
  - the current flat `rb-skills` repo layout, where skill folders live directly at repo root and global install uses `rb-sync-skills-repo/scripts/sync_skills_repo.py`;
  - the legacy `_rb-agent-skills` layout, where skills live under `skills/` and project resources are installed by root `scripts/` helpers.
- Agent destination. Default `--agent auto` installs to Codex first when present, otherwise Claude Code. Use `--agent codex` or `--agent claude` to force the global skills target.
- Tool files: a flat-pack Claude target creates a missing `CLAUDE.md` bridge automatically. For other targets, add `CLAUDE.md` with `--claude` only when requested. Cursor rules remain optional. Codex project instructions belong in `AGENTS.md`; `CODEX.md` is ignored unless the user has configured it as a fallback filename.
- Replacement flags: `--force` replaces managed project resource files only. `--replace-skills` backs up and replaces existing installed global skill folders during flat-pack sync.

## Procedure

1. Confirm the target path is the repository the human wants to prepare. If uncertain, ask before installing.
2. Run the bundled script:

   ```bash
   python3 "$HOME/.agents/skills/rb-install-skills/scripts/install_skills.py" --target "$PWD"
   ```

   If the script cannot find the source pack, pass it explicitly or set `RB_AGENT_SKILLS_PACK`:

   ```bash
   python3 "$HOME/.agents/skills/rb-install-skills/scripts/install_skills.py" --target "$PWD" --pack-root /path/to/rb-skills
   ```

   If working from this flat repo before the skill is installed globally, run:

   ```bash
   python3 rb-install-skills/scripts/install_skills.py --target "$PWD"
   ```

3. Add `--agent codex` or `--agent claude` to match the requested target. For Claude, execute the source repository's script. Recover its path from an installed edition's `.rb-claude-install.json` marker or an explicit `--pack-root`. Keep `--target` set to the project selected in step 1 if you change working directory.
4. If the human asks for optional tool files, add `--claude` or `--cursor`. `AGENTS.md` is installed without an extra flag; flat-pack Claude targets also create a missing `CLAUDE.md` bridge without `--claude`. If existing managed project resource files should be overwritten, add `--force`. If existing installed global skill folders should be backed up and replaced, add `--replace-skills` only after confirming that is intended.
5. Read the script output. It should:
   - install or verify global skills under Codex's `$HOME/.agents/skills` or Claude Code's `~/.claude/skills`;
   - for the flat repo layout, use `$rb-sync-skills-repo`'s bundled script to install Codex symlinks or generate supported Claude editions;
   - for the flat repo layout, create minimal `AGENTS.md` and `CONTEXT.md` project resources when missing;
   - for the legacy layout, use the legacy project-resource installer;
   - verify Codex symlinks point to the selected `rb-skills` repo, or verify Claude generated content through the Claude installer's `--check`;
   - confirm `.rb-agent/skills` was not created.
6. If installation succeeds and the request includes onboarding, continue into `$rb-start-project` in Codex or `/rb-start-project` in Claude Code. For installation-only or verification-only work, report the result and stop; do not begin a project interview solely because installation succeeded.

## Required behaviour

- Do not install into a target path unless it is clear which existing repository should be prepared.
- Do not create a missing target directory silently; ask the human to create or identify the repository first.
- Do not create or preserve project-local skills; skills have one source of truth in the versioned skills pack and are installed globally.
- In the flat `rb-skills` layout, treat the repo root as the source of truth. Codex global skills are symlinks into it; Claude editions are generated copies refreshed from it.
- Do not use `--force` as permission to replace global skills. Use `--replace-skills` only when the human has agreed to replace existing installed skill folders.
- For Codex, do not treat an existing copied skill folder as a successful flat-layout install. If the visibility audit reports existing folders that are not symlinks to the repo, ask before rerunning with `--replace-skills`.
- For Claude, verify generated content and permissions, not just the marker. Preserve modified or foreign copies unless replacement is authorised; the installer backs them up before replacement.
- If the pack root cannot be found, ask the human for the path to `rb-skills` or set `RB_AGENT_SKILLS_PACK`.
- If a command fails, report the failed command and do not pretend onboarding completed.

## Output

- global skill installation status;
- project resource installation status;
- visibility audit result;
- next onboarding action, usually `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.
