# RB Agent Skills

This repository contains reusable skills for Codex and Claude Code. A skill is a versioned directory containing a `SKILL.md` workflow and, where useful, model-facing metadata, scripts, references, assets, and behavioural evaluations.

The skills are intended for practical coding, modelling, AI/ML, research, review, and project-continuity work. They provide process guidance rather than a framework that you run directly.

## Quick Start

Clone the repository to a stable location:

```bash
git clone <repo-url> ~/src/rb-skills
cd ~/src/rb-skills
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink
```

The sync script selects a destination automatically:

- Codex: `${CODEX_HOME:-$HOME/.codex}/skills`
- Claude Code: `$HOME/.claude/skills`

Force an agent destination with:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --agent codex
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink --agent claude
```

Install selected skills with:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --mode symlink \
  --skills rb-start-project rb-diagnose rb-implement-with-tests
```

Restart Codex after adding, removing, renaming, or substantially changing skills. Claude Code usually detects changes under an existing `~/.claude/skills` directory, but restart it when new skills do not appear.

## Starting Project Work

Open the target repository and invoke:

```text
Codex: $rb-start-project
Claude Code: /rb-start-project
```

`rb-start-project` inspects the repository, discovers its test and CI conventions, asks only for missing decisions, and routes the first task through the narrowest appropriate workflow.

The routing rule is:

| Task state | Workflow |
| --- | --- |
| Material requirements unresolved | `rb-discuss` |
| Sufficiently understood idea needs a top-level plan | `rb-create-implementation-plan` |
| Existing multi-step plan needs sequencing or status ownership | `rb-execute-plan` |
| Agreed bounded ordinary change | `rb-implement-with-tests` |
| Agreed scientific, numerical, modelling, simulation, stochastic, or domain-sensitive change | `rb-tdd-scientific-code` |
| Unknown bug, regression, failing test, flaky test, or surprising output | `rb-diagnose` |
| Neutral repository orientation | `rb-explain-codebase` |
| Structural critique | `rb-architecture-review` |
| Defect review of a diff or pull request | `rb-review-pr-or-diff` |

`rb-discuss` is not a mandatory stage. Agreed work routes directly to planning or implementation.

## Testing Policy

The coding pipeline uses automated behavioural tests by default. A successful lint, import, build, smoke check, or source inspection does not replace a behavioural test when a plausible regression could escape.

The workflow selects test levels from the likely failure boundary:

- unit or property tests for local logic and invariants;
- component or integration tests for databases, filesystems, networks, queues, frameworks, solvers, processes, and services;
- contract tests for APIs, schemas, events, tools, and compatibility promises;
- migration, existing-data, rollback, and partial-failure tests where state changes;
- end-to-end tests for critical user and operational workflows;
- stochastic, scientific, performance, security, concurrency, recovery, and multi-agent evaluations where those risks matter.

Changes to decisions, validation, external interactions, and side effects should include relevant negative and boundary cases. Bug fixes normally require a regression test that demonstrates the defective behaviour before the fix and passes afterward.

Before completion, the agent runs the closest available repository CI-equivalent command or the largest relevant affordable subset. Anything omitted must be named with its reason and residual risk.

The skills do not impose a universal coverage percentage. They preserve existing project thresholds and focus on changed behaviours, changed branches, and diff coverage where available.

Tests must not be deleted, weakened, skipped, quarantined, or repeatedly rerun until green merely to complete a task. Intermittent failures are defects to diagnose.

## Standard and Constrained Execution Routes

A new implementation plan records one of three routes:

- `standard`: normal tested implementation through `rb-execute-plan`, `rb-implement-with-tests`, and `rb-tdd-scientific-code`;
- `constrained`: a Codex-only, first-release static-only workflow for exact read/patch operations and statically observable acceptance criteria;
- `undecided`: preserve the choice and do not enter the constrained pipeline.

The agent never selects `constrained` automatically.

### Standard Route

Use the standard route for ordinary software behaviour, scientific code, refactors, migrations, integrations, and any phase requiring tests, builds, linting, type checking, application startup, browser automation, benchmarks, network activity, or runtime observation.

In practical terms, runtime-dependent phases must use the standard route in the first release.

### Constrained Static-Only Route

The constrained route processes one approved phase at a time:

