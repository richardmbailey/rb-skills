# RB Agent Skills
This repository contains reusable skills (some of which are strongly influenced by Matt Pocock's skills https://github.com/mattpocock/skills) to be used with Codex and Claude Code. A skill is a reusable set of instructions and resources an AI agent can use to complete tasks in ways you have directed. In practical terms, a skill is a directory with a `SKILL.md` file and, optionally, supporting `agents/`, `scripts/`, `references/`, or `assets/` folders, which your agent is aware of. The agent can either choose to use a skill or the skill can be invoked directly by the user. These skills are ones I have used and developed over recent months for work on general coding projects, with a bias towards modelling projects. Expect them to change significantly as new generations of models are released - sometimes it's useful to direct AI models, sometimes it's just better to get out of their way!

## Easiest Setup

If you are not comfortable installing this manually, clone or download this repository onto your computer, open the folder in Codex or Claude Code, and ask the agent to install it for you.

Copy and paste this into Codex:

```text
I have cloned this rb-skills repository. Please install these skills for Codex. Run the sync script in dry-run mode first, then install using symlink mode, check that the skills are visible in my Codex skills directory, and tell me whether I need to restart Codex.
```

Copy and paste this into Claude Code:

```text
I have cloned this rb-skills repository. Please install these skills for Claude Code. Run the sync script in dry-run mode first, then install using symlink mode for Claude, check that the skills are visible in ~/.claude/skills, and tell me whether I need to restart Claude Code.
```

If you use both tools, ask the agent to install the skills for both Codex and Claude Code. After installation, restart the relevant app if the agent recommends it, then open the project you want to work on and start with `$rb-start-project` in Codex or `/rb-start-project` in Claude Code.

For reference, the installer places skills where each tool expects to find them.

Codex uses:

```text
${CODEX_HOME:-$HOME/.codex}/skills
```

Claude Code personal skills use:

```text
$HOME/.claude/skills
```

## Manual Quick Start

Use this route if you are comfortable running terminal commands yourself. On a new computer:

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
- discuss requirements before implementation;
- debug bugs and failing tests without jumping to fixes too early;
- implement changes with focused tests and checks;
- handle scientific, modelling, numerical, or domain-sensitive code carefully;
- review diffs and pull requests;
- turn ideas into implementation plans and ordered issues;
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

If the whole repository needs RB workflow setup (new machine, missing `AGENTS.md` or `CONTEXT.md`, or the agent cannot see the RB skills), ask for:

```text
Use $rb-install-skills on this repository.
```

`$rb-install-skills` installs or verifies the RB skills, prepares project resources such as `AGENTS.md` and `CONTEXT.md`, runs visibility checks, and then continues into start-project onboarding.

If `$rb-install-skills` reports that existing installed skills are not symlinks to this repo, rerun only after deciding those installed folders should be backed up and replaced:

```bash
python3 rb-install-skills/scripts/install_skills.py --target "$PWD" --replace-skills
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
| `$rb-explain-diff` | You want a teaching-oriented, interactive HTML explanation of a code change; use `$rb-review-pr-or-diff` when the aim is to find defects. |
| `$rb-create-skill-evals` | You want behavioural evaluations for an agent skill, including trigger boundaries, outcomes, regressions, repeated trials, or ablation comparisons—not ordinary product-code tests. |
| `$rb-architecture-review` | You want an architectural critique covering boundaries, coupling, duplication, hidden assumptions, and improvement opportunities, rather than neutral repository orientation. |
| `$rb-context-tokens` | You ask about current context size, token usage, the latest call, or `/tokens`. |
| `$rb-continue-project` | You are resuming a mature project from existing instructions, diary, handoff, and Git state; clarify if the user may instead want a standalone status artifact. |
| `$rb-diagnose` | A bug, regression, failing test, or surprising output needs root-cause investigation before choosing a fix. |
| `$rb-install-skills` | You want the full RB setup workflow: global skills, project resources, visibility checks, and initial onboarding—not sync-only or repair-only work. |
| `$rb-discuss` | A non-trivial change still has unresolved material requirements, behaviour, interfaces, edge cases, or acceptance criteria that must be discussed before planning or coding. |
| `$rb-execute-plan` | An implementation plan, phase checklist, issue list, or agreed direction already exists and needs execution, refinement, review, progress tracking, or verification gates. |
| `$rb-implement-with-tests` | Requirements are clear and you want ordinary software/product changes implemented with focused tests, executable checks, and a final review+fix loop. |
| `$rb-multi-agent-systems` | You are designing, reviewing, or debugging multiple LLM agents or orchestration layers, including boundaries, tools, handoffs, state, routing, failures, observability, evaluation, budgets, and durability. |
| `$rb-project-language` | You need shared vocabulary or `CONTEXT.md` updated with domain terms, acronyms, units, invariants, assumptions, or modelling concepts. |
| `$rb-research-question-gate` | You are evaluating a research idea, scientific hypothesis, algorithm proposal, or technical novelty claim before investing in PRD/planning/coding. |
| `$rb-review-pr-or-diff` | You want defects and risks found in a pull request or diff, with findings first and risks tied to file references. |
| `$rb-end-session` | You want to pause or close current work, prepare durable continuity notes, or create a handoff—not report ongoing project status. |
| `$rb-setup-local-agent-skills` | An existing RB skill installation or project-resource setup is incomplete, stale, or undiscoverable and needs verification or repair. |
| `$rb-start-project` | You are first onboarding a new or poorly understood project and need discovery, setup questions, goals, constraints, and workflow routing before coding. |
| `$rb-sync-skills-repo` | You want to copy, symlink, clone, update, publish, or otherwise synchronize skill folders between a Git repository and agent skill directories. |
| `$rb-tdd-scientific-code` | You are changing scientific, numerical, modelling, simulation, stochastic, or domain-sensitive code where units, invariants, tolerances, reproducibility, and review+fix matter. |
| `$rb-create-issues` | You want to decompose an existing PRD or implementation plan into ordered, reviewable issue drafts; external issue-tracker changes require a separate request. |
| `$rb-create-implementation-plan` | An idea, rough feature request, or product goal needs a new top-level implementation plan; use `$rb-execute-plan` when a plan already exists. |
| `$rb-where-are-we` | You want a deep, evidence-backed HTML state-of-play report covering goals, phase, progress, code health, risks, recent changes, and next steps. |
| `$rb-working-diary` | Long-running, context-heavy, or cumulatively substantial multi-turn work needs durable decisions, evidence, status, and next actions across compaction, sessions, or handoffs. |
| `$rb-write-skill` | You want to create or update a reusable RB-style skill; use `$rb-create-skill-evals` when the work is behavioural evaluation rather than authoring. |
| `$rb-explain-codebase` | You want neutral orientation to an unfamiliar repository's structure, control flow, data flow, dependencies, and change hotspots. |
| `$rb-wiki` | You want broader LLM-wiki design, schema or tool changes, substantial synthesis, cross-page queries, automation design, or work spanning several wiki workflows. |
| `$rb-new-wiki` | You want to create and configure a new LLM wiki from `wiki-template`, rather than operate an existing wiki. |
| `$rb-wiki-ingest` | An existing LLM wiki has new inbox files to register, ingest, validate, and move through intake. |
| `$rb-wiki-maintenance` | An existing LLM wiki needs operational upkeep such as linting, index rebuilding, registry checks, or health review. |

Codex or Claude Code should automatically invoke these when the request clearly matches the `Invoke when` guidance. The table is mainly for orientation and for cases where you want to steer the agent explicitly.

## Recommended Session Patterns

For a new feature:

```text
$rb-start-project
```

Then let the agent route through `$rb-discuss`, `$rb-create-implementation-plan`, `$rb-execute-plan` when phase work is needed, the appropriate implementation skill, and the final review+fix loop.

In Claude Code, direct invocations use slash commands, for example `/rb-start-project`, `/rb-discuss`, `/rb-execute-plan`, and `/rb-implement-with-tests`.

For a bug:

```text
Use $rb-diagnose for this failing behaviour.
```

The agent should gather evidence, reproduce the issue where possible, separate diagnosis from fixes, and preserve a check that proves the fix.

For scientific or modelling code:

```text
Use $rb-tdd-scientific-code for this change.
```

The agent should work test-first around units, invariants, tolerances, reproducibility, fixtures, stochastic behaviour, domain assumptions, and final review+fix.

For an unfamiliar repository:

```text
Use $rb-explain-codebase before editing.
```

The agent should explain structure, control flow, dependencies, change hotspots, and likely risks before proposing edits.

For long-running work:

```text
Use $rb-working-diary as we go.
```

The agent should preserve durable decisions, assumptions, status, and next actions so another session can resume without starting from scratch.

## Adding Or Updating Skills

This repo should be the source of truth for global skills. When creating a new skill, prefer this workflow:

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
