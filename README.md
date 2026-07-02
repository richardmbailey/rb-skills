# RB Agent Skills

This repository contains reusable skills for Richard's preferred Codex and Claude Code workflows. A skill is a directory with a `SKILL.md` file and, optionally, supporting `agents/`, `scripts/`, `references/`, or `assets/` folders.

The pack is designed to be cloned, versioned with Git, and installed by symlinking the skill folders into the active agent's skills directory.

Codex uses:

```text
${CODEX_HOME:-$HOME/.codex}/skills
```

Claude Code personal skills use:

```text
$HOME/.claude/skills
```

After installation, open the agent in the project you want to work on and start with `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.

## Quick Start

On a new computer:

```bash
git clone <repo-url> ~/src/rb-skills
cd ~/src/rb-skills
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink
```

The installer chooses the destination automatically. It tries Codex first when `$CODEX_HOME` or `~/.codex` exists. If Codex is not present and Claude Code is detected, it installs to `~/.claude/skills`.

Restart Codex after installing for Codex. For Claude Code, restart if `~/.claude/skills` was newly created; otherwise edits under that directory are usually detected live.

Then open the project or repository you want to work on and type one of:

```text
Codex: $rb-start-project
Claude Code: /rb-start-project
```

`rb-start-project` inspects the repository, asks setup questions, records useful context, and routes the session to the right workflow.

## What These Skills Are For

These skills are not a framework you run directly. They are reusable instructions Codex or Claude Code can discover and apply when you ask for a matching workflow.

Use them to:

- start new coding or research projects in a structured way;
- onboard an unfamiliar repository before editing;
- clarify requirements before implementation;
- debug bugs and failing tests without jumping to fixes too early;
- implement changes with focused tests and checks;
- handle scientific, modelling, numerical, or domain-sensitive code carefully;
- review diffs and pull requests;
- turn ideas into PRDs and issue plans;
- preserve continuity across long sessions;
- sync this skills pack across computers.

## Installation

Clone this repo to a stable location. For your own machines, prefer `--mode symlink` so the clone remains the source of truth and the agent sees live links into it.

```bash
git clone <repo-url> ~/src/rb-skills
cd ~/src/rb-skills
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink
```

The dry run should list the skills that would be installed. By default, the script selects the destination automatically:

- Codex first: `$CODEX_HOME/skills` when set, otherwise `~/.codex/skills` when `~/.codex` exists.
- Claude Code next: `~/.claude/skills` when Claude Code is detected and Codex is not present.

Force a destination with `--agent`:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --agent codex
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --agent claude
```

Use `--dest /path/to/skills` for an explicit directory.

Use `--mode copy` only when you want a standalone install that does not depend on keeping the clone in place.

Install only selected skills with `--skills`:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --skills rb-start-project rb-diagnose rb-implement-with-tests
```

Existing local skills are skipped by default. To replace them, use `--replace`; the script moves the previous version into a timestamped backup folder before installing.

Restart Codex after installing, adding, removing, or renaming Codex skills so discovery refreshes cleanly. In Claude Code, changes under an existing `~/.claude/skills` directory are usually detected live, but restart Claude Code if the top-level skills directory was newly created.

## First Use In A Project

After installing the pack:

1. Open Codex or Claude Code in the target project directory.
2. Invoke the start-project skill: `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.
3. Let `$rb-start-project` inspect the repository and ask its setup questions.
4. Confirm the project goal, constraints, test/check commands, and first task.
5. Let the agent route the session to the recommended workflow.

For a brand new or poorly documented project, `rb-start-project` is usually the right entrypoint. It should not write product code during onboarding. It should first understand the repository, clarify the goal, and only then ask whether to continue into implementation, diagnosis, planning, or review.

If the whole repository needs RB workflow setup, ask for:

```text
Use $rb-full-start on this repository.
```

`$rb-full-start` prepares project resources such as `AGENTS.md`, `CONTEXT.md`, visibility checks, and then continues into start-project onboarding.