```text
rb-execute-plan
  -> rb-create-low-level-plan
  -> rb-assess-plan-safety
  -> rb-safe-operation
  -> stop before the next phase
```

It is suitable only when the phase can be expressed through coordinator-owned `read_file` and exact `apply_patch` operations, or through a bounded model that proposes an exact text patch, and every acceptance criterion is observable from file state.

A bounded model does not edit the repository and does not return an execution-success report. It returns a strict unified diff. The coordinator derives the real target files and candidate contents, checks the proposal deterministically, obtains a fresh no-tool semantic assessment of those exact bytes, and only then may apply the already prepared patch:

```text
approved schema-3 plan envelope, bound to the fixed project-policy identity
              |
              v
model returns exact diff  -- no write tool -->  deterministic proposal preflight
                                                      |
                                                      v
                                         fresh no-tool patch assessment
                                                      |
                                                      v
                                  coordinator records apply intent and approvals
                                                      |
                                                      v
                                  coordinator applies bytes and records each target
                                                      |
                                                      v
                                      separated static-file verification
```

The plan assessment and patch assessment answer different questions. Plan `safe: true` says the unchanged operation envelope may be attempted. A later patch `safe: true` refers to one exact proposed diff and does not authorise a different proposal.

Before compiling a constrained phase, the user may optionally create or tighten `<project-root>/.rb-safe-operation-policy.json` with `$rb-create-safe-operation-policy`. The skill translates ordinary-language restrictions into a typed proposal, shows a deterministic preview, and waits for confirmation bound to that exact preview. The coordinator is the only writer. A rule such as “do not read or write `x.txt`” becomes an exact read denial plus create, modify, and delete denials, and every current plan, assessment, proposal, repair, verification, and resume artifact is bound to that policy identity. Policy authoring is optional; canonical absence preserves baseline behaviour.

Every constrained success criterion and verifier check uses a closed machine-readable form:

```text
<mode>::<description>
```

The recognised modes are:

```text
static_file_state
executable_test
runtime_observation
external_observation
```

The first-release runtime supports only `static_file_state`. Untyped criteria and the other modes fail deterministic preflight. For example:

```text
static_file_state::README.md contains the canonical installation command
```

is supported, while:

```text
executable_test::pytest passes
runtime_observation::the service answers /health
external_observation::the deployed endpoint is healthy
```

are rejected under the current capability profile.

Plan `safe: true` means one exact typed plan passed deterministic policy, adapter, provider, resource, evidence, effect, and verification-mode checks plus a fresh semantic assessment. It is permission to attempt that unchanged plan. A bounded patch still needs its own deterministic preflight and fresh semantic assessment before mutation. Neither verdict is a general claim that the agent, task, machine, or resulting software is safe.

Constrained `verified` means the declared static file-state criteria were covered by coordinator-observed product state and context-separated verifier evidence. It does not prove runtime behaviour.

The route is semi-formal, not an operating-system sandbox. The runtime owns four separate typed semantic roles: plan assessor, proposer, patch assessor, and verifier. In the reviewed Codex-native profile, each role runs as an ephemeral, schema-constrained Codex CLI call in a fresh temporary directory. Shell, arbitrary-code, application, MCP, delegation, browser, computer-use, and other unnecessary capabilities are disabled, the event stream must contain no tool call, and no role receives a project write interface. For bounded semantic work, the proposer returns only typed claims and a standard unified diff. `allowed_read_tools` controls optional interactive proposer reads. `read_roots` must also cover the deliberately selected source files that the coordinator places in the fixed proposer packet. Neither field needs to include new product targets merely for later verification: the deterministic coordinator observes only snapshot-selected files and declared expected product paths under the active policy, then gives that static packet to the no-tool verifier. The coordinator independently parses and assesses the exact candidate bytes, records the apply intent, and alone changes project files. The verifier returns only semantic coverage, evidence, effects, and findings; the trusted transport attaches immutable request and post-execution identities directly from the validated verifier packet. This is a materially restricted process boundary, but it is not proof of operating-system isolation or a complete child trace. The assurance label remains `instruction_only_proposal_host`, and surrounding state comparison detects relevant unexpected host mutations after a call rather than claiming they were impossible.

