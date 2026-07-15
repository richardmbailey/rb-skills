---
name: "rb-explain-diff"
description: "Use when the user asks for a rich explanation of a code change, working-tree diff, commit, branch comparison, or pull request. Explore the surrounding system and produce a self-contained interactive HTML explainer with background, intuition, a grouped code walkthrough, diagrams, and a five-question quiz."
---

# RB Explain Diff

Create a durable, beginner-friendly explanation of a specified code change as one interactive HTML page. Explain the plain-language idea before introducing technical details.

## Establish the change scope

1. Read repository instructions such as `AGENTS.md`, `CONTEXT.md`, and relevant README files.
2. Resolve the exact change target from the request: an attached diff, pull request, commit, commit range, branch comparison, staged changes, or working-tree changes.
3. If the request does not name a target, use an unambiguous target already established by the conversation. Otherwise, inspect the current staged and unstaged changes. Ask a concise question only when multiple plausible scopes would produce materially different explanations.
4. Record the repository, baseline, head, commit or pull request identifier, and inspection date in the page. State any scope assumption explicitly.
5. Treat the requested change as read-only. Apart from the explainer under `explanations/`, do not modify product code.

## Investigate before writing

1. Inspect the complete change, including file status, renames, deletions, generated files, tests, configuration, and migrations.
2. Explore the existing system broadly enough to teach it:
   - locate user-facing or public entry points;
   - trace the relevant control flow and data flow;
   - inspect callers, callees, state, schemas, interfaces, and tests;
   - read nearby documentation and useful history when they clarify intent.
3. Reconstruct the before-and-after behaviour. Trace at least one concrete example through both versions when possible.
4. Separate verified facts from inference. Mark uncertainty rather than inventing intent.
5. Exclude irrelevant generated or vendored churn from the narrative, but disclose that it was omitted.
6. Redact credentials, tokens, personal data, and other secrets even if they appear in the diff.

## Build the narrative

Write in classic, direct prose with smooth transitions. Assume no prior knowledge, but make the beginner material easy to skip. For every technical topic, first explain the practical idea in plain language and then give the precise names, files, symbols, and mechanisms.

Use these top-level sections in this order:

### Background

- Begin with a clearly labelled beginner subsection, `id="background-beginner"`, explaining the broad system, the user problem it solves, and essential vocabulary.
- Follow with a narrower subsection, `id="background-change"`, tracing the components and existing behaviour directly relevant to the change.
- Show where the change sits in the larger system. Use example data in the diagram, not only component names.

### Intuition

- Explain the smallest useful mental model for the change before implementation details.
- Use toy data to show before, transformation, and after.
- Include important invariants, trade-offs, and edge cases as callouts.
- Reuse a small number of visual families, such as a system-flow diagram and a simplified user-interface state, rather than inventing a new visual grammar for every example.

### Code

- Group the changes by responsibility, behaviour, or data flow, not merely by filename order.
- Explain how the groups fit together and why that order is useful.
- Use short, carefully selected before-and-after excerpts. Do not reproduce the whole diff.
- Name concrete paths and symbols, and explain their role in plain language before discussing implementation details.
- Connect tests and configuration to the behaviour they protect.

### Quiz

- Write exactly five medium-difficulty multiple-choice questions that test the substance of the change rather than trivia.
- Give each question at least two plausible options and exactly one correct answer.
- On click, reveal whether the selection is correct and explain why. Give useful feedback for incorrect choices.
- Make the interaction keyboard accessible and keep the correct answer hidden until the reader chooses.

## Construct the HTML

Save one self-contained file at:

```text
<repository-root>/explanations/YYYY-MM-DD-explanation-<short-slug>.html
```

Use the current local date. Create `explanations/` if needed. Choose a stable slug from the pull request, branch, commit, or main behaviour. Do not overwrite an unrelated existing explanation; add a short distinguishing suffix instead.

The file must satisfy this contract:

- Use `<!doctype html>`, a viewport meta tag, semantic headings, and one long scrolling page.
- Include a linked `<nav class="toc" aria-label="Table of contents">`. Do not use tabs for top-level navigation.
- Use top-level section IDs `background`, `intuition`, `code`, and `quiz`.
- Embed all CSS and JavaScript. Do not depend on CDNs, remote fonts, external images, or build steps.
- Provide responsive styling for narrow screens, visible keyboard focus, adequate contrast, and sensible reduced-motion behaviour.
- Build diagrams from labelled HTML boxes, connectors, lists, and inline example values. Do not use ASCII art. Prefer HTML/CSS diagrams over a library that would add an external dependency.
- Use callouts for definitions, key concepts, important edge cases, and scope limitations.
- Put every code excerpt in `<pre>` or `<pre><code>`. Escape HTML inside excerpts. Include a CSS rule that applies `white-space: pre` or `white-space: pre-wrap` to `pre`; prefer `pre-wrap` for phone layouts.
- Give diagram containers the class `diagram` and callouts the class `callout`.
- Mark up each quiz question as `<article class="quiz-question">`.
- Mark up each answer as `<button class="quiz-option" data-correct="true|false">` and include a `.quiz-feedback` element with `aria-live="polite"` inside each question.
- Use unobtrusive JavaScript event listeners to evaluate choices, expose the explanation, and show a clear selected/correct/incorrect state.

## Validate and inspect

Run the bundled validator before handing off the file:

```bash
python3 <skill-directory>/scripts/validate_explanation_html.py <repository-root>/explanations/YYYY-MM-DD-explanation-<short-slug>.html
```

The validator checks the current date, required sections, self-contained resources, diagrams, callouts, quiz structure, and code-block whitespace. Fix every error and rerun it. Use `--allow-historical-date` only when rechecking an explanation created on an earlier date; never use it to excuse a newly created file with the wrong date.

Then inspect the rendered page in a browser when browser control is available:

1. Check the page at desktop and narrow phone widths.
2. Follow every table-of-contents link.
3. Answer every quiz question, including at least one incorrect choice, and confirm the feedback is accurate.
4. Check that diagrams remain legible, code wraps without collapsing newlines, and no content overflows.
5. Recheck a representative claim and code excerpt against the repository source.

If browser inspection is unavailable, report that limitation and complete the deterministic validation.

## Report the result

Provide the change target, a link to the HTML file, the validator result, and whether browser interaction was checked. Mention material scope assumptions, omitted generated churn, or unresolved uncertainty.

## Failure handling

- If the pull request or remote change cannot be accessed, ask for a local branch, commit range, or diff rather than guessing.
- If the change is too large for one coherent walkthrough, organize it into a few themes and state what was intentionally summarized.
- If repository history conflicts with the diff, explain the observed behaviour and label inferred intent separately.
- If validation fails, do not hand off the file as complete.
