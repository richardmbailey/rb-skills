# LLM-Wiki System Instructions

This document defines how to build, maintain, and use an LLM-wiki: a persistent, git-backed, Markdown knowledge system maintained by an LLM agent and deterministic tooling.

The system is based on the LLM-wiki pattern proposed by Andrej Karpathy, extended with production-style maintenance workflows, linting, deterministic routing tools, and compatibility with Google’s Open Knowledge Format (OKF).

The core idea is simple: raw sources are preserved immutably; the wiki is a curated synthesis layer; deterministic scripts enforce structure and hygiene; the LLM performs judgement-heavy editorial work such as summarization, contradiction handling, linking, and synthesis.

The system should not behave like a generic “chat with my files” tool. It should behave like a knowledge compiler.

Raw evidence goes in. Durable, cited, cross-linked knowledge comes out.

---

# 1. Core Purpose

Build a local-first, git-backed Markdown wiki maintained by an LLM agent.

The system has six goals:

1. Preserve raw evidence immutably.
2. Convert messy sources into clean, interlinked knowledge pages.
3. Keep the wiki portable and interoperable using the Open Knowledge Format.
4. Keep the local wiki stricter than baseline OKF through a project-specific schema profile.
5. Use deterministic tools for validation, search, routing, graph traversal, and linting.
6. Let users query the wiki as a durable knowledge base rather than repeatedly searching or re-summarizing raw documents.

The wiki should improve through use. Queries that produce reusable synthesis should become new synthesis pages. Linting should reveal drift, contradictions, orphan pages, stale claims, and missing concepts. Ingest should update the graph, not just add files.

If using the wiki merely consumes it, it is a filing cabinet. If using it improves it, it is an LLM-wiki.

---

# 2. Design Philosophy

The system is built around five separations.

## 2.1 Evidence versus synthesis

Raw sources are evidence. Wiki pages are synthesis.

Do not confuse these layers. A wiki page may be wrong, incomplete, stale, or interpretive. A raw source is the thing the wiki must be able to trace back to.

## 2.2 Interchange standard versus local discipline

The wiki should be compatible with the Open Knowledge Format, but it should also enforce a stricter local schema.

OKF defines a minimal, portable, vendor-neutral structure: Markdown files, YAML frontmatter, standard Markdown links, `index.md`, and `log.md`.

The local LLM-wiki profile defines stricter rules for scientific usefulness: source immutability, mandatory metadata, citation requirements, page size limits, contradiction handling, lint workflows, and review procedures.

The distinction is:

```text
OKF = exchange format
Local profile = operating discipline
```

Producers should be strict. Consumers should be forgiving.

## 2.3 Routing versus reading

The agent must not read the entire wiki to decide what is relevant.

It must first use routing tools: index files, frontmatter queries, graph traversal, BM25 search, vector search, hybrid search, and source catalogs.

Only after narrowing the candidate set should it read full page bodies.

The rule is:

```text
Map first. Body second.
```

## 2.4 Deterministic tooling versus LLM judgement

Use deterministic scripts for mechanical operations.

Use the LLM for interpretation, synthesis, judgement, contradiction handling, and editorial decisions.

Do not ask the LLM to do what a script can do reliably. That is how one summons the file-system goblin.

## 2.5 Agent authority versus human authority

The agent may create and update ordinary wiki content under the rules in this document.

The agent must not delete files, merge duplicates, resolve serious contradictions, change schemas, or make irreversible structural changes without explicit human approval.

The human is the court of appeal.

---

# 3. Open Knowledge Format Compatibility

The wiki should be an OKF-compatible knowledge bundle.

## 3.1 OKF baseline

An OKF bundle is a directory tree of Markdown files with YAML frontmatter.

Each non-reserved `.md` file is a concept document.

The identity of a concept document is its path within the bundle, minus the `.md` suffix.

The reserved files are:

```text
index.md
log.md
```

`index.md` is a progressive-disclosure routing file.

`log.md` records update history.

OKF requires only one frontmatter field:

```yaml
type: ...
```

OKF recommends additional fields such as:

```yaml
title: ...
description: ...
resource: ...
tags: ...
timestamp: ...
```

However, OKF consumers should tolerate missing optional fields, unknown fields, unknown types, missing links, broken links, and incomplete indexes.

## 3.2 Local profile

This wiki uses a stricter local profile on top of OKF.

The local profile is called:

```text
llm-wiki-profile/0.1
```

The local profile requires additional fields, stricter source citation, page-size guidance, linting, and workflow rules.

The local profile exists because OKF is designed for interoperability, not full research-grade governance.

This distinction matters.

A minimal OKF bundle should be ingestible.

A locally maintained wiki should be stricter.

---

# 4. Repository Structure

Use this layout:

```text
llm-wiki/
  AGENTS.md
  README.md

  inbox/
    # Temporary drop zone for uncatalogued raw inputs.

  sources/
    raw/
      # Immutable original files: PDFs, transcripts, web exports, notes, audio, etc.
    _source_registry.yml
      # Machine-readable registry of all source files.

  wiki/
    index.md
    log.md
    overview.md

    concepts/
      # Stable conceptual pages.
    entities/
      # People, institutions, projects, tools, datasets, papers, places.
    summaries/
      # Source-level or topic-level summaries.
    syntheses/
      # Higher-level answers, comparisons, arguments, research memos.
    decisions/
      # Decisions, design choices, policy records, resolved questions.
    contradictions/
      # Explicit contradiction or uncertainty records.
    references/
      # OKF concept documents describing sources and linking to raw evidence.
    datasets/
      # Dataset descriptions, schemas, joins, caveats, and examples.
    methods/
      # Methods, protocols, workflows, algorithms, and modelling approaches.
    tools/
      # Software tools, scripts, packages, services, platforms.
    projects/
      # Project-level knowledge pages.

  schema/
    okf_profile.md
    page_schema.yml
    source_schema.yml
    link_policy.md
    ingest_policy.md
    query_policy.md
    lint_policy.md
    prompts/
      ingestor.md
      querier.md
      linter.md
      reviewer.md

  tools/
    ingest.py
    build_index.py
    build_graph.py
    query.py
    lint.py
    validate_frontmatter.py
    check_links.py
    source_registry.py
    word_count.py
    detect_duplicates.py
    check_reserved_files.py

  reports/
    ingest/
    lint/
    review/

  .wiki_cache/
    frontmatter.sqlite
    search.sqlite
    graph.json
    embeddings/
```

The important separation is:

```text
sources/raw/ = immutable evidence
wiki/ = OKF-compatible knowledge bundle
schema/ = rules and prompts
tools/ = deterministic machinery
reports/ = audit outputs
.wiki_cache/ = generated indexes and caches
```

Raw source files live outside the OKF bundle.

Reference pages inside `wiki/references/` describe those raw sources and make them part of the knowledge graph.

---

# 5. Hard Invariants

These rules are non-negotiable.

## 5.1 Raw source immutability

Files in `sources/raw/` must never be edited, rewritten, compressed, normalized, “cleaned up”, renamed casually, or deleted by the agent.

If a raw source is superseded, add a new source and update metadata. Do not mutate the old source.

## 5.2 Inbox is temporary, not archival

Files may be removed from `inbox/` only after all of the following are true:

1. The file has been copied into `sources/raw/`.
2. A SHA-256 hash has been computed.
3. An entry has been added to `sources/_source_registry.yml`.
4. A corresponding reference page has been created in `wiki/references/`.
5. Relevant wiki pages have been updated or a report explains why no update was made.
6. Validation has passed.
7. The changes have been reviewed or committed.

Nothing epistemically important may vanish.

## 5.3 Claims require provenance

Every important wiki claim must be traceable to at least one reference page or source.

Preferred citation style:

```markdown
This claim is supported by [Karpathy LLM-Wiki Gist](/references/karpathy-llm-wiki.md).
```

For compact citation sections:

```markdown
# Citations

- [Karpathy LLM-Wiki Gist](/references/karpathy-llm-wiki.md)
- [Google Open Knowledge Format Announcement](/references/google-open-knowledge-format.md)
```

## 5.4 Standard Markdown links are canonical

Use standard Markdown links as the canonical linking syntax:

```markdown
[Hybrid Search](/concepts/hybrid-search.md)
```

Do not make Obsidian-style `[[wikilinks]]` canonical.

Obsidian wikilinks may be generated as an optional compatibility layer, but OKF-style Markdown links are the source of truth.

## 5.5 No whole-wiki body scans for relevance

The agent must not read all page bodies to decide relevance.

It must first use:

```text
index.md
frontmatter database
graph traversal
BM25 search
vector search
hybrid search
source registry
reference pages
```

Only then may it read the narrowed set of page bodies.

