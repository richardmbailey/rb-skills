---
name: "rb-create-prd"
description: "Use when creating, revising, or reviewing a product requirements document before implementation planning; covers requirements, success measures, risks, and decisions."
---

# RB Create PRD

Create a product requirements document that gives product, design, engineering, testing, operations, and decision-makers a shared account of what must be achieved and why. Keep the PRD at the product-requirements level. Do not turn it into an implementation plan or architecture specification.

Read `references/prd-structure.md` before creating a PRD. Read it before a revision that changes the product problem, users, outcomes, scope, requirements, success measures, constraints, rollout boundary, or approval status.

A decision is material when different reasonable answers would change product behaviour, users, scope, permissions, data handling, acceptance evidence, success measures, rollout, ownership, or risk.

## Inputs

Use the supplied product brief, research, existing PRD, repository context, business constraints, and stakeholder decisions. Extract these facts when the source material supplies them:

- the product or feature owner and decision-makers;
- the problem, affected users, and evidence;
- desired user and business outcomes;
- scope, non-goals, timing constraints, and applicable policies;
- required product behaviour and quality expectations;
- success measures, baselines, target values, and measurement windows;
- dependencies, risks, rollout constraints, and operational ownership;
- the required document format, destination, and existing project template.

Do not invent missing product decisions, research findings, metrics, legal obligations, dates, priorities, or technical constraints. If missing information prevents a faithful requirement, ask for the decision. If the human wants a provisional draft, mark the gap as an assumption, open question, or `TBD` and name its owner when known.

## Workflow

1. Determine the requested operation:
   - **Create:** produce a new PRD from supplied evidence and decisions.
   - **Revise:** update an existing PRD while preserving valid decisions and traceability.
   - **Review:** identify material gaps, conflicts, unsupported claims, and readiness problems without changing the document unless requested.
2. Inspect relevant source material. Distinguish observed evidence, stakeholder decisions, assumptions, proposals, and unresolved questions. Preserve links or identifiers that let readers trace material claims and requirements to their source.
3. Establish the decision boundary. Define the product problem and desired outcome before specifying features. Separate user needs from a proposed solution. State why the work matters now when the sources establish that reason.
4. Identify users and affected parties. Record primary users, secondary users, administrators, operators, support teams, and affected non-users when their needs, permissions, actions, or risks change a requirement. Describe needs in language that focuses on the user's problem rather than an assumed interface.
5. Define outcomes and scope:
   - measurable user and business outcomes;
   - in-scope capabilities and journeys;
   - explicit non-goals and deferred work;
   - constraints that genuinely limit the solution;
   - assumptions that must be validated.
6. Write product requirements. Give each material requirement a stable ID, priority, rationale, source, and observable acceptance evidence. State required behaviour and externally meaningful constraints. Leave implementation choices to the technical planning process unless a choice is an approved product or compliance constraint.
7. Cover quality requirements that change product acceptance, launch, operation, or risk. Consider accessibility, privacy, security, safety, performance, reliability, availability, compatibility, data handling, observability, maintainability, localisation, support, and recovery. Express thresholds only when they are supported by a decision, policy, baseline, or evidence.
8. Define measurement. For each success measure, record the metric, current baseline when known, target or decision threshold, measurement window, data source, segmentation, and owner. Distinguish product success metrics from release acceptance criteria and operational guardrails.
9. Describe delivery boundaries without creating an implementation plan. Record rollout assumptions, migration or compatibility needs, experiment or pilot boundaries, launch gates, rollback expectations, dependencies, and operational handoff requirements when they change product scope, acceptance, launch authority, or operational ownership.
10. Record risks and decisions. Give each material risk a consequence, mitigation or response, owner when known, and status. List open questions with the decision-maker and decision deadline when known.
11. Review the PRD for decision readiness using `references/prd-structure.md`. Set status to `decision-ready` only when implementers can plan the work without guessing a material product decision. Set status to `approved` only when an authorised human or recorded governance process has approved it.

## Boundaries with other skills

- Use `$rb-discuss` when the user wants to explore a change but has not requested a durable PRD and material behaviour is unresolved.
- Use `$rb-research-question-gate` first when the product depends on an untested scientific, algorithmic, or novelty claim that must be evaluated before requirements are credible.
- Use `$rb-create-implementation-plan` after the PRD is decision-ready and the user asks for implementation planning.
- Use `$rb-project-language` when the project needs a durable shared vocabulary beyond the PRD.
- Do not create backlog tickets, detailed architecture, task estimates, or code unless the user separately requests that work.

## Output

For a new or revised PRD, write to the path or document named by the user. If the user does not request a file, return the PRD in Markdown. Use an existing project template when it captures every material decision required by this skill. Otherwise, preserve the project template and add the missing sections, or use the structure in `references/prd-structure.md` when no template exists.

Place unresolved items where readers will encounter their consequences and collect them in the open-decisions section. Do not hide uncertainty in polished prose.

For a review-only request, report findings in priority order. For each finding, identify the affected section, why it blocks or weakens a product decision, and the decision or evidence required. Distinguish blocking gaps from improvements that can wait.

At handoff, state:

- the PRD status: `discovery`, `draft`, `decision-ready`, or `approved`;
- the material assumptions and unresolved decisions;
- the source files or evidence used;
- whether implementation planning can begin without guessing product behaviour;
- the recommended next workflow.

## Completion check

Confirm that:

- the problem and target users are supported by evidence or clearly marked assumptions;
- outcomes are distinct from outputs and implementation choices;
- scope and non-goals define a useful boundary;
- requirements have stable IDs, priority, rationale, source, and observable acceptance evidence;
- quality, data, policy, accessibility, security, privacy, and operational concerns that change acceptance, launch, operation, or risk are covered;
- success measures specify how and when they will be evaluated;
- risks, dependencies, rollout constraints, and ownership are visible;
- conflicts and open decisions are explicit;
- no unsupported threshold, date, metric, obligation, or approval was invented;
- the PRD remains a product-requirements artifact rather than an implementation plan.
