---
name: "rb-write-skill"
description: "Use to create or update a globally discoverable RB-style Codex or Claude Code skill in the versioned rb-skills repo, with clear trigger conditions, concise procedure, and useful bundled resources where needed."
---

# RB Write Skill

## Procedure

1. Identify the repeated workflow.
2. Define when the skill should be used.
3. Define required inputs.
4. Define step-by-step procedure.
5. Define outputs and failure modes.
6. Save Richard-owned global skills in the versioned `rb-skills` repo first, not directly in an installed agent directory. Prefer `<rb-skills-repo>/<skill_name>/`, where `<rb-skills-repo>` is the clone being edited; if the source repo cannot be found, ask for its path. Use the `rb-` prefix for Richard-owned workflow/support skills unless the human explicitly asks for a general non-RB skill.
7. Write `SKILL.md` with only `name` and `description` in YAML frontmatter. Make `description` precise enough to trigger the skill before the body is loaded.
8. Add `agents/openai.yaml` with an `interface:` block containing quoted `display_name`, a 25-64 character `short_description`, and a `default_prompt` that mentions `$<skill_name>`.
9. Add `scripts/`, `references/`, or `assets/` only when they remove real repeated work. Reference any bundled resource directly from `SKILL.md`.
10. Install or refresh the skill into the active agent by running the repo sync script from the repo root:

   ```bash
   python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --skills <skill_name>
   ```

   Use `--agent codex` or `--agent claude` when the target agent must be explicit. Use `--replace` only after confirming an existing installed skill folder should be backed up and replaced.
11. Validate that frontmatter parses, the folder name matches `name`, metadata follows the current schema, no initializer TODOs remain, and the installed path points back to the repo when symlink mode was used.
12. Tell the human how to invoke the skill directly: `$<skill_name>` in Codex and `/<skill_name>` in Claude Code. Also note that matching requests should trigger the skill automatically after the agent reloads.
13. Update `$rb-working-diary` with durable design decisions when the skill work is substantial or affects general working practice.
14. Use a repository-local skills directory only if the human explicitly asks, and explain that Codex and Claude Code discover their configured global/personal skills directories, not arbitrary project-local skill folders unless that agent specifically supports the project-local location being used.
