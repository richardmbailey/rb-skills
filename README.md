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

It is suitable only when the phase can be expressed through the supported `read_file`, `apply_patch`, or bounded read/patch operations and every acceptance criterion is observable from file state.

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

`safe: true` means one exact typed plan passed deterministic policy and verification-mode checks plus a fresh semantic assessment. It is permission to attempt that unchanged plan. It is not a general claim that the agent, task, machine, or resulting software is safe.

Constrained `verified` means the declared static file-state criteria were covered by coordinator-observed product state and context-separated verifier evidence. It does not prove runtime behaviour.

The route is semi-formal, not an operating-system sandbox. Read-only role restrictions and fresh-context separation are instruction-only on the current host; complete child traces are unavailable. See [`docs/safe-operation-process.html`](docs/safe-operation-process.html) for the detailed guide.

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
| `$rb-create-low-level-plan` | **Codex-only.** Compile one statically verifiable constrained phase into a typed operational contract. |
| `$rb-assess-plan-safety` | **Codex-only.** Run deterministic identity, policy, capability, evidence, effect, and verification-mode checks plus semantic assessment. |
| `$rb-safe-operation` | **Codex-only.** Execute an unchanged approved static-only bundle and verify its typed file-state criteria. |

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

- constrained runtime unit tests;
- runtime schema drift;
- instruction contracts;
- cross-file routing, metadata, documentation, capability, and eval consistency;
- JSON syntax for active routing and behavioural evaluation plans.

Run the local checks from the repository root with:

```bash
python3 evals/skill-routing/validate_instruction_contracts.py \
  evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py \
  evals/skill-routing/consistency-contracts.json
python3 -m json.tool evals/skill-routing/eval-plan.json >/dev/null
python3 -m unittest discover -s rb-safe-operation/runtime/tests -p 'test_*.py'
```

Install the runtime package or its declared dependency before running its tests:

```bash
python3 -m pip install -e rb-safe-operation/runtime
```

## Updating and Publishing

With a symlink installation:

```bash
cd ~/src/rb-skills
git pull
```

Restart Codex after pulling changes that add, remove, rename, or substantially change skill descriptions. Re-run the sync command when using copy mode.

Before publishing, check that the repository contains no secrets, private identifiers, confidential context, local-only paths, caches, generated temporary outputs, or environment files.
