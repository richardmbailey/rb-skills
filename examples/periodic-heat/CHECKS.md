# Test-suite adoption and scope

This example uses the project workflow of `rb-build-test-suite`, with an
independent `rb-audit-test-suite` auditor and the existing local coordinator.
Focus is development; intensity is standard. Requirements R1–R8 define acceptance.
No full assurance runner, schema adapter, new scheduler or report application is
required. The example introduces its model and tests only; existing skills and
other examples are unchanged.

## Ownership and independence

The host wrote the mathematical requirements before dispatch. `/root/heat_builder`
received those requirements and owns the model and production tests.
`/root/heat_auditor` received a fresh task packet containing the requirements and
file locations, without the builder conversation. It must save its initial
challenge plan before reading implementation/tests. It owns executable fault
challenges and scientific review. Both are GPT-6 Astra, medium reasoning; their
contexts are separate but their model family and filesystem are shared. File
ownership is an instruction, not an enforced security boundary.

The host coordinates and checks artifacts. The existing deterministic coordinator
executes required commands and validates the candidate-bound review. It does not
call either LLM. The default maximum is three assessment rounds, including the
initial assessment. Each initial agent task has a stated 20-minute stop/report
instruction; the platform provides no enforced per-agent token/spend limit for
this invocation. Commands have finite timeouts. No network services, production
data, publication or paid external APIs are part of the example.

The independent analytical oracles are hand-worked local updates, discrete
Fourier eigenvalues and the continuum heat equation. This checks implementation
and discretisation, not whether a particular material follows this idealisation.
No observational dataset, calibration or stochastic inference is claimed.

## All 43 capability dispositions

“Required” applies to the selected checks for this example, not to every tool or
subtype mentioned in the skill catalogue. Deferred checks are optional for this
educational scope and cannot be reported as passes. No required capability is
waived by the selected intensity.

| Stable capability IDs | Disposition | Required | Reason and evidence boundary |
| --- | --- | --- | --- |
| `unit`, `functional`, `component` | Selected | Yes | Public solver contract, small independent cases, validation, Fourier decay and zero/final-step behaviour. |
| `property_based` | Selected | Yes | Deterministic bounded families for conservation, bounds, constants and cyclic symmetry; no claim of exhaustive input coverage. |
| `static_analysis` | Selected | Yes | Strict mypy for the numerical model, with explicit unchecked regions reported. |
| `mutation` | Selected | Yes | Auditor-selected plausible faults and healthy controls, with intended assertion evidence. |
| `coverage` | Selected | Yes | Native branch coverage and review of uncovered paths; coverage is not oracle strength. |
| `contract`, `integration`, `acceptance` | Selected | Yes | Actual CSV save/reload, CLI output and requirements-to-test mapping. |
| `lint` | Selected | Yes | Ruff with fixes and fix-only disabled; formatting checked separately. |
| `regression` | Selected | Yes | Retain exact new failures; independently review non-applicability of earlier transfer-model inputs. |
| `smoke` | Selected | Yes | CLI demonstration executes through the real output boundary. |
| `configuration` | Selected | Yes | Bounded physical/numerical parameters, stability neighbours, invalid values and frozen native test configuration. |
| `logs_events`, `auditing` | Selected | Yes | Command outcomes, native results, exact test IDs, import origins, immutable assessment and log hashes. No application event service. |
| `independent_verification` | Selected | Yes | Actual separate auditor invocation; requirements-first oracle design followed by code and exact-candidate review. |
| `fuzz` | Deferred | No | Broad unstructured fuzzing is outside this bounded numeric API trial; explicit invalid/boundary families are required. |
| `formal_verification` | Deferred | No | Analytical references and tests are used; no machine-checked implementation proof. |
| `benchmark`, `performance`, `profiling` | Deferred | No | No throughput or latency promise; finite input limits and command timeouts bound this trial. |
| `usability` | Deferred | No | No human teaching/user study requested; a readable example is not a measured usability result. |
| `ui_ux` | Selected | Yes | Only the standalone evidence report: verify values/links and offline reading without JavaScript. No application GUI. |
| `penetration`, `threat_modelling` | Not applicable | No | Local educational numerical script, no service, credentials or untrusted-code execution interface. Ordinary file errors and unsafe numeric inputs remain tested. |
| `tap_compare`, `load`, `shadowing`, `soak`, `canary`, `release_monitoring`, `traffic_shaping`, `feature_flags`, `teeing`, `chaos`, `operational_monitoring`, `ab_experiment`, `tracing`, `real_user_monitoring`, `on_call_experience` | Not applicable | No | No deployed service, traffic, release cohorts, distributed system, operational staff or human experiment. Analytic reference comparison is already part of numerical testing. |
| `exception_tracking` | Not applicable | No | No exception-tracking service; CLI write failures are covered through the public interface. |
| `dynamic_exploration` | Selected | Yes | Auditor inspection after its independent plan challenges numerical boundaries and test adequacy. |

## Change impact and completion rule

Model arithmetic affects R1–R6; output and CLI affect R7; test configuration,
audit support and coordinator commands affect R8. Requirements, test-design
criteria and initial audit plan are protected inputs. Model, production tests,
audit tests, configuration, dependency pins and reused helper code form the
assessed candidate. Generated caches, logs and reports are outside that scope.
The report is separately checked after assessment and cannot alter command exits.

For later ordinary, scientific, plan-based or direct changes: update the affected
requirement/test mapping, preserve exact regressions and justified tolerances,
run all saved required checks, and compare the candidate identity before claiming
completion. Test edits, changed requirements or a new defect require affected
independent challenges. A native check alone does not grant paired acceptance:
the final command is `status --require-verified` on a session with an actual
current-candidate independent review. Missing evidence, required failures or
unresolved scientific findings remain incomplete.

See README for rerun commands and the final evidence note/report for observations.
