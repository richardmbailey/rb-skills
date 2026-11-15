# Draft capability catalogue

This proposed skill would help a project collect the kinds of evidence its risks require. The 43 entries below describe capabilities, not a promise that every project needs or can run every check. This is a specification; no capability is implemented or installed by this document.

Select capabilities by requirements, failure boundaries, consequences and available environments. **Development** and **operations** identify useful scopes; **full** includes both. These are applicability labels, not timing restrictions: integration, security, recovery and operational checks can and often should begin before deployment. The original phase grouping is historical. Release monitoring and operational monitoring remain distinct entries.

Each entry gives practical construction work, illustrative tools, evidence and an acceptance rule, scope and cost, authority, and automation types. Tool names are examples, not compatibility or version guarantees. The allowed automation descriptions here are `executable`, `observation`, `procedure`, `human_review`, and `agent_review`; a capability can combine them. An agent review is advisory unless the project's evidence contract explicitly establishes an adequate decision role. Human judgement, participant research and operational observations cannot be replaced by a configuration file, a generated plan or an agent's assertion.

The **quick**, **standard**, and **deep** profiles allocate time, compute and evidence depth. They never grant permission, weaken an acceptance rule, or turn an omitted check into a pass. Costs below are relative starting points; measure them for the project. Deep work remains bounded. Apply the shared [evidence and reporting contract](evidence-and-report.md), recording provenance, actual execution or observation, limitations and unresolved findings. Establish acceptance criteria from requirements, justified baselines or reviewed domain tolerances before running checks; do not invent universal percentages or arbitrary pass thresholds.

## Cross-cutting scientific and reference checks

Scientific validation and differential/reference checks are mandatory considerations across the catalogue, not invented 44th and 45th original entries. For each relevant capability, explicitly determine whether each subtype applies and record the reason for omission. Scientific or numerical projects must construct applicable validation against analytical solutions, conservation laws, dimensional consistency, convergence, uncertainty, stochastic variability and relevant empirical observations. Numerical agreement alone does not establish scientific validity. Domain experts must justify assumptions, tolerances and the interpretation of discrepancies.

Differential/reference checks compare the same controlled inputs against an independently justified implementation, known answer, analytical result or authoritative dataset. Record reference provenance, version, domain of validity and shared dependencies; correlated errors can make two implementations agree incorrectly. Test disagreement handling and invalid references. Use exact comparison only where justified; use domain-supported numerical or statistical comparisons elsewhere. These subtypes can apply to unit, property, integration, regression, performance and operational comparisons. Their evidence follows the same reporting contract.

## The 43 capabilities

### 1. `unit` — Check isolated logic
- **Purpose/applicability:** Verify a small function or module whose behaviour can be separated from external systems; useful for calculations, branching and validation.
- **Construction/tools:** Derive cases from the contract; include normal, boundary and invalid inputs; control clocks and randomness; stub only external boundaries. Examples: pytest, unittest, JUnit, Vitest, QuickCheck.
- **Evidence/acceptance:** Preserve case results, inputs and failures. Required behaviours and invariants must hold; numerical results use justified tolerances and appropriate scientific/reference checks.
- **Scope/cost/profile:** Development/full; usually low cost. Quick runs changed logic and essential cases; standard runs the relevant suite; deep adds generated cases.
- **Authority/automation:** Keep fixtures local and disposable; require separate authority for external effects. `executable`.

### 2. `functional` — Check required behaviour
- **Purpose/applicability:** Establish that a feature delivers its specified result through a public interface, including meaningful failure behaviour.
- **Construction/tools:** Turn requirements into inputs and observable outcomes; exercise positive and negative paths and state transitions. Examples: pytest, REST Assured, Playwright, CLI harnesses.
- **Evidence/acceptance:** Link each scenario to its requirement and actual outputs. Required outcomes, error handling and forbidden side effects must match the contract.
- **Scope/cost/profile:** Development/full; low to moderate cost. Quick covers critical changed paths; standard covers required variants; deep explores combinations.
- **Authority/automation:** Isolate accounts, files and service endpoints; sending or changing real user data requires authority. `executable`.

### 3. `component` — Check a subsystem through its boundary
- **Purpose/applicability:** Test a cohesive service or subsystem with its internal parts connected while controlling dependencies outside its boundary.
- **Construction/tools:** Start the real component; provide realistic dependency doubles or disposable services; exercise persistence, retries and malformed responses. Examples: Testcontainers, WireMock, framework test servers.
- **Evidence/acceptance:** Record component versions, dependency contracts and observed state. Behaviour must satisfy the subsystem contract under success and specified failure modes.
- **Scope/cost/profile:** Development/full; moderate setup cost. Quick uses existing fixtures; standard covers component boundaries; deep adds recovery combinations.
- **Authority/automation:** Use disposable infrastructure and bounded resource limits; prevent accidental production connections. `executable`.

