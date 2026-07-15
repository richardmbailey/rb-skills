---
name: "rb-new-wiki"
description: "Use when creating a new LLM wiki from wiki-template, including setup choices, template copying, subject and metadata configuration, validation, and optional automations. Do not use for ingesting into or maintaining an existing wiki."
---

# RB New Wiki

Use this skill when Richard asks to start, create, duplicate, clone, or set up a new LLM-wiki from `wiki-template`.

This is the frictionless setup path for new wikis. Use `rb-wiki` for broader design or operation of an existing wiki, `rb-wiki-ingest` for processing an inbox, and `rb-wiki-maintenance` for health checks after creation.

## Required Context

- A template wiki directory, usually a `wiki-template` sibling inside the target LLM-wikis workspace.
- A target parent directory, usually the current LLM-wikis workspace or another directory chosen by the user.
- The new wiki's subject, display title, filesystem-safe base directory name, domain tag, and one-sentence description.

Ask only for missing choices that materially affect the new wiki. If Richard gives a clear subject, derive conservative defaults and state them before running setup:

- display title: title-case subject plus `Wiki` when needed;
- base directory: lowercase or existing-style kebab-case subject plus `-wiki` when needed;
- domain tag: lowercase kebab-case subject;
- parent directory: current `LLM-wikis` repo when already there;
- template path: sibling `wiki-template`.

## Setup Questions

Use these as the normal setup interview, but keep it light.

1. What is the subject/domain of the wiki?
2. What should the wiki be called on screen?
3. What base directory should it use?
4. What one-sentence mission/description should appear in the README and overview?
5. Should it start with an empty inbox, or are there initial source files to place in `inbox/`?
6. Should Codex create recurring automations now, or leave schedules for later?

For automations, the recommended default is:

- inbox sweep hourly between 7am and 11pm local time;
- nightly deterministic maintenance;
- weekly deep clean.

Scheduled inbox automations should not edit substantive content pages. They should register sources, create reference pages, rebuild routing assets, validate, and write proposed synthesis/review notes.

## Procedure

1. Read the template's `TEMPLATE.md`, `README.md`, `AGENTS.md`, and `wiki/overview.md`.
2. Confirm the destination directory does not exist. Do not overwrite an existing wiki.
3. Run the bundled setup script from any working directory:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-new-wiki/scripts/new_wiki.py" \
     --template /path/to/LLM-wikis/wiki-template \
     --parent /path/to/LLM-wikis \
     --name example-wiki \
     --title "Example Wiki" \
     --subject "example subject" \
     --tag example \
     --description "Example Wiki is a local-first LLM-wiki for example subject."
   ```

4. Inspect the generated `README.md`, `AGENTS.md`, `wiki/overview.md`, `wiki/log.md`, `wiki/index.md`, and the newest report under `reports/lint/`.
5. If Richard supplied initial source files, place copies in the new wiki's `inbox/` and use `rb-wiki-ingest` to process them. Preserve original raw evidence.
6. If Richard asks for automations, search for the Codex automation tool and create or suggest conservative cron automations for the new wiki. Do not hand-write automation TOML.
7. Run or confirm:

   ```bash
   PYTHONDONTWRITEBYTECODE=1 python3 tools/source_registry.py validate
   PYTHONDONTWRITEBYTECODE=1 python3 tools/lint.py --quick
   ```

8. Summarize the new wiki location, chosen configuration, validation status, any automations created, and next review points.

## Safety Rules

- Do not mutate `wiki-template` while creating a new wiki.
- Do not overwrite or merge into an existing destination directory.
- Do not edit files in `sources/raw/` after copying the template.
- Do not create scheduled automations that rewrite substantive content without explicit approval.
- Do not delete human-provided initial sources. If they are copied into `inbox/`, normal ingest rules decide when the inbox copy can move to `processed/`.

## Outputs

- A new sibling wiki base directory created from `wiki-template`.
- Subject-specific top-level docs and overview.
- Rebuilt `wiki/index.md` and `.wiki_cache/graph.json`.
- A fresh quick-lint report.
- Optional conservative automations for inbox, nightly maintenance, and weekly deep clean.
- A concise final summary with commands/checks run.

## Failure Modes

- If the template is missing, stop and ask for the template path.
- If the destination exists, stop and ask whether Richard wants a different name.
- If validation fails, leave the new wiki in place, report the failing command and report path, and do not create automations until the failure is understood.
