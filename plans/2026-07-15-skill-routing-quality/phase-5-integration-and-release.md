# Phase 5: Repository Integration And Release Readiness

## Phase Goal

Integrate the validated skill changes into the repository catalogue and installed skill set, complete the final review, and leave a clean commit boundary ready for the user's separate push decision.

## Scope

- README skill catalogue.
- Changed `agents/openai.yaml` files.
- Routing evals, validators, fixtures, and result report.
- Symlink installation verification.
- Final diff, metadata, and custom validation.

## Non-scope

- Git push, pull request creation, or release publication without a separate user request.
- Any `rb-wiki` modification.

## Dependencies

- All prior phases complete and reviewed.
- Accepted routing-evaluation result.
- No unresolved blocking regression.

## Task Checklist

- [v] Update README rows to match the final trigger ownership and direct-invocation names.
- [v] Verify every changed `agents/openai.yaml` display name, 25–64 character short description, and `$skill-name` default prompt.
- [v] Parse every `SKILL.md` frontmatter block and require only `name` and `description`.
- [v] Confirm folder and frontmatter names match.
- [v] Scan for TODO scaffolding, stale names, broken relative references, and obsolete routing statements.
- [v] Run all routing-manifest and evaluator validators.
- [v] Run existing custom validators or their known-good/known-bad fixtures.
- [v] Run Python syntax checks without leaving `__pycache__` artifacts.
- [v] Run `git diff --check`.
- [v] Verify description counts against baseline and record final values.
- [v] Verify the `rb-wiki` hashes and confirm no `rb-wiki/` path appears in the diff.
- [v] Run the sync script in dry-run mode for all changed skills.
- [v] Refresh symlink installs for changed skills without replacing unrelated installed skills.
- [v] Confirm every installed path points back to this repository.
- [v] Perform a final findings-first review over the complete diff.
- [v] Fix actionable findings and rerun affected checks.
- [ ] Create the final local commit only after the worktree scope is confirmed.
- [ ] Report the commit hash, checks run, remaining limitations, and whether the branch is ahead of its upstream.

## Verification Commands

```bash
git status --short --branch
git diff --check
git diff --name-only -- rb-wiki/
shasum -a 256 rb-wiki/SKILL.md rb-wiki/agents/openai.yaml rb-wiki/references/design.md
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --dry-run --skills <changed-skill-names>
```

Run the repository's structured metadata validation and each custom skill validator as documented by the changed skill.

## Verification Checklist

- [v] README, frontmatter, UI metadata, and installed discovery agree.
- [v] All deterministic validators pass.
- [v] Behavioural results meet the accepted release gate.
- [v] No untracked generated output or cache files remain.
- [v] `rb-wiki` remains unchanged by path and hash.
- [v] Final review has no blocking findings.
- [ ] The commit contains only the intended skill-quality work.

## Execution Record

- Final metadata: 28 in-scope skills, 974 description words, and no
  descriptions over 40 words.
- Final routing gate: baseline 288/288; revised 288/288.
- The findings-first review found and fixed four integration or harness issues:
  baseline packet generation now discovers skills from the baseline Git tree;
  result rows now receive strict schema validation; and one flattened fixture
  was moved to its intended `fixtures/` path. It also removed redundant passed
  result rows from machine summaries because the raw JSONL is already retained.
- Fifteen selected standalone Codex skill directories were backed up and
  replaced with repository symlinks. Ten selected skills already had correct
  symlinks. All 25 changed installed paths now resolve to this repository.
- No safe comparable Claude Code harness was available. Restart Codex after the
  commit so skill discovery reloads the updated metadata.

## Phase Exit Criteria

- The repository contains the validated routing and body improvements, their evaluation evidence, and synchronized metadata.
- The working tree is clean after the final commit.
- Push status is reported but no push occurs without a separate request.
- Every task is `[v]` and `rb-wiki` remains unchanged.
