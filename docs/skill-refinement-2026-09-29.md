# Skill refinements, 29 September 2026

All 34 active skills were reviewed and edited individually. The changes preserve specialist knowledge and explicit safeguards while reducing repeated instructions, unnecessary questions, and process that does not help the task. Retired skills and constrained-runtime code were not changed.

The combined `SKILL.md` word count fell from 36,668 to 31,704, a reduction of 13.5%. This measures entry-point length, not total repository size or actual model input. Six conditional references retain detailed procedures that are needed only for particular workflows. Some short skills gained a useful boundary instead of becoming shorter.

## Changes by skill

| Skill | Main improvement |
| --- | --- |
| `rb-diagnose` | Preserve uncertainty when evidence is incomplete; continue an already-authorised fix; select semantic methods by demonstrated suitability. |
| `rb-implement-with-tests` | Treat related edits as one bounded change, infer routine details, use meaningful tests and current evidence, and keep the completion report proportional. |
| `rb-tdd-scientific-code` | Prefer executable evidence, distinguish implementation verification from scientific validation, and avoid blocking solely on missing context documents. |
| `rb-review-pr-or-diff` | Focus review and verification on changed failure boundaries; reduce generic checklists and unnecessary technology prescriptions. |
| `rb-architecture-review` | Bound investigation and require concrete evidence and practical benefit for recommendations. |
| `rb-explain-codebase` | Explain representative control and data flows without exhaustive inventories or unsolicited redesign. |
| `rb-discuss` | Bundle independent questions, resolve material decisions, and continue work already authorised. |
| `rb-start-project` | Reuse known facts and existing authority; shorten the onboarding interview and scale the workflow to the work. |
| `rb-continue-project` | Restore relevant state and proceed into the authorised next workflow without asking for the same permission again. |
| `rb-create-prd` | Keep local revisions local and recognise a current authorised product decision that supersedes an older requirement. |
| `rb-create-implementation-plan` | Default to standard execution; explain constrained execution conditionally; scale review and test sections to actual risk. |
| `rb-execute-plan` | Reduce the core from 2,875 to 942 words; preserve linear execution and evidence-backed status while making independent review conditional on risk or an explicit gate. |
| `rb-sprint` | Use a compact `NO_CHANGE` checkpoint; reserve the full gate record for actual changes or blockers; recognise existing product-owner authority. |
| `rb-multi-agent-systems` | Reduce the core from 2,626 to 901 words; focus on architecture choice and ownership; load protocol detail only when applicable. |
| `rb-create-low-level-plan` | Clarify that deterministic validation belongs to the runtime rather than a manual reimplementation by the agent. |
| `rb-assess-plan-safety` | Clarify the division between semantic assessment and runtime-owned deterministic checks. |
| `rb-safe-operation` | Reduce the core from 2,433 to 1,029 words; separate operator decisions from coordinator internals while retaining authority, recovery, and static-verification limits. |
| `rb-create-safe-operation-policy` | Make explanation-only requests stop after read-only explanation; preserve confirmation requirements for policy mutations. |
| `rb-working-diary` | Link canonical evidence instead of copying it; load constrained continuity details only for that route. |
| `rb-end-session` | Separate durable handoff from chat archival; archive only when requested and avoid duplicate handoff content. |
| `rb-project-language` | Record evidenced vocabulary and invariants without turning the glossary into a general architecture document. |
| `rb-context-tokens` | Report session-selection uncertainty; the newest log is not proof of the current chat's identity. |
| `rb-research-question-gate` | Judge replication, teaching, and application work by their stated objectives; retain the duplicate stop rule for unsupported novelty claims. |
| `rb-explain-diff` | Preserve the rich HTML teaching contract while avoiding it for requests that only need a quick answer. |
| `rb-where-are-we` | Preserve evidence-labelled HTML reporting without inventing content to fill sections or expanding a quick status request. |
| `rb-language` | Match the requested editing scope and preserve effective prose. |
| `rb-revise-ai-draft` | Keep fidelity tracking internal and avoid unnecessary deliverables or rewriting already-effective passages. |
| `rb-simplify-language` | Make the explicit post-draft invocation from `rb-write-skill` consistent across the skill, metadata, and evals; retain manual-only routing elsewhere. |
| `rb-delegate` | Shorten repetitive examples and clarify parent ownership; treat model and cost defaults as hypotheses to verify. |
| `rb-create-skill-evals` | Distinguish workflow probes from completed task outcomes, require concrete fixtures where possible, and make comparison limitations explicit. |
| `rb-write-skill` | Prefer concise decision instructions and conditional references; update adjacent contracts; validate before sync and recognise existing source symlinks. |
| `rb-install-skills` | Continue into onboarding only when that work is requested. |
| `rb-setup-local-agent-skills` | Keep repair or verification bounded instead of restarting full onboarding. |
| `rb-sync-skills-repo` | Inspect destinations through the dry-run; preserve correct links and stop after verification-only requests. |