## 5.6 Curation over overwriting

If new evidence contradicts, refines, or supersedes old evidence, do not simply overwrite the old claim.

Instead:

1. Preserve the historical claim where useful.
2. Add the new evidence.
3. Cite both sources.
4. Explain the evolution.
5. Create or update a contradiction page if the tension is substantial.

## 5.7 No unilateral deletion

The agent must never delete files unilaterally.

It may flag duplicates, obsolete pages, orphan pages, or low-value pages.

Deletion requires explicit human approval.

## 5.8 Page size discipline

Concept, entity, summary, synthesis, decision, contradiction, method, tool, project, and dataset pages should usually stay below 1,000 words.

If a page grows beyond that, split it into smaller linked pages or flag it for review.

## 5.9 Reserved file exceptions

`index.md` and `log.md` are reserved OKF files.

They should not be treated like ordinary concept pages.

The linter must not require ordinary content-page frontmatter for reserved files.

The root `index.md` may optionally declare the OKF version and local profile, but it should primarily remain a compact routing file.

---

# 6. The Three-Layer Knowledge Architecture

The system has three conceptual layers.

## 6.1 Sources layer

Location:

```text
sources/raw/
wiki/references/
sources/_source_registry.yml
```

Purpose:

Preserve and describe raw evidence.

The raw file is immutable. The reference page is editable metadata and summary about the raw file.

The reference page links the raw source into the OKF bundle.

## 6.2 Wiki layer

Location:

```text
wiki/
```

Purpose:

Maintain synthesized, interlinked knowledge.

The wiki layer contains:

```text
concepts
entities
summaries
syntheses
decisions
contradictions
references
datasets
methods
tools
projects
overview.md
index.md
log.md
```

This is the main layer used for querying and synthesis.

## 6.3 Schema layer

Location:

```text
schema/
AGENTS.md
```

Purpose:

Define the rules that make the agent behave like a disciplined maintainer rather than a generic chatbot.

The schema layer defines:

```text
page types
metadata rules
citation rules
linking rules
ingest workflow
query workflow
lint workflow
review workflow
naming conventions
validation commands
definition of done
```

The schema file is the operating system of the wiki.

---

# 7. Canonical Local Frontmatter Schema

All ordinary content pages inside `wiki/` must use OKF-compatible YAML frontmatter with local extensions.

Use this schema:

```yaml
---
type: Concept | Entity | Summary | Synthesis | Decision | Contradiction | Reference | Dataset | Method | Tool | Project | Overview
title: "Human-readable title"
description: "One-sentence description of the page."
resource: ""
tags: [domain, topic, status]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active | draft | stale | deprecated | needs-review
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: high | medium | low | uncertain
---
```

## 7.1 Field definitions

`type`

The page type. This is the only field required by baseline OKF, but it is mandatory and strictly validated in the local profile.

`title`

Human-readable page title.

`description`

One-sentence summary of what the page is about. This is used by index builders, routing tools, and humans.

`resource`

Optional canonical URI or path for the underlying asset. For abstract concepts this may be blank. For references, datasets, tools, or projects it may point to a raw file, URL, repository, DOI, dataset path, or documentation page.

`tags`

A list of domain, topic, and status tags.

`timestamp`

The last substantive update time in ISO 8601 UTC format.

`created`

The date the page was first created.

`status`

The current page status.

Allowed values:

```text
active
draft
stale
deprecated
needs-review
```

`profile`

The local schema profile used by the page.

`sources`

A list of Markdown links to reference pages supporting the page.

`confidence`

The current confidence level.

Allowed values:

```text
high
medium
low
uncertain
```

## 7.2 Strict producer rule

All locally produced ordinary content pages must include every local-profile field.

`resource` may be blank only when there is no canonical external or raw resource.

## 7.3 Permissive consumer rule

External OKF bundles with only `type` must still be ingestible.

When ingesting external OKF material, do not reject it merely because it lacks local-profile fields. Instead, create an ingest report and enrich the metadata where possible.

---

# 8. Source Registry Schema

The source registry lives at:

```text
sources/_source_registry.yml
```

Each source entry should look like this:

```yaml
- source_id: "2026-07-08-karpathy-llm-wiki"
  raw_path: "sources/raw/2026-07-08-karpathy-llm-wiki.md"
  reference_path: "wiki/references/2026-07-08-karpathy-llm-wiki.md"
  hash_sha256: "..."
  source_type: "web"
  date_ingested: "2026-07-08"
  date_published: "unknown"
  status: "active"
```

Allowed `source_type` values:

```text
pdf
transcript
web
note
email
dataset
code
audio
video
image
other
```

Allowed `status` values:

```text
active
superseded
rejected
needs-review
```

---

# 9. Reference Page Schema

Every raw source should have a corresponding reference page in:

```text
wiki/references/
```

Example:

```yaml
---
type: Reference
title: "Karpathy LLM-Wiki Gist"
description: "A proposal for an LLM-maintained Markdown wiki that accumulates synthesis over time."
resource: "sources/raw/2026-07-08-karpathy-llm-wiki.md"
tags: [llm-wiki, knowledge-systems, source]
timestamp: 2026-07-08T00:00:00Z

created: 2026-07-08
status: active
profile: llm-wiki-profile/0.1
sources: []
confidence: high
source_id: "2026-07-08-karpathy-llm-wiki"
source_type: web
hash_sha256: "..."
date_published: unknown
date_ingested: 2026-07-08
authors: ["Andrej Karpathy"]
---
```

Then the body:

```markdown
This reference records the source that introduced the LLM-wiki pattern.

# Source Summary

Short summary of the source.

# Key Claims

- Claim one.
- Claim two.

# Extracted Concepts

- [LLM-Wiki](/concepts/llm-wiki.md)
- [Compiled Knowledge](/concepts/compiled-knowledge.md)

# Extracted Entities

- [Andrej Karpathy](/entities/andrej-karpathy.md)

# Useful Passages

Short paraphrases or limited quotations where legally and ethically appropriate.

# Links Into Wiki

- [LLM-Wiki](/concepts/llm-wiki.md)
- [LLM-Wiki versus RAG](/syntheses/llm-wiki-vs-rag.md)
```

Reference pages are editable. Raw files are not.

---

# 10. Page Types

Use a small number of page types.

Do not invent new page types casually.

## 10.1 Concept

A reusable idea, mechanism, theory, pattern, distinction, or abstraction.

Examples:

```text
/concepts/llm-wiki.md
/concepts/hybrid-search.md
/concepts/source-immutability.md
/concepts/wiki-drift.md
```

## 10.2 Entity

A named person, institution, paper, model, law, project, place, dataset, platform, or organisation.

Examples:

```text
/entities/andrej-karpathy.md
/entities/openai-codex.md
/entities/google-cloud.md
```

## 10.3 Summary

A concise summary of a bounded source, meeting, paper, topic cluster, or evidence bundle.

Examples:

```text
/summaries/llm-wiki-comments-summary.md
/summaries/plastic-treaty-meeting-2026-07-08.md
```

## 10.4 Synthesis

A higher-level integration across multiple sources or pages.

Examples:

```text
/syntheses/llm-wiki-vs-rag.md
/syntheses/why-llm-wikis-drift.md
/syntheses/research-group-knowledge-management-with-llm-wikis.md
```

## 10.5 Decision

A recorded design, research, governance, or project decision.

Examples:

```text
/decisions/use-okf-compatible-markdown-links.md
/decisions/adopt-local-profile-over-minimal-okf.md
```

## 10.6 Contradiction

A page recording an unresolved tension between sources, claims, interpretations, or versions.

Examples:

```text
/contradictions/open-weights-vs-open-source-ai.md
/contradictions/bm25-vs-vector-search-performance.md
```

## 10.7 Reference

A source catalog page corresponding to raw evidence.

Examples:

```text
/references/karpathy-llm-wiki.md
/references/google-open-knowledge-format.md
```

## 10.8 Dataset

A dataset description, schema, fields, joins, caveats, provenance, and example uses.

Examples:

```text
/datasets/plastic-leakage-database.md
/datasets/global-waste-management-indicators.md
```

## 10.9 Method

A method, workflow, protocol, model, analytical technique, or algorithm.

Examples:

```text
/methods/reciprocal-rank-fusion.md
/methods/hybrid-search-routing.md
/methods/wiki-linting.md
```

## 10.10 Tool

A software tool, package, script, CLI, API, platform, or service.

Examples:

```text
/tools/query-cli.md
/tools/sqlite-fts5.md
/tools/codex.md
```

## 10.11 Project

A coherent project, programme, research activity, or workstream.

Examples:

```text
/projects/llm-wiki-build.md
/projects/plastic-pollution-evidence-synthesis.md
```

