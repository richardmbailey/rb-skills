---
name: "rb-wiki"
description: "Use for design or extension of LLM-agent Markdown wikis, including schema or tool changes, synthesis, cross-page queries, and automation design. For template creation, inbox ingestion, or routine maintenance, use the narrower wiki skill."
---

# RB Wiki

Use this skill for work that changes or uses the wider LLM-wiki system: a git-backed
Markdown knowledge system where raw evidence is preserved, wiki pages are curated
synthesis, deterministic tools enforce structure, and an LLM agent performs
judgement-heavy editorial work.

For routine operations, use `$rb-new-wiki` to create from `wiki-template`,
`$rb-wiki-ingest` to process new inbox sources, and `$rb-wiki-maintenance` for
linting and scheduled upkeep. Return here when work spans those boundaries or changes
the wiki's design, schema, tools, synthesis, query behaviour, or automations.

## Core Reference

Read `references/design.md` before doing substantial work on an LLM-wiki, especially when creating the repository skeleton, changing schema or tools, ingesting sources, updating important synthesis pages, designing automations, or reviewing wiki health.

Use the design as the governing specification when it conflicts with ordinary note-taking habits. In particular:

- preserve `sources/raw/` as immutable evidence;
- keep `wiki/` OKF-compatible and locally stricter under `llm-wiki-profile/0.1`;
- use standard Markdown links, not Obsidian links, as canonical links;
- route before reading many page bodies;
- require provenance for important claims;
- never delete, merge, rename high-degree pages, resolve serious contradictions, or change schemas without explicit human approval.

## Subject Wiki Requests

When Richard asks to create a wiki on a specified subject, treat the subject as the domain for a new LLM-wiki unless he points to an existing wiki repository.

Required inputs:

- subject or domain;
- target parent directory or repository name;
- wiki base directory name;
- initial source set, or confirmation that the wiki should start from seed pages and an empty inbox;
- preferred upkeep cadence if different from the defaults below.

If the wiki base directory name is missing, derive a conservative filesystem-safe name from the subject and suffix it with `-wiki` when the subject name does not already end in `wiki`. For example, a subject of `LLM-agents` should create `LLM-agent-wiki`. Ask only when the missing choice would change repository location, source handling, or automation behavior.

Procedure:

1. Read `references/design.md`.
2. Create or enter the target parent repository or directory.
3. Create or enter the wiki base directory named for the wiki.
4. Build the skeleton and deterministic tools inside that wiki base directory in the phase order below.
5. Create subject-specific seed pages using the local frontmatter profile. Mark pages as `draft` or `needs-review` when they are not yet source-backed.
6. If initial sources exist, ingest them through `inbox/`, `sources/raw/`, the source registry, and reference pages before writing synthesis.
7. Generate `wiki/index.md`, `.wiki_cache/graph.json`, `wiki/log.md`, and an initial `reports/lint/` or `reports/review/` report.
8. Run validation and quick lint from the wiki base directory.
9. Set up upkeep schedules when requested, using the automation tooling described below.
10. Finish with the wiki base directory location, source/validation status, schedules created or proposed, and next human review points.

## Build Workflow

When creating a new LLM-wiki, build it in phases:

All paths in this workflow are relative to the wiki base directory, not necessarily the git repository root. A repository may contain multiple sibling wiki base directories, each with its own sources, wiki bundle, tools, cache, and reports.

1. Create the skeleton from `references/design.md` inside the wiki base directory: `inbox/`, `sources/raw/`, `sources/_source_registry.yml`, `wiki/`, `schema/`, `tools/`, `reports/`, and `.wiki_cache/`.
2. Add `AGENTS.md`, `README.md`, schema files, policy files, prompt files, reserved `wiki/index.md` and `wiki/log.md`, `wiki/overview.md`, and initial seed pages.
3. Implement deterministic validation before heavy ingest:
   - `tools/validate_frontmatter.py`
   - `tools/check_reserved_files.py`
   - `tools/check_links.py`
   - `tools/word_count.py`
   - `tools/build_index.py`
   - `tools/build_graph.py`
4. Add source registration and ingest:
   - `tools/source_registry.py`
   - `tools/ingest.py`
   - reference-page generation
   - SHA-256 validation
   - duplicate source detection
5. Add routing and query:
   - frontmatter queries
   - keyword or BM25 search
   - graph neighbors and paths
   - hybrid search when useful
6. Add linting and maintenance reports:
   - quick lint for every ingest
   - full lint for periodic review
   - reports under `reports/lint/`

Do not build large ingest or semantic search flows before reserved-file, frontmatter, link, word-count, index, and graph checks exist.

## Running The Wiki

Use this routine for ordinary work:

1. Start by entering the relevant wiki base directory, then checking `git status`, `wiki/index.md`, recent `wiki/log.md`, and available deterministic tools.
2. For queries, classify the request as lookup, comparison, synthesis, audit, maintenance, source-check, or contradiction-check.
3. Route first with `wiki/index.md`, frontmatter, graph, search, source registry, and reference pages. Read full bodies only after narrowing candidates.
4. For ingest, register raw sources before synthesis: copy original files into `sources/raw/`, hash them, update `sources/_source_registry.yml`, and create `wiki/references/` pages.
5. Update ordinary wiki pages only with citations to reference pages and meaningful standard Markdown links.
6. Rebuild generated routing assets after content changes:
   ```bash
   python tools/build_index.py
   python tools/build_graph.py
   ```
7. Run validation and quick lint:
   ```bash
   python tools/validate_frontmatter.py
   python tools/check_reserved_files.py
   python tools/check_links.py
   python tools/word_count.py
   python tools/lint.py --quick
   ```
