# Phase 2: Frontmatter Routing Across Remaining Families

## Phase Goal

Apply the proven routing pattern to every remaining in-scope skill, editing sibling descriptions together and keeping the always-loaded metadata concise.

## Scope

- Project lifecycle family.
- Understanding and review family.
- Skill-management family.
- Narrow wiki-operation family.
- Context and research family.
- `rb-multi-agent-systems` description.
- Verification-first skills when evidence shows a concrete routing gap.

## Non-scope

- Instruction-body restructuring, except a minimal consistency edit required by a changed description.
- `rb-wiki` frontmatter, body, metadata, references, or validators.

## Dependencies

- Phase 1 routing manifest, validator, result schema, and review lessons.
- Approved description pattern and baseline word counts.

## Task Checklist

### Project lifecycle

- [v] Distinguish first-time onboarding in `rb-start-project` from mature-project resumption in `rb-continue-project`.
- [v] Distinguish a deep state-of-play report in `rb-where-are-we` from resumption and onboarding.
- [v] Distinguish handoff or closure in `rb-end-session` from status reporting.

### Understanding, review, and diagnosis

- [v] Distinguish codebase orientation in `rb-explain-codebase` from architectural critique in `rb-architecture-review`.
- [v] Distinguish a teaching-oriented change explanation in `rb-explain-diff` from defect review in `rb-review-pr-or-diff`.
- [v] Distinguish root-cause investigation in `rb-diagnose` from review and from implementing an already-understood fix.

### Skill management

- [v] Distinguish authoring in `rb-write-skill` from behavioural evaluation in `rb-create-skill-evals`.
- [v] Add an ordinary-product-tests exclusion to `rb-create-skill-evals`.
- [v] Distinguish repository synchronization in `rb-sync-skills-repo` from setup repair in `rb-setup-local-agent-skills`.
- [v] Distinguish full skill and project-resource installation in `rb-install-skills` from sync-only and repair-only work.

### Wiki operations

- [v] Keep `rb-new-wiki` focused on creating a wiki from `wiki-template`.
- [v] Add explicit existing-wiki ingest boundaries to `rb-wiki-ingest`.
- [v] Add explicit upkeep boundaries to `rb-wiki-maintenance`.
- [v] Refer broader design or schema work to `rb-wiki` without editing `rb-wiki` itself.

### Context, research, and architecture

- [v] Narrow `rb-working-diary` to durable continuity needs and explicitly exclude ordinary one-turn work.
- [v] Expand realistic trigger language for glossary, terminology, units, invariants, and `CONTEXT.md` in `rb-project-language`.
- [v] Confirm `rb-context-tokens` remains uniquely narrow; document why no negative sentence is needed if tests support that decision.
- [v] Confirm the phase boundary in `rb-research-question-gate` remains clear; edit only if adjacent planning/research prompts misroute.
- [v] Rewrite `rb-multi-agent-systems` around multi-agent architecture and orchestration decisions rather than a list of product names.

### Integration

- [v] Update README catalogue wording to match every changed description.
- [v] Update `agents/openai.yaml` only where its short description or default prompt becomes stale.
- [v] Recount total description words and descriptions longer than 40 words.
- [v] Review every changed description as a sibling-family set.

## Verification Checklist

- [v] Every changed skill has realistic positive, paraphrased, and sibling-negative cases.
- [v] Each exclusion points to the correct alternative when one exists.
- [v] Narrow exact-command skills have either an explicit negative or a recorded evidence-backed reason to omit one.
- [v] No description depends on an internal skill name as its only trigger language.
- [v] Total description words do not exceed 975.
- [v] Fewer than eight descriptions exceed 40 words.
- [v] Metadata parsing and UI metadata checks pass.
- [v] `rb-wiki` hashes and diff exclusion pass.
- [v] Phase review+fix is complete.

## Tests And Commands

```bash
python3 rb-create-skill-evals/scripts/validate_eval_manifest.py evals/skill-routing/eval-plan.json
git diff --check
git diff --name-only -- rb-wiki/
shasum -a 256 rb-wiki/SKILL.md rb-wiki/agents/openai.yaml rb-wiki/references/design.md
```

Use a structured YAML parser to validate all `SKILL.md` frontmatter and `agents/openai.yaml`; do not substitute regular expressions for YAML parsing.

## Execution Record

- `evals/skill-routing/validate_skill_metadata.rb` uses Ruby's YAML parser and
  passes all skill frontmatter and UI metadata.
- Final in-scope description cost is 974 words; no description exceeds 40
  words.
- The expanded routing suite contains 96 cases across six sibling families.
- The final three-trial revised condition passes 288/288 classifications.
- `rb-wiki` remained byte-identical at the three recorded hashes.

## Phase Exit Criteria

- Every in-scope routing family has explicit, mutually understandable ownership.
- Always-loaded description cost is no greater than baseline.
- All frontmatter and sibling-family cases pass the phase gate or have documented unresolved failures.
- Every task is `[v]`, review findings are fixed, and `rb-wiki` remains unchanged.