If `$rb-full-start` reports that existing installed skills are not symlinks to this repo, rerun only after deciding those installed folders should be backed up and replaced:

```bash
python3 rb-full-start/scripts/full_start.py --target "$PWD" --replace-skills
```

## How Skills Are Invoked

Codex and Claude Code can use these skills in two ways:

- Automatic invocation: when your request matches a skill description, the agent should load and follow that skill before acting.
- Explicit invocation: you can name a skill directly, such as `Use $rb-diagnose` in Codex or `/rb-diagnose` in Claude Code, when you want to steer the session.

You do not need to memorize every skill name. In normal project work, start with `rb-start-project` and let it route the session. Explicit skill names are useful when you already know the workflow you want or when you want to correct the agent's routing.

If the agent does not appear to use the right skill, mention it directly with `$skill-name` in Codex or `/skill-name` in Claude Code.

## Skill Reference

This pack currently contains these skills:

| Skill | Invoke when |
| --- | --- |
| `$rb-architecture-review` | You want to inspect a codebase for architecture problems, unclear boundaries, duplication, hidden assumptions, or refactoring opportunities. |
| `$rb-context-tokens` | You ask about current context size, token usage, the latest call, or `/tokens`. |
| `$rb-continue-session` | You are resuming a mature project and want the agent to orient from diary notes, handoffs, git state, and existing project instructions before editing. |
| `$rb-diagnose` | You have a bug, regression, failing test, surprising output, or unclear failure and need evidence before fixes. |
| `$rb-full-start` | You want the agent to prepare a repository end-to-end for RB workflows, including global skills, project resources, visibility checks, and then start-project onboarding. |
| `$rb-clarify` | You are considering a non-trivial feature or change and need requirements, docs, ambiguity, edge cases, and an implementation plan clarified before coding. |
| `$rb-implementation-phase-planner` | You need an implementation plan, phase checklist, MVP/walking-skeleton sequence, verification gates, or a review of an existing plan. |
| `$rb-implement-with-tests` | Requirements are clear and you want ordinary software/product changes implemented with focused tests and executable checks. |
| `$rb-multi-agent-systems` | You are designing, reviewing, or debugging multi-LLM-agent systems, agent frameworks, tool/MCP architecture, routing, tracing, evals, retrieval, or durability. |
| `$rb-project-language` | You need to capture or update project vocabulary, domain terms, invariants, assumptions, or `CONTEXT.md`, especially in scientific or domain-heavy repositories. |
| `$rb-research-question-gate` | You are evaluating a research idea, scientific hypothesis, algorithm proposal, or technical novelty claim before investing in PRD/planning/coding. |
| `$rb-review-pr-or-diff` | You want a review of a pull request, branch, or diff, with findings first and risks tied to file/line references. |
| `$rb-session-handoff` | You want to pause, end, archive, hand off, or prepare continuity notes for another agent session. |
| `$rb-setup-local-agent-skills` | You need to verify or repair RB global skill installation, project resources, `AGENTS.md`, `CONTEXT.md`, or agent skill discovery. |
| `$rb-start-project` | You are starting a project, onboarding a repository, or want guided setup questions before coding. |
| `$rb-sync-skills-repo` | You want to install, sync, copy, symlink, update, clone, publish, or share skills from this Git repo across computers. |
| `$rb-tdd-scientific-code` | You are changing scientific, numerical, modelling, simulation, stochastic, or domain-sensitive code where units, invariants, tolerances, and reproducibility matter. |
| `$rb-to-issues` | You want to split a PRD or implementation plan into ordered issues with scope, acceptance criteria, tests, risks, and dependencies. |
| `$rb-to-prd` | You want to turn an idea or rough feature request into a practical PRD with goals, constraints, risks, success criteria, and validation approach. |
| `$rb-triage` | You need to classify and prioritise tasks by urgency, importance, risk, dependency, effort, uncertainty, and validity implications. |
| `$rb-working-diary` | Work is long-running or context-heavy and needs durable notes, assumptions, decisions, status, or next actions across sessions. |
| `$rb-write-skill` | You want the agent to create or update a reusable RB-style skill with clear triggers, procedure, metadata, and supporting resources. |
| `$rb-zoom-out` | You want to understand an unfamiliar repository's structure, control flow, data flow, dependencies, and change hotspots before editing. |