## 10.12 Overview

A high-level state-of-the-wiki synthesis.

Usually:

```text
/overview.md
```

---

# 11. Naming Rules

Use lowercase kebab-case filenames.

Good:

```text
/concepts/llm-wiki.md
/concepts/hybrid-search.md
/entities/andrej-karpathy.md
/syntheses/llm-wiki-vs-rag.md
/decisions/use-okf-markdown-links.md
```

Bad:

```text
/concepts/LLM Wiki!!.md
/concepts/misc ideas.md
/concepts/thoughts2_final_revised.md
```

Prefer stable slugs over clever ones.

The agent must not rename files casually. Renaming can break links, invalidate cached graph data, and create noisy git diffs.

A page slug should be changed only when:

1. The current name is materially misleading.
2. There is a clear canonical replacement.
3. All inbound links can be updated.
4. The change is logged.
5. Human approval is obtained for high-degree pages.

---

# 12. New Page Versus Edit Rule

Create a new page when the item is a distinct entity, concept, method, dataset, tool, project, contradiction, decision, or synthesis that other pages would naturally link to.

Edit an existing page when the new information is:

```text
an attribute
an update
an example
a caveat
a refinement
a measurement
a contradiction about an existing topic
a new source for an existing claim
```

Examples:

```text
New page:
- A new method called hybrid search routing.
- A new dataset used across multiple analyses.
- A recurring concept such as context contamination.
- A contradiction between two claims.

Edit existing page:
- A new date for an existing project.
- A new caveat about an existing method.
- A new paper supporting an existing concept.
- A correction to an existing entity profile.
```

If uncertain, do not create a speculative page automatically. Add a `needs-review` item in the ingest or lint report.

---

# 13. Standard Body Rules

Every ordinary content page must begin with a one-sentence plain-language summary immediately after frontmatter.

Example:

```markdown
An LLM-wiki is a persistent, agent-maintained Markdown knowledge base that compiles raw sources into interlinked synthesis.
```

This first sentence should normally match or closely mirror the `description` field.

The duplication is deliberate:

```text
description = machine routing and metadata
first sentence = human and LLM scanning
```

Use clear headings, lists, tables, and code blocks where useful.

Do not force every page type into the same body template. Use type-specific templates.

---

# 14. Type-Specific Templates

## 14.1 Concept template

```markdown
---
type: Concept
title: "Concept Title"
description: "One-sentence description."
resource: ""
tags: [domain, concept, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Definition

Plain-language definition.

# Key Claims

- Claim one, with a link to supporting source or concept.
- Claim two, with a link to supporting source or concept.

# Evidence

- `YYYY-MM-DD`: Evidence from [Source Title](/references/source-id.md).

# Relationships

- Related to [Related Concept](/concepts/related-concept.md).
- Contrasts with [Contrasting Concept](/concepts/contrasting-concept.md).
- Used by [Relevant Method](/methods/relevant-method.md).

# Open Questions

- Question one.
- Question two.

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created from [Source Title](/references/source-id.md).
```

## 14.2 Entity template

