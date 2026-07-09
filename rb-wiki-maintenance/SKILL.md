---
name: "rb-wiki-maintenance"
description: "Use when Richard asks Codex to run LLM-wiki maintenance, quick or full lint, nightly upkeep, weekly deep clean, graph/index rebuilding, source registry checks, or wiki health review."
---

# RB Wiki Maintenance

Use this skill when Richard asks to maintain an existing LLM-wiki, run quick or full lint, do a nightly tidy-up, run a weekly clean, review reports, rebuild the graph/index, or check wiki health.

This is a narrow operational skill for upkeep. Use `rb-wiki` for broader design/setup and use `rb-wiki-ingest` when the main task is processing new inbox files.

## Required Context

- A wiki base directory, usually the current working directory or a child directory containing `AGENTS.md`, `wiki/`, `sources/`, `tools/`, and `reports/`.
- A requested maintenance level:
  - quick or unspecified: quick lint and routing asset checks;
  - nightly: deterministic maintenance and quick lint;
  - weekly/full/deep clean: full lint and prioritized review.

If multiple wiki base directories are present, choose the one the user named. If none is named and only one exists, use that. If several plausible wikis exist, ask which one to maintain.

## Procedure

1. Enter the wiki base directory.
2. Read `AGENTS.md`, `README.md`, `wiki/index.md`, recent `wiki/log.md`, and the latest reports in `reports/ingest/`, `reports/lint/`, and `reports/review/` where present.
3. Run the appropriate command:

   Quick or unspecified:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/lint.py --quick
   ```

   Nightly upkeep:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/wiki_cron.py nightly
   ```

   Weekly/full/deep clean:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/wiki_cron.py weekly
   ```

4. Review generated reports. Prioritize issues in this order:
   1. raw source integrity and registry/hash mismatches;
   2. invalid frontmatter, reserved-file issues, malformed YAML, and broken links;
   3. missing or invalid source coverage;
   4. stale high-degree pages and overview drift;
   5. contradiction candidates affecting important syntheses;
   6. orphan pages and weak reciprocal linking;
   7. oversized pages and duplicate candidates;
   8. coverage gaps and candidate new pages.
5. Make only mechanical, unambiguous repairs. For substantive content, contradiction handling, merges, deletes, renames, or schema changes, write review notes and ask Richard.
6. Re-run quick lint after any repair.
7. Summarize health status, generated reports, warnings, repairs made, and review items.

## Safety Rules

- Do not delete files, merge pages, rename pages, resolve serious contradictions, rewrite important synthesis, or change schemas without explicit approval.
- Do not treat scheduled reports as authority to make irreversible changes.
- Do not scan all page bodies before routing through index, frontmatter, graph, search, and reports.
- Raw source files in `sources/raw/` are immutable.

## Outputs

- A lint or review report under `reports/`.
- Rebuilt `wiki/index.md` and `.wiki_cache/graph.json` when needed.
- A concise final summary with overall status and prioritized next actions.