Codex or Claude Code should automatically invoke these when the request clearly matches the `Invoke when` guidance. The table is mainly for orientation and for cases where you want to steer the agent explicitly.

## Recommended Session Patterns

For a new feature:

```text
$rb-start-project
```

Then let the agent route to `$rb-clarify`. After requirements and docs are clear, it should produce an implementation plan and ask before continuing into `$rb-implement-with-tests`.

In Claude Code, direct invocations use slash commands, for example `/rb-start-project`, `/rb-clarify`, and `/rb-implement-with-tests`.

For a bug:

```text
Use $rb-diagnose for this failing behaviour.
```

The agent should gather evidence, reproduce the issue where possible, separate diagnosis from fixes, and preserve a check that proves the fix.

For scientific or modelling code:

```text
Use $rb-tdd-scientific-code for this change.
```

The agent should work test-first around units, invariants, tolerances, reproducibility, fixtures, stochastic behaviour, and domain assumptions.

For an unfamiliar repository:

```text
Use $rb-zoom-out before editing.
```

The agent should explain structure, control flow, dependencies, change hotspots, and likely risks before proposing edits.

For long-running work:

```text
Use $rb-working-diary as we go.
```

The agent should preserve durable decisions, assumptions, status, and next actions so another session can resume without starting from scratch.

## Adding Or Updating Skills

This repo should be the source of truth for Richard-owned global skills. When creating a new skill, prefer this workflow:

1. Create the skill folder in this repo, for example `rb-example-skill/`.
2. Add `SKILL.md` with `name` and `description` frontmatter.
3. Add `agents/openai.yaml` with the display metadata.
4. Validate that the folder name matches the skill name.
5. Install or refresh the skill into the active agent with `$rb-sync-skills-repo` or:

   ```bash
   python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --skills rb-example-skill
   ```

6. Restart Codex, or restart Claude Code if the top-level `~/.claude/skills` directory was newly created.

When editing an existing symlinked skill, edit the repo copy. Codex will read the updated file through the symlink after restart. Claude Code usually detects `SKILL.md` edits live when the skills directory is already watched.

## Updating This Pack Later

If you installed with symlinks, update the clone:

```bash
cd ~/src/rb-skills
git pull
```

Restart Codex after pulling changes that add, remove, rename, or substantially change skill descriptions. For Claude Code, restart if newly added or renamed skills do not appear.

If you installed with copy mode, run the sync script again after pulling.

## Sharing And Publishing

Before sharing publicly, check that the repo does not include:

- secrets, API keys, tokens, or `.env` files;
- private account IDs;
- confidential institutional context;
- local-only absolute paths that should not travel;
- generated outputs, caches, or temporary files.

Keep local/system material out of the repo, especially:

```text
.system/
.rb-agent-global-backups/
output/
outputs/
codex-primary-runtime/
.env
.env.*
__pycache__/
*.pyc
```

## Troubleshooting

If the agent cannot see a skill:

1. Check that the skill directory exists under `${CODEX_HOME:-$HOME/.codex}/skills` for Codex or `~/.claude/skills` for Claude Code.
2. Check that the directory contains `SKILL.md`.
3. If it is a symlink, check that the clone has not moved.
4. Restart Codex or Claude Code.
5. Run `$rb-setup-local-agent-skills` if the setup still looks wrong.

If a newly cloned machine has no `$rb-sync-skills-repo` yet, run the bootstrap script directly from the clone as shown in the Quick Start section. The skill becomes available only after installation and the relevant agent reload/restart.