```markdown
---
type: Entity
title: "Entity Name"
description: "One-sentence description of the entity."
resource: ""
tags: [domain, entity, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Description

Who or what this entity is.

# Known Attributes

| Attribute | Value | Source |
|---|---|---|
| Example | Example | [Source](/references/source-id.md) |

# Relationships

- Connected to [Concept](/concepts/concept.md).
- Part of [Project](/projects/project.md).

# Timeline

- `YYYY-MM-DD`: Event with source.

# Open Questions

- Question one.

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.3 Summary template

```markdown
---
type: Summary
title: "Summary Title"
description: "One-sentence summary of the source, meeting, or topic cluster."
resource: ""
tags: [domain, summary, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Scope

What this summary covers.

# Main Points

- Point one.
- Point two.
- Point three.

# Extracted Concepts

- [Concept One](/concepts/concept-one.md)
- [Concept Two](/concepts/concept-two.md)

# Extracted Entities

- [Entity One](/entities/entity-one.md)

# Implications

Why this source or cluster matters.

# Open Questions

- Question one.

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.4 Synthesis template

```markdown
---
type: Synthesis
title: "Synthesis Title"
description: "One-sentence description of the synthesis."
resource: ""
tags: [domain, synthesis, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-one.md"
  - "/references/source-two.md"
confidence: medium
---

One-sentence summary.

# Answer

Direct answer or central synthesis.

# Supporting Evidence

- Evidence from [Source One](/references/source-one.md).
- Evidence from [Source Two](/references/source-two.md).

# Interpretation

How the evidence fits together.

# Contradictions and Caveats

- Relevant contradiction or uncertainty.

# Related Pages

- [Concept](/concepts/concept.md)
- [Entity](/entities/entity.md)
- [Method](/methods/method.md)

# Citations

- [Source One](/references/source-one.md)
- [Source Two](/references/source-two.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.5 Decision template

```markdown
---
type: Decision
title: "Decision Title"
description: "One-sentence description of the decision."
resource: ""
tags: [domain, decision, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: high
---

One-sentence summary.

# Decision

State the decision.

# Context

Why the decision was needed.

# Options Considered

| Option | Advantages | Disadvantages |
|---|---|---|
| Option A | ... | ... |
| Option B | ... | ... |

# Rationale

Why this option was chosen.

# Consequences

Expected implications.

# Review Trigger

When this decision should be revisited.

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.6 Contradiction template

```markdown
---
type: Contradiction
title: "Contradiction Title"
description: "One-sentence description of the unresolved tension."
resource: ""
tags: [domain, contradiction, needs-review]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: needs-review
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-a.md"
  - "/references/source-b.md"
confidence: uncertain
---

One-sentence summary.

# Claim A

State the first claim.

Supported by:

- [Source A](/references/source-a.md)

# Claim B

State the conflicting or contrasting claim.

Supported by:

- [Source B](/references/source-b.md)

# Source Comparison

Explain whether the conflict may be due to scope, date, definitions, method, evidence quality, or interpretation.

# Current Interpretation

State the best current interpretation without pretending the contradiction has disappeared.

# Resolution Status

Unresolved, partially resolved, resolved, or needs expert review.

# Affected Pages

- [Affected Concept](/concepts/affected-concept.md)
- [Affected Synthesis](/syntheses/affected-synthesis.md)

# Citations

- [Source A](/references/source-a.md)
- [Source B](/references/source-b.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.7 Reference template

```markdown
---
type: Reference
title: "Reference Title"
description: "One-sentence summary of the source."
resource: "sources/raw/source-file.ext"
tags: [domain, reference, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources: []
confidence: high
source_id: "source-id"
source_type: web
hash_sha256: "..."
date_published: unknown
date_ingested: YYYY-MM-DD
authors: []
---

One-sentence summary.

# Source Summary

Brief summary of the raw source.

# Key Claims

- Claim one.
- Claim two.

# Extracted Concepts

- [Concept](/concepts/concept.md)

# Extracted Entities

- [Entity](/entities/entity.md)

# Useful Passages

Short paraphrases or limited quotations where appropriate.

# Links Into Wiki

- [Relevant Page](/concepts/relevant-page.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.8 Dataset template

```markdown
---
type: Dataset
title: "Dataset Title"
description: "One-sentence description of the dataset."
resource: ""
tags: [domain, dataset, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Scope

What the dataset covers.

# Schema

| Field | Type | Description | Caveats |
|---|---|---|---|
| field_name | string | Description | Caveat |

# Provenance

Where the dataset came from.

# Joins

How this dataset links to other datasets.

# Known Caveats

- Caveat one.
- Caveat two.

# Example Uses

```python
# Example query or analysis snippet
```

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.9 Method template

```markdown
---
type: Method
title: "Method Title"
description: "One-sentence description of the method."
resource: ""
tags: [domain, method, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Purpose

What this method is for.

# Procedure

1. Step one.
2. Step two.
3. Step three.

# Inputs

- Input one.
- Input two.

# Outputs

- Output one.
- Output two.

# Failure Modes

- Failure mode one.
- Failure mode two.

# Related Tools

- [Tool](/tools/tool.md)

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.10 Tool template

```markdown
---
type: Tool
title: "Tool Title"
description: "One-sentence description of the tool."
resource: ""
tags: [domain, tool, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# What It Does

Describe the tool.

# Interface

```bash
example command
```

# Inputs

- Input one.

# Outputs

- Output one.

# Dependencies

- Dependency one.

# Failure Modes

- Failure mode one.

# Related Pages

- [Method](/methods/method.md)

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

## 14.11 Project template

```markdown
---
type: Project
title: "Project Title"
description: "One-sentence description of the project."
resource: ""
tags: [domain, project, active]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: medium
---

One-sentence summary.

# Aim

What the project is trying to achieve.

# Current State

Where things stand now.

# Key Decisions

- [Decision](/decisions/decision.md)

# Related Concepts

- [Concept](/concepts/concept.md)

# Related Entities

- [Entity](/entities/entity.md)

# Open Questions

- Question one.

# Next Review

When this page should be reviewed.

# Citations

- [Source Title](/references/source-id.md)

# Change History

- `YYYY-MM-DD`: Created.
```

---

# 15. Index Rules

`wiki/index.md` is a reserved OKF routing file.

It should be compact.

It should not become a prose essay.

It should support progressive disclosure: humans and agents should be able to inspect it before opening individual pages.

Recommended structure:

```markdown
---
okf_version: "0.1"
profile: "llm-wiki-profile/0.1"
---

# Wiki Index

## Concepts

- [LLM-Wiki](/concepts/llm-wiki.md) — Persistent LLM-maintained Markdown knowledge base.
- [Hybrid Search](/concepts/hybrid-search.md) — Search method combining lexical and semantic retrieval.
- [Wiki Drift](/concepts/wiki-drift.md) — Failure mode where pages silently become stale.

## Entities

- [Andrej Karpathy](/entities/andrej-karpathy.md) — Researcher associated with the LLM-wiki proposal.
- [OpenAI Codex](/entities/openai-codex.md) — Coding agent used to build and maintain the repository.

## Syntheses

- [LLM-Wiki versus RAG](/syntheses/llm-wiki-vs-rag.md) — Comparison of compiled knowledge and query-time retrieval.

## References

- [Karpathy LLM-Wiki Gist](/references/karpathy-llm-wiki.md) — Source proposing the LLM-wiki pattern.
```

`index.md` should usually be generated by `tools/build_index.py`.

The index entry for each page should contain:

```text
link
title
one-line description
optional tags
optional status
```

The index is a map, not the territory.

---

# 16. Overview Rules

`wiki/overview.md` is not the same as `index.md`.

`index.md` routes.

`overview.md` synthesizes.

`overview.md` should explain the current high-level state of the wiki:

```text
major domains
most important concepts
active projects
known contradictions
recently added themes
stale areas
open questions
```

The linter should flag overview drift when `overview.md` lags behind recent changes.

---

# 17. Log Rules

`wiki/log.md` is a reserved OKF update-history file.

It should record major operations:

```markdown
# Log

## 2026-07-08

- Ingested [Karpathy LLM-Wiki Gist](/references/karpathy-llm-wiki.md).
- Created [LLM-Wiki](/concepts/llm-wiki.md).
- Updated [LLM-Wiki versus RAG](/syntheses/llm-wiki-vs-rag.md).
- Ran quick lint: yellow due to two orphan pages.
```

Git history provides exact diffs.

`log.md` provides human-readable intent and context.

Keep both.

---

# 18. Linking Policy

Use standard Markdown links as canonical.

Preferred:

```markdown
The [LLM-Wiki](/concepts/llm-wiki.md) pattern differs from [Retrieval-Augmented Generation](/concepts/retrieval-augmented-generation.md) because synthesis is stored persistently rather than reconstructed at query time.
```

Avoid Obsidian-only canonical links:

```markdown
The [[LLM-Wiki]] pattern differs from [[Retrieval-Augmented Generation]].
```

Optional compatibility:

A tool may generate Obsidian-style wikilinks or aliases for local browsing, but these must not replace standard Markdown links.

## 18.1 Good links

Link concepts, entities, tools, datasets, projects, decisions, contradictions, syntheses, and references.

Good:

```markdown
[Hybrid Search](/concepts/hybrid-search.md)
[OpenAI Codex](/entities/openai-codex.md)
[Query CLI](/tools/query-cli.md)
[Source Immutability](/concepts/source-immutability.md)
```

## 18.2 Bad links

Do not link generic nouns just to inflate the graph.

Bad:

```markdown
[system](/concepts/system.md)
[knowledge](/concepts/knowledge.md)
[data](/concepts/data.md)
[thing](/concepts/thing.md)
```

A dense graph full of meaningless edges is just a hairball with delusions of grandeur.

## 18.3 Reciprocal linking

When creating a new important page, update likely parent or neighboring pages to link back to it.

Every important page should have:

```text
at least one source link
at least two meaningful outgoing links where possible
at least one inbound link from index, overview, a parent page, or a related page
```

The linter should flag pages with zero inbound links.

---

# 19. Source Ingestion Workflow

The ingest workflow is the heart of the system.

## 19.1 Capture

Users place raw files in:

```text
inbox/
```

Examples:

```text
inbox/karpathy-llm-wiki.md
inbox/project-meeting-2026-07-08.txt
inbox/plastic-treaty-draft.pdf
inbox/voice-note-recycling-policy.m4a
inbox/web-clip-open-knowledge-format.html
```

No curation happens at capture time.

Capture should be low-friction.

## 19.2 Register source

For each inbox item, the agent or deterministic script must:

1. Compute SHA-256 hash.
2. Generate stable `source_id`.
3. Copy the original file into `sources/raw/`.
4. Add or update entry in `sources/_source_registry.yml`.
5. Create a reference page in `wiki/references/`.
6. Validate that the raw file exists and hash matches.
7. Only then mark the inbox item as processed.

Example source ID:

```text
2026-07-08-karpathy-llm-wiki
```

## 19.3 Create reference page

Create a `Reference` page describing the source.

The reference page should include:

```text
source summary
key claims
extracted concepts
extracted entities
links into wiki
limited useful passages where appropriate
```

The reference page is part of the OKF bundle.

The raw source file remains immutable outside the bundle.

## 19.4 Route before reading wiki bodies

Before updating wiki content, the agent must identify relevant existing pages using deterministic tools.

Use:

```bash
python tools/query.py search "query text"
python tools/query.py hybrid "query text"
python tools/query.py graph neighbors page-slug
python tools/query.py graph path page-a page-b
python tools/query.py frontmatter --type Concept --tag llm-wiki
```

The agent should select the smallest sufficient set of candidate pages, usually 10–20, before reading full bodies.

## 19.5 Extract knowledge

For each source, extract:

```text
entities
concepts
methods
datasets
tools
projects
key claims
definitions
quantitative facts
contradictions
decisions
open questions
methodological details
links to existing pages
candidate new pages
```

The agent should classify each extracted item:

```text
new page
update existing page
contradiction
minor fact for reference page only
needs human review
```

## 19.6 Update wiki

For each relevant update:

1. Preserve existing useful text.
2. Add new evidence and nuance.
3. Cite reference pages.
4. Update `timestamp`.
5. Add source link to frontmatter.
6. Add relevant Markdown links.
7. Add reciprocal links where appropriate.
8. Keep pages under the size limit or split them.
9. Update `overview.md` if the change is significant.
10. Rebuild `index.md`.
11. Append to `log.md`.
12. Write an ingest report.

## 19.7 Validate after ingest

Run:

```bash
python tools/validate_frontmatter.py
python tools/check_links.py
python tools/word_count.py
python tools/build_index.py
python tools/build_graph.py
python tools/lint.py --quick
```

If a tool is missing, implement the tool before relying on manual inspection for that class of validation.

## 19.8 Commit

A successful ingest should produce a clear git commit:

```bash
git add sources/ wiki/ reports/ .wiki_cache/
git commit -m "ingest: add karpathy llm-wiki source"
```

---

# 20. Query Workflow

The query workflow should answer from the wiki first, then raw sources only when needed.

## 20.1 Classify the query

Classify the user’s question as one or more of:

```text
lookup
comparison
synthesis
audit
maintenance
source-check
contradiction-check
```

Examples:

```text
lookup:
What is hybrid search?

comparison:
How does an LLM-wiki differ from RAG?

synthesis:
What architecture should we use for a research-group knowledge wiki?

audit:
Which pages make unsupported claims?

maintenance:
Which concepts are underdeveloped?

source-check:
Where did this claim come from?

contradiction-check:
Do any pages conflict about this point?
```

## 20.2 Route first

Use routing tools before reading bodies:

```bash
python tools/query.py search "question text"
python tools/query.py hybrid "question text"
python tools/query.py graph neighbors llm-wiki
python tools/query.py graph path llm-wiki retrieval-augmented-generation
python tools/query.py frontmatter --type Synthesis --tag knowledge-systems
```

Read:

```text
index.md
relevant frontmatter records
graph neighborhood
top search hits
source registry entries
selected reference pages
```

Then read the selected full page bodies.

## 20.3 Open raw sources only when needed

Open raw sources only if:

1. Exact wording matters.
2. A wiki page is ambiguous.
3. A claim appears unsupported.
4. A contradiction needs source-level inspection.
5. The user explicitly asks for source-grounded detail.
6. A reference page appears stale or incomplete.

The wiki should usually be the first working layer.

Raw sources are the court record.

## 20.4 Answer format

A good answer should include:

```text
direct answer
key evidence
relevant wiki links
source links for important claims
known contradictions or uncertainties
whether the answer comes from wiki synthesis, raw sources, or both
```

## 20.5 Save valuable synthesis

If a query produces a reusable answer, the agent should propose or create a synthesis page depending on the current operating mode.

Create a synthesis page when:

```text
the answer integrates multiple pages
the answer is likely to be asked again
the answer clarifies a recurring distinction
the answer resolves or reframes a known contradiction
the answer would improve future routing
```

Do not create a synthesis page for one-off answers.

---

# 21. Lint Workflow

The linter is the wiki’s immune system.

It is not optional.

Run quick lint after every ingest.

Run full lint periodically.

## 21.1 Linter authority

The linter may:

```text
inspect metadata
read pages
query frontmatter
use graph tools
use search tools
detect missing fields
detect broken links
detect orphan pages
detect stale pages
detect duplicate pages
detect oversized pages
detect missing citations
detect overview drift
flag contradiction candidates
repair frontmatter when unambiguous
write lint reports
append to log.md
```

The linter must not:

```text
delete files
merge duplicates
rename files
create content pages
rewrite content pages
resolve substantive contradictions
change schemas
silently alter meaning
```

## 21.2 Lint checks

Run checks in this order.

### 1. Reserved file check

Validate `index.md` and `log.md` under reserved OKF rules.

Do not require ordinary content-page frontmatter for these files.

Check that `index.md` exists.

Check that `log.md` exists.

Check whether `index.md` appears stale relative to generated index data.

### 2. Schema integrity

Find pages missing required local-profile fields:

```text
type
title
description
resource
tags
timestamp
created
status
profile
sources
confidence
```

Repair metadata only when correct values are unambiguous.

Flag uncertain values for user review.

### 3. OKF compatibility

Check that all ordinary concept documents have valid YAML frontmatter.

Check that `type` exists.

Check that links are standard Markdown links.

Flag Obsidian-only links if no standard Markdown equivalent exists.

### 4. Staleness

Sort all pages by `timestamp` ascending.

Surface the 5–10 oldest important pages.

Check whether newer sources or pages contradict, supersede, or refine them.

Propose updates but do not apply substantive content changes.

### 5. Coverage gaps

Scan summaries, references, concepts, entities, methods, tools, datasets, and syntheses for repeated mentions of things that lack dedicated pages.

Candidate gaps include:

```text
tools
people
projects
datasets
methods
concepts
institutions
papers
laws
models
places
```

List each candidate gap.

Do not create pages during lint.

### 6. Overview drift

Compare `overview.md` against the newest summaries, entities, concepts, decisions, contradictions, datasets, methods, tools, projects, and syntheses.

If `overview.md` lags behind major changes, flag it as drifted.

### 7. Orphan check

For each ordinary page, compute inbound links.

Flag pages with zero inbound links.

Suggest existing pages that should link to them.

### 8. Duplicate detection

Look for duplicate or near-duplicate:

```text
filenames
slugs
titles
descriptions
body text
semantic content
```

List suspected duplicates.

Do not delete or merge.

### 9. Broken links

Find Markdown links pointing to missing local pages.

Suggest likely intended targets where obvious.

### 10. Page size

Flag pages over 1,000 words.

Suggest split targets.

### 11. Source coverage

Flag pages with empty `sources` unless they are appropriate exceptions.

Flag claims that appear unsupported.

Flag pages whose sources do not exist.

### 12. Contradiction candidates

Identify pages where newer sources appear to conflict with older claims.

Flag the tension and cite both sides.

Do not resolve the contradiction unless explicitly asked.

## 21.3 Lint report format

Write reports to:

```text
reports/lint/YYYY-MM-DD-lint-report.md
```

Use this structure:

```markdown
# Lint Report — YYYY-MM-DD

# Summary

Overall health status: 🟢 Green / 🟡 Yellow / 🔴 Red

# 1. Reserved File Check

# 2. Schema Integrity

# 3. OKF Compatibility

# 4. Staleness

# 5. Coverage Gaps

# 6. Overview Drift

# 7. Orphan Check

# 8. Duplicate Detection

# 9. Broken Links

# 10. Page Size

# 11. Source Coverage

# 12. Contradiction Candidates

# Overall Health

| Check | Status | Notes |
|---|---|---|
| Reserved files | Pass/Warn/Fail | ... |
| Schema integrity | Pass/Warn/Fail | ... |

# Next Steps

1. Action one.
2. Action two.
3. Action requiring human approval.

# Log Entry

Suggested entry for `wiki/log.md`.
```

---

# 22. Deterministic Tools

Implement these before serious use.

## 22.1 `tools/source_registry.py`

Responsibilities:

```text
compute file hashes
generate source IDs
copy files from inbox to sources/raw
update sources/_source_registry.yml
detect duplicate raw sources by hash
validate raw file existence
```

## 22.2 `tools/validate_frontmatter.py`

Responsibilities:

```text
parse YAML frontmatter
validate local-profile required fields
validate allowed type values
validate allowed status values
validate confidence values
validate timestamp format
skip reserved files under ordinary page rules
report malformed YAML
```

## 22.3 `tools/check_reserved_files.py`

Responsibilities:

```text
check index.md exists
check log.md exists
validate optional OKF/profile metadata
ensure reserved files are not treated as ordinary pages
```

## 22.4 `tools/check_links.py`

Responsibilities:

```text
extract standard Markdown links
resolve bundle-relative local links
detect broken links
compute inbound links
compute outbound links
detect Obsidian-only links
suggest likely target pages
```

## 22.5 `tools/build_index.py`

Responsibilities:

```text
read frontmatter
read first-sentence summaries
group pages by type
write wiki/index.md
preserve optional OKF/profile header
sort consistently
exclude deprecated pages or mark them clearly
```

## 22.6 `tools/build_graph.py`

Responsibilities:

```text
extract nodes from pages
extract edges from Markdown links
write .wiki_cache/graph.json
compute degree statistics
compute orphan list
compute connected components
```

## 22.7 `tools/query.py`

Responsibilities:

```text
frontmatter queries
keyword search
BM25 search
vector search
hybrid search
graph neighbors
graph shortest path
graph explanation
cluster inspection
source lookup
```

Suggested interface:

```bash
python tools/query.py search "query text"
python tools/query.py hybrid "query text"
python tools/query.py vector "query text"
python tools/query.py bm25 "query text"
python tools/query.py graph neighbors /concepts/llm-wiki.md
python tools/query.py graph path /concepts/llm-wiki.md /concepts/rag.md
python tools/query.py graph explain /concepts/llm-wiki.md
python tools/query.py frontmatter --type Concept --tag llm-wiki
```

## 22.8 `tools/word_count.py`

Responsibilities:

```text
count words in page bodies
ignore frontmatter
flag pages over 1,000 words
suggest candidate headings for splits
```

## 22.9 `tools/detect_duplicates.py`

Responsibilities:

```text
detect duplicate slugs
detect duplicate titles
detect near-identical descriptions
detect high text similarity
detect likely semantic duplicates
write review report
```

## 22.10 `tools/lint.py`

Responsibilities:

```text
run quick lint
run full lint
call lower-level validation tools
produce Markdown lint report
append log entry
exit nonzero on serious failure
```

## 22.11 `tools/ingest.py`

Responsibilities:

```text
process inbox files
call source registry
create reference pages
prepare ingest report
invoke agent or prompt for synthesis
run validation
run quick lint
```

---

# 23. Search and Graph Layer

Start simple, then mature.

## 23.1 Minimum viable routing

Use:

```text
index.md
ripgrep
frontmatter parser
link graph
```

## 23.2 Better routing

Add:

```text
SQLite FTS5
BM25 keyword search
frontmatter.sqlite
graph.json
```

## 23.3 Mature routing

Add:

```text
local embeddings
hybrid BM25 + vector search
reciprocal rank fusion
graph neighborhood expansion
cluster-aware search
source sub-catalogs
CLI interface
optional MCP server
```

## 23.4 Routing policy

Before reading bodies, the agent should ask:

```text
Which pages are probably relevant?
Which pages link to this page?
What cluster does this page belong to?
What is the shortest path between two concepts?
Which sources support this concept?
Which pages cite this source?
Which pages are stale but central?
Which contradictions affect this topic?
```

Then it should read only the selected pages.

---

# 24. Contradiction Handling

Never erase a contradiction by smoothing it into vague prose.

Use this pattern:

```markdown
# Evidence and Evolution

- `2026-06-01`: [Source A](/references/source-a.md) argues that X increases under condition Y.
- `2026-07-08`: [Source B](/references/source-b.md) reports that X decreases in a different dataset under condition Z.

# Current Interpretation

The apparent conflict likely reflects different boundary conditions: Y versus Z. This page therefore treats the claim as context-dependent rather than universal.

# Open Uncertainty

More evidence is needed on whether the discrepancy is methodological, definitional, or substantive.
```

Create a dedicated contradiction page when:

```text
the disagreement affects multiple pages
the disagreement affects an important synthesis
the sources are both credible
the disagreement is unresolved
the contradiction is likely to recur in future queries
```

A contradiction page should:

```text
state both claims
cite both sides
compare scope and methods
link all affected pages
state current interpretation
mark resolution status
```

---

# 25. Drift Control

Drift is the main long-term failure mode.

A page has drifted when:

```text
new evidence changes the state of knowledge but the page does not reflect it
an overview page no longer represents current wiki contents
a synthesis page relies on stale claims
an entity page misses important updates
cross-references are not updated after ingest
a source changes interpretation but related pages are untouched
```

Controls:

```text
run quick lint after every ingest
run full lint periodically
prioritize stale high-degree pages
prioritize stale overview and synthesis pages
track contradiction candidates
track orphan pages
track low-inbound pages
track pages with many sources but no synthesis
track pages with old timestamps and high centrality
```

A stale page with many inbound links is dangerous because many queries will route through it.

High-degree stale pages should be reviewed first.

---

# 26. Role Separation

## 26.1 Ingestor

The ingestor may create and update content pages.

Responsibilities:

```text
register sources
create reference pages
extract concepts and entities
update existing pages
create new pages when justified
add citations
add links
update reciprocal links
write ingest reports
run validation
```

## 26.2 Querier

The querier answers questions using the wiki.

Responsibilities:

```text
route before reading
answer from wiki synthesis first
consult raw sources only when needed
cite relevant pages
surface uncertainty
propose reusable synthesis pages
```

## 26.3 Linter

The linter audits health.

Responsibilities:

```text
detect structural problems
detect drift
detect orphans
detect duplicates
detect broken links
detect missing sources
flag coverage gaps
produce reports
repair unambiguous metadata
```

The linter must not rewrite content pages.

## 26.4 Reviewer

The reviewer checks agent changes before they become trusted.

Responsibilities:

```text
inspect git diff
check source preservation
check hallucinated claims
check schema validity
check link quality
check contradiction handling
approve or reject proposed merges/deletions
```

---

# 27. Deterministic Scripts Versus LLM Judgement

Use deterministic scripts for:

```text
file hashing
source registration
frontmatter validation
word counts
link extraction
backlink calculation
orphan detection
duplicate slug detection
reserved file checks
index generation
graph generation
BM25 search
vector search
hybrid search
page selection
git diff checks
```

Use the LLM for:

```text
summarization
concept extraction
entity recognition
source interpretation
contradiction judgement
new-page-versus-edit judgement
synthesis writing
cross-link suggestions
staleness interpretation
coverage gap interpretation
```

Use the human for:

```text
deletion
merging duplicates
resolving serious contradictions
changing schemas
accepting controversial rewrites
renaming high-degree pages
deciding whether uncertain information is worth preserving
```

---

# 28. Git Workflow

Use git aggressively.

Git history is the exact audit trail.

`log.md` is the readable operational history.

## 28.1 Ingest branch

```bash
git checkout -b ingest/2026-07-08-karpathy-llm-wiki
python tools/ingest.py inbox/karpathy-llm-wiki.md
python tools/lint.py --quick
git diff
git add sources/ wiki/ reports/ .wiki_cache/
git commit -m "ingest: add karpathy llm-wiki source"
```

## 28.2 Synthesis branch

```bash
git checkout -b synthesis/llm-wiki-operating-model
python tools/query.py hybrid "how should this wiki operate?"
python tools/lint.py --quick
git diff
git add wiki/ reports/ .wiki_cache/
git commit -m "synthesis: define llm-wiki operating model"
```

## 28.3 Lint branch

```bash
git checkout -b maintenance/wiki-lint-2026-07-08
python tools/lint.py --full
git diff
git add reports/ wiki/log.md
git commit -m "lint: run full wiki health check"
```

## 28.4 Merge and deletion workflow

For duplicates or obsolete files:

1. Linter flags candidates.
2. Human selects canonical page.
3. Agent proposes merge plan.
4. Human approves.
5. Agent migrates unique content.
6. Agent marks duplicate as deprecated.
7. Agent updates inbound links.
8. Agent runs validation.
9. Human reviews diff.
10. Deletion, if desired, happens only after explicit approval.

Deprecate before deleting.

---

# 29. Human Operating Procedures

## 29.1 Adding a new source

1. Drop raw file into `inbox/`.
2. Run or ask the agent to run ingest.
3. Review the ingest report.
4. Review the git diff.
5. Check that raw source preservation happened.
6. Check that no claims were invented.
7. Check that links are meaningful.
8. Check that citations point to reference pages.
9. Check that no page sprawl occurred.
10. Approve, revise, or reject.
11. Commit.

## 29.2 Asking a question

Ask the wiki directly:

```text
Using the LLM-wiki, compare compiled knowledge against RAG for research-group knowledge management.
```

The agent should:

```text
route through search and graph tools
read selected pages
answer directly
cite wiki and reference pages
surface uncertainty
propose a synthesis page if reusable
```

## 29.3 Correcting a page

Corrections should be explicit.

Do not silently erase embarrassing wrongness. Quietly deleting the trail may feel nice, but it is scientifically shabby.

Use a correction note:

```markdown
# Change History

- `2026-07-08`: Richard corrected the interpretation. The previous wording overgeneralized from [Source A](/references/source-a.md).
```

## 29.4 Reviewing drift

Regularly ask:

```text
Which high-degree pages are stale?
Which syntheses rely on old claims?
Which contradictions remain unresolved?
Which concepts are mentioned often but lack pages?
Which overview sections lag behind recent ingests?
```

## 29.5 Reviewing schema

Schema changes require care.

Before changing the schema:

1. Create a decision page.
2. Explain the reason.
3. List affected page types.
4. Update validation tools.
5. Run migration dry-run.
6. Review diff.
7. Commit schema and migration together.

---

# 30. Build Phases

## 30.1 Phase 1: Skeleton

Create:

```text
repository layout
AGENTS.md
README.md
schema files
basic page templates
empty index.md
empty log.md
overview.md
seed pages
```

Seed pages might include:

```text
/concepts/llm-wiki.md
/concepts/open-knowledge-format.md
/concepts/source-immutability.md
/concepts/wiki-drift.md
/concepts/hybrid-search.md
/concepts/compiled-knowledge.md
/concepts/retrieval-augmented-generation.md
/syntheses/llm-wiki-vs-rag.md
/decisions/use-okf-compatible-markdown-links.md
```

## 30.2 Phase 2: Basic validation

Implement:

```text
validate_frontmatter.py
check_reserved_files.py
check_links.py
word_count.py
build_index.py
build_graph.py
```

Do not ingest heavily until validation exists.

## 30.3 Phase 3: Source registration

Implement:

```text
source_registry.py
ingest.py
reference page generation
hash validation
duplicate source detection
```

Support Markdown and plain text first.

Add PDF, HTML, email, audio, and video ingestion later.

Do not build a grand cathedral before the shed has a roof.

## 30.4 Phase 4: Query and routing

Implement:

```text
keyword search
BM25 search
frontmatter queries
graph neighbors
graph path
hybrid search
```

Use simple search first.

Add embeddings when the wiki is large or semantically varied enough.

## 30.5 Phase 5: Linting

Implement deterministic lint checks first:

```text
reserved files
frontmatter
broken links
orphan pages
duplicate slugs
page size
missing sources
index freshness
```

Then add LLM-assisted lint checks:

```text
staleness
coverage gaps
contradiction candidates
overview drift
```

## 30.6 Phase 6: Review and automation

Add:

```text
scheduled lint reports
branch-based maintenance workflow
reviewer prompt
optional MCP server
optional Obsidian compatibility export
optional static site generation
optional HTML graph viewer
```

---

# 31. Minimal Command Set

The system should eventually support:

```bash
python tools/source_registry.py add inbox/file.md
python tools/ingest.py inbox/
python tools/validate_frontmatter.py
python tools/check_reserved_files.py
python tools/check_links.py
python tools/word_count.py
python tools/build_index.py
python tools/build_graph.py
python tools/query.py search "query text"
python tools/query.py bm25 "query text"
python tools/query.py vector "query text"
python tools/query.py hybrid "query text"
python tools/query.py graph neighbors /concepts/llm-wiki.md
python tools/query.py graph path /concepts/llm-wiki.md /concepts/retrieval-augmented-generation.md
python tools/query.py frontmatter --type Concept --tag llm-wiki
python tools/detect_duplicates.py
python tools/lint.py --quick
python tools/lint.py --full
```

The agent should know these commands and use them before reading many page bodies.

---

# 32. Pasteable AGENTS.md

```markdown
# AGENTS.md — LLM-Wiki Maintainer

## Mission

This repository is an LLM-wiki: a persistent, git-backed, OKF-compatible Markdown knowledge base maintained by an LLM agent and deterministic tools.

The goal is to compile raw sources into durable, cited, cross-linked knowledge.

Do not treat this as a generic notes folder or a normal RAG index. Raw sources are immutable evidence. Wiki pages are synthesized, maintained knowledge.

## Design Principles

1. Preserve raw evidence.
2. Maintain an OKF-compatible wiki bundle.
3. Enforce the stricter local profile.
4. Route before reading.
5. Use deterministic tools for mechanical checks.
6. Use LLM judgement for synthesis and interpretation.
7. Never delete without explicit human approval.
8. Prefer curation over overwriting.
9. Make contradictions explicit.
10. Keep the graph healthy through linting.

## Repository Layout

- `inbox/` — temporary drop zone for new uncatalogued material.
- `sources/raw/` — immutable raw sources. Never edit or delete these.
- `sources/_source_registry.yml` — machine-readable source registry.
- `wiki/` — OKF-compatible knowledge bundle.
- `wiki/index.md` — reserved OKF routing file.
- `wiki/log.md` — reserved OKF update-history file.
- `wiki/overview.md` — high-level synthesis of current wiki state.
- `wiki/concepts/` — concept pages.
- `wiki/entities/` — entity pages.
- `wiki/summaries/` — source or topic summaries.
- `wiki/syntheses/` — reusable higher-level answers and memos.
- `wiki/decisions/` — recorded decisions.
- `wiki/contradictions/` — unresolved tensions.
- `wiki/references/` — source catalog pages.
- `wiki/datasets/` — dataset descriptions.
- `wiki/methods/` — methods and protocols.
- `wiki/tools/` — tools and software descriptions.
- `wiki/projects/` — project pages.
- `schema/` — schemas, prompts, and policies.
- `tools/` — deterministic tooling.
- `reports/` — ingest, lint, and review reports.
- `.wiki_cache/` — generated indexes, graph files, search DBs, and embeddings.

## OKF Compatibility

The wiki is an Open Knowledge Format-compatible bundle.

Use Markdown files with YAML frontmatter.

Use standard Markdown links as canonical.

Use `index.md` and `log.md` as reserved files.

The local profile is stricter than baseline OKF. Locally created ordinary pages must include the full local frontmatter schema.

External OKF bundles with only minimal metadata should still be ingestible.

## Hard Rules

1. Never edit, rewrite, rename casually, or delete files in `sources/raw/`.
2. Never delete any file unless Richard explicitly approves.
3. Never remove historical claims merely because newer evidence exists.
4. When evidence changes, append nuance, cite the new source, and mark the evolution.
5. Every important wiki claim must trace to at least one source or reference page.
6. Do not scan all page bodies to find relevance. Use index, frontmatter, graph, and search tools first.
7. Keep ordinary content pages under 1,000 words where possible.
8. If a page grows too large, split it into smaller linked pages or flag it.
9. Use dense but meaningful standard Markdown links.
10. Update reciprocal links where appropriate.
11. Run validation after changing the wiki.
12. Record important operations in `wiki/log.md` or an appropriate report.
13. Do not treat `index.md` or `log.md` as ordinary content pages.
14. Do not make Obsidian-style wikilinks canonical.

## Canonical Local Frontmatter

Every ordinary content page in `wiki/` must begin with:

```yaml
---
type: Concept | Entity | Summary | Synthesis | Decision | Contradiction | Reference | Dataset | Method | Tool | Project | Overview
title: "Human-readable title"
description: "One-sentence description of the page."
resource: ""
tags: [domain, topic, status]
timestamp: YYYY-MM-DDTHH:MM:SSZ

created: YYYY-MM-DD
status: active | draft | stale | deprecated | needs-review
profile: llm-wiki-profile/0.1
sources:
  - "/references/source-id.md"
confidence: high | medium | low | uncertain
---
```

Immediately after the frontmatter, include a one-sentence plain-language summary.

## Source Handling

When ingesting from `inbox/`:

1. Compute a content hash.
2. Create a stable source ID.
3. Copy the original file into `sources/raw/`.
4. Update `sources/_source_registry.yml`.
5. Create a `Reference` page in `wiki/references/`.
6. Only then remove or archive the inbox copy, and only after successful validation.

Never lose raw evidence.

## Ingest Workflow

When asked to ingest a source:

1. Register the source.
2. Create or update its reference page.
3. Use deterministic routing before reading wiki bodies:
   - `wiki/index.md`
   - frontmatter search
   - graph neighbors
   - BM25 search
   - vector search
   - hybrid search
4. Select the smallest sufficient set of relevant pages.
5. Extract concepts, entities, methods, datasets, tools, projects, claims, contradictions, decisions, and open questions.
6. Decide whether each item is:
   - a new page;
   - an update to an existing page;
   - a contradiction;
   - a minor fact for the reference page only;
   - a review item.
7. Update or create pages.
8. Add source citations and Markdown links.
9. Update reciprocal links.
10. Update `overview.md` if the change is significant.
11. Rebuild `index.md` and graph cache.
12. Append to `wiki/log.md`.
13. Run validation and quick lint.
14. Produce an ingest report.

## New Page Versus Edit Heuristic

Create a new page when the item is a distinct concept, entity, project, method, dataset, tool, decision, contradiction, or synthesis that other pages would naturally link to.

Edit an existing page when the new information is an attribute, update, example, extension, caveat, new source, or correction for an existing page.

If uncertain, mark the issue as `needs-review` in the report.

## Query Workflow

When asked a question:

1. Classify the question as lookup, comparison, synthesis, audit, maintenance, source-check, or contradiction-check.
2. Use routing tools before reading page bodies.
3. Read only relevant pages and reference records.
4. Open raw sources only when exact wording, ambiguity, contradiction, or user request requires it.
5. Answer directly.
6. Include relevant Markdown links.
7. Cite reference pages for important claims.
8. State uncertainty and contradictions.
9. If the answer is reusable, propose or create a synthesis page depending on current operating mode.

## Lint Workflow

When asked to lint:

Run checks for:

1. reserved file integrity;
2. schema integrity;
3. OKF compatibility;
4. stale pages;
5. coverage gaps;
6. overview drift;
7. orphan pages;
8. duplicate pages;
9. broken links;
10. oversized pages;
11. missing sources;
12. contradiction candidates.

The linter may repair frontmatter only when the correct value is certain.

The linter must not create, delete, merge, rename, or rewrite content pages without explicit approval.

Write a Markdown lint report in `reports/lint/`.

## Link Policy

Use standard Markdown links:

```markdown
[Hybrid Search](/concepts/hybrid-search.md)
```

Do not use Obsidian-style wikilinks as canonical links.

Link meaningful concepts, entities, references, datasets, methods, tools, projects, decisions, contradictions, and syntheses.

Do not link generic nouns.

Every important new page should have at least one source link and at least two meaningful outgoing links where possible.

Update inbound links from related pages when creating important new pages.

## Contradiction Policy

Do not hide contradictions.

If new evidence conflicts with old evidence:

1. preserve the old claim where useful;
2. append the new evidence;
3. cite both sources;
4. explain the current interpretation;
5. create or update a contradiction page if the issue is substantial.

## Validation Commands

After changes, run relevant checks:

```bash
python tools/validate_frontmatter.py
python tools/check_reserved_files.py
python tools/check_links.py
python tools/word_count.py
python tools/build_index.py
python tools/build_graph.py
python tools/lint.py --quick
```

If a command is missing, implement the missing tool before relying on manual inspection.

## Definition of Done

A task is done only when:

1. raw sources are preserved;
2. reference pages exist for ingested sources;
3. wiki pages have valid local-profile frontmatter;
4. important claims have source links;
5. standard Markdown links are used;
6. relevant reciprocal links are present;
7. no obvious duplicate or orphan was introduced;
8. page size limits are respected or split recommendations are recorded;
9. index and graph are rebuilt;
10. lint passes or warnings are explained;
11. git diff is reviewed;
12. a clear summary of changes is provided.
```

---

# 33. Wiki Linter Prompt

```markdown
# Wiki Linter — System Prompt

You are a wiki health checker. When invoked, run a structured lint pass over an OKF-compatible Markdown wiki and produce a report.

Use deterministic tools for frontmatter queries, reserved-file checks, link checks, graph checks, search, duplicate detection, word counts, and file reads.

## Checks

### 1. Reserved File Integrity

Check that `index.md` and `log.md` exist.

Validate them under reserved OKF rules, not ordinary content-page rules.

Flag stale or missing reserved files.

### 2. Schema Integrity

Find ordinary pages missing required local-profile fields:

- type
- title
- description
- resource
- tags
- timestamp
- created
- status
- profile
- sources
- confidence

Repair metadata only when the correct value is unambiguous.

Flag uncertain values for user review.

### 3. OKF Compatibility

Check that pages are Markdown files with YAML frontmatter.

Check that `type` exists.

Check that local links use standard Markdown syntax.

Flag Obsidian-only links.

### 4. Staleness

Sort pages by `timestamp` ascending.

Surface the 5–10 oldest important pages.

Check whether newer pages or sources contradict, supersede, or refine them.

Propose updates but do not apply substantive content changes.

### 5. Coverage Gaps

Scan references, summaries, entities, concepts, datasets, methods, tools, projects, and syntheses for repeated mentions of things that lack dedicated pages.

List candidate gaps.

Do not create pages.

### 6. Overview Drift

Compare `overview.md` against the newest content pages.

If `overview.md` lags behind major changes, flag it as drifted.

### 7. Orphan Check

For each ordinary page, check whether any other page links to it.

Flag pages with zero inbound links.

Suggest which existing pages should link to them.

### 8. Duplicate Detection

Look for multiple files with the same or near-identical slugs, names, titles, descriptions, or body content.

List suspected duplicates with file paths.

Do not delete or merge anything.

### 9. Broken Links

Find standard Markdown links pointing to missing local pages.

Suggest likely intended targets where obvious.

### 10. Page Size

Flag ordinary content pages over 1,000 words.

Suggest possible split targets.

### 11. Source Coverage

Flag pages with empty or invalid `sources`.

Flag claims that appear unsupported.

### 12. Contradiction Candidates

Identify pages where newer sources appear to conflict with older claims.

Flag the tension and cite both sides.

Do not resolve the contradiction unless explicitly asked.

## Output Format

# Lint Report — YYYY-MM-DD

# Summary

One-line overall health status: 🟢 Green / 🟡 Yellow / 🔴 Red

# 1. Reserved File Integrity
# 2. Schema Integrity
# 3. OKF Compatibility
# 4. Staleness
# 5. Coverage Gaps
# 6. Overview Drift
# 7. Orphan Check
# 8. Duplicate Detection
# 9. Broken Links
# 10. Page Size
# 11. Source Coverage
# 12. Contradiction Candidates

# Overall Health

| Check | Status | Notes |
|---|---|---|
| Reserved files | Pass/Warn/Fail | ... |
| Schema integrity | Pass/Warn/Fail | ... |
| OKF compatibility | Pass/Warn/Fail | ... |
| Staleness | Pass/Warn/Fail | ... |
| Coverage gaps | Pass/Warn/Fail | ... |
| Overview drift | Pass/Warn/Fail | ... |
| Orphans | Pass/Warn/Fail | ... |
| Duplicates | Pass/Warn/Fail | ... |
| Broken links | Pass/Warn/Fail | ... |
| Page size | Pass/Warn/Fail | ... |
| Source coverage | Pass/Warn/Fail | ... |
| Contradictions | Pass/Warn/Fail | ... |

# Next Steps

Numbered list of actions.

Mark which require human approval.

# Log Entry

Suggested entry for `wiki/log.md`.

## Hard Rules

- Never delete files unilaterally.
- Never merge duplicates without approval.
- Never create or edit substantive content pages.
- Never resolve substantive contradictions.
- Do repair frontmatter when the correct value is certain.
- Log the lint pass to `wiki/log.md` when done.
```

---

# 34. Reviewer Prompt

```markdown
# Wiki Reviewer — System Prompt

You are a reviewer for an LLM-wiki change set.

Your job is to inspect proposed changes before they are treated as trusted wiki updates.

## Review Checks

1. Raw sources were preserved in `sources/raw/`.
2. Source registry entries are correct.
3. Reference pages exist for new sources.
4. Wiki pages use valid local-profile frontmatter.
5. `index.md` and `log.md` were handled under reserved-file rules.
6. Important claims are supported by reference links.
7. Standard Markdown links are used.
8. No Obsidian-only canonical links were introduced.
9. No raw source was edited.
10. No file was deleted without approval.
11. No historical claim was silently erased.
12. Contradictions were represented explicitly.
13. Page size limits were respected or split recommendations were recorded.
14. Reciprocal links were added where appropriate.
15. No obvious duplicate page was created.
16. No high-degree page was renamed without approval.
17. Validation commands were run.
18. Lint warnings are explained.

## Output Format

# Review Report — YYYY-MM-DD

# Verdict

Approve / Request Changes / Reject

# Main Issues

# Required Fixes

# Suggested Improvements

# Risk Notes

# Final Recommendation
```

---

# 35. Practical Operating Model

The routine use pattern should be:

```text
capture → ingest → validate → review → commit → query → synthesize → lint → maintain
```

## Daily or per-session

```text
drop files into inbox
run ingest
review diff
commit accepted changes
```

## Weekly or periodic

```text
run full lint
review stale high-degree pages
review contradiction candidates
review orphan pages
review coverage gaps
update overview.md
```

## Project milestone

```text
ask synthesis questions
convert reusable answers into synthesis pages
review decisions
archive or deprecate old pages
update overview and project pages
```

---

# 36. Recommended First Seed Pages

Create these manually or through a controlled initial ingest:

```text
/concepts/llm-wiki.md
/concepts/open-knowledge-format.md
/concepts/compiled-knowledge.md
/concepts/retrieval-augmented-generation.md
/concepts/source-immutability.md
/concepts/wiki-drift.md
/concepts/context-contamination.md
/concepts/hybrid-search.md
/concepts/bm25-search.md
/concepts/vector-search.md
/concepts/reciprocal-rank-fusion.md
/concepts/frontmatter.md
/concepts/progressive-disclosure.md
/methods/source-ingestion.md
/methods/wiki-linting.md
/methods/graph-routing.md
/tools/query-cli.md
/tools/sqlite-fts5.md
/decisions/use-okf-compatible-markdown-links.md
/decisions/adopt-local-profile-over-minimal-okf.md
/syntheses/llm-wiki-vs-rag.md
/syntheses/llm-wiki-operating-model.md
```

---

# 37. Failure Modes

## 37.1 Context contamination

The agent reads too much irrelevant text and produces muddled synthesis.

Prevention:

```text
route before reading
use compact index
use graph and search tools
limit page reads
```

## 37.2 Page sprawl

The agent creates too many tiny marginal pages.

Prevention:

```text
use new-page-versus-edit heuristic
require natural linkability
flag uncertain pages for review
lint for duplicates
```

## 37.3 Mega-pages

Pages become too long and unfocused.

Prevention:

```text
1,000-word target
word-count linting
split pages by concept
use synthesis pages for integration
```

## 37.4 Silent drift

Pages become stale as new evidence accumulates elsewhere.

Prevention:

```text
quick lint after ingest
full lint periodically
stale high-degree page review
overview drift detection
contradiction candidate detection
```

## 37.5 Unsupported synthesis

The agent writes plausible claims without evidence.

Prevention:

```text
required sources field
citation checks
review reports
source coverage lint
raw source inspection for high-stakes claims
```

## 37.6 Broken graph

Links break, orphans accumulate, and navigation degrades.

Prevention:

```text
standard Markdown links
link checker
graph builder
orphan lint
reciprocal link updates
```

## 37.7 Schema erosion

Agents gradually violate the schema.

Prevention:

```text
AGENTS.md
validate_frontmatter.py
schema decision pages
review before schema changes
strict local profile
```

## 37.8 Overwriting history

New evidence replaces old claims without recording the evolution.

Prevention:

```text
curation over overwriting
change history sections
contradiction pages
source citations
git diff review
```

---

# 38. The Simplest Mental Model

```text
/sources/raw = evidence
/wiki = OKF-compatible compiled knowledge
/wiki/references = source catalog inside the knowledge graph
/schema = law
/tools = bureaucracy
AGENTS.md = constitution
index.md = map
overview.md = state of knowledge
log.md = readable memory
linter = immune system
git = forensic record
agent = synthesis engine
human = court of appeal
```

That is the system.

The rest is implementation detail, but implementation detail sharp enough to remove fingers.