# Periodic heat diffusion

This example follows temperature changes around a closed ring. Heat spreads to
both neighbours, conserving the mean. It verifies the explicit Euler discretisation
of an ideal diffusion equation; it does not establish a material's real behaviour.

`heat.py` uses the Python standard library. Python 3.11 or newer is required;
the recorded trial uses Python 3.14. Tool versions are pinned in requirements.txt.
Use a dedicated environment, not global installations:

```bash
python3 -m venv /tmp/periodic-heat-venv
/tmp/periodic-heat-venv/bin/python -m pip install -r requirements.txt
source /tmp/periodic-heat-venv/bin/activate
```

Run commands from this directory using that environment's Python. The CLI example
has four cells initially at [400,300,300,300] kelvin, spacing 1 metre, diffusivity
0.25 m²/s, and one step of 1 second. Its result is [350,325,300,325] kelvin.

```bash
python heat.py --output /tmp/heat.csv
```

`simulate` accepts a sequence and the keyword arguments specified in
[REQUIREMENTS.md](REQUIREMENTS.md). `Solution` is frozen and contains a tuple of
kelvin temperatures, metre spacing and elapsed seconds. `write_csv` writes
`x_m,time_s,temperature_K` and propagates file errors. The CLI also exits nonzero
on output failure. Destination parent directories must already exist.

## Required checks

Create a new evidence directory for each assessment; never overwrite failed runs.
The following are ordinary native commands, each of which must succeed. No final
report command may substitute for an earlier failure. `RUN` and the cache paths
must refer to fresh directories owned by this assessment.

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export RUN=evidence/my-new-run
mkdir -p "$RUN"
export COVERAGE_FILE="$RUN/.coverage"
python -m pytest -c pytest.ini --confcutdir=. -p no:cacheprovider --collect-only -q
python -m coverage run -m pytest -c pytest.ini --confcutdir=. -p no:cacheprovider -s --basetemp="$RUN/tmp" --junitxml="$RUN/tests.xml"
python -m coverage json -o "$RUN/coverage.json"
python -m coverage report
python -m ruff check --no-fix --no-fix-only --no-cache heat.py test_heat.py audit_science.py audit_suite.py
python -m ruff format --check --no-cache heat.py test_heat.py audit_science.py audit_suite.py
python -m mypy --strict --cache-dir=/tmp/periodic-heat-mypy heat.py
```

Plugin autoload is disabled because this standalone example uses only pytest itself;
this prevents unrelated environment plugins from changing discovery or execution.
Use a fresh owned `--basetemp` so pytest never clears unrelated temporary files.

## Coordinator assessment

The saved [check-plan.json](check-plan.json) runs all required checks: project
coverage, lint, formatting, model typing, independent science and fault challenges,
reused evidence-parser controls, and exact executed-ID reconciliation. It uses
`python3` from the active environment. Run it from the repository root:

```bash
# From this example directory, after activating the environment above:
cd ../..
mkdir -p examples/periodic-heat/evidence/assessment
python3 rb-audit-test-suite/scripts/test_loop.py init --project "$PWD" \
  --plan examples/periodic-heat/check-plan.json \
  --state-dir "$PWD/examples/periodic-heat/evidence/new-session"
python3 rb-audit-test-suite/scripts/test_loop.py run \
  --state-dir "$PWD/examples/periodic-heat/evidence/new-session"
```

`run` exits 3 when all commands pass but independent review remains pending;
this is intentional. A nonzero command failure returns 1. Use a new state directory
only for a genuinely new authorised session, not to reset a failed round budget.
Copy `evidence/assessment/` into that state's numbered round directory after each
run and before another run can overwrite its native outputs. Audit child artifacts
already use fresh retained directories. Keep every round, including failures.

Have a separate auditor inspect the requirements, current candidate digest and
raw evidence. Submit its actual candidate-bound JSON review using the coordinator's
[`review` schema](../../rb-audit-test-suite/references/coordinator.md), then run:

```bash
python3 rb-audit-test-suite/scripts/test_loop.py review \
  --state-dir "$PWD/examples/periodic-heat/evidence/new-session" --review /path/to/actual-review.json
python3 rb-audit-test-suite/scripts/test_loop.py status \
  --state-dir "$PWD/examples/periodic-heat/evidence/new-session" --require-verified
```

Only the final command's zero exit establishes local paired acceptance. Running
the commands does not create an independent reviewer or dispatch an LLM. See
[EVIDENCE.md](EVIDENCE.md) and [report.html](report.html) for this completed trial's
actual observations and limits. Required environment versions are recorded in
[environment.json](environment.json); other environments need fresh verification.

For any later change, update the affected requirements/test mapping, retain known
regressions, review the numerical criteria, and execute the required commands.
Reconcile every collected and executed ID with the frozen list in
[TEST_DESIGN.md](TEST_DESIGN.md), allowing no missing, skipped or expected-failing
required test. Verify the printed import origin and compare candidate hashes
before and after checks. Obtain current independent scientific review and pass
the bounded coordinator assessment before claiming project checks passed.

## Builder evidence and limits

`evidence/builder/red.log` and `red.xml` retain the tests-first missing-module
failure (exit 2). `green-1.log` records the first implemented passing run. Initial
lint and formatting failures are retained separately from the explicit formatting
repair and final passing reports. `tests.xml`, `tests.log`, `collection.txt`,
`coverage.json`, `lint.log`, `format.log`, and `mypy.log` hold native results.
The host retains command receipts and complete final candidate evidence.

Coverage measures the imported model and real CSV operations in the test process.
The CLI is tested in real child processes with 10-second timeouts; its argument
parsing and `__main__` lines are not measured by the parent coverage process.
The remaining missing coverage is exactly those CLI lines and entry branch.
Strict mypy checks all model function bodies with no suppressions, ignored
imports or `Any` annotations. Tests and independent audit tooling are outside
that type claim. Ruff checks the model, developer tests and audit tests, with separate
formatting assessment and no automatic fixes. There are no runtime dependencies,
external services, network actions, empirical datasets or stochastic claims.