8. Review `git diff`, explain warnings, and update `wiki/log.md` or the relevant report.

If a required tool is missing, implement the missing deterministic tool before relying on manual inspection for that validation class.

## Periodic Upkeep Model

Run upkeep as a two-layer system:

1. Deterministic scheduled checks produce reports and caches.
2. Agent maintenance sessions interpret those reports and make cited, reviewed edits.

Recommended cadence:

- **After every ingest or substantive edit:** rebuild index and graph, run validation, run quick lint, write an ingest or maintenance report, and review the diff.
- **Daily or per active session:** process `inbox/`, check source registry integrity, scan quick-lint warnings, and confirm no raw source was changed.
- **Weekly:** run full lint, review broken links, orphan pages, oversized pages, duplicate candidates, missing sources, stale high-degree pages, and overview drift.
- **Monthly or at project milestones:** review decisions, contradictions, deprecated/stale pages, schema/tool changes, and whether repeated query answers should become synthesis pages.

Scheduled automation should be conservative. It may run deterministic scripts, rebuild caches, and write reports. It should not delete files, merge pages, rename high-degree pages, resolve serious contradictions, or rewrite substantive content without an agent/human review step.

## Inbox Processing

For the normal operating model, Richard should be able to drop documents into `inbox/` and have scheduled automation pick them up.

Default inbox behavior:

1. Detect files in `inbox/` on a recurring schedule.
2. For each supported file, compute a SHA-256 hash and stable source ID.
3. Copy the original file into `sources/raw/` without mutating it.
4. Update `sources/_source_registry.yml`.
5. Create or update a reference page in `wiki/references/`.
6. Run deterministic routing before reading many wiki page bodies.
7. In a manual agent session, update only clearly relevant wiki pages with citations; in scheduled polling, write proposed synthesis updates to an ingest report instead of editing content pages.
8. Rebuild `wiki/index.md` and `.wiki_cache/graph.json`.
9. Run validation and quick lint.
10. Leave the inbox file in place or move it only according to the wiki's explicit processed-inbox policy. Never delete an inbox file unless all design conditions are satisfied and Richard has approved the deletion policy.

Unsupported, ambiguous, duplicate, very large, encrypted, or failed files should be left untouched in `inbox/` and listed in `reports/ingest/` with a `needs-review` status.

Codex automations should be treated as scheduled polling, not true filesystem event watching. For near-real-time ingestion, set a frequent inbox processor schedule. For exact event-driven ingestion, create a local watcher or launch agent only if Richard explicitly asks for that extra local service.

## Automation Setup

When Richard asks to set up schedules, recurring upkeep, monitoring, reminders, or automatic wiki checks, use Codex's automation tooling when available. Search for the automation tool first in the active environment and use it rather than writing raw automation directives by hand.

Create or propose these default automations for a new subject wiki unless Richard asks for a different cadence:

1. **Inbox processor:** poll `inbox/`, register and ingest supported new files, create reference pages, rebuild index/graph, run quick validation, and write an ingest report with recommended synthesis updates. Scheduled inbox processors should not edit substantive content pages unless Richard explicitly asks for that behaviour. Use a frequent schedule for active projects or a daily early-morning schedule for quieter projects.
2. **Daily tidy-up:** run at end of day or early morning, check registry integrity, validate frontmatter/reserved files/links, rebuild index and graph if needed, run quick lint, summarize new ingest reports, and list items needing Richard's review.
3. **Weekly full wiki lint:** run full lint, detect orphans, duplicates, oversized pages, missing sources, stale high-degree pages, broken links, overview drift, and contradiction candidates. Produce a prioritized report without deleting or merging anything.
4. **Monthly governance review:** review decisions, contradictions, stale or deprecated pages, schema/tool changes, repeated query themes that should become syntheses, and maintenance work requiring Richard's approval.

Prefer cron-style automations for repository upkeep because they run against a workspace. Prefer thread heartbeat automations only for short follow-ups in the current conversation. Use suggested automation creation when the environment, worktree setup, or schedule should be reviewed before saving.

Automation prompts should instruct the agent to:

- read `AGENTS.md`, this skill if available, `wiki/index.md`, recent `wiki/log.md`, and the latest reports before acting;
- run deterministic tools before reading many page bodies;
- write reports under `reports/`;
- append human-readable operations to `wiki/log.md` only when changes are made;
- avoid destructive or substantive content changes without explicit approval;
- summarize what changed, what failed, and what needs Richard's review.

## Maintenance Priorities

When a lint or upkeep report is large, prioritize in this order:

1. Raw source integrity and registry/hash mismatches.
2. Invalid frontmatter, missing reserved files, malformed YAML, and broken local links.
3. Pages with empty or invalid `sources`.
4. Stale high-degree pages and drifted `overview.md`.
5. Contradiction candidates that affect important syntheses.
6. Orphan pages and weak reciprocal linking.
7. Oversized pages and duplicate candidates.
8. Coverage gaps and candidate new pages.

Treat scheduled reports as triage inputs, not as authority to make irreversible changes.

## Expected Outputs

For build work, produce the implemented repository structure, deterministic tools, seed pages, validation results, and a clear diff summary.

For ingest work, produce registered raw sources, reference pages, updated cited wiki pages, rebuilt index/graph, validation output, and an ingest report.

For query work, produce a direct answer with relevant wiki links, source/reference links for important claims, and uncertainty or contradiction notes.

For upkeep work, produce a lint or maintenance report, prioritized next actions, any safe repairs made, validation output, and a list of changes that require Richard's approval.
