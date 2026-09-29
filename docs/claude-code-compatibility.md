# Claude Code compatibility

The repository has a separate Claude installation profile. It derives ordinary workflows from shared sources, supplies Claude host instructions, and replaces the Codex delegation procedure with a Claude edition. The top-level skill text, Codex metadata, model defaults, and constrained runtime are unchanged by this compatibility work.

## What is installed

`platforms/claude/profile.json` classifies every active skill. An unclassified new skill stops generation until its compatibility is decided. Twenty-eight shared skills are included, plus the Claude delegation override, for 29 installed skills.

Five remain excluded: `rb-context-tokens`, `rb-create-low-level-plan`, `rb-assess-plan-safety`, `rb-safe-operation`, and `rb-create-safe-operation-policy`. Their Codex session format, provider identity, exact run authority, and runtime assumptions are not translated. Standard planning, execution, and sprint workflows remain available.

The source layout is:

- [profile.json](../platforms/claude/profile.json): supported, overridden, excluded, and manual-only skills.
- [preamble.md](../platforms/claude/preamble.md): host rules inserted into generated skills.
- [Claude rb-delegate](../platforms/claude/skills/rb-delegate/SKILL.md): model choice and native delegation procedure.
- [install.py](../platforms/claude/install.py): generation, content validation, backup, and refresh.

Claude supports `SKILL.md`, supporting resources, and `/skill-name` invocation. Generated copies retain those resources and omit Codex's `agents/openai.yaml`. [Official skills documentation](https://code.claude.com/docs/en/skills).

## Installation and refresh

Use the [README commands](../README.md#claude-code-compatibility). `--agent claude` routes the RB sync through the Claude generator. Codex and generic non-RB synchronization keep their existing behaviour. Always pass the agent explicitly on a machine with both products; automatic destination selection still prefers Codex.

The Claude generator writes real directories, not links into shared source. Each has a `.rb-claude-install.json` marker containing its source repository, content hashes, and file permissions. `--check` compares installed content and permissions with what the current source would generate. A correct marker alone is insufficient.

Re-running installation updates unmodified generated copies. Existing links, foreign directories, and locally modified copies are preserved unless `--replace` is supplied; replacement saves a backup. A dry-run writes nothing. Conflicts are checked before installation, generated files are staged, and a failed replacement is rolled back. Excluded legacy directories block installation rather than remaining discoverable or being deleted automatically. Review and move such directories before retrying.

Do not edit generated copies as source. Keep common changes in the versioned top-level skills and Claude-only changes under `platforms/claude/`. Re-run the generator after either changes. Do not set `CODEX_HOME` to a Claude directory.

## Project instructions and continuity

The full project installer now creates a missing `CLAUDE.md` bridge automatically for a Claude target. It imports `AGENTS.md` instead of duplicating shared policy and adds the Claude model-choice and runtime boundaries. Existing `CLAUDE.md`, `AGENTS.md`, and `CONTEXT.md` files remain untouched unless explicit force is requested. An existing bridge should be checked by its owner; successful skill installation does not prove every pre-existing project instruction is suitable.

The repository itself has a [CLAUDE.md](../CLAUDE.md) bridge. The locally observed Claude CLI is 2.1.275; an explicit import supports that version, while current documentation describes direct `AGENTS.md` support from 2.1.277 subject to configuration. [Official project-instruction documentation](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools).

The RB diary remains shared Markdown at `${CODEX_HOME:-$HOME/.codex}/diary/`. Claude uses filesystem access to the same history; this is not Claude automatic memory. An explicitly chosen alternative canonical root applies consistently to onboarding, continuation, setup, and handoff. There is no automatic migration or second diary.

## Delegation and manual invocation

Claude's `rb-delegate` has no fixed model. It asks for a model available in the user's setup, or explicit permission to inherit the parent model, before dispatch. A prior choice is reused only within its authorised scope. An unavailable choice produces a visible question rather than a silent substitution. A small task that does not benefit from delegation needs no model question. The parent retains integration, verification, and completion judgement.

Native Claude subagents can perform independent review; model and tool controls must be supported by the active interface. The selected reviewer must not have implemented the change. If required review cannot run, the task stays implemented rather than verified. Codex's GPT defaults and delegation parameters are not copied into this edition. [Official subagent documentation](https://code.claude.com/docs/en/sub-agents).

Generated `rb-simplify-language` frontmatter includes `disable-model-invocation: true`. No user settings rewrite is needed. Claude's `user-invocable: false` is not the manual-only control. [Official invocation controls](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill).

The authorised post-draft review in `rb-write-skill` is generated as an explicit read of `references/claude-language-review/SKILL.md`, with supporting resources bundled alongside it. This uses the method within the already-authorised authoring procedure. It does not call the disabled manual Skill tool or enable discovery for unrelated tasks. Changes to the shared post-draft step require a reviewed exporter update; a missing replacement anchor fails generation.

## Validation

Installation tests cover exported resources and invocation metadata, unsupported requests, dry-run behaviour, source preservation, refresh, local edits, backups, content drift, and failure recovery. Project-setup tests cover the shared-policy import, preservation of existing files, generated-copy verification, source discovery, and unchanged Codex setup. Repository CI includes these tests and the Claude delegation evaluation manifest.

All 46 skill regression tests pass under Python 3.12, including 27 exporter tests and seven Claude setup tests. Setup regressions reproduced four missing behaviours before the fixes; five additional permission and preview regressions also failed before their fixes. Metadata, instruction contracts, consistency contracts, all 29 evaluation manifests, compilation, and whitespace checks pass. Runtime source is unchanged, so the constrained-runtime suite was not repeated for this installation change; this is not a full remote CI result.

The 29 Claude editions were installed locally and passed `--check`, including generated frontmatter parsing. Six pre-existing Claude symlinks were backed up and replaced; their shared targets were not edited. All 34 Codex links still point to the same sources. Comparison against the start of this task confirms that the only changed pre-existing `rb-*` files are the two shared installation scripts with their Claude branches. No Claude account settings were changed.

The delegation manifest covers missing, reused, inherited, unavailable, and out-of-scope model choices, unnecessary delegation, and unavailable required review. Manifest validity is not proof of model behaviour.

Live Claude model trials are not completed: the local CLI's authentication status reports `loggedIn: false`. No alternative account, API key, or provider was substituted. After authentication, run matched with-skill/without-skill trials using these cases, plus a bounded bug fix, shared-diary continuation, and HTML artifact validation. Earlier Codex probes do not establish Claude performance.