The Codex-native profile is deliberately opt-in and is never selected merely because a plan says `safe: true`. After `prepare-run-authority`, exact confirmation, plan compilation, and a passing `doctor`, the manifest-pinned `codex-run --enable-codex-cli` command performs plan assessment, optional patch proposal, optional patch assessment, coordinator-only application, and static verification. It uses the locally authenticated Codex CLI and does not read an OpenAI API key. The one confirmed preparation is the authority envelope for all permitted semantic calls in that unchanged run, so the user does not confirm each call separately. A different run, provider, model, plan, policy, target set, effect set, permission set, expiry, or budget needs a new preview and confirmation. `codex-resume --enable-codex-cli` continues a known journalled resource pause under the same confirmed authority and aggregate budget. The host checks the exact Codex executable, version, model, and ChatGPT login before the workflow can persist its first semantic-call intent. Before each dispatch, the coordinator records the complete typed request and the transport rechecks the same identity, then validates the strict response and usage. A complete typed proposer response is persisted before its diff is parsed, so rejected syntax remains auditable. When the confirmed resource grant explicitly permits `proposal_format_error`, the coordinator may automatically ask for corrected unified-diff syntax with a fresh request token. The retry count may be `unbounded`, but calls, tokens, bytes, elapsed time, and cost remain bounded by the same finite aggregate grant. Scope, path, metadata, safety, state, side-effect, identity, incomplete-call, and commit-ambiguity failures are not automatically retried. An incomplete or uncertain provider call is not replayed. The authenticated Codex service receives the deliberately selected source packet and the absolute path names used for policy and identity binding, so both must fit the confirmed data classification and account policy. The temporary working directory prevents ambient project discovery; it does not keep supplied request data local-only. `acceptance-summary` emits only operational totals and identity hashes; it omits prompts, diffs, file contents, reasoning, responses, credentials, and machine-local project paths. See [`docs/safe-operation-process.html`](docs/safe-operation-process.html) for the detailed guide, [`docs/live-provider-acceptance.md`](docs/live-provider-acceptance.md) for qualification evidence and limits, [`docs/project-policy-runtime-0.3-migration.md`](docs/project-policy-runtime-0.3-migration.md) for the current migration boundary, and [`docs/proposal-first-runtime-0.2-migration.md`](docs/proposal-first-runtime-0.2-migration.md) for the historical schema-1 migration.

## Skill Reference

| Skill | Use when |
| --- | --- |
| `$rb-start-project` | First onboarding of a new or poorly understood project, including testing and CI discovery before routing. |
| `$rb-continue-project` | Resume a mature project from instructions, diary, handoff, Git state, and preserved testing context. |
| `$rb-discuss` | Material behaviour, interfaces, edge cases, failure handling, tests, or acceptance criteria remain unresolved. |
| `$rb-create-implementation-plan` | A sufficiently understood idea needs a top-level plan, testing architecture, risks, success criteria, and route choice. |
| `$rb-execute-plan` | An existing multi-step plan needs phase sequencing, task status, test coverage, CI-equivalent checks, and phase-level verification. |
| `$rb-implement-with-tests` | One agreed ordinary change is ready for automated behavioural tests, appropriate test-level selection, and review+fix. |
| `$rb-tdd-scientific-code` | Scientific or numerical work needs test-first units, invariants, tolerances, benchmarks, stochastic checks, integration coverage, and review. |
| `$rb-diagnose` | A bug, regression, flaky test, or surprising output needs evidence-led root-cause work before a fix. |
| `$rb-review-pr-or-diff` | A diff or pull request needs findings-first review, including wrongly levelled, missing, flaky, or weakened tests. |
| `$rb-explain-codebase` | Neutral orientation to structure, control flow, data flow, dependencies, tests, and change hotspots. |
| `$rb-architecture-review` | Structural critique of boundaries, coupling, duplication, hidden assumptions, test seams, and refactoring opportunities. |
| `$rb-multi-agent-systems` | Design or review multiple agents or orchestration, including deterministic runner control and a transition, denial, contract, recovery, end-to-end, and held-out test matrix. |
| `$rb-project-language` | Capture domain terminology, units, invariants, assumptions, and shared vocabulary. |
| `$rb-research-question-gate` | Evaluate a scientific, algorithmic, or novelty claim before investing in planning or coding. |
| `$rb-where-are-we` | Produce a deep evidence-backed HTML project state-of-play report. |
| `$rb-end-session` | Close or hand off a session with Git state, testing evidence, omitted checks, risks, and next actions. |
| `$rb-working-diary` | Preserve cumulative decisions, evidence, test/CI status, risks, and next actions across sessions or compaction. |
| `$rb-explain-diff` | Create a teaching-oriented interactive explanation of a code change. |
| `$rb-create-skill-evals` | Design behavioural evaluations for agent skills, routing boundaries, outcomes, regressions, and ablations. |
| `$rb-write-skill` | Create or update a reusable RB-style skill. |
| `$rb-install-skills` | Install or verify the complete RB setup and project resources. |
| `$rb-setup-local-agent-skills` | Repair an incomplete, stale, or undiscoverable skill installation. |
| `$rb-sync-skills-repo` | Synchronise skill folders between this repository and agent skill directories. |
| `$rb-context-tokens` | Inspect context size or token usage. |
| `$rb-create-low-level-plan` | **Codex-only.** Compile one statically verifiable constrained phase into a schema-3 plan containing exact actions or proposal-only bounded patch operations, with fixed project-policy, provider, and resource bindings. |
| `$rb-assess-plan-safety` | **Codex-only.** Assess the unchanged plan envelope, including identity, policy, adapter, grants, evidence, effects, approvals, and static verification limits. |
| `$rb-safe-operation` | **Codex-only.** Obtain and assess exact bounded diffs, apply accepted bytes through coordinator code, recover from known journalled states, and run separated static verification. |
| `$rb-create-safe-operation-policy` | **Codex-only.** Translate natural-language path restrictions into a typed fixed-root policy proposal, preview the complete authority change, and persist only after proposal-bound confirmation. |

