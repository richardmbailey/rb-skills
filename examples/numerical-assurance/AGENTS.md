# Completion for this example

Use the saved `./run_tests.sh` command for ordinary, scientific, plan-based and
direct changes. Set `RB_TEST_PYTHON` to the intended environment's Python when
needed. Do not replace the suite on routine implementation changes.

Update REQUIREMENTS.md and the change-impact mapping when behaviours change.
Before claiming a change verified, run required tests on the final candidate,
check exact test IDs/import origins and inspect retained failures and gaps.
For scientific changes, obtain independent reference checks and review. Run
`python -m tools.run_mutations --output artifacts/mutations/UNIQUE_ID` when
changing the model or assertions; update mutation anchors deliberately if source
structure changes, without weakening the six intended fault classes.

The suite's local success means its listed checks passed. Full skill qualification
also needs the normalized evidence/report checks and independent review described
by the skill. Missing required evidence remains incomplete. These are cooperative
local controls, not protected CI or proof of empirical scientific validity.
