# Repository Guidance

This repository contains reusable agent skills for Codex and Claude Code. Keep skill instructions concise, procedural, and focused on decisions another agent must make.

When instructions name a skill as `$rb-name`, use that form in Codex and `/rb-name` in Claude Code. The workflow meaning is the same; only the direct invocation syntax changes.

## Deterministic vs Semantic Text Handling

When implementing or reviewing code that handles text:

- Use deterministic parsing for stable structure and syntax: JSON, YAML, XML, CSV, frontmatter, exact delimiters, known IDs, URLs, file paths, logs, protocol fields, and other formats with explicit grammar.
- Prefer structured parsers and existing libraries for structured formats before regex.
- Use an LLM-backed path when correctness depends on meaning: intent, relevance, classification, summarisation, ambiguity resolution, rubric judgment, natural-language extraction, entity or claim matching, or deciding whether differently worded passages mean the same thing.
- Do not build elaborate regexes, keyword lists, fuzzy string scoring, or brittle heuristics as substitutes for semantic understanding.
- When using an LLM, wrap it with deterministic boundaries: bounded inputs, typed outputs, validation, retries or visible failure, and focused fixtures/evals where practical.
