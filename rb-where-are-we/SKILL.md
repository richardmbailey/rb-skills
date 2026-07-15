---
name: "rb-where-are-we"
description: "Use when the user wants a deep, evidence-backed HTML state-of-play report covering project goals, current phase, progress, code health, risks, recent changes, and next steps. Do not use merely to resume work or create a handoff."
---

# RB Where Are We

Create a professional state-of-play report that starts with the one-minute answer and becomes progressively more detailed. Explain the practical meaning first, then provide precise technical evidence.

## Scope and boundaries

- Default to the repository in the current working directory. Confirm the path only when the target is genuinely ambiguous.
- Treat the project as read-only. Create only the HTML report under `reports/status/`; do not edit product code, plans, diaries, issue state, or other status sources.
- Report the whole project unless the user names a particular implementation plan, phase, workstream, or release.
- This is deeper than `$rb-continue-project`: it assesses goals, progress, health, readiness, risks, and recent changes rather than only preparing to resume work.
- Summarize recent changes here. Recommend `$rb-explain-diff` when a particular change needs a full teaching-oriented walkthrough.
- Identify architecture only as far as needed to understand status. Recommend `$rb-explain-codebase` or `$rb-architecture-review` for a dedicated deep analysis.

## Gather evidence

Use each source for the kind of truth it can support:

1. Read repository instructions first: `AGENTS.md`, `CONTEXT.md`, tool-specific instructions, and relevant README files.
2. Establish intended direction from PRDs, roadmaps, architecture decisions, implementation plans, phase files, issue descriptions, and release criteria.
3. Establish continuity from existing working-diary entries, handoffs, decisions, investigations, and open questions. Read these when discoverable, but do not create or update them during this reporting workflow unless the user separately asks.
4. Establish current repository state from the active branch, `git status --short`, recent commits, relevant diffs, file structure, and active plan/checklist files.
5. Establish code health from current tests, builds, linters, type checks, benchmark or evaluation artifacts, coverage reports, CI results, runtime logs, and deployment evidence when available.
6. Consult external issue trackers, pull requests, dashboards, or project systems only when the user names them, repository instructions identify them as authoritative, or they are already in scope.

Do not read the entire repository indiscriminately. Follow project indexes, plans, entry points, test configuration, and recent changes to select relevant evidence.

## Keep claims honest

Label important claims with one of four evidence states:

- `verified`: observed or checked in this run;
- `documented`: stated by a project source, with its date or revision when available;
- `inferred`: a reasoned conclusion from evidence, clearly separated from fact;
- `unknown`: evidence is absent, stale, contradictory, or inaccessible.

Use live repository state for current truth, but use goal and plan documents for intended direction. When sources conflict, show the disagreement and explain which source is more current or authoritative.

Never invent completion percentages, performance numbers, deadlines, or confidence. Use numeric progress only when a real denominator exists, such as a phase checklist or explicit acceptance-criteria set, and show how the number was calculated.

Do not present old test or benchmark results as current. Give the result, source, and date, or label it unknown. Distinguish "not run", "not found", and "failed".

## Run proportionate checks

1. Discover the repository's documented test and validation commands before running anything.
2. Run safe, already-configured, reasonably quick checks when they materially improve the report's freshness.
3. Do not install dependencies, start services, alter data, run migrations, access production, or launch expensive or long-running suites and benchmarks without approval.
4. If a useful check is unavailable or disproportionate, report the limitation rather than substituting an improvised result.
5. Record every command run, its outcome, and when it ran in the evidence appendix.

## Assess the state of play

Build the report around these questions:

1. What is the project trying to achieve, and for whom?
2. What is the current roadmap, milestone, release, or implementation phase?
3. What capabilities work now, what is incomplete, and what is only planned?
4. How healthy is the code across:
   - functional completeness;
   - correctness and test evidence;
   - runtime performance and efficiency;
   - reliability, operations, and observability;
   - maintainability and technical debt;
   - delivery or release readiness?
5. What is blocked, risky, contradictory, or unknown?
6. What changed recently, including committed and uncommitted work?
7. What are the few highest-value next steps, and how will completion be verified?

Use the health labels `strong`, `mixed`, `at-risk`, and `unknown`, always with a plain-language rationale and evidence. These are judgments, not scores.

## Build the progressive narrative

