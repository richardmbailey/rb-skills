---
name: "rb-research-question-gate"
description: "Use before PRD, implementation planning, or coding when evaluating a research idea, scientific hypothesis, algorithm proposal, or technical novelty claim. Guides Codex through literature/novelty mapping, nearest-prior-art threat audit, research-question formulation, hypotheses, falsifiers, and a stop/revise/proceed gate."
---

# /rb:research-question-gate - decide whether a research idea should proceed

## Purpose

Use this skill to keep research exploration honest before product or code momentum takes over. The goal is not to prove the idea is good; the goal is to decide whether it is already done, too vague, untestable, or worth narrowing into a research design.

## Ground Rules

- Treat "stop" as a valid successful outcome.
- Do not write a PRD, implementation plan, experiment script, or code until the gate explicitly allows it.
- Prefer primary sources: peer-reviewed papers, arXiv papers, major conference proceedings, standards documents, and major-lab technical reports.
- Use cautious technical language. Avoid novelty, breakthrough, semantic, intelligent, or marketing-style claims unless the source evidence justifies them.
- Separate signal source, actuator, regime, and evaluation target. Many false novelty claims collapse because these dimensions get blurred.
- If the topic is current, niche, or fast moving, browse/search rather than relying on memory.
- When the gate permits a next phase, report the outcome and wait for user approval before starting PRD, research design, implementation planning, or code unless the user explicitly requested that continuation.

## Required Inputs

Collect or create these before moving past the first gate:

- Seed idea or problem statement.
- Target domain and intended contribution type: algorithm, model, method, measurement, dataset, tool, theory, or application.
- User's tolerance for stopping, narrowing, or reframing.
- Any supplied literature reviews, Deep Research reports, PDFs, notes, or source folders.
- Constraints on source quality, date range, venue, scale, compute, and acceptable claims.

If required inputs are missing, ask only the smallest number of questions needed to begin. When reasonable, create a first-pass framing document and mark unknowns explicitly.

## Procedure

### 1. Set The Phase Boundary

State what is in scope and out of scope. Usually:

- In scope: literature prompts, novelty map, gap matrix, source audit, research question, hypotheses, falsifiers, minimum non-code evidence.
- Out of scope: PRD, implementation plan, repository architecture, training runs, experiments, code, paper claims.

Record this boundary in `CONTEXT.md`, a research README, or another durable project note when the project is substantial.

### 2. Normalize The Idea

Rewrite the idea in technical terms:

- What is the object being changed or studied?
- What input signals are used?
- What actuator or intervention is proposed?
- What regime is it used in?
- What outcome would count as success?
- What claims are explicitly not being made?

Avoid preserving vague phrases from the user if they can be replaced by measurable terms.

### 3. Commission Or Read The Broad Literature Map

If the user wants to use ChatGPT Deep Research or another external research tool, produce prompts rather than pretending the local audit is exhaustive. Include:

- Main state-of-the-art report prompt.
- Adversarial novelty prompt: "Find prior art that would make this idea not novel."
- Nearest-prior-art prompt: "Compare this idea against the closest known methods."
- Citation-audit prompt: "Check whether cited sources actually support the claims."

Store or link the prompt text, returned reports, follow-up responses, and known provenance such as tool, date, model, and source folder before using them for a gate decision. Treat external research outputs as discovery aids until primary sources have been checked.

If supplied research already exists, read it and extract claims into a structured matrix.

### 4. Build A Review And Gap Matrix

Create a matrix with columns suited to the domain. For algorithm/method work, include:

- Source.
- Area or prior-art class.
- Context, scale, or regime.
- Adaptation signal or mechanism.
- Signal timing.
- Actuator/intervention.
- Granularity.
- Relation to seed idea: duplicate, overlap, adjacent, distant.
- What it already covers.
- What it does not cover.
- Novelty impact and confidence.

End this step with an explicit initial decision: stop, revise/narrow, or continue to research-question formulation.

### 5. Formulate The Research Question

Only do this if the broad idea survives as at least a narrowed question. Produce:

- Central research question.
- Key definitions.
- Exact hypotheses.
- Null hypotheses.
- Threat model from nearest prior art.
- Falsifying evidence.
- Minimum non-code evidence required before PRD or implementation planning.
- Targeted search checklist for the most dangerous prior-art zones.

Make the question narrow enough that a direct prior could falsify it.

### 6. Run The Targeted Source Audit

Search the exact combination and the likely alternate vocabulary. For each dangerous prior-art zone, record:

- Search queries used.
- Primary sources inspected.
- Direct quotes or short paraphrases with links, respecting copyright limits.
- Whether the source matches the signal source.
- Whether it matches the actuator/intervention.
- Whether it matches the regime.
- Whether it preserves or changes the core mechanism.
- Whether it triggers a stop condition.

Classify each source as direct, high-overlap, adjacent, baseline, or not relevant. Be especially suspicious of near misses where only one dimension differs.

### 7. Separate Dimensions Explicitly

Produce tables or notes that distinguish:

- Signal source: scalar loss, confidence, entropy, internal state, gradients, optimizer state, metadata, human labels, environment feedback, novelty, etc.
- Actuator: sample weighting, token weighting, loss weighting, global schedule, layer/group/tensor multiplier, architecture change, regularizer, selection, synthetic signal, evaluation filter, etc.
- Regime: pretraining, continued training, fine-tuning, RL/post-training, inference, test-time adaptation, offline analysis, deployment.
- Baseline class: simple heuristic, established algorithm, learned controller, modern state-of-the-art method, ablation, placebo/control.

This separation is often where the real research question emerges.

### 8. Apply A Decision Rubric

Define explicit criteria before deciding. Adapt the thresholds to the field, but include at least:

- Stop criteria: direct duplicate found; core terms cannot be operationalized; the distinction collapses into known work; only weak baselines would support the claim; or the first credible test is infeasible.
- Revise criteria: one dimension survives, but the original framing is too broad, the contribution type changes, or a near miss forces a narrower regime, signal, actuator, or claim.
- Proceed criteria: no direct duplicate found; nearest priors are understood; signal, actuator, and regime distinctions survive; falsifiers are clear; and credible controls/baselines can be named.

State which criteria passed, failed, or remain uncertain.

### 9. Decide The Gate

Use one of these outcomes:

- **Stop**: direct prior found, distinction collapses, claim is untestable, or only weak baselines would support it.
- **Revise**: part of the idea survives, but the original framing is too broad or the contribution type changes.
- **Proceed to narrow PRD/research design**: no direct duplicate found, nearest priors are understood, falsifiers are clear, and the first non-code research design can be written.

Proceeding to PRD/research design is not permission to code. Unless the user already asked to continue, stop after reporting the gate outcome and ask whether to create the PRD/research-design document. The PRD/research design must still define operational measures, controls, baselines, falsifiers, minimum experiments, and stop criteria.

## Deliverables

Prefer files over chat-only output for substantial projects. Suggested artifacts:

- `deep_research_prompts.md`
- `review_gap_matrix.md`
- `decision_rubric.md`
- `phase_1_assessment.md`
- `research_question_formulation.md`
- `source_audit.md`

Update `CONTEXT.md` and `$rb-working-diary` with durable decisions, especially if the result blocks or permits later PRD work.

## Failure Modes

Stop and ask for user direction if:

- The user wants implementation before accepting the novelty gate.
- Required sources are inaccessible and the result would depend on guessing.
- The idea cannot be expressed in measurable terms.
- The closest prior art appears to be a direct duplicate.
- The only surviving claim relies on marketing language or weak comparisons.

When uncertain, recommend another targeted audit or Deep Research prompt rather than inflating confidence.
