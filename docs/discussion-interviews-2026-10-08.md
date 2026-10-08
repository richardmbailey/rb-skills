# Discussion interviews: change and validation record

The user approved keeping automatic selection of `rb-discuss` while making it a focused interview with the user. The revised skill covers initial goals and later consequential decisions. Routine clarification, technical investigation, and resuming agreed work stay with their existing workflows.

The interview offers distinct options, short trade-offs, and a recommendation when the known goals and evidence support one. It prefers native clickable questions when the host permits them, preserves a custom-answer path, and falls back to text. Defaults and silence do not settle a decision. Only work that depends on an unanswered choice waits.

Continuation, handoff, diary, onboarding, and the neighbouring planning and implementation skills now preserve that boundary. Handoffs separate agreements, pending user choices, agent investigations, and nonblocking risks. The instruction contracts deliberately replace the old broad ambiguity gate with this narrower human-decision boundary; they retain the safeguards against reopening agreed work and add checks for question delivery and pending decisions.

The `rb-write-skill` and `skill-creator` guidance governed the edit. The required `rb-simplify-language` review included an independent audit. Its findings were repaired: an active-interview case no longer conflicts with handoff routing; native-tool tests require observed calls and explicit prerequisites; and text fallback does not force an unsupported recommendation.

A separate pre-publication reviewer checked the complete change, surrounding documentation and routing, all recorded probe responses, and publication-sensitive content. The review found no actionable defects. Its provenance clarification is recorded below.

## Checks performed

- All 46 skill regression tests passed, including Claude installation and setup tests.
- All 30 behavioural manifests validated. The new `rb-discuss` manifest has 13 cases; continuation and end-session each gained two cases. Ten routing cases were added.
- Metadata, instruction contracts, consistency contracts, publication hygiene, JSON parsing, Python compilation of the relevant skill tooling, and `git diff --check` passed.
- The routing packet builder validated the combined routing manifest and generated 174 revised packets. This was packet generation, not execution of 174 routing trials.
- Codex installations already link to the changed source directories. The ten affected Claude editions were refreshed through the repository installer after a clean dry-run; the installer retained backups.

## Decision probes and limits

[Recorded inputs and outputs](../evals/skill-routing/results/2026-10-08-discussion-probes.json) contain six synthetic scenarios under three conditions: previous instructions from commit `9a9b5b7`, revised instructions, and no supplied skill instructions. Each condition used three fresh `gpt-5.6-luna` agents with maximum reasoning and no inherited task conversation: 54 scenario responses in total. The parent reviewed every response; that review was not blinded. Shared platform instructions remained in effect. The recorded `rb-discuss` text matches the final skill. After the probes, continuation and end-session regained their general blockers, assumptions, and caveats bullets. Those final wording additions were reviewed and validated, but the probes were not repeated for them; the original packets remain unchanged.

All three revised trials allowed a custom answer in the proposed clickable question; none of the old or no-skill trials did. Revised trials also consistently asked a usable text question when the tool was mode-restricted. All conditions sensibly continued the agreed implementation scenario and preserved the unanswered decision in the independent-work scenario. These small probes support the particular interaction rules, not a general claim that skills improve model quality. No aggregate pass rate or cost saving is claimed.

The probes proposed actions and tool-call JSON; they did not call a native question tool, implement a product change, or run a live two-session handoff. Full behavioural-manifest execution, native clickable UI tests, the full semantic routing suite, and Claude model trials remain unrun. Generated-profile checks establish installation compatibility, not identical model behaviour. Unsupported native-tool cases must be reported as unrun, not passed.

The optional bundled `skill-creator/scripts/quick_validate.py` could not run because the available system Python environments lack PyYAML. The repository's Ruby metadata validator successfully parsed and checked the skill YAML instead.

The constrained-runtime suite, locked Linux wheelhouse setup, schema export/drift checks, and Python-version matrix were omitted because no runtime, schema, launcher, or constrained-workflow instructions changed. This is the relevant skill-validation subset of CI, not a claim that the full workflow ran locally. Residual uncertainty concerns live host interaction and model selection behaviour, which the recorded probes do not establish.
