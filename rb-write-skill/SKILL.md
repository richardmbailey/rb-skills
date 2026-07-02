---
name: "rb-write-skill"
description: "Use to write a new globally discoverable RB-style Codex skill in the canonical skills directory with clear trigger conditions, concise procedure, and useful bundled resources where needed."
---

# /rb:write-skill — write a new Codex skill

## Procedure

1. Identify the repeated workflow.
2. Define when the skill should be used.
3. Define required inputs.
4. Define step-by-step procedure.
5. Define outputs and failure modes.
6. Save it under the canonical pack `skills/<skill_name>/SKILL.md` when editing this pack. For Richard-owned workflow/support skills, use the `rb-` prefix unless the human explicitly asks for a general non-RB skill. For ad hoc personal skills outside this pack, use `$CODEX_HOME/skills/<skill_name>/SKILL.md`, or `~/.codex/skills/<skill_name>/SKILL.md` when `CODEX_HOME` is unset.
7. Write `SKILL.md` with only `name` and `description` in YAML frontmatter. Make `description` precise enough to trigger the skill before the body is loaded.
8. Add `agents/openai.yaml` with an `interface:` block containing quoted `display_name`, a 25-64 character `short_description`, and a `default_prompt` that mentions `$<skill_name>`.
9. Add `scripts/`, `references/`, or `assets/` only when they remove real repeated work. Reference any bundled resource directly from `SKILL.md`.
10. Validate that frontmatter parses, the folder name matches `name`, metadata follows the current schema, and no initializer TODOs remain.
11. Update `$rb-working-diary` with durable design decisions when the skill work is substantial or affects general working practice.
12. Use a repository-local skills directory only if the human explicitly asks, and explain that Codex auto-discovers the global skills directory, not arbitrary project-local skill folders.
