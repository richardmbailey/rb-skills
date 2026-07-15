# RB Skills Routing And Instruction Quality Implementation Plan

## Summary

Improve the trigger descriptions and instruction bodies for every skill in `rb-skills` except `rb-wiki`. The work should reduce both missed invocations and accidental invocations, remove duplicated or irrelevant instructions, preserve safety and output contracts, and introduce behavioural routing evaluations that compare the current baseline with the revised skills.

The baseline is commit `9875708` (`Add reporting and skill evaluation workflows`). At that baseline the repository has 29 skills, 975 frontmatter-description words, eight descriptions longer than 40 words, and only two descriptions that explicitly route a neighbouring request to another skill.

`rb-wiki` is deliberately frozen for this project. The narrower `rb-new-wiki`, `rb-wiki-ingest`, and `rb-wiki-maintenance` skills remain in scope because their descriptions can be clarified without editing the umbrella skill.

## Goals

- Make each in-scope skill easy to invoke from realistic user language, including paraphrases and underspecified requests.
- Put important negative routing boundaries in frontmatter descriptions, where they can affect skill selection.
- Distinguish overlapping skill families with concise, consistent language.
- Remove instructions that repeat the same routing rule, introduce irrelevant technology preferences, or do not materially change agent behaviour.
- Retain safety rules, evidence requirements, validation contracts, and project-specific operating constraints.
- Add reproducible positive, negative, ambiguous, and regression cases for skill routing.
- Compare the revised skills against the `9875708` baseline before accepting the changes.
- Keep total always-loaded description text at or below the baseline while improving routing precision.

## Non-goals

- Do not edit any file under `rb-wiki/`.
- Do not redesign the LLM-wiki architecture or resolve the overlap inside the `rb-wiki` body during this project.
- Do not change the substantive output contracts of `rb-explain-diff` or `rb-where-are-we` unless an evaluation exposes a real defect.
- Do not change product code outside this skills repository.
- Do not replace semantic routing evaluation with keyword-only heuristics.
- Do not publish or push changes automatically; commits and pushes remain separate user decisions.
- Do not require every narrowly scoped skill to contain a formulaic `Do not use` sentence when its nearest boundary is already unambiguous and tested.

## Users

- Richard, using the skills through Codex and Claude Code.
- Codex and Claude Code, which must select the correct skill from frontmatter metadata.
- Future maintainers who need to understand why one skill owns a request and neighbouring skills do not.

## Requirements

### Routing contract

Each in-scope description must state:

1. the user intent or task that should invoke the skill;
2. concrete natural-language trigger concepts, not only internal skill names;
3. the nearest confusing negative case when a sibling skill overlaps;
4. the alternative skill for that negative case when one exists;
5. the distinctive output or workflow only when it materially helps disambiguation.

Descriptions should normally follow this shape without becoming mechanical:

```text
Use when <positive user intent and realistic trigger language>.
Do not use for <nearest neighbouring intent>; use $<sibling-skill> instead.
```

### Instruction-body contract

- Keep instructions procedural and tied to observable decisions, outputs, validations, or safety constraints.
- Remove repeated routing explanations once the frontmatter and one body boundary express them clearly.
- Remove general technology recommendations from cross-domain workflow skills unless those recommendations are essential to that workflow.
- Move detailed, conditional framework guidance into a directly linked reference file when it remains useful but should not always load.
- Preserve the deterministic-versus-semantic text-handling rule, but use a concise consistent form rather than repeating long catalogues everywhere.
- Preserve explicit permission boundaries, read-only defaults, validation requirements, and failure handling.

### Evaluation contract

- Use repository-level routing evaluations under `evals/skill-routing/`.
- Evaluate realistic user prompts semantically; use deterministic validation for manifest structure, expected skill names, fixture layout, and result schemas.
- Record the expected selected skill, skills that must not be selected, acceptable clarification behaviour, and outcome checks where the body changed.
- Compare baseline and revised descriptions under matched model and harness conditions.
- Repeat important nondeterministic cases at least three times.
- Preserve raw results and distinguish routing failure, execution failure, evaluator failure, and unavailable execution.

## Assumptions

- The versioned repository at `/Users/richardbailey/GitHub/rb-skills` remains the source of truth.
- The existing symlink installation model remains unchanged.
- Codex is the primary evaluation harness; Claude Code is a secondary compatibility target when a safe non-interactive evaluation route is available.
- The frontmatter `description` is the main automatic-selection surface; body-only negative cases cannot prevent the initial over-call.
- Existing `agents/openai.yaml` files are updated only when the display name, short description, or default prompt becomes stale.
- `rb-context-tokens`, `rb-end-session`, `rb-implement-with-tests`, `rb-new-wiki`, `rb-research-question-gate`, and `rb-tdd-scientific-code` are verification-first: edit them only when the routing review or behavioural evidence identifies a concrete issue.

