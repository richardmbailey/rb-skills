---
name: "rb-write-skill"
description: "Use when creating or updating an RB-style Codex or Claude Code skill in the rb-skills repository, including triggers, instructions, metadata, and resources. For behavioural tests of an existing skill, use $rb-create-skill-evals."
---

# RB Write Skill

Create or update reusable RB skills in the versioned `rb-skills` repository. Treat the repository copy as the source of truth and install from it only after the skill validates.

## Required decisions

Before editing, determine:

- the repeated workflow the skill will support;
- the conditions under which the skill must be selected;
- whether invocation is automatic or manual-only;
- the required inputs, procedure, outputs, and failure behaviour;
- the target agents: Codex, Claude Code, or both;
- whether scripts, references, assets, or behavioural evaluations are required.

If a missing decision would change the trigger boundary, required behaviour, permissions, outputs, or failure handling, ask the human before writing the affected rule.

## Procedure

1. Locate the versioned `rb-skills` repository. If its path cannot be found, ask the human for the path.
2. Create or update `<rb-skills-repo>/<skill_name>/`. Use the `rb-` prefix for a user-owned workflow or support skill unless the human explicitly requests a general non-RB skill.
3. Write `SKILL.md`:
   - include only `name` and `description` in YAML frontmatter;
   - make `name` identical to the skill directory name;
   - treat `description` as the selection contract that is available before the body loads;
   - for automatic invocation, describe the requests that should select the skill and important requests that should not;
   - for manual-only invocation, begin the description with `Manual invocation only`, name the accepted invocation forms, and state that task content alone must not select the skill;
   - define required inputs, ordered procedure, outputs, boundaries, and failure behaviour in the body.
4. After the first complete draft, apply `$rb-simplify-language` to `SKILL.md` and any agent-facing reference text. This user-owned procedure is an explicit instruction to invoke the manual-only language-review skill for the completed draft; the skill must not be selected during initial routing merely because the task is skill authoring. Preserve the intended trigger boundary, requirements, permissions, outputs, rationale, examples, and useful redundancy. If the review exposes a missing decision that would change behaviour, ask the human instead of inventing the answer.
5. Add `agents/openai.yaml` with an `interface:` block containing:
   - a quoted `display_name`;
   - a quoted `short_description` containing 25 to 64 characters;
   - a quoted `default_prompt` that mentions `$<skill_name>` and preserves the selected invocation mode.
6. Add `scripts/`, `references/`, or `assets/` only when they eliminate repeated instructions, parsing, validation, or asset recreation. Reference each bundled resource directly from `SKILL.md`.
7. Add or update behavioural evaluations when the trigger contract or required behaviour changes. Use `$rb-create-skill-evals` for the evaluation workflow.
8. Install or refresh the skill by running the repository sync script from the repository root:

   ```bash
   python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --skills <skill_name>
   ```

   If the human names one target agent, add `--agent codex` or `--agent claude`. If both agents are targets, run the command once per agent. Use `--replace` only after confirming that the existing installed skill directory may be backed up and replaced.
9. Validate each requirement separately:
   - YAML frontmatter parses;
   - the directory name equals `name`;
   - `agents/openai.yaml` follows the current metadata schema;
   - no initializer placeholder or TODO remains;
   - each referenced resource exists;
   - each behavioural-evaluation manifest validates;
   - each symlink installation resolves to the repository skill directory.
10. Hand off the result:
   - report the created or changed files and validation results;
   - report installation success or the exact failed stage;
   - tell the human to invoke `$<skill_name>` in Codex or `/<skill_name>` in Claude Code;
   - for automatic invocation, explain which matching requests should select the skill after reload;
   - for manual-only invocation, state that the skill remains inactive until the human explicitly invokes it.
11. Use `$rb-working-diary` when its trigger conditions are met. Record durable design decisions, validation evidence, omitted checks, and residual risks.

## Location boundary

Save user-owned global skills in the versioned `rb-skills` repository first. Do not author the source skill directly in an installed agent directory.

Use a repository-local skills directory only when the human explicitly requests one. Explain that Codex and Claude Code discover their configured global or personal skills directories. They do not discover an arbitrary project-local directory unless that agent supports the selected location.

## Completion check

Before completion, confirm that:

- the description expresses the intended automatic or manual-only trigger boundary;
- the first complete draft received the required `$rb-simplify-language` review;
- every required input, action, output, and failure response has an unambiguous owner;
- bundled resources and evaluations are referenced and valid;
- installation claims match observed sync results;
- the handoff does not claim automatic selection for a manual-only skill.
