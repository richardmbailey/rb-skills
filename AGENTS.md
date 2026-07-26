# Repository Guidance

This repository contains reusable agent skills for Codex and Claude Code. Active
skills live in top-level `rb-*` directories containing a `SKILL.md`. Retired
skills are historical material under `retired-skills/` and are not installed by
the normal sync. Wiki-specific operational skills belong in the separate
`rb-wiki` repository.

When instructions name a skill as `$rb-name`, use that form in Codex and `/rb-name` in Claude Code.

The constrained execution skills `$rb-create-low-level-plan`,
`$rb-assess-plan-safety`, and `$rb-safe-operation` are Codex-only in the
current release.

## Skill Authoring

- Keep skill instructions concise, procedural, and focused on decisions another
  agent must make.
- Preserve each skill's frontmatter, trigger boundary, required behaviour, and
  tool or platform limitations.
- Update adjacent `agents/openai.yaml`, behavioural eval manifests, routing
  cases, instruction contracts, and consistency contracts when a change affects
  their promises or trigger surface.
- Prefer references or scripts for detailed reusable material rather than
  expanding every `SKILL.md`.
- Preserve existing repository conventions and user changes. Do not broaden a
  task silently.

## Testing And Validation

- Use automated behavioural tests by default for code changes. A successful
  lint, import, build, smoke check, source inspection, or generated plan does not
  replace a behavioural test when a plausible regression could escape.
- Bug fixes normally require a regression test that demonstrates the defective
  behaviour and passes after the fix. Changes to decisions, validation,
  external interactions, or side effects require relevant negative, boundary,
  timeout, permission-denial, partial-failure, duplicate, idempotency,
  rollback, or corrupted-response cases.
- Select the test level from the failure boundary: unit or property,
  component/integration, contract, migration, end-to-end, scientific,
  stochastic, performance, security, concurrency, recovery, or agent eval.
- Never delete, weaken, skip, quarantine, or repeatedly rerun a failing test
  merely to obtain a green result. Treat flakiness as a defect.
- Run the closest available CI-equivalent command before completion, or the
  largest relevant affordable subset. Name every omitted check, its reason, and
  the residual risk.

The authoritative workflow is `.github/workflows/validate-skills.yml`. Run the
relevant subset of these repository checks from the root:

```bash
python3 evals/skill-routing/validate_instruction_contracts.py \
  evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py \
  evals/skill-routing/consistency-contracts.json
for manifest in rb-*/evals/eval-plan.json; do
  python3 rb-create-skill-evals/scripts/validate_eval_manifest.py "$manifest"
done
python3 -m unittest discover -s rb-safe-operation/runtime/tests -p 'test_*.py'
git diff --check
```

When skill descriptions or frontmatter change, also run:

```bash
ruby evals/skill-routing/validate_skill_metadata.rb
```

Run the full constrained-runtime suite for runtime, schema, launcher, or
cross-cutting constrained-workflow changes. It requires the supported
dependencies described in the README and runtime contract; a missing local
environment is an unrun check, not a pass.

## Generated Schemas And The Constrained Runtime

- The Python package under `rb-safe-operation/runtime/` is the source of truth
  for constrained-runtime models and schemas.
- Never hand-edit files under a `references/generated/` directory.
- After a runtime or schema change, use the manifest-pinned launcher described
  in `rb-safe-operation/references/runtime-contract.md` to regenerate all
  three mirrors:
  `rb-create-low-level-plan/references/generated/`,
  `rb-assess-plan-safety/references/generated/`, and
  `rb-safe-operation/references/generated/`.
- Confirm schema drift is absent and the three mirrors are byte-identical before
  completion.
- The first-release constrained route supports exact read/patch work and
  `static_file_state` verification only. It cannot run tests, builds, linting,
  type checking, application commands, browser automation, or runtime/external
  observations.
- Never select `constrained` implicitly. `safe: true` authorises an attempt
  of one unchanged typed plan; it is not a general safety claim, sandbox
  guarantee, or proof of runtime correctness.

## Agentic Architecture

- For systems involving multiple LLM agents, agentic workflows, or orchestration
  layers, use `$rb-multi-agent-systems`.
- Use the simplest architecture that expresses the required behaviour. Prefer
  a pipeline or dependency graph where sufficient, otherwise default
  non-trivial orchestration to a deterministic state-machine runner. Escalate to
  dynamic planning only when the simpler models cannot express the requirement.
- Keep control-flow complexity separate from durability requirements. A simple
  state machine may still need persistence, retries, scheduling, or crash
  recovery.
- Treat agent actions and transitions as proposals validated by runner-owned
  policy, permissions, schemas, budgets, quality gates, and human checkpoints.
  Logging and tracing provide visibility and evidence; they do not enforce
  safety.

## Local State And Publishing

- Preserve unrelated working-tree changes and stage only the intended scope.
- Treat `.rb-safe-operation/` as local control-plane state. Do not stage or
  publish its plans, assessment bundles, audit runs, coordinator records,
  approvals, or leases unless the human explicitly requests those exact files.
- Before publishing, check for secrets, private identifiers, confidential
  context, machine-local paths, caches, temporary outputs, and environment
  files.

## Deterministic vs Semantic Text Handling

When implementing or reviewing code that handles text:

- Use deterministic parsing for stable structure and syntax: JSON, YAML, XML, CSV, frontmatter, exact delimiters, known IDs, URLs, file paths, logs, protocol fields, and other formats with explicit grammar.
- Prefer structured parsers and existing libraries for structured formats before regex.
- Use an LLM-backed path when correctness depends on meaning: intent, relevance, classification, summarisation, ambiguity resolution, rubric judgment, natural-language extraction, entity or claim matching, or deciding whether differently worded passages mean the same thing.
- Do not build elaborate regexes, keyword lists, fuzzy string scoring, or brittle heuristics as substitutes for semantic understanding.
- When using an LLM, wrap it with deterministic boundaries: bounded inputs, typed outputs, validation, retries or visible failure, and focused fixtures/evals where practical.
