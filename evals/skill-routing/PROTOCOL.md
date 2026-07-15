# Skill Routing Evaluation Protocol

This protocol measures whether a user request maps to the intended skill description. It does not claim to observe private model reasoning or prove that the runtime loaded a skill internally.

## Blinding

For each independent trial, give the classifier exactly one generated packet. The packet contains:

- one user request;
- the available skill names and frontmatter descriptions for the selected condition;
- the allowed output schema.

Do not expose the manifest's expected skill, forbidden skills, rationale, previous classifications, or aggregate results. Run trials independently and do not allow one trial to read another trial's output.

## Conditions

- `baseline`: metadata read from commit `9875708`.
- `revised`: metadata read from the working tree.

Use the same cases, classifier instructions, trial count, and scorer for both conditions.

## Classifier instruction

```text
For each JSONL packet, decide which single available skill best matches the user request using only the supplied names and descriptions. Choose outcome=clarify when the request does not contain enough information to select safely. Choose outcome=no_skill when none applies. Return exactly one valid JSON object per input line using the response_schema. Do not invoke a skill or solve the user's task.
```

## Generate packets

```bash
python3 evals/skill-routing/build_trial_packets.py \
  evals/skill-routing/eval-plan.json \
  --condition baseline \
  --trial 1 \
  --output evals/skill-routing/packets/baseline-trial-1.jsonl
```

Repeat for every declared trial and for the revised condition.

When the revised working tree is a writable copy without its own `.git`
directory, pass that copy with `--repo` and the source Git checkout with
`--baseline-repo`.

## Score results

```bash
python3 evals/skill-routing/score_results.py \
  evals/skill-routing/eval-plan.json \
  evals/skill-routing/results/raw/baseline-trial-*.jsonl \
  --output evals/skill-routing/results/baseline-summary.json
```

Inspect every failure manually. A failure may indicate bad metadata, an ambiguous case, or an incorrect expected label. Do not change descriptions merely to satisfy a mistaken evaluator.
