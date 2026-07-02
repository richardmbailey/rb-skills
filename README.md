# Codex Skills

This repository contains reusable Codex skill folders (some of which were heavily influenced by Matt Pocock's skills https://github.com/mattpocock/skills). Each skill is a directory with a `SKILL.md` file and, optionally, supporting `agents/`, `scripts/`, `references/`, or `assets/` folders.

## Install On A New Computer

Clone this repo to a stable location, then run the sync script directly from the clone once.

For a Codex agent on a fresh machine: read this file first, treat `rb-sync-skills-repo` as the bootstrap installer in the cloned repo, run the dry run, then run the install command. The `$rb-sync-skills-repo` skill will only become discoverable after this first install and a Codex restart.

```bash
git clone <repo-url> ~/src/codex-skills
cd ~/src/codex-skills
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink
```

Then restart Codex. After the restart, Codex should discover the installed skills, including `$rb-sync-skills-repo`, and future syncs can use that skill normally.

## Recommended Install Mode

Use `--mode symlink` for your own machines. The cloned repo remains the source of truth, and Codex sees the skills through links in:

```text
${CODEX_HOME:-$HOME/.codex}/skills
```

Use `--mode copy` when you want a standalone install that does not depend on keeping the clone in place.

## Installing A Subset

Install only selected skills with `--skills`:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --skills rb-to-prd rb-review-pr-or-diff
```

Existing local skills are skipped by default. To replace them, use `--replace`; the script moves the previous version into a timestamped backup folder before installing.

## Updating Later

If you installed with symlinks, pull the latest repo changes:

```bash
cd ~/src/codex-skills
git pull
```

Restart Codex after adding, removing, or renaming skills so discovery refreshes cleanly.

## Publishing Or Sharing

Before sharing publicly, check that the repo does not include secrets, private account IDs, confidential institutional context, local-only paths, or generated output. Keep local/system material out of the repo, especially:

```text
.system/
.rb-agent-global-backups/
output/
codex-primary-runtime/
.env
.env.*
__pycache__/
*.pyc
```
