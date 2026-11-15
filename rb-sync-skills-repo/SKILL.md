---
name: rb-sync-skills-repo
description: Use when copying, symlinking, cloning, updating, publishing, or otherwise synchronizing skill folders between a Git repository and Codex or Claude Code skill directories. For project-resource setup or discovery repair, use a setup or installation skill.
---

# RB Sync Skills Repo

## Overview

Use this skill to bootstrap or update agent skills from a versioned repository. Prefer a local clone as the source of truth. For Codex and generic repositories, symlink selected skill folders into the discoverable skills directory; use copy mode when the user wants a standalone install. For this RB repository's Claude target, the script generates supported Claude editions regardless of `--mode`.

By default, the bundled script chooses the destination automatically: use Codex's user skills directory when Codex configuration is present, otherwise use Claude Code's personal skills directory when Claude Code is detected. If neither agent is detected, default to Codex.

Bundled script: `scripts/sync_skills_repo.py`.

## Workflow

1. Identify the source:
   - If the user provides a local repo path, use it directly.
   - If the user provides a GitHub URL or `owner/repo`, clone or pull it first, requesting approval for networked git commands when required.
   - If the repo has a nested skills directory, use that subdirectory as the script source.

2. Inspect before installing:
   - Install only direct child directories containing `SKILL.md`, unless the source itself is a single skill folder.
   - Do not install `.system`, `.git`, `.rb-agent-global-backups`, `output`, `codex-primary-runtime`, caches, or generated files.
   - For public sharing, scan for secrets and personal identifiers before committing or publishing.

3. Dry-run the install:

```bash
python3 /path/to/skills-repo/rb-sync-skills-repo/scripts/sync_skills_repo.py /path/to/skills-repo --dry-run
```

Pass `--agent codex` or `--agent claude` to match the requested target in both the dry-run and install commands. Inspect the exact destinations and planned actions. If an existing symlink already resolves to the requested source, source edits are already available through it. Report that state rather than replacing the link or claiming a new installation. Claude generated copies need a refresh when their source changes. A verification-only request stops after the dry-run.

4. Install:

```bash
python3 /path/to/skills-repo/rb-sync-skills-repo/scripts/sync_skills_repo.py /path/to/skills-repo --mode symlink
```

Use `--dest /path/to/skills` for an explicit destination. For Codex or generic repositories, use `--mode copy` if the cloned repo should not remain present. Use `--skills name-a name-b` to install a subset supported by the target. Use `--replace` only after confirming existing destination folders should be backed up and replaced.

For this RB repository's Claude target, run from the source repository. Re-running refreshes unmodified generated copies. Modified copies, foreign directories, and existing links block installation unless replacement is authorised. Backups are saved under `DEST/.rb-claude-backups/<skill-name>-<uuid>`. Excluded legacy skills block installation even with `--replace`; review and move them before retrying.

To verify that installed Claude generated content and permissions match the source, run `python3 platforms/claude/install.py . --dest /path/to/skills --check` from the source repository.

5. Codex detects skill changes automatically. Ask the user to restart only when a new or changed skill does not appear. For Claude Code, edits under an already-watched `~/.claude/skills` directory are usually detected live; restart Claude Code if the top-level skills directory was newly created.

## Script Usage

```bash
python3 scripts/sync_skills_repo.py SOURCE [--agent auto|codex|claude] [--dest DEST] [--mode symlink|copy] [--skills NAME ...] [--dry-run] [--replace] [--allow-name-mismatch]
```

Defaults:
- `--agent auto` tries Codex first, then Claude Code.
- Codex user destination is `$HOME/.agents/skills`. Use repository-local `.agents/skills` only when the user explicitly requests repository-scoped installation.
- Claude Code destination is `~/.claude/skills`.
- For Codex and generic repositories, `--mode symlink` links each installed skill back to the clone.
- For Codex and generic repositories, existing destinations are skipped unless `--replace` is set.
- For Codex and generic repositories, replacement moves the existing destination to `DEST/.skill-backups/<skill-name>-<timestamp>`. The RB Claude refresh and backup rules above take precedence for its target.

## Publishing Guidance

When helping the user prepare a skills repo, recommend this shape:

```text
repo-root/
  rb-example-skill/
    SKILL.md
    agents/openai.yaml
    scripts/
    references/
    assets/
  another-skill/
    SKILL.md
```

Add a repository `.gitignore` that excludes local-only material:

```gitignore
.DS_Store
__pycache__/
*.pyc
.env
.env.*
.system/
.rb-agent-global-backups/
output/
codex-primary-runtime/
```

Keep private account IDs, tokens, local paths, and institution-specific confidential material out of any public repo.
