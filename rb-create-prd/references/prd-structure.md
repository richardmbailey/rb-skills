# PRD Structure and Readiness Guide

Use this structure as a completeness model. Follow an existing project template when it covers the same decisions. Include a section when omitting it could hide a product decision, acceptance condition, launch constraint, owner, or material risk. Otherwise, omit it.

## Recommended document structure

### 1. Document control

- Title
- Status: `discovery`, `draft`, `decision-ready`, or `approved`
- Product or feature owner
- Decision-makers and required reviewers
- Last updated date
- Related research, strategy, policy, design, technical, and delivery artifacts
- Change or decision history when the PRD is revised after circulation

Only an authorised human or governance process can set `approved`.

### 2. Summary

State the user problem, affected users, intended outcome, proposed product boundary, and reason for doing the work. Keep this section concise enough to support a go/no-go discussion.

### 3. Problem and evidence

Describe:

- the current user or operational problem;
- who experiences it and under which circumstances;
- its frequency, severity, scale, or strategic importance when known;
- research, analytics, incidents, support evidence, policy, or stakeholder decisions that establish the problem;
- assumptions and evidence gaps.

Do not present a preferred feature as if it were the user problem.

### 4. Users, affected parties, and needs

Identify primary and secondary users and any administrators, operators, support teams, data subjects, or affected non-users. Record accessibility and inclusion needs that change a requirement or acceptance condition.

A useful need states what the person needs to accomplish and why. Use a user-story format only when it helps. Do not force every need into one sentence template.

### 5. Outcomes and success measures

Separate outcomes from deliverables. For each metric, record:

| Field | Meaning |
| --- | --- |
| Metric | The quantity or bounded qualitative result to evaluate. |
| Baseline | Current value and observation period, or `unknown`. |
| Target | Approved target, threshold, or directional decision rule. |
| Window | When and for how long measurement occurs. |
| Source | System, study, or review method that supplies the evidence. |
| Segments | User or operating groups that must be examined separately. |
| Owner | Person or role responsible for measurement and interpretation. |

Also record guardrails that must not worsen, such as safety incidents, task failure, latency, complaints, accessibility failures, or support demand.

### 6. Scope and non-goals

State capabilities, journeys, user groups, channels, platforms, regions, data, and lifecycle stages that are in scope. State explicit non-goals, exclusions, and deferred work. Explain any boundary that could otherwise be mistaken for an omission.

### 7. User journeys and use cases

Describe the important start-to-finish journeys, triggers, expected outcomes, error paths, recovery paths, and administrative or support paths. Include misuse or abuse cases when they affect the requirements.

### 8. Product requirements

Use stable IDs. Define priority terms locally. A suitable default is:

- `required`: the product cannot satisfy the approved scope without it;
- `important`: expected for the intended outcome, but a decision-maker may defer it;
- `optional`: useful if cost and timing permit;
- `deferred`: explicitly outside the current delivery boundary.

Use a table such as:

| ID | Priority | Requirement | Rationale | Source | Acceptance evidence |
| --- | --- | --- | --- | --- | --- |
| PRD-001 | required | The product ... | User or business reason | Research or decision link | Observable product result |

Each requirement should:

- describe one coherent product behaviour or constraint;
- trace to a user need, outcome, policy, risk, or explicit decision;
- avoid hidden implementation choices;
- cover relevant error, empty, denied, interrupted, and recovery behaviour;
- define observable acceptance evidence without prescribing a test harness.

### 9. Quality and policy requirements

Consider each category. Add requirements for a category when it changes product acceptance, launch, operation, or risk:

- accessibility and inclusive use;
- privacy, consent, retention, and data minimisation;
- security, abuse prevention, and permissions;
- safety and regulated behaviour;
- performance, capacity, and scalability;
- reliability, availability, recovery, and continuity;
- interoperability, compatibility, migration, and portability;
- localisation and internationalisation;
- auditability and observability;
- maintainability and supportability where these create product constraints.

Trace mandatory obligations to an authoritative source. Do not invent numeric thresholds.

For an AI or machine-learning product, also consider model and data provenance, evaluation populations, uncertainty and failure behaviour, human oversight, abuse and prompt-injection risks, monitoring for drift, fallback behaviour, and the authority to suspend automated decisions.

### 10. Data and measurement design

Record data inputs, outputs, ownership, sensitivity, retention, quality expectations, reporting needs, and material analytics events. Identify consent, deletion, access, correction, and audit requirements when relevant. Separate product requirements from a future data-model design.

### 11. Dependencies and constraints

Record external systems, teams, vendors, policies, approvals, data sources, contracts, platforms, deadlines, budgets, and compatibility boundaries that affect scope or feasibility. Name the owner and current status when known.

### 12. Rollout and operational boundaries

Capture product-level decisions about pilots, cohorts, regions, feature access, migration, compatibility, launch gates, rollback expectations, support readiness, training, communications, monitoring, and post-launch review. Leave deployment mechanics and task sequencing to the implementation plan.

### 13. Risks

For each material risk, record the cause, consequence, likelihood or uncertainty, mitigation or response, owner, and status. Include product, user, adoption, delivery, operational, data, privacy, security, safety, accessibility, dependency, and measurement risks where applicable.

### 14. Open decisions

| ID | Decision needed | Why it matters | Options or evidence | Decision-maker | Needed by | Status |
| --- | --- | --- | --- | --- | --- | --- |

Do not bury open decisions only in this table. Mark the affected requirement or section as unresolved too.

### 15. Traceability

Maintain a visible line from evidence and user needs to outcomes, requirements, acceptance evidence, and success measures. A simple requirement-source table is sufficient unless the project already has a stronger system.

## Decision-readiness gate

Call the PRD `decision-ready` only when:

1. The problem, users, and intended outcomes are clear enough to test the product premise.
2. Scope and non-goals prevent materially different interpretations of the product boundary.
3. Required product behaviour and applicable quality constraints are explicit.
4. Acceptance evidence is observable and success measurement is feasible.
5. Dependencies, risks, policies, and operational boundaries that could change the product are visible.
6. No unresolved question would force an implementation team to choose product behaviour, user permissions, data policy, success thresholds, or launch scope without authority.
7. Evidence, decisions, and assumptions are distinguishable and traceable.

A decision-ready PRD can still evolve. Record subsequent product decisions and keep requirement IDs stable where practical.

## Source-informed principles

This guide incorporates these published practices:

- Atlassian's PRD guidance: purpose, goals, assumptions, user stories, scope exclusions, shared understanding, and iterative maintenance: <https://www.atlassian.com/agile/product-management/requirements/>
- GOV.UK Service Manual guidance: base user needs on research, describe problems rather than solutions, refine them with evidence, and trace user stories to needs: <https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs>
- Agile Alliance guidance: preserve the distinction between product value and implementation detail, use acceptance criteria, and treat story templates as aids rather than rigid compliance forms: <https://agilealliance.org/glossary/user-stories/> and <https://agilealliance.org/glossary/user-story-template/>
