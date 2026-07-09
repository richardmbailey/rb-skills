---
name: "rb-wiki-ingest"
description: "Use when Richard asks Codex to process an LLM-wiki inbox, ingest newly dropped files, register raw sources, create reference pages, run quick validation, move processed inbox files, and report review items."
---

# RB Wiki Ingest

Use this skill when Richard asks to process a wiki inbox, ingest new wiki material, add sources to an LLM-wiki, run the inbox sweep, or trigger wiki ingestion from Codex.

This is a narrow operational skill for an existing LLM-wiki. Use `rb-wiki` for broader wiki design, setup, schema changes, or substantial synthesis work.

## Required Context

- A wiki base directory, usually the current working directory or a child directory containing `AGENTS.md`, `inbox/`, `sources/`, `wiki/`, `tools/`, and `reports/`.
- Files may have been dropped into `inbox/`.

If multiple wiki base directories are present, choose the one the user named. If none is named and only one exists, use that. If several plausible wikis exist, ask which one to process.

## Procedure

1. Enter the wiki base directory.
2. Read `AGENTS.md`, `README.md`, `wiki/index.md`, recent `wiki/log.md`, and the latest `reports/ingest/` report if present.
3. Inspect `inbox/` without opening many source bodies. Note supported, unsupported, and already processed-looking files.
4. Run the cron-safe inbox command:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/wiki_cron.py inbox
   ```

5. Review the generated report under `reports/ingest/`.
6. If new reference pages were created, route first using `wiki/index.md`, `tools/query.py`, frontmatter, graph data, and the new reference pages before reading full wiki bodies.
7. In a manual Codex session, make only safe, clearly relevant, cited synthesis updates. Scheduled inbox automations should write proposed synthesis updates or review notes instead of editing content pages. If the update would require judgement, contradiction resolution, page merging, schema changes, or broad rewriting, write a review note instead of making the change.
8. Rebuild and validate after any substantive edit:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/build_index.py
   PYTHONDONTWRITEBYTECODE=1 python3 tools/build_graph.py
   PYTHONDONTWRITEBYTECODE=1 python3 tools/lint.py --quick
   ```

9. Summarize what was ingested, where raw files were preserved, which inbox files moved to `inbox/processed/YYYY-MM-DD/`, validation status, and what needs Richard's review.

## Safety Rules

- Raw sources in `sources/raw/` are immutable.
- Successfully processed direct inbox files may move to `inbox/processed/YYYY-MM-DD/`; do not delete them.
- Unsupported, failed, encrypted, ambiguous, or very large files stay in `inbox/` for review.
- Do not delete files, merge pages, rename high-degree pages, resolve serious contradictions, or change schemas without explicit approval.
- Do not read the whole wiki to decide relevance. Route first.

## Outputs

- An ingest report in `reports/ingest/`.
- Any new raw source copies in `sources/raw/`.
- Any new reference pages in `wiki/references/`.
- Rebuilt `wiki/index.md` and `.wiki_cache/graph.json` when content changed.
- A concise final summary with validation results and review items.