## Constraints

- Preserve all existing user work and use small reviewable commits.
- Keep `SKILL.md` frontmatter to `name` and `description` only.
- Keep each `SKILL.md` under 500 lines and prefer progressive disclosure.
- Do not make `rb-wiki` changes indirectly through formatting, metadata regeneration, or broad search-and-replace.
- Do not assume that a shorter description is better if it loses realistic trigger language.
- Do not declare improved routing from static review alone.
- Do not install dependencies merely to run the evaluation suite without explicit approval.
- Use deterministic parsers for YAML/JSON and semantic judgment for intent boundaries.

## Proposed Approach

### 1. Work by routing family

Edit and evaluate sibling skills together so each boundary is written from both sides.

| Family | Skills | Boundary to establish |
| --- | --- | --- |
| Planning and delivery | `rb-discuss`, `rb-create-implementation-plan`, `rb-execute-plan`, `rb-create-issues`, `rb-implement-with-tests`, `rb-tdd-scientific-code` | unresolved requirements vs top-level planning vs phase execution vs issue decomposition vs ordinary/scientific implementation |
| Project lifecycle | `rb-start-project`, `rb-continue-project`, `rb-where-are-we`, `rb-end-session` | first onboarding vs resumption vs state-of-play assessment vs handoff/closure |
| Understanding and review | `rb-explain-codebase`, `rb-architecture-review`, `rb-explain-diff`, `rb-review-pr-or-diff`, `rb-diagnose` | orientation vs structural critique vs teaching explanation vs defect review vs root-cause investigation |
| Skill management | `rb-write-skill`, `rb-create-skill-evals`, `rb-sync-skills-repo`, `rb-setup-local-agent-skills`, `rb-install-skills` | author/update vs evaluate vs repository sync vs setup repair vs full installation/onboarding |
| Wiki operations | `rb-new-wiki`, `rb-wiki-ingest`, `rb-wiki-maintenance` | create from template vs process new sources vs maintain an existing wiki; `rb-wiki` remains untouched |
| Context and research | `rb-working-diary`, `rb-project-language`, `rb-context-tokens`, `rb-research-question-gate` | durable continuity vs vocabulary/context capture vs token reporting vs research novelty gate |
| Agent architecture | `rb-multi-agent-systems` | multi-agent boundaries and orchestration, not any isolated mention of an agent framework or tool |

### 2. Classify the expected edit depth

#### Substantive routing or body cleanup

- `rb-working-diary`
- `rb-start-project`
- `rb-execute-plan`
- `rb-discuss`
- `rb-setup-local-agent-skills`
- `rb-multi-agent-systems`

#### Frontmatter boundary improvement, with body edits only if needed

- `rb-architecture-review`
- `rb-continue-project`
- `rb-create-implementation-plan`
- `rb-create-issues`
- `rb-create-skill-evals`
- `rb-diagnose`
- `rb-explain-codebase`
- `rb-explain-diff`
- `rb-install-skills`
- `rb-project-language`
- `rb-review-pr-or-diff`
- `rb-sync-skills-repo`
- `rb-where-are-we`
- `rb-write-skill`
- `rb-wiki-ingest`
- `rb-wiki-maintenance`

#### Verification-first; change only with evidence

- `rb-context-tokens`
- `rb-end-session`
- `rb-implement-with-tests`
- `rb-new-wiki`
- `rb-research-question-gate`
- `rb-tdd-scientific-code`

### 3. Preserve `rb-wiki` mechanically

Record and recheck these baseline SHA-256 values:

```text
rb-wiki/SKILL.md                  6c73575aa8204d2f50516c26e7fba72e617c4f9df9f922fe8d0288896620f42c
rb-wiki/agents/openai.yaml        e617d6ff0fef687911ea4c47854f71364672251df578da049a0490c9858fd9b4
rb-wiki/references/design.md      0cdf1b376cbd607feacd967914c29c17b1c402bf3800b726c34d8401aee9df62
```

The final diff must contain no path under `rb-wiki/`, and these hashes must remain unchanged.

### 4. Use small reversible commits

Recommended checkpoints:

1. routing-evaluation skeleton and planning-family walking slice;
2. remaining frontmatter routing boundaries;
3. high-priority body cleanup and progressive disclosure;
4. expanded evaluations, metadata/README integration, and final review fixes.

## Implementation Phases

