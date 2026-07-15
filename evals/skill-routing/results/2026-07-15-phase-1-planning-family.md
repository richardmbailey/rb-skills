# Phase 1 Planning-Family Routing Evaluation

## Result

The revised planning-family descriptions preserve perfect routing on this
bounded evaluation while making the ownership boundaries explicit for human
readers and future classifiers.

| Condition | Trials | Cases per trial | Passed | Failed | Pass rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline at `9875708` | 3 | 21 | 63 | 0 | 100% |
| Revised working tree | 3 | 21 | 63 | 0 | 100% |

There were no under-calls, over-calls, inappropriate clarifications, critical
regressions, or disagreements between trials in either condition.

## Scope And Cost

| Skill | Baseline description words | Revised description words |
| --- | ---: | ---: |
| `rb-discuss` | 20 | 36 |
| `rb-create-implementation-plan` | 25 | 38 |
| `rb-execute-plan` | 34 | 39 |
| `rb-create-issues` | 20 | 41 |
| `rb-implement-with-tests` | 40 | 40 |
| `rb-tdd-scientific-code` | 35 | 35 |

The description growth in this family is deliberate. It states positive and
negative ownership directly. Repository-wide description cost remains a Phase
2 gate and may require concise reductions elsewhere.

## Harness

- Classifier: three independent Codex subagents per condition in the current
  runtime. The exact underlying model identifier is not exposed.
- Input: generated JSONL packets containing one request and only the available
  skill names and descriptions for that condition.
- Blinding: classifiers could not read the answer manifest, scorer, other
  packets, or other trial outputs.
- Scoring: deterministic comparison of typed `outcome`, selected skill, and
  forbidden sibling selections.
- Raw results: `results/raw/baseline-trial-*.jsonl` and
  `results/raw/revised-trial-*.jsonl`.
- Aggregate planning-family scores are recorded in this report; the raw JSONL
  remains available for independent rescoring.

The harness tests metadata-based selection. It does not observe or prove the
Codex runtime's private internal skill-loading decision, and it does not test
whether a selected skill produces a good task outcome. Those limitations are
carried into the repository-wide evaluation.

## Commands

```bash
python3 evals/skill-routing/validate_routing_eval.py \
  evals/skill-routing/eval-plan.json

python3 evals/skill-routing/build_trial_packets.py \
  evals/skill-routing/eval-plan.json \
  --condition baseline --trial 1 \
  --repo . --baseline-repo /Users/richardbailey/GitHub/rb-skills \
  --output evals/skill-routing/packets/baseline-trial-1.jsonl

python3 evals/skill-routing/score_results.py \
  evals/skill-routing/eval-plan.json \
  evals/skill-routing/results/raw/baseline-trial-1.jsonl \
  evals/skill-routing/results/raw/baseline-trial-2.jsonl \
  evals/skill-routing/results/raw/baseline-trial-3.jsonl \
  --output evals/skill-routing/results/baseline-summary.json
```

The revised condition used the same commands, prompts, trial count, response
schema, and scorer, with `--condition revised`.

## Protected Scope

The excluded `rb-wiki` files remained byte-identical:

- `rb-wiki/SKILL.md`: `6c73575aa8204d2f50516c26e7fba72e617c4f9df9f922fe8d0288896620f42c`
- `rb-wiki/agents/openai.yaml`: `e617d6ff0fef687911ea4c47854f71364672251df578da049a0490c9858fd9b4`
- `rb-wiki/references/design.md`: `0cdf1b376cbd607feacd967914c29c17b1c402bf3800b726c34d8401aee9df62`
