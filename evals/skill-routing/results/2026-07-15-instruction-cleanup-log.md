# Instruction-Body Cleanup Log

The cleanup removes repeated or misplaced guidance while preserving safety,
approval, validation, and workflow boundaries. Line count is recorded only as
supporting information; it is not the success measure.

| Skill | Baseline lines | Revised lines | Classification | Change and retained contract |
| --- | ---: | ---: | --- | --- |
| `rb-start-project` | 140 | 116 | Duplicate and generic | Replaced two routing lists plus a repeated full workflow chain with one routing table. Retained onboarding questions, no-code boundary, explicit approval, handoff output, and review+fix requirement. |
| `rb-execute-plan` | 115 | 110 | Irrelevant defaults and duplicate | Removed cross-domain Pydantic, PydanticAI, and Ollama defaults and collapsed repeated phase-review instructions. Retained walking skeletons, `[ ]`/`[x]`/`[v]`, per-phase files, verification gates, and one full review+fix gate. |
| `rb-multi-agent-systems` | 116 | 103 | Relocated and duplicate | Moved version-sensitive framework and product choices to `references/framework-selection.md`. Retained capability scaling, contracts, permissions, state, failure containment, budgets, observability, evaluation, durability, and official-documentation checks. |
| `rb-setup-local-agent-skills` | 54 | 47 | Relocated legacy compatibility | Confirmed legacy layout remains supported by `rb-install-skills/scripts/install_skills.py`; moved its commands to `references/legacy-pack.md` and kept only the discovery decision in the main skill. |
| `rb-working-diary` | 117 | 117 | Over-broad trigger | Removed the implication that every review, diagnosis, onboarding, or implementation task requires diary work. Retained the one-turn exclusion, compact entry form, secret rule, cross-session purpose, and checkpoint guidance. |
| `rb-discuss` | 30 | 29 | Generic and boundary-blurring | Replaced generic restatement and ambiguity steps with material decision categories and bounded questions. Retained the no-code stop condition and requirements handoff. |
| `rb-create-implementation-plan` | 19 | 18 | Generic and boundary-blurring | Replaced generic restatement/questions with planning decisions and a durable-plan contract. Retained the bundled template and the handoff to plan execution. |

`rb-continue-project`, `rb-create-skill-evals`, and
`rb-research-question-gate` were reviewed for description/body repetition. Their
remaining body language expresses execution or gate contracts not present in
frontmatter, so no deletion was justified.

Deterministic cleanup contracts are encoded in
`evals/skill-routing/instruction-contracts.json`. The validator checks both the
preserved requirements and the removed or relocated language. Its good fixture
passes and its deliberately bad fixture fails for missing required text,
forbidden text, duplicated text, and excessive length.
