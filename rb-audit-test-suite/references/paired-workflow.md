# Builder and auditor workflow

Two reasoning roles suffice for this workflow. The host can act as the builder
and invoke the auditor as a separate agent, or dispatch both roles when it already
owns a broader task. The host relays evidence and authority; it need not create a
third reasoning agent to judge agreement. Use existing native test commands and
the narrow coordinator, not a new scheduler or general testing platform.

## Start and preserve authority

Every invocation of `rb-build-test-suite` to create or extend a suite owns this
whole workflow, including for non-scientific projects. The host invokes the
independent auditor and manages repair rounds without asking the user to call
another skill or approve each already-authorized test repair. This applies to
explicit skill calls and automatic selection for matching construction requests.
A direct audit alone does not authorize repairs. Routine execution of an adopted
suite uses its saved commands rather than rebuilding the suite.

An explicit user limit, such as planning-only or no audit, takes precedence;
report that deliverable as partial, not completed paired verification. Missing
delegation, unresolved requirements, insufficient authority or exhausted rounds
leave acceptance incomplete. Ask only for the missing decision or authority;
continue independent work that does not depend on it. Building tests alone does
not authorize changes to application behaviour, scientific criteria or deployments.

Record requirements, numerical bounds, known historical failures, permitted edits
and required checks. Protect the requirements and known-regression criteria from
changes during a run. The host reviews policy changes under existing user authority;
never relax a criterion merely because a round failed. A legitimate criteria
change starts a new run with the prior evidence retained and the reason recorded.

Assign distinct builder/auditor identities and write scopes. Give the auditor the
requirements and historical cases before developer explanations or tests. Keep
its initial plan, then allow implementation inspection. Record actual host
invocations and shared context/tool limitations. Enforced isolation is required
only when project policy calls for it; prompt restrictions are not a sandbox.

## Deterministic work and judgement

Agents choose meaningful assertions, oracles and fault classes. Tests execute those
assertions as ordinary code. Audit tests execute the project tests on healthy and
faulty copies and check the resulting observations. No LLM should judge each
numerical value during a deterministic test run. Fix random-generation seeds or
settings, record tool versions and isolate clocks/services when repeatability is
required. Stochastic validity needs its own predetermined statistical criteria.

The coordinator runs only declared commands. A command for an audit is a test of
the suite, so zero means its healthy and faulty expectations were satisfied. The
coordinator does not reinterpret an arbitrary nonzero exit as a detected defect.
It also cannot decide whether an oracle is scientifically justified or whether a
challenge covers a requirement; those are attributed reviewer judgements.

Use [coordinator.md](coordinator.md) for the implemented plan/review schema and
CLI. Include every assessed source, test, configuration, environment lock and
scientific input in the candidate scope. Include both project and audit commands.
Keep generated logs and coordinator state outside that scope. The host checks
that omitted inputs cannot change the claimed outcome. The coordinator is a
cooperative local tool, not an agent sandbox or authenticated evidence service.

## Bounded sequence

1. The builder writes tests and runs the project's normal checks. The auditor may
   derive its initial challenge plan concurrently from the requirements.
2. The auditor writes executable challenges and validates their healthy controls.
   Each inherited numerical failure becomes an exact executable regression or a
   justified, reviewed non-applicability decision. A semantic reminder is not a
   substitute for the historical test case.
3. Freeze the local policy after both roles have defined their required commands.
   The default limit is three total assessments: the initial assessment and at
   most two repair assessments. Set finite command timeouts. The host also sets
   agent time/turn/spend limits supported by its platform before dispatch and
   discloses limits it cannot enforce. The coordinator does not meter LLM calls.
4. Run the coordinator. Preserve all outcomes. An application bug is reported to
   the owner; fix it only within the user's authorized scope. A test flaw returns
   to the builder. An invalid challenge returns to the auditor. Neither role may
   silently remove a requirement or suppress an observed failure.
5. After a repair, rerun affected local checks before the next assessment. The
   coordinator requires all declared commands for each acceptance attempt. The
   auditor reviews the current candidate and receipts, including prior findings.
   The host initiates this cycle; do not wait for another user invocation. Reuse
   the same distinct auditor for follow-up reviews when available.
6. Submit the auditor's candidate-bound review. The host must have actually
   invoked that reviewer. A review claiming approval with unresolved blocking
   findings cannot pass. Declared identity fields alone are only host attestations.
7. Finish on the coordinator's terminal result. Only `verified_local` supports the
   declared local acceptance claim; report the meaning and limitations. Budget
   exhaustion or unresolved findings require an incomplete handoff. Do not reset
   the round counter to hide failure or continue without a recorded new decision.

The state machine has no automated agent-dispatch integration: the host invokes
the two roles using existing tools and submits their artifacts to the coordinator.
For the user, the builder skill is the single entry point; dispatch is the host's
responsibility within that invocation, not a manual task handed back to the user.
The executable coordinator enforces command and state decisions; skill instructions
own the host's dispatch and scientific-review obligations.

## Reuse and stopping conditions

Reuse valid evidence bound to unchanged inputs; do not require a fresh agent merely
because a repair round begins. New findings get stable IDs and executable evidence.
Recheck repaired findings and controls that the changes could affect. Before final
acceptance, run all declared required commands against the same frozen candidate.

Stop earlier when the remaining issue needs a scientific decision, unavailable
service or missing authorization. Report it directly and continue only independent
work. No number of agreeing agents resolves an undefined requirement. Reports
must separate passed checks, remaining gaps and tested fault classes; do not claim
that passing chosen mutations estimates the probability of all possible defects.