### 4. `fuzz` — Explore unexpected inputs
- **Purpose/applicability:** Discover crashes, hangs and invariant violations in parsers, protocols, state machines or other large input spaces.
- **Construction/tools:** Build a harness and oracle; seed valid and malformed examples; set time/resource limits; preserve and minimise discoveries. Examples: libFuzzer, AFL++, cargo-fuzz, Atheris.
- **Evidence/acceptance:** Save harness, corpus, seeds, budget and reproducing inputs. No unresolved violation of the declared safety properties may remain within the explored scope; absence of findings is not exhaustive proof.
- **Scope/cost/profile:** Development/full; potentially high compute. Quick replays discoveries; standard uses bounded campaigns; deep expands budgets and states.
- **Authority/automation:** Sandbox dangerous parsers and cap filesystem/network effects; live target fuzzing needs explicit scope. `executable`.

### 5. `property_based` — Check rules across generated cases
- **Purpose/applicability:** Verify general invariants, round trips and relationships where examples alone poorly cover the input space.
- **Construction/tools:** Specify independent properties; generate valid and invalid inputs; shrink failures; persist counterexamples. Examples: Hypothesis, QuickCheck, fast-check, proptest.
- **Evidence/acceptance:** Record generators, seeds, example budgets and minimal failures. Properties must hold for explored cases; justify generators and scientific/metamorphic assumptions.
- **Scope/cost/profile:** Development/full; low to high depending on the oracle. Quick replays failures; standard generates bounded cases; deep explores wider distributions.
- **Authority/automation:** Bound generated sizes and runtime; use disposable state for stateful properties. `executable`.

### 6. `formal_verification` — Prove a precisely stated property
- **Purpose/applicability:** Examine critical algorithms, protocols or policies where a formal model can express the important assumptions and guarantees.
- **Construction/tools:** Define the model, properties and environment assumptions; check counterexamples; connect the model to implementation obligations. Examples: TLA+/TLC, Alloy, Dafny, Lean, Coq, CBMC.
- **Evidence/acceptance:** Preserve model, proof/checker output and bounds. Accept only the stated proven or exhaustively checked property within its assumptions; review abstraction and implementation correspondence separately.
- **Scope/cost/profile:** Development/full; often high expertise cost. Quick checks existing models; standard updates relevant properties; deep broadens modelling or proofs.
- **Authority/automation:** Local analysis usually has limited effects; do not describe a proof as authority to deploy. `executable`, `human_review`.

### 7. `static_analysis` — Find defects without running the program
- **Purpose/applicability:** Detect type, data-flow, security or API errors visible in source or intermediate representations.
- **Construction/tools:** Select language-aware analyzers; configure actual build context; review suppressions; compare findings with the established baseline. Examples: mypy, Pyright, CodeQL, Semgrep, compiler analyzers.
- **Evidence/acceptance:** Retain analyzer configuration, version and findings. Resolve or explicitly disposition findings according to the project's reviewed policy; successful analysis does not prove runtime behaviour.
- **Scope/cost/profile:** Development/full; low to moderate, sometimes high. Quick targets changed modules; standard covers the relevant graph; deep runs costly analyses.
- **Authority/automation:** Treat source upload and hosted scanning as separate data-sharing actions. `executable`, `human_review`.

