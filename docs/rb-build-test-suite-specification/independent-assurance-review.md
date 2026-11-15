# Independent assurance review

The design provides a strong basis for building useful project-specific tests and reporting their limits. It does not yet ensure that every later generated change goes through those tests. That broader goal needs an explicit connection to the development workflow and a check that the selected tests cover the changed behaviour. Passing the proposed suite would support its recorded claims; it would not establish that an application is reliable in every situation or that a scientific model is empirically valid.

Date: 2026-11-15. This reviewer did not author the design. Review scope was the specification package: README, capability catalogue, module interface, evidence/report contract, implementation plan, draft skill, four schemas, schema checks and historical validation records. Repository guidance and the review and multi-agent architecture skills were applied. Only this report was written; no implementation or existing specification was changed.

## Findings

### 1. [P1] Connect routine generated changes to the suite before claiming they must pass it

**Classification:** Missing requirement for the clarified user goal, not a defect in an implemented runner.

**Locations:** [README.md:36](README.md), lines 36–44 and 263–268; [skill-draft.md:63](skill-draft.md), procedure step 10; [IMPLEMENTATION_PLAN.md:72](IMPLEMENTATION_PLAN.md).

The skill is deliberately selected for suite construction, while feature and scientific implementation remain with other skills. CI integration is conditional on a request, and protected external enforcement is optional. These are coherent boundaries for a suite-building tool. They do not fulfill “pass all generated code through a project-specific suite” on subsequent implementation tasks.

**Failure example:** A project receives a good suite on Monday. On Tuesday an implementation agent changes a calculation, runs only its new unit test, and declares completion. Nothing specified here requires that agent to invoke the saved runner, refresh affected scientific checks, or present an acceptance result for Tuesday's final candidate. A local wrapper can also be omitted entirely. The existing identity checks prevent reusing stale evidence *inside a run*; they do not cause a run to happen.

**Proposed change:** Add a project adoption contract and a task in the plan that integrates the saved suite with relevant implementation/completion instructions. Require a final candidate-bound result before declaring a code change verified, or an explicit incomplete status naming gaps. Reconsider affected requirements and tests when behaviour changes. Keep this skill's construction routing boundary; routine implementation should invoke the existing runner rather than rebuild the suite. Distinguish this cooperative local policy from enforced merge/release protection. If enforcement is requested, prepare a separately authorized protected CI integration with a final aggregation job that fails on missing, skipped, cancelled or insufficient required results, and verify protection/bypass settings before calling it enforced.

**Acceptance cases:** Build a suite, then make a new change through each supported implementation route. A known failing change, a missing run, a post-run edit and a quick-only run missing a required deep check must each prevent a verified-completion claim. A healthy complete run must allow it. For a protected integration, a skipped required job and an unauthorized attempt to weaken the workflow must not produce an accepted merge decision.

**Official basis:** GitHub documents both required checks and bypass settings; it also permits `skipped` and `neutral` check states to satisfy branch protection. Therefore “required check exists” is insufficient unless the workflow's own final decision checks completeness. [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches). This supports the proposed integration boundary, not a claim that the current draft secretly promises protected enforcement.

### 2. [P1] Account for changed behaviour before evaluating the selected checks

**Classification:** Missing acceptance requirement for the clarified goal.

**Locations:** [evidence-and-report.md:107](evidence-and-report.md), lines 107–121; [module-interface.md:43](module-interface.md), configuration requirements; [IMPLEMENTATION_PLAN.md:268](IMPLEMENTATION_PLAN.md), P2.1–P2.2.

The gate correctly evaluates the recorded scope. The design also requires reasoned capability selection, requirement IDs and substantive tests. However, 43 capability dispositions are not an inventory of application behaviour, and the specification does not require reconciliation of the *current change* with the accepted requirement/test inventory before acceptance. An omitted requirement cannot fail a gate that never contains it. This becomes material when the suite is reused for all generated changes.