## Deliberate contract changes

Metadata, routing cases, evaluation manifests, the planning template, README, and instruction/consistency contracts were updated to match the new behaviour. The validators themselves were not weakened to obtain passing results.

Standard execution remains the default for a missing or undecided route. Independent review remains required for substantial, high-risk, or cross-cutting work and for existing explicit gates. A small local change may use inline review when no such gate applies. Verification still requires appropriate evidence; unavailable required review still blocks verified status.

The revised semantic-text rule accepts an established semantic method whose measured behaviour meets the requirement. It does not force a new LLM call when an appropriate classifier already exists, and it does not license brittle keyword rules as substitutes for semantic understanding. Explicit project technology choices remain authoritative.

Constrained execution still requires explicit selection and exact authority for an unchanged typed plan. It still supports static file-state verification only. Runtime checks cannot be represented as static verification. Relocated procedures remain directly linked from their owning skills.

## Validation and evidence

- All 28 behavioural evaluation manifests and all CI-selected JSON files validate. This confirms structure, not that every behavioural case was executed.
- Routing manifest, metadata, instruction contracts, and consistency contracts pass. Metadata covers 34 skills and 1,079 description words.
- All 12 skill regression tests pass.
- The runtime suite ran 286 tests: 285 passed and one was skipped because `RB_SAFE_OPERATION_TEST_WHEELHOUSE` was unavailable. The skipped test was `test_disposable_setup_reuse_and_identity_tamper_gates`.
- Python compilation and publication-hygiene checks pass. Generated-schema source comparison reports no drift; consistency checks confirm matching mirrors.
- The installed manifest-pinned launcher rejected the schema check with `runtime_source_hash_mismatch`. Its manifest pins an older source identity. Runtime source and launcher code were not changed by this revision, and the installation was not repaired as part of this work. The separate source-based schema check does not establish installed-runtime readiness.
- The primary Linux CI environment, wheelhouse-backed setup/tamper test, and Python-version matrix were not reproduced locally. This is not a claim of full CI completion.
- An independent reviewer examined the skill text and adjacent documentation. Two inconsistencies were found and corrected: the replication exception versus novelty rubric, and the post-draft language-review exception versus manual-only metadata. A follow-up review confirmed those fixes.

Six workflow scenarios were each run three times with the revised guidance and three times without skill guidance, using fresh `gpt-5.6-luna` agents at maximum reasoning. The scenarios tested continuation authority, small-change review, an explicit independent-review gate, an unchanged sprint, an authorised product change, and an incompatible constrained acceptance criterion.

The parent reviewed the answers against criteria recorded before the trials. All 18 answers with skills matched the primary decisions. Seventeen baseline answers did so clearly; one baseline answer was ambiguous about who could change the execution route. The baseline was already strong. These small, unblinded decision probes do not demonstrate better coding outcomes, lower defect rates, or a cost advantage. They also do not compare the old skills against the revised skills. The enlarged evaluation manifests have not all been run as model trials.

Exact [trial inputs and protocol](../evals/skill-routing/results/2026-09-29-workflow-probe-inputs/protocol.json), [criteria](../evals/skill-routing/results/2026-09-29-workflow-probe-inputs/criteria.json), and [responses](../evals/skill-routing/results/2026-09-29-workflow-probes.json) are retained. The input snapshots preserve the exact wording tested; subsequent minor editorial changes are not silently substituted into them.

## Installation and remaining state

The repository sync script was run in dry-run mode and then with `--agent codex --mode symlink`. It created 32 missing links and retained two correct existing links. All 34 links in the Codex destination resolve to the revised repository sources. No conflicting destination was replaced. Claude installation was not refreshed.

Changes remain uncommitted and have not been pushed. Further evidence of benefit would require matched end-to-end tasks using no skills, the previous skills, and these revised skills, with blinded outcome review and cost measurement.