Wiki-specific operational skills live with the wiki system in [`richardmbailey/rb-wiki`](https://github.com/richardmbailey/rb-wiki). They are not duplicated in this general skill pack.

Retired skills remain under [`retired-skills/`](retired-skills/README.md) for historical reference and are not installed by the normal sync.

## Continuity and Handoff

For long-running work, the diary and handoff should preserve:

- objective and current status;
- selected test levels and affected boundaries;
- exact focused, integration, coverage, benchmark, and CI-equivalent commands and outcomes;
- checks not run and why;
- flaky-test evidence and unresolved failures;
- accepted residual regression or scientific risk;
- current Git state, plan/phase state, and exact next action.

Tests are never reported as passed unless they were run in the current session or clearly documented with date and context in an authoritative handoff.

## Repository Validation

The repository CI validates:

- the constrained runtime on Python 3.10 and 3.12;
- the full runtime unit and integration suite, including setup, manifest, launcher, reuse, and tamper gates on the reviewed Linux wheelhouse;
- runtime schema drift and byte-identical generated-schema mirrors;
- instruction contracts;
- cross-file routing, metadata, documentation, capability, and eval consistency;
- JSON syntax for active routing and behavioural evaluation plans;
- the complete behavioural-eval manifest structure, including cases, evaluator fields, and duplicate IDs.

Run the local checks from the repository root with Python 3.10 or newer:

```bash
python3 evals/skill-routing/validate_instruction_contracts.py \
  evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py \
  evals/skill-routing/consistency-contracts.json
for manifest in rb-*/evals/eval-plan.json; do
  python3 rb-create-skill-evals/scripts/validate_eval_manifest.py "$manifest"
done
python3 -m unittest discover -s rb-safe-operation/runtime/tests -p 'test_*.py'
```

For development tests, install the runtime package and its locked dependency set. Routine skill use must use the manifest-pinned installation described above; it must not import an ambient editable package:

```bash
python3 -m pip install -e rb-safe-operation/runtime
```

The setup/manifest/launcher/tamper integration test requires an approved wheelhouse supplied through `RB_SAFE_OPERATION_TEST_WHEELHOUSE`; repository CI provides the reviewed Linux wheelhouse automatically.

## Updating and Publishing

With a symlink installation:

```bash
cd ~/src/rb-skills
git pull
```

Restart Codex after pulling changes that add, remove, rename, or substantially change skill descriptions. Re-run the sync command when using copy mode.

Before publishing, check that the repository contains no secrets, private identifiers, confidential context, local-only paths, caches, generated temporary outputs, or environment files.
