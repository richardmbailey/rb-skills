# Proposal-First Runtime 0.2 Migration

This document records the historical schema-1 to runtime-0.2 migration. Runtime 0.3 and schema 3 supersede its executable instructions; use [Safe-operation runtime 0.3 migration](project-policy-runtime-0.3-migration.md) for current runs.

Runtime 0.2 removes the old execution path in which a bounded model could act as an executor and then return its own success report. A bounded model now returns an exact unified diff. Deterministic coordinator code prepares and checks the proposal, a fresh no-tool role assesses the exact candidate content, and the coordinator alone applies accepted bytes and creates the execution report.

## What changed

- Runtime and package version: `0.2.0`.
- Public plan, assessment, run, execution-report, and verification schemas: `2.0`.
- New typed artifacts cover provider and resource authority, proposal context, role calls, exact patch proposals, deterministic proposal preflight, semantic patch assessment, apply intent, repair outcomes, complete coordinator state, and human intervention.
- PydanticAI 2.19.0 is the owned proposal-host path. It exposes no write tool and only registers the bounded `read_file` tool when the plan permits it.
- The JSON-line adapter now returns proposals instead of execution reports. It remains instruction-only and cannot provide interactive read tools.
- Exact and bounded patches share one pure preparation, journalled commit, and recovery implementation.
- One-use mutation approvals are consumed after the apply intent is durable and immediately before commit.
- Eligible repairs remain logically unbounded, while an explicit finite run-resource grant limits aggregate unattended provider work.

## Old plans and paused runs

Schema-1 plans and run artifacts remain readable through the redacted `inspect-legacy` audit command. They cannot be assessed, executed, repaired, verified, or resumed by runtime 0.2. This is deliberate: an old bounded task does not contain the proposal, provider, resource, assessment, and recovery authority required by the new workflow.

To continue old work:

1. inspect the old artifact for audit and source-phase identity;
2. recompile the source phase as a newly identified schema-2 low-level plan;
3. create explicit provider and root run-resource grants;
4. obtain the adapter capability profile from the installed runtime;
5. run complete plan preflight and semantic reassessment;
6. start a new run from the fixed schema-2 handoffs.

Do not edit or relabel the old plan or run in place. A paused schema-1 run stays historical. A runtime downgrade likewise cannot interpret an in-progress schema-2 proposal-first run.

## Installation

Provision runtime 0.2 explicitly from the reviewed hash-pinned wheelhouse with `scripts/setup_runtime.py`. Normal operation then uses the manifest-recorded bootstrap interpreter and `scripts/run_runtime.py`. It does not download dependencies, discover ambient providers, or fall back to a stale runtime.

After installation, `runtime-info` must report runtime `0.2.0`, schema `2.0`, Pydantic `2.13.4`, PydanticAI Slim `2.19.0`, and matching source, lock, environment, and package identities.

## Remaining assurance limits

Framework tool allocation is not an operating-system sandbox. The JSON-line adapter relies on instruction-level role separation and surrounding state comparison. Semantic assessors and verifiers can miss harmful meaning, complete child traces are unavailable, manual approval identity is not authenticated by this release, and static verification does not prove runtime correctness. Phases that require tests, builds, application behaviour, or external observation must use the standard route.
