# RB Agent Skills

This repository contains reusable skills for Codex and Claude Code. A skill is a versioned directory containing a `SKILL.md` workflow and, where useful, model-facing metadata, scripts, references, assets, and behavioural evaluations.

Most workflows can be used in either agent, but the whole pack is not interchangeable. See [Claude Code compatibility](#claude-code-compatibility) before installing into Claude Code.

The skills are intended for practical coding, modelling, AI/ML, research, review, and project-continuity work. They provide process guidance rather than a framework that you run directly.

## Latest changes

- Added `$rb-build-test-suite` and `$rb-audit-test-suite`. One builder invocation now handles test construction, independent audit, authorized repairs and final verification for every suite build or extension. The default limit is three assessment rounds; missing evidence or unresolved findings remain incomplete. See [building and auditing test suites](#building-and-auditing-test-suites).
- Added the [periodic heat example](examples/periodic-heat/README.md), with deterministic developer tests, independent mathematical checks and deliberate-fault experiments. Its [recorded results](examples/periodic-heat/EVIDENCE.md) distinguish numerical verification from empirical validity.
- The narrow local test coordinator now checks retained command-log hashes before acceptance. CI retains raw audit evidence on failure. This coordinator is separate from the deferred full assurance runner; see the [review and repairs](docs/test-suite-system/fresh-review.md).

- Refined `$rb-discuss` into a focused user interview with options, grounded recommendations, and clickable choices where supported. Continuation and handoff skills preserve settled decisions and keep technical investigations out of the interview workflow. See the [change and validation record](docs/discussion-interviews-2026-10-08.md).

- Added a separate Claude profile with generated skill copies, native manual-only controls, and user-selected subagent models. Codex skill sources and model defaults are unchanged.

- Simplified the active skills: recognise existing authority, use proportionate standard-route review, keep unchanged sprint checkpoints compact, and load specialist constrained/runtime detail through references. Exact constrained-runtime gates remain unchanged.

- Added `$rb-delegate` for cost-aware Codex execution: delegate bounded, independently verifiable work to cheaper sub-agents while the parent retains integration, verification, and completion judgement.
- Added `$rb-sprint` for adaptive implementation: reconcile each bounded delivery increment with the authoritative PRD, preserve the current plan by default, and permit only the smallest evidence-backed plan change that passes its fail-closed gate. `$rb-execute-plan` remains the linear plan-execution workflow.
- Added `$rb-language` for ordinary drafting and light prose editing when no specialist skill owns the task. `$rb-revise-ai-draft` retains responsibility for substantive revision of supplied AI-like prose.
- Added `$rb-create-prd` for creating, revising, and reviewing decision-ready product requirements before implementation planning.
- Added `$rb-simplify-language`, a manual-only skill for reducing ambiguity in agent-facing control text or any other text that the user explicitly supplies.
- Updated `$rb-write-skill` to distinguish automatic and manual-only triggering, cover both Codex and Claude Code conventions, and apply `$rb-simplify-language` after the first complete skill draft.
- Updated the project lifecycle skills and their behavioural routing contracts so onboarding, continuation, requirements discussion, PRD creation, implementation planning, execution, review, and completion use consistent boundaries.
- Added `examples/safe-space-invaders`, a dependency-free WebGL game that records where constrained static-file work ends and standard behavioural verification is still required.
- Qualified the optional Codex-native constrained runtime for static file work, with schema-3 plans, fixed project policies, bounded patch proposals, explicit run authority, and validated rollback. This remains an opt-in, Codex-only route.
- Licensed the repository under the Mozilla Public License 2.0.

## Quick Start

Clone the repository to a stable location. Keep this clone: the installed Codex skills will link to it.

```bash
git clone https://github.com/richardmbailey/rb-skills.git ~/src/rb-skills
cd ~/src/rb-skills
```

### Ask Codex to install

Open the clone in Codex and give it this instruction:

```text
Read README.md and AGENTS.md. Install all active top-level skills from this
repository globally for Codex, using symlinks to this stable clone so future
pulls update the installed skills. Use the bundled sync script with
--agent codex --mode symlink, inspect its dry-run, then install. Verify that
every installed skill is a symlink resolving to its matching directory in
this clone and has a readable SKILL.md. If copies or conflicting links already
exist, report them and preserve them; ask before backing them up and replacing
them unless I have already authorised that replacement. Report the destination,
verified link count, and how to install newly added skills after future pulls.
```

This installs the skills only. For project setup and onboarding, use `rb-install-skills` and `rb-start-project` afterwards as needed.

### Install from the terminal

From the clone's root, preview and install:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent codex --mode symlink --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent codex --mode symlink
```

The Codex default is `$HOME/.agents/skills`. If Codex already uses another global skill directory, such as `~/.codex/skills`, pass `--dest /path/to/skills` to both commands and use that same destination for later checks and syncs. Use one installation destination for this pack. Repository-scoped `.agents/skills` requires an explicitly selected `--dest`.

Install selected skills by adding, for example, `--skills rb-start-project rb-diagnose rb-implement-with-tests` to both commands. Use copy mode only when you deliberately want a standalone installation: copies require syncing again after source updates.

A `skip: ... already exists` message does not verify a repository link. Inspect existing copies or conflicting links before replacing them. Once replacement is authorised, repeat the dry-run and install with `--replace`; the script preserves the previous directories under the destination's `.skill-backups/` folder.

### Verify the Codex links

From the clone's root, run this read-only check after installation. It checks all active skills; if you deliberately installed a subset, restrict `skills` to that selection. For a custom destination, set `RB_SKILL_DEST` to the same directory used with `--dest`.

```bash
python3 - <<'PY'
import os
from pathlib import Path

root = Path.cwd().resolve()
destination = Path(os.environ.get("RB_SKILL_DEST", "~/.agents/skills")).expanduser()
skills = sorted(p for p in root.glob("rb-*") if p.is_dir() and (p / "SKILL.md").is_file())
if not skills:
    raise SystemExit("No active skills found; run from the rb-skills clone root.")
errors = []
for source in skills:
    link = destination / source.name
    if not link.is_symlink() or link.resolve() != source.resolve():
        errors.append(f"{source.name}: missing or incorrect repository symlink")
    elif not (link / "SKILL.md").is_file() or not os.access(link / "SKILL.md", os.R_OK):
        errors.append(f"{source.name}: SKILL.md is missing or unreadable")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Verified {len(skills)} repository symlinks in {destination}")
PY
```

Codex detects skill changes automatically. Restart only when a new or changed skill does not appear.

To verify a full project setup, check the global installation and the project's readable `AGENTS.md` and `CONTEXT.md` together. This command reports gaps and leaves the files in place. Pass `--dest` if you chose a custom skills directory. For Claude, use `--agent claude` to check its generated skills and the project's `CLAUDE.md`.

```bash
python3 rb-install-skills/scripts/install_skills.py --check --agent codex \
  --pack-root "$PWD" --target /path/to/project
```

### Update after a pull

Pulling into the same clone updates **existing linked skills** directly; there is no copy to refresh. Keep the clone at its installed path. If you move it, rerun installation for the new location and review replacement of the old links.

**New skill directories need new links.** After a pull that adds skills, rerun sync with the same destination, then run the link check above:

```bash
cd ~/src/rb-skills
git pull --ff-only
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent codex --mode symlink --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent codex --mode symlink
```

Correct existing links are left in place; new links are added. The script does not automatically remove links for deleted or renamed skills; inspect those separately. No Git hook is required for updates to existing linked skills.

For Claude Code, use `--agent claude` and the separate profile below. It generates adapted copies that require refreshing after pulls.

## Claude Code compatibility

The Claude profile installs **31 skills**: 30 derived from the shared procedures plus a Claude-specific `rb-delegate`. It excludes the Codex token reporter and the four constrained-runtime/policy skills. Codex continues using the original top-level sources, metadata, model defaults, and symlink installation.

From the repository root, preview and install:

```bash
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent claude --dry-run
python3 rb-sync-skills-repo/scripts/sync_skills_repo.py . --agent claude
python3 platforms/claude/install.py . --check
```

Claude receives generated copies even if `--mode symlink` was requested. Re-run the command after pulling source updates. Unmodified generated copies refresh automatically; locally edited copies or pre-existing links require an explicit `--replace`, which preserves backups. Review the dry-run first. Unsupported legacy skill directories cause a visible failure rather than being silently deleted. Use `--skills` for a subset and pass the same selection to `--check`.

For full project setup, including a `CLAUDE.md` import of shared `AGENTS.md` when missing:

```bash
python3 rb-install-skills/scripts/install_skills.py --agent claude \
  --pack-root "$PWD" --target /path/to/project
```

Existing project instructions are preserved. This repository includes its own [CLAUDE.md](CLAUDE.md) bridge. Use `/rb-name` in Claude when shared instructions say `$rb-name`; the generated edition supplies host-specific setup, continuity, and review rules without changing literal code or runtime commands.

Claude delegation asks which model to use before dispatch unless the user has already selected one for the task. Explicit inheritance is supported; there is no hard-coded Claude model or silent fallback. Required independent-review gates still apply.

The generated `rb-simplify-language` has Claude-native manual-only frontmatter. The authoring workflow uses a bundled copy of its review method for its explicitly authorised post-draft step, so it does not need to enable automatic invocation. [Claude invocation controls](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill).

See the [compatibility and maintenance guide](docs/claude-code-compatibility.md) for the profile, exclusions, refresh behaviour, validation evidence, and remaining live-Claude test limitation.

## Repository layout

- The 36 active skills are the top-level `rb-*` directories that contain a `SKILL.md` file.
- Cross-skill routing cases and consistency checks live in `evals/skill-routing/`.
- Worked examples and their verification notes live in [`examples/`](examples/README.md).
- Current guides, design baselines and dated validation records are indexed in [`docs/`](docs/README.md).
- Historical skills live in `retired-skills/` and are excluded from normal installation.
- `.github/workflows/validate-skills.yml` is the authoritative repository validation workflow.

[`rb-build-test-suite`](rb-build-test-suite/SKILL.md) is available as an
instructions-and-references edition covering all 43 capabilities, routine adoption,
change-impact review and module/evidence/HTML contracts. Its default project
workflow reuses existing tools and native reports with a compact evidence note;
the full assurance workflow applies when required. It does not bundle an
executable runner, adapters or renderer. The broader [implementation plan](docs/rb-build-test-suite-specification/IMPLEMENTATION_PLAN.md)
is deferred; partial executable work is preserved under `development/rb-build-test-suite/`.

One invocation handles every build or extension and automatically invokes
[`rb-audit-test-suite`](rb-audit-test-suite/SKILL.md). Two reasoning roles write
and challenge deterministic tests. The auditor skill includes a small local
coordinator for command failures, candidate-bound review and bounded repair
rounds. The host dispatches the agents; the coordinator does not call LLMs or
implement the full assurance runner. The user need not alternate skill calls. See
[the paired workflow](rb-audit-test-suite/references/paired-workflow.md).

## Starting Project Work

Open the target repository and invoke:

```text
Codex: $rb-start-project
Claude Code: /rb-start-project
```

`rb-start-project` inspects the repository, discovers its test and CI conventions, asks only for missing decisions, and routes the first task through the narrowest appropriate workflow.

For a project that will continue beyond onboarding, it also records a durable eight-stage pipeline covering research assessment, requirements discussion, PRD creation when required, implementation planning, implementation, review, and completion. `$rb-continue-project` restores that pipeline in later sessions.

The routing rule is:

| Task state | Workflow |
| --- | --- |
| Scientific, algorithmic or novelty premise needs assessment before planning | `rb-research-question-gate` |
| Interview about goals or consequential requirements needing user judgement | `rb-discuss` |
| Supplied AI-generated, formulaic, or generic prose needs a faithful revision | `rb-revise-ai-draft` |
| Product or feature needs a durable requirements document | `rb-create-prd` |
| Sufficiently understood idea needs a top-level plan | `rb-create-implementation-plan` |
| Existing multi-step plan should be followed linearly | `rb-execute-plan` |
| Existing plan needs PRD-aligned sprint review and evidence-driven replanning | `rb-sprint` |
| Agreed bounded ordinary change | `rb-implement-with-tests` |
| Agreed scientific, numerical, modelling, simulation, stochastic, or domain-sensitive change | `rb-tdd-scientific-code` |
| Create or extend reusable test infrastructure, including its independent audit and repairs | `rb-build-test-suite` |
| Independently assess whether existing tests catch specified defects | `rb-audit-test-suite` |
| Unknown bug, regression, failing test, flaky test, or surprising output | `rb-diagnose` |
| Neutral repository orientation | `rb-explain-codebase` |
| Structural critique | `rb-architecture-review` |
| Defect review of a diff or pull request | `rb-review-pr-or-diff` |

`rb-discuss` is not a mandatory stage. It guides an interview with the user about goals, outcomes, scope, priorities, and consequential requirements. It offers options with trade-offs and a recommendation when the evidence supports one. It uses clickable choices when a native question tool is available and permitted, and falls back to text otherwise. The user can supply another answer; a displayed default or silence is not agreement.

When meaningful alternatives exist, the interview supplies clickable options; open discovery can use a free-text answer box. If the question tool returns before the user answers, the agent keeps the turn open and waits instead of following the question with a final response that could dismiss it. This governs agent behaviour; it does not guarantee how every host renders or retains its question UI.

Agreed work routes directly to planning or implementation. A new session or technical uncertainty does not require an interview. Handoffs preserve settled decisions and separate pending user choices from agent investigations and nonblocking risks. An unanswered choice blocks only work that depends on it.

Requests to create, revise, or review a product requirements document select `$rb-create-prd` automatically. Users can also invoke `$rb-create-prd` in Codex or `/rb-create-prd` in Claude Code.

## Linear and Adaptive Plan Delivery

After a top-level implementation plan is approved, choose the delivery workflow from the amount of expected discovery:

- Use `$rb-execute-plan` when the approved plan should be followed linearly through its phases and verification gates.
- Use `$rb-sprint` when implementation evidence may require changes to the remaining plan between bounded delivery increments.

`$rb-sprint` requires an authoritative PRD or equivalent requirements artifact and an existing implementation plan. The requirements remain authoritative until an authorised human changes them. Record such a decision before adapting the plan; do not ask for the same approval again. The plan is a technical strategy that may change only when the evidence shows that preserving it would create a specific delivery problem.

The normal sprint transition does not change the plan:

```text
review -- NO_CHANGE ------------------------> sprint_ready -> building -> verifying -> review
   |
   +-- REPLAN -----------------------------> replan -> sprint_ready
   +-- AWAITING_HUMAN_DECISION ------------> stop for an authorised decision
   +-- BLOCKED ----------------------------> stop until the named condition changes
   +-- all completion conditions satisfied -> complete
```

Every review starts with `NO_CHANGE`. An unchanged plan needs only its revision/checkpoint, the evidence checked, and next increment. Proposed changes and unresolved decisions use the full gate record. The gate may return `REPLAN` only when its record establishes all of the following:

- the exact implementation-plan state under review;
- new externally grounded evidence, such as a test, review, experiment, repository observation, operational observation, or explicit human statement;
- the exact task, phase, assumption, dependency, constraint, risk, or verification item affected by that evidence;
- how the evidence contradicts, invalidates, blocks, already satisfies, or makes that item obsolete;
- the concrete problem that preserving the item would cause;
- why a local execution refinement cannot solve the problem and why the proposed plan delta is the smallest adequate response;
- authority for the change and every affected verification, rollout, or rollback commitment.

Agent preference, reflection, novelty, generic best practice, stylistic consistency, an equally viable alternative, or a speculative future risk does not justify replanning. If the evidence is missing or ambiguous, the agent must not edit the plan. It returns `NO_CHANGE` when the current plan remains supported, `AWAITING_HUMAN_DECISION` for governed technical or product decisions, or `BLOCKED` when affected work cannot safely continue. The same evidence against the same plan state must produce the same result unless new evidence or the plan state changes.

Local implementation details may change under `NO_CHANGE` when they do not alter the plan, product behaviour, contracts, dependencies, risk, or acceptance evidence. A real plan edit requires `REPLAN`. Every accepted delta is recorded in the plan change log without erasing completed or verified history.

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

## Building and Auditing Test Suites

For a new suite or an extension, invoke one skill:

```text
Codex: $rb-build-test-suite
Claude Code: /rb-build-test-suite
```

Give it the project and the behaviours to verify. The host builds executable
tests, invokes a separate auditor using `rb-audit-test-suite`, repairs tests and
test infrastructure within the authorized scope, reruns required checks and obtains
review of the exact final candidate. You do not need to invoke the second skill
or request each repair cycle. Claude still requires a model choice when none has
already been authorized for the task.

The default is three total assessment rounds: the initial assessment and up to
two repairs. The existing local coordinator or equivalent CI must preserve failures
and enforce acceptance. Missing delegation, unresolved criteria, insufficient
authority or exhausted rounds produce an incomplete result. An explicit request
for planning-only or no audit takes precedence and yields a partial deliverable.
Application changes and deployment need their own authority.

Invoke `rb-audit-test-suite` directly for an audit of existing tests; that alone
does not authorize repairs. Routine execution of an adopted suite uses its saved
command rather than rebuilding it. Scientific checks, failure evidence and exact
candidate identity remain required even in the lightweight project workflow.
See the [workflow and current evidence](docs/test-suite-system/README.md) and the
[new numerical example](examples/periodic-heat/README.md).

## Cost-Aware Delegation

`$rb-delegate` may be selected automatically alongside the skill that owns a substantial Codex task. It applies only when a subtask has a bounded objective and context, produces an independently verifiable result, and is expected to save more work than briefing and review will add. Users may also invoke it directly in Codex.

The Codex skill uses these starting settings when the user delegates the model choice.

| Subtask | Model |
| --- | --- |
| Well-defined, independently checkable work | `gpt-6.2-sol` with medium reasoning |
| Independently scoped difficult mathematics, synthesis, coding, review, or investigation | `gpt-6.2-astra` with medium reasoning |
| Final synthesis, cross-cutting decisions, integration, and completion judgement | Parent agent |

The parent checks the host's available settings and sends a self-contained task packet when choosing a model. It checks the returned work and alone decides whether the user's task is complete. Compare accepted outcomes, elapsed time, rework and observed cost before changing the defaults. For multi-agent products, use `$rb-multi-agent-systems` for orchestration architecture.

## Skill Reference

| Skill | Use when |
| --- | --- |
| `$rb-start-project` | First onboarding of a new or poorly understood project, including testing and CI discovery before routing. |
| `$rb-continue-project` | Resume a mature project from instructions, diary, handoff, Git state, and preserved testing context. |
| `$rb-discuss` | The user wants an interview about goals or a consequential requirement needs their judgement; not routine clarification, technical investigation, or resuming agreed work. |
| `$rb-create-prd` | Create, revise, or review product requirements, including users, outcomes, scope, success measures, risks, dependencies, and unresolved decisions. |
| `$rb-create-implementation-plan` | A sufficiently understood idea needs a top-level plan with `[ ]`, `[x]`, and `[v]` task states, testing architecture, risks, success criteria, and route choice. |
| `$rb-execute-plan` | An existing multi-step plan should be followed linearly under standard conditions by default, with `[ ]`, `[x]`, and `[v]` task status, test coverage, independent sub-agent review for substantial/high-risk/cross-cutting work or explicit gates before `[v]`, CI-equivalent checks, and verification. |
| `$rb-sprint` | An existing plan needs bounded PRD-aligned sprints; it preserves the plan by default and permits only the smallest authorised delta that passes the evidence gate. |
| `$rb-build-test-suite` | Build reusable tests, automatically invoke the independent auditor, repair issues and verify the final suite from one invocation. |
| `$rb-audit-test-suite` | Independently challenge test suites with healthy/faulty controls, historical regressions and failure-propagation checks; coordinate bounded repairs when authorized. |
| `$rb-implement-with-tests` | One agreed ordinary change is ready for automated behavioural tests, appropriate test-level selection, and review+fix. |
| `$rb-tdd-scientific-code` | Scientific or numerical work needs test-first units, invariants, tolerances, benchmarks, stochastic checks, integration coverage, and review. |
| `$rb-diagnose` | A bug, regression, flaky test, or surprising output needs evidence-led root-cause work before a fix. |
| `$rb-review-pr-or-diff` | A diff or pull request needs findings-first review, including wrongly levelled, missing, flaky, or weakened tests. |
| `$rb-explain-codebase` | Neutral orientation to structure, control flow, data flow, dependencies, tests, and change hotspots. |
| `$rb-architecture-review` | Structural critique of boundaries, coupling, duplication, hidden assumptions, test seams, and refactoring opportunities. |
| `$rb-delegate` | **Codex-only.** Reduce expensive parent-model work on substantial tasks by delegating bounded, independently verifiable subtasks while retaining parent verification and completion ownership. |
| `$rb-multi-agent-systems` | Design or review multiple agents or orchestration, including deterministic runner control and a transition, denial, contract, recovery, end-to-end, and held-out test matrix. |
| `$rb-language` | Draft or lightly edit ordinary user-facing prose when no specialist skill owns the task. |
| `$rb-simplify-language` | Only when explicitly invoked, reduce semantic ambiguity in supplied text; intended primarily for agent-facing control text but available for any text. |
| `$rb-revise-ai-draft` | Substantively revise supplied AI-generated, formulaic, or generic prose into plain, natural writing while preserving meaning, evidence, uncertainty, citations, and authorial voice. |
| `$rb-project-language` | Capture domain terminology, units, invariants, assumptions, and shared vocabulary without expanding terminology work into architecture design. |
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

Give the outcome of checks run in the current session. When reusing an earlier CI result, cite the dated run or log and tested revision. Check whether it covers the affected files, local edits and relevant environment. Say which checks still need to run if those conditions differ.

## Repository Validation

The authoritative CI workflow validates:

- Python compilation and JSON syntax;
- the complete behavioural-eval manifest structure, including cases, evaluator fields, and duplicate IDs;
- skill metadata, instruction contracts and cross-file consistency;
- skill/exporter/setup regressions, packaged test-suite reference schemas, and the local test coordinator and numerical audit example;
- publication hygiene;
- the full constrained-runtime test suite, including setup and tamper gates, without skipped tests;
- runtime schema drift and generated-schema mirrors; and
- constrained-runtime support under Python 3.10 and 3.12.

Manifest validation checks evaluation definitions; it does not execute the model
trials they describe. The workflow uploads `validation-output/` even on failure,
including the numerical audit’s child receipts and parent JUnit report. The
periodic heat example is a separate recorded local trial, not a current CI job.

CI replays the saved Sol and Astra results offline. The trial report gives the prompts, scoring rules, token use and instructions for a fresh comparison. [Matched GPT-6.2 workflow trial](evals/gpt-6.2-workflows/README.md)

Run these general local checks from the repository root with Python 3.10 or newer.
They are a subset of CI; additional test-suite and constrained-runtime checks follow:

```bash
python3 evals/skill-routing/validate_instruction_contracts.py \
  evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py \
  evals/skill-routing/consistency-contracts.json
python3 evals/skill-routing/validate_routing_eval.py \
  evals/skill-routing/eval-plan.json
for manifest in rb-*/evals/eval-plan.json platforms/claude/skills/*/evals/eval-plan.json; do
  python3 rb-create-skill-evals/scripts/validate_eval_manifest.py "$manifest" || exit 1
done
for suite in evals/skill-routing/tests rb-install-skills/tests rb-context-tokens/tests; do
  python3 -m unittest discover -s "$suite" -p 'test_*.py' || exit 1
done
ruby evals/skill-routing/validate_skill_metadata.rb
python3 evals/skill-routing/validate_publication_hygiene.py
git diff --check
```

The GPT-6.2 trial grader uses SQLite controls available in Python 3.11 and newer. To test the grader and replay the saved comparison offline, use that version or newer.

```bash
python3 -m unittest discover -s evals/gpt-6.2-workflows -p 'test_*.py'
python3 evals/gpt-6.2-workflows/check.py evals/gpt-6.2-workflows/trials.jsonl evals/gpt-6.2-workflows/readings.json
```

For changes to the test-suite skills, run the checks below in a project-local
virtual environment with the pinned dependencies installed. CI uses Python 3.12
for these checks. The owned temporary directory retains native evidence and avoids
clearing unrelated pytest files:

```bash
python3 -m pip install -r docs/rb-build-test-suite-specification/checks/requirements.txt \
  -r rb-audit-test-suite/examples/numerical/requirements.txt
python3 -m unittest discover -s docs/rb-build-test-suite-specification/checks -p 'test_*.py'
python3 -m unittest discover -s rb-audit-test-suite/tests -p 'test_*.py'
rb_validation_dir="$(mktemp -d "${TMPDIR:-/tmp}/rb-skills-validation.XXXXXX")"
python3 -m pytest -c rb-audit-test-suite/examples/numerical/pytest.ini \
  rb-audit-test-suite/examples/numerical/audit -q \
  --basetemp="$rb_validation_dir/pytest" --evidence="$rb_validation_dir/audit-evidence" \
  --junitxml="$rb_validation_dir/audit.xml"
```

Run the [periodic heat example's saved checks](examples/periodic-heat/README.md)
when changing that example; its final acceptance also requires actual independent
review. These examples verify stated requirements and selected fault classes,
not a universal probability of correctness.

Runtime, schema, launcher, or cross-cutting constrained-workflow changes also require the full constrained-runtime suite and schema checks from `.github/workflows/validate-skills.yml`. Install its exact locked dependencies as the workflow does. The setup and tamper tests also require an approved wheelhouse through `RB_SAFE_OPERATION_TEST_WHEELHOUSE`; repository CI prepares the reviewed Linux wheelhouse automatically.

Normal constrained operation must use the explicit manifest-pinned setup and launcher described in [`rb-safe-operation/references/runtime-contract.md`](rb-safe-operation/references/runtime-contract.md). It must not use an ambient editable package.

## Updating and Publishing

With a symlink installation:

```bash
cd ~/src/rb-skills
git pull
```

Codex normally detects pulled skill changes automatically. Restart only when a change does not appear. Re-run the sync command when using copy mode or the generated Claude profile.

Before publishing, check that the repository contains no secrets, private identifiers, confidential context, local-only paths, caches, generated temporary outputs, or environment files.

## Safe Execution: Standard and Constrained Routes

A new implementation plan records one of three routes:

- `standard`: normal tested implementation through linear `rb-execute-plan` or adaptive `rb-sprint`, with task delivery through `rb-implement-with-tests` and `rb-tdd-scientific-code`;
- `constrained`: a Codex-only, first-release static-only workflow for exact read/patch operations and statically observable acceptance criteria;
- `undecided` preserves an open route choice. Already authorised work uses standard execution unless a recorded user decision holds it.

The agent never selects `constrained` automatically. Ordinary planning does not require a route-selection question; explain the specialist route only when requested or compared.

### Standard Route

Use the standard route for ordinary software behaviour, scientific code, refactors, migrations, integrations, and any phase requiring tests, builds, linting, type checking, application startup, browser automation, benchmarks, network activity, or runtime observation.

In practical terms, runtime-dependent phases must use the standard route in the first release.

Both `$rb-execute-plan` and `$rb-sprint` default to `standard` for authorised work when the route is missing or `undecided`. If the user asks to wait for their route choice, record which work is held and carry that instruction into the handoff. Resume the held work when the user releases it. Selecting the constrained route still requires its own approvals.

### Constrained Static-Only Route

The constrained route processes one approved phase at a time:

```text
rb-execute-plan or rb-sprint
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

The route is semi-formal, not an operating-system sandbox. The runtime owns four separate typed semantic roles: plan assessor, proposer, patch assessor, and verifier. In the reviewed Codex-native profile, each role runs as an ephemeral, schema-constrained Codex CLI call in a fresh temporary directory. Shell, arbitrary-code, application, MCP, delegation, browser, computer-use, and other unnecessary capabilities are disabled, the event stream must contain no tool call, and no role receives a project write interface. For bounded semantic work, the proposer returns only typed claims and a standard unified diff. The earlier plan-assessment packet binds selected source files by hash and metadata; immediately before proposal, the coordinator re-reads those files, verifies the same hashes and metadata, and places their exact complete text in the fixed proposer packet. `allowed_read_tools` controls only additional interactive proposer reads. `read_roots` must cover the deliberately selected source files that the coordinator supplies. Neither field needs to include new product targets merely for later verification: the deterministic coordinator observes only snapshot-selected files and declared expected product paths under the active policy, then gives that static packet to the no-tool verifier. The coordinator independently parses and assesses the exact candidate bytes, records the apply intent, and alone changes project files. The verifier returns only semantic coverage, evidence, effects, and findings; the trusted transport attaches immutable request and post-execution identities directly from the validated verifier packet. This is a materially restricted process boundary, but it is not proof of operating-system isolation or a complete child trace. The assurance label remains `instruction_only_proposal_host`, and surrounding state comparison detects relevant unexpected host mutations after a call rather than claiming they were impossible.

The Codex-native profile is deliberately opt-in and is never selected merely because a plan says `safe: true`. After `prepare-run-authority`, exact confirmation, plan compilation, and a passing `doctor`, the manifest-pinned `codex-run --enable-codex-cli` command performs plan assessment, optional patch proposal, optional patch assessment, coordinator-only application, and static verification. It uses the locally authenticated Codex CLI and does not read an OpenAI API key. The one confirmed preparation is the authority envelope for all permitted semantic calls in that unchanged run, so the user does not confirm each call separately. A different run, provider, model, plan, policy, target set, effect set, permission set, expiry, or budget needs a new preview and confirmation. `codex-resume --enable-codex-cli` continues a known journalled resource pause under the same confirmed authority and aggregate budget. The host checks the exact Codex executable, version, model, and ChatGPT login before the workflow can persist its first semantic-call intent. Before each dispatch, the coordinator records the complete typed request and the transport rechecks the same identity, then validates the strict response and usage. A complete typed proposer response is persisted before its diff is parsed, so rejected syntax remains auditable. When the confirmed resource grant explicitly permits `proposal_format_error`, the coordinator may automatically ask for corrected unified-diff syntax with a fresh request token. The retry count may be `unbounded`, but calls, tokens, bytes, elapsed time, and cost remain bounded by the same finite aggregate grant. Scope, path, metadata, safety, state, side-effect, identity, incomplete-call, and commit-ambiguity failures are not automatically retried. An incomplete or uncertain provider call is not replayed. The authenticated Codex service receives the deliberately selected source packet and the absolute path names used for policy and identity binding, so both must fit the confirmed data classification and account policy. The temporary working directory prevents ambient project discovery; it does not keep supplied request data local-only. `acceptance-summary` emits only operational totals and identity hashes; it omits prompts, diffs, file contents, reasoning, responses, credentials, and machine-local project paths. See [`docs/safe-operation-process.html`](docs/safe-operation-process.html) for the detailed guide, [`docs/live-provider-acceptance.md`](docs/live-provider-acceptance.md) for qualification evidence and limits, [`docs/project-policy-runtime-0.3-migration.md`](docs/project-policy-runtime-0.3-migration.md) for the current migration boundary, and [`docs/proposal-first-runtime-0.2-migration.md`](docs/proposal-first-runtime-0.2-migration.md) for the historical schema-1 migration.

The release candidate with runtime source `ecfd1ae5c1d4cae4d086b2ee50704a23da986ca9736655773acc4c284e43ad29` passed the complete five-run Codex-native matrix on 30 July 2026 and passed all 286 no-skip runtime tests under Python 3.10 and 3.12. This qualifies that exact runtime identity for optional static use within the limits above. It does not make the route the default or make an unqualified later runtime equivalent. Any public revision carrying this claim must preserve the same runtime identity and pass review and remote CI for its complete repository tree.

Explicit runtime setup retains each complete setup manifest by its content hash before selecting it as current. A rollback is also explicit: `scripts/rollback_runtime.py` accepts one retained manifest hash, revalidates its source checkout, launcher, bootstrap interpreter, installed environment, package, and dependency locks, and only then atomically selects it. The retained source checkout must still exist unchanged. A failed or corrupted rollback leaves the current manifest untouched, and neither setup nor rollback deletes project run records.

## Licence

Unless a file states otherwise, the source code, skill instructions, documentation, schemas, and examples in this repository are made available under the [Mozilla Public License 2.0](LICENSE).

This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed with this repository, you can obtain one at <https://mozilla.org/MPL/2.0/>.

Copyright (c) 2026 Richard Bailey.