Use these top-level sections in this exact order:

1. `executive-summary` - the one-minute answer: overall goal, current phase, health, biggest risk, and recommended next move.
2. `goals-roadmap` - destination, users, milestones, completed work, and a visible "you are here" marker.
3. `health` - the six health dimensions above, with current evidence and limitations.
4. `current-phase` - phase objective, verified completion, work in progress, remaining tasks, dependencies, and exit criteria.
5. `system-view` - the minimum architecture and data flow needed to understand the status of the implemented pieces.
6. `risks` - blockers, technical debt, unresolved decisions, contradictory evidence, and material unknowns.
7. `recent-changes` - the lowest-level section: the current worktree plus a clearly stated recent commit or phase window, grouped by behaviour rather than listed mechanically.
8. `next-steps` - a short ordered set of actions with rationale, dependency, and verification method.
9. `evidence` - sources, commands, dates, scope, exclusions, and confidence limitations.

Keep recent code discussion selective. Use short code snippets only when they clarify an important change or risk; do not turn the report into a line-by-line review.

## Construct the HTML

Save one self-contained file at:

```text
<repository-root>/reports/status/YYYY-MM-DD-where-are-we-<project-or-scope-slug>.html
```

Use the current local date. Create `reports/status/` if needed. Do not overwrite an unrelated report; add a short distinguishing suffix when necessary.

The file must satisfy this contract:

- Use `<!doctype html>`, `lang`, a viewport meta tag, semantic headings, and one long scrolling page.
- Include one linked `<nav class="toc" aria-label="Table of contents">`. Do not use tabs for top-level navigation.
- Use the nine section IDs listed above and include all of them in the table of contents.
- Embed all CSS and any JavaScript. Do not depend on CDNs, remote fonts, external images, network requests, or build steps.
- Provide responsive styling, visible keyboard focus, adequate contrast, print-friendly layout, and reduced-motion behaviour.
- Show the generation time in `<time class="report-generated" datetime="...">`.
- Include an `.evidence-legend`. Mark major claims with `data-evidence="verified|documented|inferred|unknown"` and visible text, not colour alone.
- Present the six code-health dimensions as `.health-card` elements with `data-health="strong|mixed|at-risk|unknown"`.
- Include at least one `.check-result`, even when it records that no live checks were run, and list consulted sources as `.evidence-source` elements.
- State the recent-history scope in an element with class `change-window`.
- Use simple HTML/CSS flow or system diagrams when they clarify multiple milestones or components. Give diagram containers class `diagram`; do not use ASCII art or external diagram libraries.
- Use callouts for the most important risk, contradiction, definition, or limitation.
- Use native `<details>` elements for optional low-level evidence when useful; keep every top-level section on the same page.
- Put every code excerpt in `<pre>` or `<pre><code>`. Escape HTML inside excerpts. If the page contains a `<pre>`, its CSS must apply `white-space: pre` or `white-space: pre-wrap`; prefer `pre-wrap` for narrow screens.

## Validate and inspect

Run the bundled validator:

```bash
python3 <skill-directory>/scripts/validate_status_html.py <repository-root>/reports/status/YYYY-MM-DD-where-are-we-<slug>.html
```

Fix every validation error. Use `--allow-historical-date` only when rechecking an older report, never to excuse a newly created file with the wrong date.

When browser control is available, inspect desktop and phone widths, follow the table-of-contents links, open details elements, confirm diagrams remain legible, and check print preview when practical. If browser inspection is unavailable, report that limitation.

Before handoff, recheck representative status claims against their sources and ensure failed, missing, and stale evidence is visible rather than softened.

## Report the result

Return a link to the HTML file and briefly state:

- the project and scope assessed;
- live checks run and their outcomes;
- the recent-change window;
- major evidence limitations;
- whether deterministic and browser validation passed.

Do not begin the recommended implementation work unless the user separately asks.

## Failure handling

- If there is no formal goal or plan, say so and separate inferred direction from documented intent.
- If the repository is not under Git, use available files and timestamps and mark Git history unavailable.
- If the worktree is dirty, preserve it and explain how those changes affect the current state.
- If the repository is too large for full inspection, state the sampled scope and what was excluded.
- If evidence conflicts or is stale, show the conflict and use `unknown` rather than forcing a confident conclusion.
- If validation fails, do not present the report as complete.
