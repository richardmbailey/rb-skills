---
name: "rb-create-skill-evals"
description: "Use when the user wants to create tests or evals for an agent skill, prove whether a skill triggers correctly or improves outcomes, add regression coverage for a SKILL.md, compare performance with and without a skill, or decide whether a skill can be retired. Inspect the target skill and build a repository-local behavioural evaluation suite with positive and negative cases, isolated fixtures, suitable validators, repeat trials, and ablation conditions."
---

# RB Create Skill Evals

Build tests that show whether an agent skill changes behaviour usefully and reliably. A valid `SKILL.md` is not enough: the suite must test selection, completed outcomes, regressions, and the skill's marginal value.

## Establish the target and purpose

1. Read repository instructions and locate the target skill, including its `SKILL.md`, `agents/openai.yaml`, scripts, references, assets, and any existing evals.
2. Resolve whether the user wants to test one skill, several related skills, or the skill-routing system. Ask only when plausible targets would produce materially different suites.
3. Determine the main purpose:
   - **trigger quality**: the skill loads for appropriate requests and stays out of unrelated requests;
   - **outcome quality**: using the skill produces work that satisfies its contract;
   - **regression protection**: future edits, model changes, or harness changes do not reduce performance;
   - **skill lift**: results are better with the skill than without it;
   - **retirement**: the current model performs equally well without the skill.
4. Preserve existing product code and user changes. Add or update only evaluation resources unless the user separately asks to improve the target skill.

## Derive the behavioural contract

Translate the skill into claims that can be tested. Record:

- requests that should invoke it, including natural paraphrases;
- neighbouring requests that should not invoke it;
- required inputs and environmental assumptions;
- observable outputs, side effects, and prohibited actions;
- important decisions the agent must make;
- deterministic invariants such as paths, schemas, commands, tests, or HTML structure;
- semantic qualities such as accuracy, usefulness, restraint, or quality of explanation;
- expected cost, latency, or token effects when these matter.

Treat the frontmatter description as the trigger contract and the body as the execution contract. Identify vague, overlapping, untestable, or contradictory requirements, but do not silently rewrite them.

## Design discriminating cases

Start with 10–20 cases when practical. A useful initial set contains:

- three straightforward requests that should trigger the skill;
- two realistic paraphrases or underspecified requests that should still trigger;
- three adjacent requests that should not trigger;
- two ambiguous, difficult, or failure-prone cases;
- real production prompts or traces when available and safe to use.

Each case must state what success means. Avoid cases that pass whether or not the skill is present. Include at least one case likely to expose harmful over-triggering and one likely to expose a plausible but incorrect output.

Judge the completed result first. Skill invocation and tool traces are diagnostic signals, not substitutes for a correct outcome. Do not require one exact reasoning path unless the path itself is a safety or compliance requirement.

## Choose evaluators

Use the least subjective evaluator that can measure the real requirement:

1. Prefer existing tests, compilers, schema parsers, linters, exact artifact checks, and execution-based assertions.
2. Write focused deterministic validators for stable structure or behaviour. Make them discriminating by checking meaningful values and failure cases, not only file existence or keywords.
3. Use a bounded semantic evaluator when correctness depends on meaning. Give it a short rubric, the minimum necessary evidence, typed pass/fail output, and visible reasons.
4. Use human review for high-consequence or irreducibly subjective judgments. State who reviews what and what evidence they need.
5. Combine evaluators when a valid artifact can still be substantively wrong. Structural validation and semantic quality are separate dimensions.

Test evaluators against at least one known-good and one deliberately bad artifact where practical. A validator that accepts both is not useful.

## Build the suite

Place the suite next to the target skill by default:

```text
<skill-directory>/evals/
├── eval-plan.json
├── fixtures/
├── validators/
└── run_evals.py        # when an executable harness is available
```

Use a repository-level `evals/<skill-name>/` directory instead when the repository already has that convention or when tests span several skills.

Write `eval-plan.json` with this minimum shape:

```json
{
  "schema_version": 1,
  "skill": "rb-example-skill",
  "conditions": ["with_skill", "without_skill"],
  "default_trials": 3,
  "cases": [
    {
      "id": "positive-basic",
      "kind": "outcome",
      "prompt": "A realistic user request",
      "should_trigger": true,
      "fixture": "fixtures/basic",
      "success": [
        {
          "name": "artifact contract",
          "evaluator": "deterministic",
          "command": "python3 validators/check_basic.py {workspace}"
        }
      ]
    }
  ]
}
```

Allowed case kinds are `trigger`, `outcome`, `regression`, and `retirement`. `should_trigger` is required for trigger cases and optional for others. Use `null` only when invocation is intentionally irrelevant. Semantic success checks use `"evaluator": "semantic"` and a non-empty `rubric`; manual checks use `"evaluator": "manual"` and non-empty `instructions`.

Validate the plan with the bundled script:

```bash
python3 <this-skill-directory>/scripts/validate_eval_manifest.py <target-skill-directory>/evals/eval-plan.json
```

## Make execution honest

1. Use a fresh temporary workspace for every case and trial. Seed only the declared fixture and dependencies.
2. Prevent access to earlier outputs, conversations, expected answers, and hidden evaluator data.
3. Run at least three trials for important nondeterministic cases; use five or six when reliability is central.
4. Run both `with_skill` and `without_skill` conditions unless the user asks only for trigger diagnostics. Keep prompts, fixtures, model, harness, limits, and validators matched.
5. Test every deployment-relevant model and harness, but do not create a costly matrix with tools nobody uses.
6. Capture outcome, validator results, skill invocation when observable, duration, model, harness, token usage when available, and errors.
7. Keep raw results separate from interpretation. Never replace a failed run with a successful rerun without recording both.

If the environment has no documented non-interactive agent interface, create and validate the cases and evaluators, then report that automated execution is not yet wired. Do not invent a brittle command or claim that the suite has run.

## Analyse the results

Report at least:

- pass rate by case and condition;
- the difference between with-skill and without-skill performance;
- variability across trials;
- false-positive and false-negative trigger cases;
- cost or latency changes when available;
- failures caused by the skill, including stale or conflicting instructions;
- evaluator limitations and uncertain judgments.

Do not call a skill helpful merely because a with-skill run passed. It must outperform, stabilize, constrain, or otherwise improve the matched baseline. Do not recommend retirement from a single successful no-skill run.

## Improve only with permission

When the user asked only for tests, finish the suite and report failures without editing the target skill. When the user also asked to improve it, use the failures to make the smallest justified change, rerun the same suite, and show the before-and-after result. Add new regression cases for newly discovered failures.

## Handoff

Return:

- the target skill and evaluation purpose;
- links to the eval plan, fixtures, validators, and runner;
- validation and execution commands;
- conditions, models, harnesses, cases, and trial count actually run;
- pass rates and skill lift, or a clear statement that execution was unavailable;
- important failures, evaluator limitations, and the recommended next decision.

Direct invocation is `$rb-create-skill-evals` in Codex and `/rb-create-skill-evals` in Claude Code.

## Failure handling

- If the target skill cannot be found, ask for its directory or repository rather than testing a similarly named skill.
- If requirements cannot be observed or graded, expose that gap and propose a bounded human or semantic rubric.
- If tests require credentials, production systems, destructive actions, or expensive model runs, build the safe portion and request approval before execution.
- If a previous suite conflicts with this format, preserve its working convention unless migration would materially improve reliability.
- If the manifest validator fails, do not present the suite as ready.
