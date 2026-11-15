# A numerical model used to try the testing skill

`model.py` transfers mass between two stores with explicit Euler integration.
It is a short standalone script using only Python's standard library. The
analytical exponential solution provides an independent numerical reference.
See [the requirements](REQUIREMENTS.md) for equations, units and justified bounds.

Run a simulation:

```bash
python3 model.py --output result.csv
```

Create a development environment and run the saved suite:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
RB_TEST_PYTHON="$PWD/.venv/bin/python" ./run_tests.sh
.venv/bin/python -m tools.run_mutations --output artifacts/mutations/new-trial
```

Output locations must be new, so failed evidence is not overwritten. The wrapper
also works when invoked from another directory or a project path containing spaces.
The trial was run using an existing disposable environment; fresh environment
installation and other Python/OS versions are not claimed as tested.

The suite combines behavioural and independent numerical tests, 150 deterministic
Hypothesis examples, read-only Ruff lint and formatting, strict mypy on the model,
and branch coverage. Six deliberately wrong model copies test whether meaningful
assertions detect plausible scientific mistakes. Additional controls check that
linting, typing and formatting failures are propagated. No mutant replaces the
working model.

The independent reviewer designed tests before reading the implementation, then
found two floating-point boundary defects missed by the initial tests. Both were
recorded, fixed and protected by regression tests. See
[the independent review](independent-review.md) for provenance and limits.

The project's [43 capability dispositions](capabilities.json) distinguish selected
checks from irrelevant operational features and deferred work. See
[change impact](change-impact.json) and [adoption](adoption.json) for the local
completion policy. Raw execution results, the fault matrix, normalized evidence
and the human assessment are retained under `artifacts/`; generated evidence is
ignored by Git to keep temporary paths and machine data local.

The `contracts/` directory contains unchanged copies of the skill's reference
schemas, included so the example can be moved without depending on this repository.
Package observations with `python -m tools.package_evidence --run RUN_DIRECTORY
--mutations MUTATIONS_DIRECTORY --output NEW_OUTPUT_DIRECTORY`. Exit 2 explicitly
means the complete skill qualification remains incomplete; it does not erase
passing numerical checks or relabel missing evidence as a pass.

This is one real project trial, not a controlled measurement of the skill's
benefit across projects. Passing numerical tests does not validate a real-world
physical model. A short local harness does not qualify the full proposed runner,
protected CI, all 43 capabilities or every HTML interaction.