1. [Phase 1: Evaluation walking skeleton and planning family](phase-1-evaluation-walking-skeleton.md)
2. [Phase 2: Frontmatter routing across remaining families](phase-2-frontmatter-routing.md)
3. [Phase 3: Instruction-body cleanup](phase-3-instruction-body-cleanup.md)
4. [Phase 4: Behavioural evaluation and regression hardening](phase-4-behavioural-evaluation.md)
5. [Phase 5: Repository integration and release readiness](phase-5-integration-and-release.md)

Use `[ ]` for planned tasks, `[x]` for implemented tasks, and `[v]` only after the task has passed its stated verification check.

## Validation Plan

### Deterministic validation

- Parse every `SKILL.md` frontmatter block and require only `name` and `description`.
- Require folder name and frontmatter name to match.
- Validate every `agents/openai.yaml` interface block and explicit `$skill-name` default prompt.
- Run `git diff --check`.
- Run all existing custom validators and the new routing-eval manifest validator.
- Count description words and descriptions longer than 40 words.
- Verify the three `rb-wiki` hashes and absence of `rb-wiki/` paths in the diff.
- Scan for initializer TODOs, stale skill names, and README catalogue drift.

### Semantic and behavioural validation

- Test positive, paraphrased, adjacent-negative, and ambiguous prompts.
- Give the evaluator only the available skill metadata and user request when judging routing.
- Use typed results: expected skill, observed skill, pass/fail, confidence, explanation, and error category.
- Compare the `9875708` baseline with revised metadata using the same prompt set, harness, model, and trial count.
- Add outcome checks for skills whose bodies changed materially.
- Review every failure manually before changing wording; do not optimize to a mistaken evaluator.

### Review gate

At each phase end:

1. inspect the complete diff;
2. identify weakened safety or scope rules;
3. fix actionable findings;
4. rerun affected deterministic and behavioural checks;
5. mark tasks `[v]` only after evidence is recorded.

## Risks

- **Descriptions become longer while adding exclusions.** Mitigate by removing synonym lists and output detail that does not help selection.
- **Negative clauses suppress legitimate paraphrases.** Mitigate with positive paraphrase tests and sibling-family evaluation.
- **A routing evaluator rewards keyword matching.** Mitigate with natural paraphrases, deliberately overlapping vocabulary, and manual review of failures.
- **Body trimming removes a real safety rule.** Mitigate by classifying every deleted instruction as duplicate, generic, obsolete, or relocated, and checking the resulting contract.
- **Framework guidance becomes stale.** Move conditional product details out of always-loaded bodies and require current official documentation when concrete implementation depends on them.
- **Legacy setup users still need `_rb-agent-skills` support.** Do not delete that path until current usage is checked; otherwise move it into a conditional reference.
- **Evaluation cost grows too large.** Run a planning-family walking slice first, then expand by routing family and prioritize known overlaps.
- **`rb-wiki` changes accidentally.** Enforce path and hash checks before every phase commit.

## Success Criteria

- No file under `rb-wiki/` changes, and all three recorded hashes match.
- Every in-scope skill has either an explicit nearest-neighbour exclusion in its description or a documented reason that its trigger is already uniquely narrow.
- The planning, lifecycle, understanding/review, skill-management, and wiki-operation families each have matched positive and negative routing cases.
- Targeted baseline routing failures improve without creating a regression in previously passing critical cases.
- High-priority body duplication is removed from `rb-start-project`, `rb-execute-plan`, and `rb-multi-agent-systems` without losing required behaviour.
- `rb-working-diary` no longer presents ordinary one-turn work as an automatic trigger.
- `rb-discuss` distinguishes unresolved requirements from already-approved implementation.
- Total frontmatter-description words do not exceed the 975-word baseline, and fewer than eight descriptions exceed 40 words.
- All metadata, manifest, custom validator, syntax, and whitespace checks pass.
- README routing guidance and `agents/openai.yaml` metadata agree with the final skills.
- Raw behavioural results and limitations are saved; no claim of improvement relies only on static prose review.
- The final review reports no blocking findings, or residual risks are explicitly accepted.

## Open Questions

1. Is any current machine still dependent on the legacy `_rb-agent-skills` installation layout? Recommended default: retain support but move details into a conditional reference unless live evidence shows it can be removed safely.
2. Which model and harness combinations should define the release gate? Recommended default: Codex as the required primary target, with a smaller Claude Code compatibility sample.
3. What execution budget is acceptable for repeated routing trials? Recommended default: three trials for all critical family cases, then expand only for unstable results.
4. Should descriptions use explicit `Do not use` wording uniformly? Recommended default: require it for overlapping families, but allow narrow command-like skills to remain concise when negative tests demonstrate reliable routing.
