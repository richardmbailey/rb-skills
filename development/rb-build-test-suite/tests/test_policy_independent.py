"""Expected outcomes chosen from the public contract before policy implementation.

These tests exercise deterministic decisions, not artifact authentication or
scientific validity. They do not call production code to calculate expectations.
"""
import math
import unittest

from rb_test_suite.policy import evaluate_criterion, exit_code


def criterion(predicate, expected):
    return {'id': 'criterion1', 'requirement_id': 'requirement1',
            'type': 'assertion' if predicate in ('equals', 'is_true') else 'metric',
            'predicate': predicate, 'expected': expected, 'unit': None,
            'justification': 'Independent boundary fixture.'}


class IndependentPolicyCases(unittest.TestCase):
    def test_inclusive_numeric_boundaries(self):
        cases = [('at_most', 2, 2, 'satisfied'),
                 ('at_most', 2, 2.01, 'violated'),
                 ('at_least', 2, 2, 'satisfied'),
                 ('at_least', 2, 1.99, 'violated'),
                 ('equals', 'kg', 'kg', 'satisfied'),
                 ('equals', 'kg', 'tonnes', 'violated'),
                 ('is_true', True, True, 'satisfied'),
                 ('is_true', True, False, 'violated')]
        for predicate, expected, actual, outcome in cases:
            with self.subTest(predicate=predicate, actual=actual):
                self.assertEqual(evaluate_criterion(criterion(predicate, expected), actual), outcome)

    def test_missing_evidence_cannot_satisfy_assertion(self):
        self.assertEqual(evaluate_criterion(criterion('is_true', True), None), 'unknown')

    def test_boolean_cannot_equal_one(self):
        try:
            outcome = evaluate_criterion(criterion('equals', 1), True)
        except ValueError:
            return  # Strict input rejection is also permitted by the contract.
        self.assertNotEqual(outcome, 'satisfied')

    def test_nonfinite_cannot_satisfy_metric(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                try:
                    outcome = evaluate_criterion(criterion('at_least', 0), value)
                except ValueError:
                    continue
                self.assertNotEqual(outcome, 'satisfied')

    def test_exit_precedence_preserves_failure(self):
        for outcome, expected in [('ACCEPTED', 0), ('REJECTED', 1),
                                  ('INSUFFICIENT_EVIDENCE', 2), ('NOT_EVALUATED', 2)]:
            gate = {'outcome': outcome, 'policy_digest': 'a' * 64,
                    'required_failures': [], 'required_gaps': [],
                    'blocking_finding_ids': [], 'rationale': 'Independent fixture.'}
            with self.subTest(outcome=outcome):
                self.assertEqual(exit_code(gate), expected)
                self.assertEqual(exit_code(gate, runner_error=True), 3)
                self.assertEqual(exit_code(gate, runner_error=True, cancelled=True), 130)


if __name__ == '__main__':
    unittest.main()
