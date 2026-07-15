---
name: "rb-explain-codebase"
description: "Use when the user needs orientation to an unfamiliar repository: its structure, control flow, data flow, dependencies, and change hotspots. Do not use for architectural critique or to explain one specific diff."
---

# /rb:explain-codebase - understand the codebase

## Purpose

Explain an unfamiliar repository before making changes.

## Procedure

1. Read `AGENTS.md`, `CONTEXT.md`, README files, and obvious setup docs when present.
2. Inspect top-level files and directories.
3. Identify package managers, build systems, runtimes, test frameworks, and common commands.
4. Map important modules and public entry points.
5. Trace main control flow and data flow.
6. If the repository implements a multi-LLM-agent system, also use `$rb-multi-agent-systems` to map agent boundaries, tools, handoffs, state, retrieval, observability, evals, provider routing, and durability.
7. Identify external dependencies, likely change hotspots, risky areas, and places where behavior is guarded by tests.
8. Update `$rb-working-diary` with durable orientation notes when the repo is substantial or future work is likely.

## Required behaviour

- Do not edit code during orientation unless the human explicitly asks.
- Do not pretend uncertain architecture is known; mark unknowns clearly.
- Prefer concrete file and symbol references over broad summaries.

## Output

- repository purpose and apparent project type
- important directories/files and what owns what
- entry points, build/test commands, and runtime configuration
- main control-flow and data-flow sketch
- dependency and integration map
- likely hotspots and risky areas
- recommended next skill or first safe investigation step
