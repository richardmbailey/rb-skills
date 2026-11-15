"""Independent cross-record expectations from public O01-O12 cases.

The helper only writes synthetic artifacts. Expected outcomes are literal;
production predicates or aggregators never calculate the expected answers.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from rb_test_suite.policy import exit_code
from rb_test_suite.validation import validate_run
from test_contracts import fixture


def freeze(root, evidence, plan):
    raw = json.dumps(plan).encode()
    path = plan['plan_id'] + '.json'
    (root / path).write_bytes(raw)
    record = {'id': plan['plan_id'], 'path': path, 'sha256': hashlib.sha256(raw).hexdigest(),
              'bytes': len(raw), 'media_type': 'application/json', 'sensitivity': 'ordinary',
              'redacted': False, 'access': 'local'}
    evidence['plans'] = [p for p in evidence['plans'] if p['id'] != plan['plan_id']] + [record]


def fail(result):
    result.update(assessment='FAILED', reason='Independent defective fixture.')
    result['criteria'][0].update(observed=False, outcome='violated')
    result['counts'].update(passed=0, failed=1)
    result['receipt']['exit_code'] = 1


class CrossRecordTable(unittest.TestCase):
    def test_required_outcome_table(self):
        cases = [('healthy', 'ACCEPTED', 0),
                 ('omitted', 'INSUFFICIENT_EVIDENCE', 2),
                 ('deep_omitted', 'INSUFFICIENT_EVIDENCE', 2),
                 ('required_failure', 'REJECTED', 1),
                 ('failure_and_gap', 'REJECTED', 1),
                 ('blocked', 'INSUFFICIENT_EVIDENCE', 2),
                 ('timeout', 'INSUFFICIENT_EVIDENCE', 2),
                 ('timeout_with_failure', 'REJECTED', 1),
                 ('cancelled_with_failure', 'REJECTED', 130)]
        for case, outcome, expected_exit in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                plan, evidence = fixture(root)
                result = evidence['results'][0]
                if case in ('omitted', 'deep_omitted'):
                    evidence['results'] = []
                    if case == 'deep_omitted':
                        plan['profile'] = 'deep'
                        evidence['profile'] = 'quick'
                        freeze(root, evidence, plan)
                if case in ('required_failure', 'failure_and_gap', 'timeout_with_failure',
                            'cancelled_with_failure'):
                    fail(result)
                if case == 'failure_and_gap':
                    evidence['change_impact']['status'] = 'pending'
                if case == 'blocked':
                    result.update(execution='blocked', assessment='BLOCKED', receipt=None,
                                  criteria=[], counts=None)
                if case in ('timeout', 'timeout_with_failure'):
                    result['execution'] = 'timed_out'
                    result['receipt'].update(termination='timeout', exit_code=None)
                    if case == 'timeout':
                        result.update(assessment='REQUIRES_REVIEW', criteria=[], counts=None)
                if case == 'cancelled_with_failure':
                    evidence['state'] = 'cancelled'
                evaluated = validate_run(evidence, [plan], root)
                self.assertEqual(evaluated['gate']['outcome'], outcome)
                self.assertEqual(exit_code(evaluated['gate'],
                                           cancelled=case == 'cancelled_with_failure'), expected_exit)
                self.assertEqual(evaluated['adoption']['completion'],
                                 'verified' if outcome == 'ACCEPTED' else 'incomplete')

    def test_optional_failure_stays_visible_without_failing_required_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, evidence = fixture(root)
            optional = copy.deepcopy(plan)
            optional.update(plan_id='plan2', module_id='functional.optional',
                            capability_id='functional', required=False,
                            requirement_ids=['optional_behaviour'])
            optional['criteria'][0].update(id='c_optional', requirement_id='optional_behaviour')
            result = copy.deepcopy(evidence['results'][0])
            result.update(plan_id='plan2', module_id='functional.optional')
            result['receipt']['id'] = 'receipt2'
            result['criteria'][0]['criterion_id'] = 'c_optional'
            fail(result)
            evidence['results'].append(result)
            cap = next(c for c in evidence['capabilities'] if c['id'] == 'functional')
            cap.update(disposition='selected', required=False,
                       module_ids=['functional.optional'], assessment='FAILED')
            freeze(root, evidence, optional)
            evaluated = validate_run(evidence, [plan, optional], root)
            self.assertEqual(evaluated['gate']['outcome'], 'ACCEPTED')
            self.assertEqual(evaluated['results'][1]['assessment'], 'FAILED')
            self.assertEqual(next(c for c in evaluated['capabilities']
                                  if c['id'] == 'functional')['assessment'], 'FAILED')

    def test_later_success_cannot_erase_earlier_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, evidence = fixture(root)
            later = copy.deepcopy(evidence['results'][0])
            later.update(attempt=2)
            later['receipt']['id'] = 'receipt2'
            fail(evidence['results'][0])
            evidence['results'].append(later)
            evaluated = validate_run(evidence, [plan], root)
            self.assertEqual(evaluated['gate']['outcome'], 'REJECTED')
            self.assertEqual([r['assessment'] for r in evaluated['results']], ['FAILED', 'PASSED'])

    def test_blocking_finding_rejects_passing_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan, evidence = fixture(root)
            evidence['findings'].append({'id': 'finding1', 'severity': 'high',
                'claim': 'Independent reproducer shows wrong output units.',
                'requirement_ids': ['mass_transfer'], 'module_ids': ['unit.transfer'],
                'artifact_ids': ['a1'], 'remediation': 'Repair units and rerun.',
                'blocking': True, 'resolution': 'open', 'resolution_artifact_ids': []})
            evaluated = validate_run(evidence, [plan], root)
            self.assertEqual(evaluated['gate']['outcome'], 'REJECTED')
            self.assertEqual(evaluated['gate']['blocking_finding_ids'], ['finding1'])


if __name__ == '__main__':
    unittest.main()
