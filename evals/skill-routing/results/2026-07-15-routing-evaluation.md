# RB Skills Routing Evaluation — 2026-07-15

## Result

The revised descriptions preserve perfect routing across this 96-case suite
while making sibling ownership and negative boundaries explicit. The primary
benefit is clarity and future resilience, not a measured improvement over the
current model: the baseline already scored perfectly on the final cases.

| Condition | Cases | Trials | Classifications | Passed | Failed | Pass rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline commit `9875708` | 96 | 3 | 288 | 288 | 0 | 100% |
| Final revised metadata | 96 | 3 | 288 | 288 | 0 | 100% |

Both conditions produced 24 appropriate clarifications: eight ambiguous cases
across three trials. There were no false negatives, forbidden sibling
selections, evaluator errors, or disagreements in the final matched runs.

## Family Coverage

| Family | Cases | Classifications per condition | Baseline | Revised |
| --- | ---: | ---: | ---: | ---: |
| Planning and delivery | 21 | 63 | 100% | 100% |
| Project lifecycle | 14 | 42 | 100% | 100% |
| Understanding, review, and diagnosis | 16 | 48 | 100% | 100% |
| Skill management | 16 | 48 | 100% | 100% |
| Narrow wiki operations | 10 | 30 | 100% | 100% |
| Context, research, and multi-agent architecture | 19 | 57 | 100% | 100% |

Every in-scope skill has at least three realistic positive prompts. Every
modified skill has at least three adjacent-negative prompts. Cases use natural
paraphrases, shared sibling vocabulary, and requests that omit internal skill
names. The suite includes one or more explicit clarification cases per family.

## Regression Found And Fixed

An intermediate revised run scored 287/288. One classifier selected
`rb-continue-project` for “Tell me where we are and then carry on with the
project,” while five other revised classifications across the intermediate and
final runs treated it as ambiguous.

Manual review kept the clarification label: without durable resumption context
or a requested artifact, the request does not distinguish a quick continuation
brief from a standalone state-of-play report. The `rb-continue-project`
description was revised to require clarification when the deliverable could be
a standalone status artifact. Three fresh blinded trials then passed 288/288.
The prompt and expected label were not changed.

## Metadata Cost

- Baseline in-scope description budget: 975 words.
- Final revised descriptions: 974 words.
- Descriptions longer than 40 words: 0, down from 8 at baseline.
- Skills included in the word budget: 28.
- `rb-wiki`: excluded from edits and target evaluation.

## Evaluation Method

Each packet contained one user request plus the complete available skill-name
and description list for one condition. Three independent Codex subagents per
condition classified packets using only that metadata. They could not read the
hidden expected labels, forbidden siblings, scorer, other packets, or other
trial outputs.

The deterministic scorer required the expected outcome and skill and rejected
forbidden selections, duplicate results, invalid conditions or trials, missing
case results, and unknown cases. The scorer itself passed a known-good fixture,
reported a known-wrong selection as a failure, and rejected an incomplete run.

Instruction-body cleanup is checked separately by
`instruction-contracts.json`. Its deterministic validator verifies retained
safety, approval, status, validation, and routing contracts; verifies that
relocated product and legacy guidance is directly linked; and rejects a
deliberately bad fixture.

## Raw Evidence

- Baseline raw classifications: `results/raw/baseline-full-trial-1.jsonl`,
  `baseline-full-trial-2.jsonl`, and `baseline-full-trial-3.jsonl`.
- Final revised classifications: `results/raw/revised-final-trial-1.jsonl`,
  `revised-final-trial-2.jsonl`, and `revised-final-trial-3.jsonl`.
- Machine summaries: `results/baseline-full-summary.json` and
  `results/revised-final-summary.json`.
- Intermediate unstable run: `results/revised-full-summary.json`.
- Planning-family walking-skeleton record:
  `results/2026-07-15-phase-1-planning-family.md`.
- Instruction cleanup record:
  `results/2026-07-15-instruction-cleanup-log.md`.

## Limitations

- The harness tests semantic selection from supplied metadata. It does not
  observe the Codex runtime's private internal skill-loading event.
- The final repeated evaluation uses independent Codex subagents from the
  current runtime; the exact model identifier is not exposed.
- No safe, documented, comparable Claude Code classification harness was
  available, so Claude compatibility was not measured.
- The harness did not expose reliable per-classification latency or token usage.
- Task-execution quality was not rerun for all skills. Material instruction
  cleanup was bounded by deterministic contract checks and existing custom
  validators, so no claim is made that this suite measures every possible task
  outcome.
- A perfect score on a finite suite is evidence for these boundaries, not a
  universal guarantee across future models or unseen prompts.

## Protected Scope

The excluded files remained byte-identical throughout:

- `rb-wiki/SKILL.md`: `6c73575aa8204d2f50516c26e7fba72e617c4f9df9f922fe8d0288896620f42c`
- `rb-wiki/agents/openai.yaml`: `e617d6ff0fef687911ea4c47854f71364672251df578da049a0490c9858fd9b4`
- `rb-wiki/references/design.md`: `0cdf1b376cbd607feacd967914c29c17b1c402bf3800b726c34d8401aee9df62`
