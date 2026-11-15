# Independent scientific acceptance review

The tests were designed directly from REQUIREMENTS.md before reading or importing the candidate model or reading any other tests. Context consisted of the parent task, repository AGENTS.md and this example's REQUIREMENTS.md. No previous numerical examples, prior trial outcomes, or test-suite specification material were read. This is context separation, not filesystem write isolation.

## Frozen design

The exact reference uses A0=4 kg, B0=3 kg, k=1/day and steps of 0.5, 0.5 and 0.25 days. Simultaneous transfers of 2, 1 and 0.25 kg give states (4,3), (2,5), (1,6), (0.75,6.25). All are binary-exact numbers. This exercises transfer direction, receiving store, rate, shortened final step, conversion, immutability and real CLI output independently of candidate calculations.

The continuous oracle is 1000 exp(-2) kg. Forward Euler must underpredict A and refinement from 0.2 to 0.1 to 0.05 days must give the specified error ratios. The default CLI oracle is the independently derived geometric sequence 1000*(0.98**n), with B fixed by conservation. The continuous error allowance and trajectory conservation allowance are those fixed in the requirements. CLI comparisons permit floating-point rounding (1e-9 kg and 1e-12 days/tonnes).

Boundary coverage includes zero rate, zero duration, zero mass, the positivity equality, small and large bounded masses, every non-finite argument, every signed-domain violation, total-mass overflow, step-count quotient overflow, the exact 100000-step limit and a fractional step beyond it. Real subprocess CLI tests cover defaults, all parameter flags, invalid input before output creation and output IO failure. Each subprocess has a 15-second bound.

No candidate execution or inspection has occurred at design freeze. Results and review findings will be appended after parent authorization. The independent suite does not alone satisfy required Hypothesis, lint, type, branch inspection or mutant evidence; those remain separate development obligations.

## Initial execution and genuine finding

After parent authorization, the original frozen design passed: `45 passed in 1.32s`. Frozen source SHA256: `ff3333a8fb4702cdded37e356249d929988f768f17b18077f346dfaef65e7692`.

Candidate inspection then exposed inconsistent rounding between exact Fraction step counting and floating-point step times. `simulate(4,3,1,1,1/3)` produced times `[0, 0.3333333333333333, 0.6666666666666666, 1.0, 1]`, including a zero-length final step. A separately labelled post-inspection regression was added. The pre-fix run returned exit 1: `1 failed, 45 passed in 1.37s`. Failure was `test_no_duplicate_endpoint_when_float_grid_rounds_to_duration`, on `assert all(left.time_days < right.time_days for left, right in zip(samples, samples[1:]))`, with `assert False`. This is a behavioural failure, not an import error or timeout. The implementation agent and parent were notified before any repair.

Commands used the dedicated validation Python and fresh, separately owned temporary directories for attempts 1 and 2, with `python -m pytest examples/numerical-assurance-repeat-2/tests/test_independent.py -q --basetemp=...`.

## Repair verification and final test freeze

The implementation agent added a stop when the emitted timestamp reaches the requested duration. Inspection confirms the change addresses the reproduced duplicate endpoint. The repaired candidate SHA256 is `29027f941b2f6ac847edf26f3ec8719ae9fc78f7044ce8519936e3a2885539ef`. Independent rerun with a fresh owned temporary directory for attempt 3 returned exit 0: `46 passed in 0.87s`, including the previously failing regression.

Root Ruff initially found import ordering and adjacent-pair iteration style issues in the independent tests. Formatting and equivalent `itertools.pairwise` changes addressed them without changing numerical criteria. Final `ruff check` passed and `ruff format` reported the file unchanged. The final test file, including the explicitly labelled post-inspection regression, is frozen at SHA256 `2885cac9a9b55d8db3673896371682abc57d05f8086e3f130f82ed152858282a`.

The scientific equations are analytical teaching references, not empirical validation. No common comparison candidate or prior trial result has been inspected. These results establish the stated sampled acceptance checks, not exhaustive floating-point correctness. The original frozen suite did not detect the duplicate endpoint; it was found during source review and is therefore reported separately, not counted as a success of blind test design. Required broader development checks and mutation results are owned by the implementation agent and parent, rather than claimed here as independently rerun.