**Failure example:** Existing tests cover mass conservation. A new conversion from kilograms to tonnes is added to the exported report, but that output behaviour is not added to the suite's requirement inventory. All existing required criteria pass. Candidate hashes correctly identify the new source, yet the selected gate can accept without checking the new conversion. Coverage might show execution of the changed line without checking its value.

**Proposed change:** Define a versioned change-impact record linking changed source/configuration/data and affected interfaces to requirements, required checks, justified exclusions and unresolved coverage. Use deterministic diffs/parsers for the inventory and agent/domain review for semantic impact. Do not use keyword scoring or demand one test per line. Require unresolved material behaviours to remain insufficient evidence. For scientific changes, make explicit whether the change affects implementation verification, assumptions, numerical tolerances, empirical validation or all of these. Encode this record and its acceptance obligations in P1/P2 and the routine integration from finding 1.

**Acceptance cases:** On a fixture with an existing passing suite, add a new public output and seed a units defect. The next invocation must identify the missing requirement/check or construct a discriminating test; merely hashing the changed code and rerunning the old suite cannot qualify the entire change. Include a harmless documentation-only change and a change already covered by existing tests so the check does not force unnecessary suite expansion.

**Official basis:** Coverage.py explicitly demonstrates complete statement execution with an untested branch; this supports treating execution coverage as evidence of paths, not complete behavioural adequacy. [Coverage.py branch coverage](https://coverage.readthedocs.io/en/latest/branch.html). NASA distinguishes checking numerical implementation against justified answers from comparison with experimental observations. [NASA verification assessment](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html), [NASA validation assessment](https://www.grc.nasa.gov/www/wind/valid/tutorial/valassess.html). The requested change is an inference from these limits and the user's broader workflow goal.

### 3. [P2] Qualify the link between the candidate snapshot and the Python code actually imported

**Classification:** Missing concrete implementation acceptance case beneath an existing identity requirement.

**Locations:** [module-interface.md:129](module-interface.md), lines 129–143 and 222–227; [IMPLEMENTATION_PLAN.md:326](IMPLEMENTATION_PLAN.md), P4.1 and P4.7; [schemas/contracts.schema.json:616](schemas/contracts.schema.json), `Candidate`.

Hashing the project source and recording environment versions does not by itself establish which copy Python imported. The draft says to hash the exact bytes executed, but its adapter qualification cases focus on collection, counts, output and exits. They do not describe how to detect a stale installed package or a local checkout that shadows the distribution intended for delivery.

**Failure example:** A `src/` project has a healthy older package installed in its environment. The working checkout contains a new defect, but generated tests import the installed copy. Test collection is nonempty, all assertions pass, and the working-tree digest remains unchanged. Conversely, tests may pass against checkout files that are absent from the built wheel. These are accidental environment failures, not an adversarial runner threat.

**Proposed change:** Add an explicit execution-mode contract for checkout/editable versus built distribution, preserving project conventions. Record and verify relevant package import origins or equivalent adapter evidence against the intended snapshot/artifact. When a package/distribution is the deliverable, include a clean installation and representative workflow against that artifact where this failure boundary matters. No universal packaging test is needed for a standalone script. Also freeze selected test identities and reconcile them with execution, rather than relying on aggregate counts alone; the current expected-selection requirement should be made concrete in the adapter contract.

**Acceptance cases:** A stale healthy installation beside a defective checkout cannot qualify the checkout. A deliberately missing package data file must be detected when testing the distributable. Healthy editable and installed-package modes both work, and custom test discovery is preserved. A different set of tests with the same count cannot satisfy the frozen required selection.

**Official basis:** Pytest documents how import modes, `sys.path`, layouts and editable versus regular installations determine the tested code, and explains installed-package testing as a way to detect packaging defects. [Pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html). This is a proposed discriminating test for the existing identity promise, not evidence that an unavailable adapter currently imports the wrong code.

### 4. [P2] Qualify static-tool scope and configuration before interpreting an empty diagnostic result

**Classification:** Missing concrete adapter acceptance cases; existing high-level controls already cover part of the risk.

**Locations:** [capabilities.md:61](capabilities.md), lines 61–65 and 96–101; [IMPLEMENTATION_PLAN.md:328](IMPLEMENTATION_PLAN.md), P4.3; [module-interface.md:215](module-interface.md), adapter acceptance.

The catalogue appropriately preserves configuration and reviews suppressions, but P4's explicit negative cases do not test a clean tool result caused by unanalyzed code or configuration-driven mutation. For an all-generated-code workflow, the adapter must report what was actually checked and whether that matches the intended claim.

**Failure examples:** With mypy's default treatment of unannotated functions, a generated function containing an obvious type error can produce no diagnostic. A Ruff project configured to fix files can change the candidate during an intended read-only check; `fix-only` can suppress reporting of leftover violations. Final identity validation may invalidate the run afterwards, but it does not undo an unauthorized source edit.

**Proposed change:** Add effective configuration and scope evidence to each selected static adapter. For a chosen type checker, define how generated/changed untyped functions, dynamic `Any`, skipped imports and suppressions affect the claim. A project may retain gradual typing; disclose unchecked regions rather than imply full type checking. For Ruff assessment, explicitly disable fixes and fix-only behaviour, retain the existing rule policy, and verify no source changes. Inspect effective nested configuration and exclusions without flattening the project's intended hierarchy. Keep mutation/format repair as a separate authorized edit followed by a new candidate and checks.

**Acceptance cases:** An unannotated defective function must either be detected under the promised checking mode or shown as outside the type-checking claim. Include missing-import/`Any` and suppression cases. A Ruff fixture with `fix=true` and `fix-only=true` must leave source bytes unchanged during assessment and still expose a remaining required violation. A nested configuration and an excluded changed file must be visible in scope evidence. Healthy gradual-typing and deliberate exclusion cases remain usable under their recorded policy.

**Official basis:** [Mypy common issues](https://mypy.readthedocs.io/en/stable/common_issues.html) documents unchecked unannotated bodies and `Any` propagation. [Ruff configuration and CLI](https://docs.astral.sh/ruff/configuration/) documents hierarchical configuration and disabling fix/fix-only behaviour. These sources justify tool-specific qualification; they do not justify imposing strict typing or a universal lint rule set on every project.

## Existing planned controls that should be retained

These are requirements in the design, not implemented or independently demonstrated controls:

- The deterministic runner evaluates frozen criteria, keeps optional failures visible, rejects missing required evidence, and preserves failures in partial runs. Profiles limit work without waiving acceptance. No “all 43 passed” or coverage-based confidence score is promised.
- Independent review distinguishes session separation, context separation, write permissions, oracle provenance and external enforcement. The design explicitly says a locally editable runner is not tamper-proof. A shared filesystem or different model is not presented as independent proof.
- Scientific requirements already include analytical and limiting cases, conservation, dimensions, convergence, justified tolerances, reference provenance, stochastic uncertainty/power and leakage checks. Empirical validity is explicitly separate from numerical agreement. These align with the scope limits in the NASA references above; adding another verifier cannot replace domain evidence.
- Coverage and mutation are treated as evidence about exercised paths and test sensitivity. Surviving, equivalent, invalid and timed-out mutants are separated; mutation uses disposable copies. Current mutmut documentation confirms fork/platform constraints and scope/selection controls, so pinned real-tool qualification is necessary as already planned. [Mutmut documentation](https://mutmut.readthedocs.io/en/latest/).
- Property testing has bounded generation and persisted counterexamples. Flaky outcomes must remain visible; failed stochastic assertions are not retried to obtain a pass. Pytest and Hypothesis identify uncontrolled state and irreproducible failures as relevant causes, supporting tests of cleanup/order dependence where those boundaries exist. [Pytest flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html), [Hypothesis flaky failures](https://hypothesis.readthedocs.io/en/latest/tutorial/flaky.html).
- Process termination, permission denial, authority checks, interrupted effects, evidence corruption, hostile report input, actual host trials and healthy/defective project pairs all have planned acceptance cases. A pipeline with a deterministic runner is sufficient; this review found no need for a distributed agent framework.
- CI must preserve failure exits and evidence, and candidate code must not receive release secrets. When implementing templates, qualify least-privilege tokens and untrusted-code triggers as part of those existing boundaries. GitHub warns specifically about privileged `pull_request_target`/`workflow_run` handling of untrusted code. [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use).

## Optional refinements, not universal blockers

Formatting is a separate tool result from linting. If a project requires Ruff formatting, include `ruff format --check` as a distinct check under the existing lint capability or a subtype; do not add an arbitrary 44th catalogue entry. A formatting-only violation should fail that formatting criterion while clean lint remains clean. If a project has no formatting acceptance requirement, this is optional and does not establish scientific correctness. [Ruff formatter](https://docs.astral.sh/ruff/formatter/) documents the separate command and check-mode exit meanings.

For suitable stateful/concurrent suites, bounded order/parallelism checks can expose flakiness. This is an application of the existing failure-boundary policy, not a requirement to repeat every test on every change. Similarly, branch coverage and targeted mutation should address consequential changed logic; neither a universal percentage nor mutation of every generated line is warranted.

## Contradictions and schema conclusions

No additional confirmed internal contradiction is asserted by this review. In particular, accepting a structurally valid but semantically inconsistent record is not itself a schema defect: the documents explicitly assign cross-record integrity, truth and gate evaluation to the future semantic validator. The schema tests accurately describe themselves as structural checks.

The schemas provide closed record shapes, criterion definitions, candidate/policy identities, receipts, import identities, report rows and limited state implications. Their existence does not implement a runner, authenticate a producer, verify the executed import path, or establish that selected assertions are adequate. P1 explicitly owns the missing semantic implementation and further configuration/packet schemas. Findings 2–4 should extend that work and its fixtures, rather than mistake permissive structural fields for demonstrated runtime vulnerabilities.

The “scientific-core” independent-review default exists in README lines 323–328 and the plan assumptions. Its project-specific claim boundaries should be fixed in the requirement/impact record proposed in finding 2. It is not necessary to make independent agent review mandatory for every cosmetic edit.

## Evidence and limits

Implementation remains unstarted: no active `rb-build-test-suite/` is delivered by this package, and all implementation tasks are planned. Existing validation records are historical reports; they were not treated as proof of current runtime behaviour.

This review read the actual specification/contracts/test source and consulted the primary tool documentation linked above. JSON contracts were parsed for inspection, but no new runtime or behavioural result is claimed. An attempted rerun of `python3 -m unittest discover -s docs/rb-build-test-suite-specification/checks -v` failed during import because the available system Python lacks `jsonschema`. This is an unavailable validation environment, not a failing schema assertion. No dependencies were installed and no paid trials ran. The earlier recorded nine schema tests were not independently reproduced here.

Initial guessed Hypothesis and NASA subpage URLs failed through the web tool; their working official pages were then reached from the official documentation indexes and are linked above. Tool versions and site contents are current observed documentation, not a compatibility qualification of the future adapters.

No full repository CI, constrained-runtime suite, browser tests, OS matrix, target-project suite, protected CI deployment, real verifier handoff or live agent evaluation was run. The report changes no runtime, so rerunning unrelated suites would not establish the missing implementation behaviour. Reliability improvement, scientific defect-detection rates, false-positive rates and the benefit of independent agents remain empirical claims to measure in the planned held-out trials. No finite passing suite warrants a guarantee of reliable software or true science beyond the claims, domains and evidence it actually assesses.

**Review verdict:** Retain the architecture and scientific safeguards. Address findings 1 and 2 before presenting the design as meeting the clarified all-generated-code goal; add findings 3 and 4 to adapter qualification before claiming that candidate-bound passes cover the intended code. The design is reviewable and implementable, but no assurance capability is implemented or validated by this review.