Static adapters must satisfy [effective scope and type-policy requirements](assurance-contract.md#4-record-static-tool-scope-and-prevent-assessment-edits),
including explicit unchecked regions and compatible gradual typing.

### 8. `mutation` — Check whether tests detect plausible defects
- **Purpose/applicability:** Assess test sensitivity by making controlled code changes that should alter behaviour.
- **Construction/tools:** Choose meaningful operators and scope; run tests against mutants; inspect survivors and equivalent mutants; add behaviour-focused tests. Examples: PIT, mutmut, Stryker.
- **Evidence/acceptance:** Record killed, surviving, timed-out and excluded mutants with reasons. Required fault classes must be detected; interpret scores against a justified project target rather than a universal percentage.
- **Scope/cost/profile:** Development/full; high repeated execution cost. Quick targets critical changed code; standard covers risk areas; deep expands operators and modules.
- **Authority/automation:** Mutate disposable copies; preserve source and never publish mutants. `executable`, `human_review`.

### 9. `coverage` — Identify code or requirements not exercised
- **Purpose/applicability:** Locate gaps in executed paths, conditions or requirement scenarios; coverage is supporting evidence, not proof of useful assertions.
- **Construction/tools:** Instrument relevant suites; map uncovered critical paths to scenarios; distinguish unreachable code from missing tests. Examples: coverage.py, JaCoCo, Istanbul, gcov.
- **Evidence/acceptance:** Preserve reports and scope exclusions. Review critical gaps against the project's coverage policy and behavioural evidence; meeting a percentage alone does not establish adequacy.
- **Scope/cost/profile:** Development/full; usually low overhead. Quick examines changes; standard measures suites; deep adds branch/condition or requirements coverage.
- **Authority/automation:** Instrument disposable builds; prevent sensitive source/report publication. `executable`, `human_review`.

### 10. `benchmark` — Measure a controlled workload repeatedly
- **Purpose/applicability:** Compare algorithm or component speed and resource use under repeatable conditions.
- **Construction/tools:** Define representative workloads; control warm-up and environment; repeat measurements; retain distributions and baseline identity. Examples: pytest-benchmark, Google Benchmark, JMH, hyperfine.
- **Evidence/acceptance:** Record hardware, workload, samples and uncertainty. Assess against a requirement or justified baseline comparison; first measurements establish a baseline rather than inventing a pass limit.
- **Scope/cost/profile:** Development/full; moderate compute. Quick checks established small workloads; standard repeats representative cases; deep explores scale and variability.
- **Authority/automation:** Reserve bounded compute and avoid interference with live services. `executable`.

### 11. `contract` — Check agreements between systems
- **Purpose/applicability:** Detect incompatible API, event, file or consumer/provider changes, including semantics that schema checks miss.
- **Construction/tools:** Capture consumer expectations; verify providers; test errors, optional fields and compatibility transitions. Examples: Pact, Schemathesis, OpenAPI validators, JSON Schema validators.
- **Evidence/acceptance:** Preserve contract versions and provider/consumer results. Every required supported interaction must remain compatible; schema validity alone is insufficient for behavioural promises.
- **Scope/cost/profile:** Development/full; moderate setup. Quick verifies affected contracts; standard covers supported counterparts; deep includes migration/version matrices.
- **Authority/automation:** Publish contracts or invoke external providers only within granted access; use isolated credentials. `executable`.

### 12. `lint` — Enforce agreed source conventions
- **Purpose/applicability:** Catch mechanical mistakes and inconsistent conventions that have deterministic rules.
- **Construction/tools:** Use repository configuration; apply scoped rules; inspect exceptions; separate style findings from behavioural defects. Examples: Ruff, ESLint, ShellCheck, markdownlint.
- **Evidence/acceptance:** Retain command and findings. Satisfy the agreed rules or documented exceptions; lint success cannot substitute for behaviour tests.
- **Scope/cost/profile:** Development/full; low cost. Quick checks changed files; standard checks repository scope; deep rarely changes lint depth.
- **Authority/automation:** Read-only by default; auto-fixes require authorized file edits and diff review. `executable`.

Ruff assessment must disable both fixes and fix-only behaviour, preserve source
bytes and expose effective scope. Required formatting is a separate check under
this capability; see [static-tool assurance](assurance-contract.md#4-record-static-tool-scope-and-prevent-assessment-edits).

### 13. `acceptance` — Verify that the delivered result meets user needs
- **Purpose/applicability:** Establish whether concrete stakeholder requirements and workflows are satisfied.
- **Construction/tools:** Agree realistic acceptance scenarios and owners; prepare representative data; execute journeys; collect required human decisions. Examples: Cucumber, Playwright, structured acceptance records.
- **Evidence/acceptance:** Link observed outcomes and reviewer decisions to criteria. Obtain the specified stakeholder acceptance; automated scenarios cannot replace required human sign-off.
- **Scope/cost/profile:** Development/operations/full; moderate coordination cost. Quick checks a narrow change; standard covers agreed criteria; deep exercises wider contexts.
- **Authority/automation:** Use authorized participants and datasets; submission, purchase or publication steps need appropriate authority. `executable`, `human_review`, `procedure`.

### 14. `regression` — Prevent previously correct behaviour from breaking
- **Purpose/applicability:** Protect supported behaviour and reproduce reported defects at the boundary where they occur.
- **Construction/tools:** Reproduce the defect or establish trusted expected behaviour; add the smallest effective test; verify failure before the fix where feasible and success after it. Examples: existing test frameworks, approved snapshots, reference datasets.
- **Evidence/acceptance:** Retain reproduction and before/after results or explain unavailable pre-fix evidence. The defect must be detected and resolved without weakening expectations or concealing flakiness.
- **Scope/cost/profile:** Development/full, with operational replay where authorized; low to high. Quick runs affected regressions; standard adds neighbours; deep runs broad history.
- **Authority/automation:** Sanitize captured data and avoid replaying real destructive actions. `executable`.

### 15. `smoke` — Check that essential paths are available
- **Purpose/applicability:** Quickly detect unusable builds, deployments or environments before investing in broader checks.
- **Construction/tools:** Choose a small set of critical start-up and transaction paths; include a cleanup step and clear failure output. Examples: shell/CLI harnesses, HTTP probes, Playwright.
- **Evidence/acceptance:** Record actual probes and outputs. Essential paths must complete as specified; success supports readiness for further checking, not full correctness.
- **Scope/cost/profile:** Development/operations/full; low cost, suitable for all profiles.
- **Authority/automation:** Prefer harmless synthetic transactions; real writes need authorized test identities and cleanup. `executable`, `observation`.

### 16. `usability` — Observe whether people can complete their tasks
- **Purpose/applicability:** Examine learnability, comprehension, accessibility in use and practical task completion for intended users.
- **Construction/tools:** Define representative tasks and participant groups; obtain consent; observe sessions without leading participants; analyse problems and limitations. Examples: moderated sessions, consented recordings, task protocols.
- **Evidence/acceptance:** Preserve appropriately protected observations and findings. Evaluate against agreed task outcomes and research criteria; small samples and missing groups remain explicit limitations.
- **Scope/cost/profile:** Development/operations/full; substantial human coordination. Quick can review existing evidence; standard/deep require suitably scoped participant work.
- **Authority/automation:** Recruitment, recording and personal data collection require authorization and consent. `procedure`, `human_review`, `observation`.

### 17. `ui_ux` — Check interface behaviour and presentation
- **Purpose/applicability:** Verify navigation, interaction states, responsive layouts and accessibility requirements across supported interfaces.
- **Construction/tools:** Map key screens and states; test keyboard and assistive interactions; compare approved visual references; inspect actual rendering. Examples: Playwright, axe-core, screenshot comparisons, accessibility inspectors.
- **Evidence/acceptance:** Retain rendered evidence, interaction results and review findings. Satisfy design and accessibility criteria; automated scans alone do not establish usable or accessible experiences.
- **Scope/cost/profile:** Development/operations/full; moderate cost. Quick checks changed views; standard covers supported layouts; deep adds devices and human reviews.
- **Authority/automation:** Isolate accounts and prevent sensitive content in screenshots. `executable`, `human_review`, `observation`.

### 18. `penetration` — Test exploitable security weaknesses
- **Purpose/applicability:** Investigate whether an explicitly authorized target can be compromised through realistic attack paths.
- **Construction/tools:** Agree target scope, exclusions, rate limits and stop conditions; execute controlled probes; verify findings minimally; document remediation and retesting. Examples: OWASP ZAP, Burp Suite, approved specialist tooling.
- **Evidence/acceptance:** Preserve sanitized reproductions, affected assets and retest results. Apply the agreed security risk policy; an incomplete scope or scan without findings is not a security guarantee.
- **Scope/cost/profile:** Development/operations/full; specialist and potentially high cost. Quick reviews prior evidence; active standard/deep testing requires scoped authority.
- **Authority/automation:** Require explicit target authorization; exploitation, persistence, data access and production disruption are separately constrained. `executable`, `procedure`, `human_review`.

### 19. `threat_modelling` — Identify how the system could be abused
- **Purpose/applicability:** Find threats arising from assets, trust boundaries, privileges and realistic adversaries before or after implementation.
- **Construction/tools:** Map data flows and dependencies; enumerate abuse cases; assess controls; assign verification and unresolved risk owners. Examples: STRIDE workshops, attack trees, OWASP Threat Dragon.
- **Evidence/acceptance:** Preserve the reviewed model, assumptions and linked controls/tests. Relevant threats need verified controls or explicitly accepted residual risk; a diagram alone is insufficient.
- **Scope/cost/profile:** Development/operations/full; moderate judgement cost. Quick revisits changed boundaries; standard reviews system scope; deep explores adversarial combinations.
- **Authority/automation:** Protect sensitive architecture; modelling grants no authority to attack systems. `procedure`, `human_review`, `agent_review`.

### 20. `performance` — Check whether the system meets resource and response needs
- **Purpose/applicability:** Evaluate end-to-end responsiveness, throughput, resource demand and scaling under representative conditions.
- **Construction/tools:** Define workloads and service objectives; establish baselines; measure latency distributions and resource use; investigate bottlenecks. Examples: k6, Gatling, Locust, platform metrics.
- **Evidence/acceptance:** Preserve environment, workload and measurement windows. Meet justified service objectives with uncertainty and workload limits stated; correct output remains required.
- **Scope/cost/profile:** Development/operations/full; moderate to high cost. Quick runs small established checks; standard measures representative workloads; deep explores scale.
- **Authority/automation:** Bound resource spend and traffic; production testing needs approved impact and stop conditions. `executable`, `observation`.

### 21. `integration` — Check connected parts together
- **Purpose/applicability:** Detect failures in real dependency interactions, state transfer and lifecycle behaviour; useful well before deployment.
- **Construction/tools:** Assemble representative dependencies; exercise transactions, auth, retries, concurrency and migrations; inject relevant boundary failures. Examples: Testcontainers, Docker Compose, pytest, service harnesses.
- **Evidence/acceptance:** Record participating versions and resulting state. Cross-boundary behaviours and recovery guarantees must satisfy their contracts without unintended effects.
- **Scope/cost/profile:** Development/operations/full; moderate setup/runtime. Quick checks changed boundaries; standard tests dependency paths; deep explores failures and version combinations.
- **Authority/automation:** Use isolated data and infrastructure; shared environments require scoped access and cleanup. `executable`.

### 22. `tap_compare` — Compare corresponding observations at a selected boundary
- **Purpose/applicability:** Detect divergence by observing matching messages or outputs from two versions or paths without making the candidate authoritative.
- **Construction/tools:** Select a tap point; correlate equivalent inputs/results; normalize only justified nondeterminism; classify differences against a reference. Examples: comparison harnesses, event consumers, proxy capture facilities.
- **Evidence/acceptance:** Retain sampled scope, correlation losses and discrepancies. Differences must meet the defined compatibility or domain tolerance rules; missing pairs cannot count as agreement.
- **Scope/cost/profile:** Development/operations/full; moderate data and analysis cost. Quick uses saved sanitized samples; standard/deep expand representative observations.
- **Authority/automation:** Capturing traffic requires data-access authority and retention controls; this entry does not authorize duplication or replay. `observation`, `executable`.

### 23. `load` — Check behaviour under expected and peak demand
- **Purpose/applicability:** Establish capacity and failure behaviour as request volume or concurrent work increases.
- **Construction/tools:** Model arrival patterns and realistic user mixes; ramp demand; watch saturation, errors and recovery; set stop conditions. Examples: k6, Locust, Gatling, JMeter.
- **Evidence/acceptance:** Preserve offered versus achieved load and outcome distributions. Meet agreed demand/service objectives and graceful-overload requirements within tested limits.
- **Scope/cost/profile:** Development/operations/full; high infrastructure cost. Quick uses modest bounded loads; standard tests expected peaks; deep explores capacity boundaries.
- **Authority/automation:** Require approved target, traffic limits and cost limits; avoid third-party impact. `executable`, `observation`.

### 24. `shadowing` — Run a candidate beside the serving system
- **Purpose/applicability:** Observe candidate behaviour on representative live or replayed inputs while the established system remains authoritative.
- **Construction/tools:** Isolate candidate side effects; route authorized copies or replays; correlate results; compare correctness and resource use; provide a shutdown path. Examples: service-mesh mirroring, isolated replay harnesses.
- **Evidence/acceptance:** Preserve input coverage, mismatches and isolation evidence. Candidate results must meet defined rules; traffic representativeness and untested write paths remain explicit.
- **Scope/cost/profile:** Development/operations/full; moderate to high duplicated compute. Quick uses recorded inputs; standard/deep require approved observation windows.
- **Authority/automation:** Live duplication and data transfer need authority; suppress email, billing, writes and external calls unless separately approved. `executable`, `observation`.

### 25. `configuration` — Check valid and invalid operating settings
- **Purpose/applicability:** Detect unsafe defaults, incompatible combinations, environment drift and missing configuration handling.
- **Construction/tools:** Parse schemas; test supported combinations and invalid values; exercise startup, reload and fallback behaviour; inspect secrets handling. Examples: JSON Schema, CUE, policy engines, application harnesses.
- **Evidence/acceptance:** Preserve sanitized settings and actual behavioural outcomes. Valid settings must produce required behaviour; invalid or unsafe settings must fail as specified. File existence is insufficient.
- **Scope/cost/profile:** Development/operations/full; low to moderate. Quick checks changed settings; standard covers supported combinations; deep explores interaction boundaries.
- **Authority/automation:** Read secrets minimally; changing shared or live configuration requires authority and recovery planning. `executable`, `observation`.

### 26. `soak` — Find faults that emerge over time
- **Purpose/applicability:** Detect leaks, accumulating state, timer errors and gradual degradation under sustained representative operation.
- **Construction/tools:** Choose duration from suspected failure mechanisms; run stable workloads; track resources and correctness over time; test cleanup and recovery. Examples: load harnesses, process metrics, time-series dashboards.
- **Evidence/acceptance:** Preserve continuous measurements, interruptions and trends. Meet justified stability criteria across the observed duration; shorter runs cannot establish longer-term stability.
- **Scope/cost/profile:** Development/operations/full; high elapsed-time cost. Quick reviews completed evidence; standard/deep schedule bounded runs appropriate to risks.
- **Authority/automation:** Long-lived compute and production exposure require budget and operational authority. `executable`, `observation`.

### 27. `canary` — Evaluate a release with limited exposure
- **Purpose/applicability:** Detect release-specific regressions on an authorized subset before wider rollout.
- **Construction/tools:** Define cohorts, comparable baseline, guardrails and rollback; deploy the candidate within exposure limits; observe enough evidence before deciding. Examples: Argo Rollouts, Flagger, deployment platform controls.
- **Evidence/acceptance:** Record release identity, exposure, observed metrics and decision. Promotion requires agreed release criteria; insufficient samples remain inconclusive, not successful.
- **Scope/cost/profile:** Operations/full; development can rehearse controls. Standard/deep depend on authorized release windows; quick may inspect existing evidence.
- **Authority/automation:** Deployment, user exposure, promotion and rollback need established authority; profiles do not grant it. `procedure`, `executable`, `observation`, `human_review`.

### 28. `release_monitoring` — Observe the effects of a particular release
- **Purpose/applicability:** Connect post-deployment changes in behaviour, incidents and user outcomes to a specific release and decision window.
- **Construction/tools:** Mark deployment identity/time; compare suitable baseline and cohorts; track release risks and alerts; assign rollback/escalation ownership. Examples: deployment annotations, Grafana, release dashboards.
- **Evidence/acceptance:** Retain actual observation windows, signals and decisions. Close release evaluation only when defined criteria and duration are met; a dashboard definition is not evidence of a healthy release.
- **Scope/cost/profile:** Operations/full; moderate observation time. Quick reviews existing windows; standard/deep monitor authorized releases with stated limits.
- **Authority/automation:** Read-only observation differs from rollback or paging; those actions require existing authority. `observation`, `procedure`, `human_review`.

### 29. `traffic_shaping` — Verify routing and demand controls
- **Purpose/applicability:** Check rate limiting, prioritization, routing weights and backpressure under representative demand and failures.
- **Construction/tools:** Define routing/fairness requirements; test configuration in isolation; generate controlled traffic; measure actual distribution and recovery. Examples: Envoy, NGINX, service meshes, load harnesses.
- **Evidence/acceptance:** Record realized routing, rejection behaviour and affected clients. Controls must satisfy the agreed policy; configured weights alone do not show actual distribution.
- **Scope/cost/profile:** Development/operations/full; moderate cost. Quick validates local behaviour; standard/deep exercise realistic traffic and failures.
- **Authority/automation:** Changing live routes or throttles requires authority, impact bounds and rollback. `executable`, `observation`, `procedure`.

### 30. `feature_flags` — Check controlled feature exposure
- **Purpose/applicability:** Verify targeting, default states, combinations, cached values and safe fallback or disablement.
- **Construction/tools:** Enumerate supported states and transitions; test evaluations and downstream behaviour; exercise unavailable flag services and kill switches. Examples: OpenFeature SDKs, flag-provider test adapters, application harnesses.
- **Evidence/acceptance:** Retain evaluated cohorts and behavioural results. Exposure and fallback must match policy, including permission boundaries; configuration alone cannot prove enforcement.
- **Scope/cost/profile:** Development/operations/full; low to moderate. Quick checks changed states; standard covers supported combinations; deep adds transition/failure cases.
- **Authority/automation:** Live flag changes can expose users or change data; require appropriate change authority. `executable`, `observation`, `procedure`.

### 31. `exception_tracking` — Verify that failures are captured and actionable
- **Purpose/applicability:** Check error capture, grouping, context, alerting and redaction across relevant failure paths.
- **Construction/tools:** Trigger controlled exceptions; trace them through ingestion and grouping; test missing context, rate limiting and sensitive-data handling. Examples: Sentry, Rollbar, OpenTelemetry pipelines.
- **Evidence/acceptance:** Retain sanitized event receipts and alert outcomes. Required errors must arrive with useful safe context within agreed timing; an installed SDK is insufficient.
- **Scope/cost/profile:** Development/operations/full; low to moderate. Quick uses a synthetic event; standard/deep cover important failure classes and pipeline failures.
- **Authority/automation:** External event submission and notifications need authorized destinations; avoid real secrets and unnecessary paging. `executable`, `observation`.

### 32. `teeing` — Verify safe duplication of an input stream
- **Purpose/applicability:** Check that copies sent to a secondary consumer preserve required data without disrupting the primary path; this is transport behaviour, not candidate quality.
- **Construction/tools:** Define copy semantics, ordering and loss policy; test backpressure, duplicates and secondary failure; verify isolation. Examples: proxies, stream brokers, dedicated duplication harnesses.
- **Evidence/acceptance:** Record delivery, losses, ordering and primary-path impact. Duplication must meet its contract and preserve primary guarantees; secondary success does not establish semantic agreement.
- **Scope/cost/profile:** Development/operations/full; moderate bandwidth/storage cost. Quick uses synthetic streams; standard/deep exercise representative rates and failures.
- **Authority/automation:** Duplication may disclose data or repeat effects; approve destination, retention and suppression of secondary writes. `executable`, `observation`.

### 33. `profiling` — Locate resource consumption
- **Purpose/applicability:** Explain CPU, memory, allocation, I/O or contention costs for a specified workload.
- **Construction/tools:** Reproduce the workload; select a profiler with known overhead; collect representative samples; relate hotspots to code and verify proposed improvements. Examples: perf, py-spy, cProfile, async-profiler.
- **Evidence/acceptance:** Preserve profiles, workload and overhead caveats. Findings must support the stated bottleneck claim; resource acceptance comes from project objectives, not the presence of a flame graph.
- **Scope/cost/profile:** Development/operations/full; moderate overhead. Quick samples locally; standard targets representative paths; deep investigates sustained or rare events.
- **Authority/automation:** Production attachment and memory capture require authority and protection of sensitive contents. `executable`, `observation`, `human_review`.

### 34. `logs_events` — Check diagnostic and domain event records
- **Purpose/applicability:** Verify that important events are emitted, structured, correlated, retained and safely handled.
- **Construction/tools:** Exercise success/failure paths; parse records deterministically; check required fields, ordering assumptions and redaction; simulate sink failure. Examples: structured-log harnesses, Fluent Bit, OpenSearch queries.
- **Evidence/acceptance:** Retain sanitized observed records and ingestion results. Required events must be accurate and available under the defined contract without prohibited data; configuration alone is insufficient.
- **Scope/cost/profile:** Development/operations/full; low to moderate. Quick checks changed events; standard covers key flows; deep examines loss and retention behaviour.
- **Authority/automation:** Access and export need data authority; tests must not fabricate real business events in authoritative systems. `executable`, `observation`.

### 35. `chaos` — Test resilience to controlled disruption
- **Purpose/applicability:** Examine recovery and containment under explicitly scoped infrastructure or dependency failures.
- **Construction/tools:** State a resilience hypothesis; establish steady state; inject one bounded fault; monitor guardrails; abort and restore; expand only with evidence. Examples: Chaos Mesh, LitmusChaos, Toxiproxy.
- **Evidence/acceptance:** Preserve fault timing, blast radius, recovery observations and cleanup. Meet defined resilience objectives and restore expected state; an interrupted experiment is reported honestly.
- **Scope/cost/profile:** Development/operations/full; potentially high risk/cost. Quick can use local fault injection; standard/deep require suitable approved environments.
- **Authority/automation:** Fault injection needs explicit target and disruption authority with stop and recovery controls. `executable`, `procedure`, `observation`.

### 36. `operational_monitoring` — Check continuing service health
- **Purpose/applicability:** Observe ongoing availability, capacity, correctness and service objectives independently of a particular release.
- **Construction/tools:** Define service indicators and owners; validate collection and alert delivery with safe probes; inspect missing data, noise and escalation behaviour. Examples: Prometheus, Grafana, synthetic probes, alert managers.
- **Evidence/acceptance:** Retain observed windows, probe outcomes and alert receipts. Required signals and response paths must work; silent or missing telemetry cannot establish health.
- **Scope/cost/profile:** Operations/full, with development rehearsals; continuing storage and staffing cost. Profiles bound review windows, not claims about unobserved periods.
- **Authority/automation:** Reading metrics differs from changing monitors or paging people; obtain authority for changes and notifications. `observation`, `executable`, `procedure`.

### 37. `ab_experiment` — Estimate the effect of a controlled change
- **Purpose/applicability:** Compare user or system outcomes through a justified experimental design when randomization and measurement are suitable.
- **Construction/tools:** Specify hypothesis, assignment unit, power assumptions, outcomes and guardrails; validate randomization and instrumentation; define analysis and stopping before exposure. Examples: experimentation platforms, statistical notebooks, assignment tests.
- **Evidence/acceptance:** Preserve assignment checks, analysis, uncertainty and deviations. Apply the agreed decision rule; inconclusive evidence remains inconclusive and significance alone does not establish practical value.
- **Scope/cost/profile:** Operations/full, with development design and simulation; potentially high duration/sample cost. Quick reviews prior evidence; standard/deep depend on design needs.
- **Authority/automation:** User exposure, personal data and treatment changes require appropriate authorization and applicable consent. `procedure`, `executable`, `observation`, `human_review`.

### 38. `tracing` — Follow work across system boundaries
- **Purpose/applicability:** Verify that distributed operations can be correlated and diagnosed across services, queues and retries.
- **Construction/tools:** Instrument required spans and propagation; run representative flows; test asynchronous boundaries, sampling and redaction; inspect traces. Examples: OpenTelemetry, Jaeger, Tempo.
- **Evidence/acceptance:** Retain sanitized trace examples and completeness findings. Required paths must be reconstructable within the agreed sampling policy; installed instrumentation alone is insufficient.
- **Scope/cost/profile:** Development/operations/full; moderate storage/overhead. Quick checks changed paths; standard covers key journeys; deep tests gaps and failure propagation.
- **Authority/automation:** Export destinations and sensitive attributes need authorized handling; live sampling changes can affect cost and privacy. `executable`, `observation`.

### 39. `dynamic_exploration` — Investigate behaviour through guided exploration
- **Purpose/applicability:** Discover unanticipated interactions where fixed scenarios leave meaningful uncertainty; includes bounded agent-assisted exploration.
- **Construction/tools:** Set a charter, environment and action limits; explore states; record actions and observations; convert reproducible findings into tests. Examples: browser/CLI exploration, model-based explorers, approved agent harnesses.
- **Evidence/acceptance:** Preserve reproducible paths and unresolved hypotheses. Close the scoped exploration only against its coverage/learning objectives; absence of discoveries is not proof of correctness.
- **Scope/cost/profile:** Development/operations/full; variable human/compute cost. Quick uses a narrow charter; standard/deep expand bounded areas.
- **Authority/automation:** Enforce permissions outside the explorer; do not allow inferred permission for destructive or external actions. `procedure`, `human_review`, `agent_review`, `executable`.

### 40. `real_user_monitoring` — Observe experience in actual use
- **Purpose/applicability:** Measure real-world performance, failures and interaction outcomes across supported user contexts.
- **Construction/tools:** Define necessary signals and privacy constraints; validate instrumentation with controlled sessions; inspect sampling and cohort gaps; analyse actual observations. Examples: browser performance APIs, consent-aware RUM platforms.
- **Evidence/acceptance:** Preserve aggregate observations, sampling limitations and collection checks. Evaluate against experience objectives across relevant cohorts; absent or biased data cannot establish success.
- **Scope/cost/profile:** Operations/full, with development instrumentation checks; ongoing privacy/storage cost. Profiles bound analysis scope and observation duration.
- **Authority/automation:** Collection, identifiers, recordings and external transfers require appropriate authorization and consent; minimize data. `observation`, `executable`, `human_review`.

### 41. `auditing` — Verify accountable records and controls
- **Purpose/applicability:** Establish whether important actions, permissions and changes can be reconstructed and assessed against agreed obligations.
- **Construction/tools:** Identify required records and controls; sample real authorized transactions; test missing/tampered records and access controls; reconcile independent sources. Examples: audit-log queries, signed records, control checklists.
- **Evidence/acceptance:** Retain protected evidence references, discrepancies and reviewer conclusions. Required controls need observed supporting evidence; a policy document or logging setting does not prove operation or compliance.
- **Scope/cost/profile:** Development/operations/full; moderate to high review cost. Quick inspects narrow changes; standard/deep broaden periods and samples with stated limits.
- **Authority/automation:** Access confidential records minimally; altering retention, permissions or authoritative records requires separate authority. `observation`, `procedure`, `human_review`, `executable`.

### 42. `on_call_experience` — Check whether responders can diagnose and recover
- **Purpose/applicability:** Assess alert clarity, runbook usability, access, escalation and recovery burden for the people who operate the service.
- **Construction/tools:** Agree safe drills or review real incidents; involve intended responders; time and observe diagnosis/recovery; record obstacles and follow-up actions. Examples: tabletop exercises, staging drills, incident review records.
- **Evidence/acceptance:** Preserve responder observations and drill/incident outcomes. Meet agreed response and usability expectations; runbook existence or agent walkthrough alone cannot validate responder experience.
- **Scope/cost/profile:** Operations/full, with development rehearsals; meaningful staff time. Quick reviews existing evidence; standard/deep require scheduled participation.
- **Authority/automation:** Contacting responders, triggering pages or disrupting systems requires explicit authority; simulations must be identified as simulations. `procedure`, `human_review`, `observation`.

### 43. `independent_verification` — Obtain a check with credible independence
- **Purpose/applicability:** Reduce shared blind spots for consequential claims through an independent reviewer, implementation, dataset or method.
- **Construction/tools:** Define the claim and required independence; provide evidence without prescribing the conclusion; reproduce or challenge results; reconcile disagreements. Examples: separate test harnesses, reference implementations, specialist review, authorized agent review.
- **Evidence/acceptance:** Record reviewer/method provenance, shared dependencies and findings. Required independent checks must support the claim or leave disagreements unresolved; a second agent is not automatically independent evidence.
- **Scope/cost/profile:** Development/operations/full; moderate to high cost. Quick may check a narrow claim; standard/deep broaden independence and evidence proportionate to consequences.
- **Authority/automation:** Sharing source or data and engaging reviewers require authorization; required human expertise cannot be replaced by an agent. `executable`, `human_review`, `agent_review`, `procedure`.
