# Construct a project-specific suite

Use the project's requirements and plausible failure modes to choose checks.
The catalogue is a set of options and evidence obligations. It is not a demand
to run every tool on every project.

Start with [the project workflow](project-workflow.md). Reuse an existing task
runner and native reports before writing supporting code. The full module and
schema protocol is conditional on choosing the assurance workflow.

## Development checks

1. Read existing tests, scripts, package manifests, locks, build configuration and
   CI. Preserve custom discovery, fixtures, naming, environment managers and rules.
   Inspect structured files without importing application code or running hooks.
2. Define requirements and failure cases before writing assertions. Include the
   relevant negative, boundary, timeout, permission, corruption, concurrency and
   recovery cases. Choose test level from the failure boundary. A mocked dependency
   cannot establish that the real integration works.
3. Prefer existing commands when they assess the required behaviour and preserve
   usable evidence. Extend them when necessary. Where a local adapter or wrapper
   is needed, implement it with behavioural tests before relying on its output.
   The skill has no packaged scripts to call or copy as a finished implementation.
4. Test the constructed workflow on a healthy case and a deliberately defective
   case. Demonstrate that the assertion catches the defect for the intended reason.
   Preserve failures; do not alter expected values to match candidate output.
5. Select expensive property, mutation, performance and end-to-end checks according
   to risk and budget. Keep every required check in the acceptance policy even
   when the selected profile cannot run it.

## Python qualification

Record interpreter, dependency lock, tool and parser versions. Qualify actual
options/output for those versions; do not infer compatibility from tool presence.
Preserve target environments and separate any runner dependencies.

- Pytest must collect a nonempty frozen set of exact required IDs. Reconcile
  actual execution and per-test outcomes, including parametrization and custom
  discovery. Zero tests, skips, expected failures and same-count substitutions
  cannot qualify missing required assertions.
- Verify actual first-party import origins in the test process against the
  intended checkout, editable installation, script or built artifact. An old
  installed package cannot qualify new checkout code. For a packaged deliverable,
  use clean installation and a representative workflow with checkout shadowing
  excluded. Include required package data. Scripts need no universal wheel test.
- Ruff lint assessment uses qualified `--no-fix --no-fix-only` options and rejects
  masked failure exits. Inspect effective nested settings and file selection;
  verify source bytes remain unchanged. Required formatting uses a separate
  `ruff format --check` result under `lint`. Repairs are separate authorized edits.
- Type-checking policy must explain untyped bodies, `Any`, skipped imports and
  suppressions. Preserve justified gradual typing while displaying unchecked
  regions. A clean diagnostic stream cannot support a broader checking claim.
- Coverage measures execution, not oracle strength. Inspect consequential branches
  and requirements; keep established targets without inventing a universal number.
  Child-process CLI execution may be unmeasured; configure supported collection or
  disclose that gap separately from integration assertions.
- Property tests bound generation and retain counterexamples. Mutation uses
  disposable copies and distinguishes survivors, equivalent-reviewed mutants,
  invalid mutations and timeouts. Benchmarks retain hardware, repetitions,
  uncertainty and a comparable baseline; a first measurement is not a pass limit.

Tool guidance: [pytest](https://docs.pytest.org/en/stable/explanation/goodpractices.html),
[Ruff configuration](https://docs.astral.sh/ruff/configuration/),
[Ruff formatting](https://docs.astral.sh/ruff/formatter/),
[mypy](https://mypy.readthedocs.io/en/stable/common_issues.html),
[branch coverage](https://coverage.readthedocs.io/en/latest/branch.html).

## Operational and human evidence

For each selected operational capability, specify target/configuration identity,
permitted effects, time window, samples, stop conditions and recovery owner.
Separate building a procedure from performing it. Use disposable services for
construction tests. Import real observations only with validated source,
authentication, scope and freshness. Synthetic receipts qualify handling only.

Live load, fault injection, traffic changes, process attachment, notifications,
participant contact and deployment need existing or explicit authority for those
actions. Do not turn a focus choice or a generated configuration into permission.
Missing live systems or participants leave the relevant outcome blocked or deferred.
An agent walkthrough cannot establish human usability or on-call experience.

## Saved workflow and adoption

Keep selected tests and requirements version controlled. Give generated files
clear ownership. When adding a generator that will update files automatically,
use a managed hash and three-way comparison before updates;
preserve hand edits and resolve existing wrapper conflicts. Check interruption,
repeated construction and rollback without overwriting intervening edits.

Save a relocatable command such as `./run_tests.sh`, with argument arrays and
safe path handling underneath. It must preserve nonzero exits, partial evidence
and required gaps. No successful report command may mask a failed test run.
A local command does not create protected merge enforcement.

Add the adoption rule to existing project instructions without replacing their
unrelated content: later generated changes update impact review, invoke required
saved checks and compare final identities before claiming verification. The
[assurance contract](assurance-contract.md) supplies the complete rule and cases.
Its typed records are required in the assurance workflow; a reviewed project note
and native artifacts can establish the shared obligations in the project workflow.
