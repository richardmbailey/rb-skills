---
name: rb-sync-skills-repo
description: Install or sync personal Codex or Claude Code skills from a Git or GitHub repository into the active agent skills directory. Use when the user wants to move, share, version, clone, bootstrap, symlink, copy, update, or publish skill folders across computers.
---

# RB Sync Skills Repo

## Overview

Use this skill to bootstrap or update agent skills from a versioned repository. Prefer a local clone as the source of truth, then symlink selected skill folders into the discoverable skills directory; use copy mode when the user wants a standalone install.

By default, the bundled script chooses the destination automatically: use Codex first when `$CODEX_HOME` or `~/.codex` exists, otherwise use Claude Code's personal skills directory when Claude Code is detected.

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

4. Install:

```bash
python3 /path/to/skills-repo/rb-sync-skills-repo/scripts/sync_skills_repo.py /path/to/skills-repo --mode symlink
```

Use `--agent codex` or `--agent claude` to force a target agent. Use `--dest /path/to/skills` for an explicit destination. Use `--mode copy` if the cloned repo should not remain present. Use `--skills name-a name-b` to install a subset. Use `--replace` only after confirming existing destination folders should be moved to timestamped backups.

5. Tell the user to restart Codex so newly installed or updated Codex skills are rediscovered. For Claude Code, edits under an already-watched `~/.claude/skills` directory are usually detected live; restart Claude Code if the top-level skills directory was newly created.

## Script Usage

```bash
python3 scripts/sync_skills_repo.py SOURCE [--agent auto|codex|claude] [--dest DEST] [--mode symlink|copy] [--skills NAME ...] [--dry-run] [--replace] [--allow-name-mismatch]
```

Defaults:
- `--agent auto` tries Codex first, then Claude Code.
- Codex destination is `$CODEX_HOME/skills` when set, otherwise `~/.codex/skills`.
- Claude Code destination is `~/.claude/skills`.
- `--mode symlink` links each installed skill back to the clone.
- Existing destinations are skipped unless `--replace` is set.
- Replacement moves the existing destination to `DEST/.skill-backups/<skill-name>-<timestamp>`.

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
