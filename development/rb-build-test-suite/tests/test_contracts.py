"""Contract boundary fixtures; synthetic records do not claim product execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from rb_test_suite.models import schemas
from rb_test_suite.validation import (ContractError, parse_json, parse_yaml, parse_xml,
                                      validate_record, validate_run, contained_path)
from rb_test_suite.policy import evaluate_criterion, exit_code

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
_spec = importlib.util.spec_from_file_location('draft_contract_fixtures', ROOT / 'docs/rb-build-test-suite-specification/checks/test_schemas.py')
_draft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_draft)


def fixture(root):
    plan, evidence, report = _draft.fixture()
    evidence['capabilities'][-1]['required'] = False
    evidence['artifacts'] = []
    evidence['plans'] = []
    def artifact(ident, payload, json_data=False):
        raw = json.dumps(payload).encode() if json_data else payload.encode()
        path = root / (ident + ('.json' if json_data else '.txt'))
        path.write_bytes(raw)
        record = {'id': ident, 'path': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'media_type': 'application/json' if json_data else 'text/plain', 'bytes': len(raw),
                  'sensitivity': 'ordinary', 'redacted': False, 'access': 'local'}
        (evidence['plans'] if ident == 'plan1' else evidence['artifacts']).append(record)
    for ident in ('a1', 'instructions1', 'impact-review1'):
        artifact(ident, 'Synthetic contract fixture: ' + ident)
    artifact('inventory1', {'schema_version': '1.0.0', 'baseline_digest': None, 'candidate_digest': _draft.H,
                            'changes': [dict(evidence['change_impact']['changes'][0], before_digest=None, after_digest=_draft.H)]}, True)
    artifact('origins1', {'schema_version': '1.0.0', 'source_digest': _draft.H,
                         'distribution_digest': None, 'config_digest': _draft.H,
                         'environment_digest': _draft.H, 'build_tool': None,
                         'origins': evidence['results'][0]['receipt']['execution_evidence']['first_party_origins']}, True)
    artifact('plan1', plan, True)
    return plan, evidence


class ParserCases(unittest.TestCase):
    def test_json_yaml_duplicate_nonfinite_unknown(self):
        for parser, payload in [(parse_json, '{"x":1,"x":2}'), (parse_json, '{"x":NaN}'),
                                (parse_json, '{"x":1e999}'), (parse_yaml, 'x: 1\nx: 2'),
                                (parse_yaml, 'x: .inf'), (parse_yaml, 'x: &a [1]\ny: *a'),
                                (parse_yaml, 'x: !!python/object:example {}')]:
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                parser(payload)
        self.assertEqual(parse_yaml('x: 1'), {'x': 1})
        self.assertEqual(parse_json('{"x":true}'), {'x': True})

    def test_size_and_depth_limits(self):
        for parser in (parse_json, parse_yaml, parse_xml):
            with self.assertRaises(ContractError):
                parser('x' * 33, max_bytes=32)
        with self.assertRaises(ContractError):
            parse_json('{"x":' + '[' * 70 + '0' + ']' * 70 + '}')

    def test_xml(self):
        self.assertEqual(parse_xml('<testsuite tests="1"/>').tag, 'testsuite')
        for text in ('<!DOCTYPE x [<!ENTITY a "unsafe">]><x>&a;</x>',
                     '<!DOCTYPE x SYSTEM "file:///etc/passwd"><x/>', '<x>'):
            with self.assertRaises(ContractError):
                parse_xml(text)


class ContractCases(unittest.TestCase):
    def test_draft_structural_compatibility(self):
        for kind, record in zip(('module-plan', 'evidence', 'report'), _draft.fixture()):
            validate_record(kind, record)

    def test_generated_schema_drift(self):
        for name, schema in schemas().items():
            self.assertEqual(json.loads((PACKAGE / 'schemas' / name).read_text()), schema)

    def test_catalogue(self):
        data = parse_yaml((PACKAGE / 'references/catalogue.yaml').read_bytes())
        validate_record('catalogue', data)
        data['entries'][1]['id'] = data['entries'][0]['id']
        with self.assertRaises(ContractError):
            validate_record('catalogue', data)

    def test_invalid_shapes_and_dates(self):
        for field, value in [('schema_version', '2.0.0'), ('started_at', '2026-02-30T00:00:00Z'),
                             ('started_at', '2026-11-15T12:00:00+00:00'), ('unknown', True)]:
            evidence = _draft.fixture()[1]
            evidence[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_record('evidence', evidence)
        plan = _draft.fixture()[0]
        plan['limits']['timeout_seconds'] = True
        with self.assertRaises(ContractError):
            validate_record('module-plan', plan)

    def test_safe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'escape').symlink_to('/tmp')
            for path in ('../escape', '/absolute', 'escape/file'):
                with self.subTest(path=path), self.assertRaises(ContractError):
                    contained_path(root, path)

    def test_predicate_validation(self):
        c = _draft.fixture()[0]['criteria'][0]
        for update in ({'expected': 1}, {'type': 'metric'}, {'predicate': 'between', 'type': 'metric',
                                                              'expected': {'lower': 2, 'upper': 1}}):
            with self.assertRaises(ContractError):
                evaluate_criterion(dict(c, **update), True)
        metric = dict(c, type='metric', predicate='between', expected={'lower': 1, 'upper': 2}, unit='kg')
        self.assertEqual(evaluate_criterion(metric, {'observed': 1, 'unit': 'kg'}), 'satisfied')
        self.assertEqual(evaluate_criterion(metric, {'observed': 1, 'unit': 'g'}), 'unknown')

    def test_local_complete_fixture_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            result = validate_run(e, [p], Path(tmp))
            self.assertEqual(result['gate']['outcome'], 'ACCEPTED')
            self.assertEqual(result['adoption']['completion'], 'verified')
            self.assertEqual(e['gate']['outcome'], 'INSUFFICIENT_EVIDENCE')

    def test_failure_survives_timeout_and_other_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            r = e['results'][0]
            r.update(execution='timed_out', assessment='FAILED')
            r['criteria'][0].update(observed=False, outcome='violated')
            e['change_impact']['status'] = 'pending'
            result = validate_run(e, [p], Path(tmp))
            self.assertEqual(result['gate']['outcome'], 'REJECTED')
            self.assertTrue(result['gate']['required_gaps'])
            self.assertEqual(exit_code(result['gate']), 1)

    def test_missing_artifact_is_gap_tampering_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p, e = fixture(root)
            (root / 'a1.txt').unlink()
            self.assertEqual(validate_run(e, [p], root)['gate']['outcome'], 'INSUFFICIENT_EVIDENCE')
            (root / 'a1.txt').write_text('tampered')
            with self.assertRaises(ContractError):
                validate_run(e, [p], root)

    def test_bad_references_and_cycles(self):
        for mutation in ('cycle', 'criterion', 'module', 'duplicate'):
            with tempfile.TemporaryDirectory() as tmp:
                p, e = fixture(Path(tmp))
                if mutation == 'cycle':
                    p['depends_on'] = [p['module_id']]
                elif mutation == 'criterion':
                    e['results'][0]['criteria'][0]['criterion_id'] = 'missing'
                elif mutation == 'module':
                    e['results'][0]['module_id'] = 'missing'
                else:
                    e['results'].append(copy.deepcopy(e['results'][0]))
                with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                    validate_run(e, [p], Path(tmp))

    def test_impact_and_identity_gaps(self):
        for mutation in ('missing_path', 'stale', 'unresolved', 'selection', 'origin'):
            with tempfile.TemporaryDirectory() as tmp:
                p, e = fixture(Path(tmp))
                if mutation == 'missing_path':
                    e['change_impact']['changes'].append({'path': 'src/new.py', 'kind': 'source', 'change': 'added', 'previous_path': None})
                elif mutation == 'stale':
                    e['adoption']['candidate_digest'] = 'b' * 64
                elif mutation == 'unresolved':
                    e['change_impact']['behaviours'][0]['disposition'] = 'unresolved'
                    e['change_impact']['unresolved_behavior_ids'] = ['transfer']
                elif mutation == 'selection':
                    e['results'][0]['receipt']['execution_evidence']['executed_test_ids'] = ['different_same_count']
                elif mutation == 'origin':
                    e['results'][0]['receipt']['execution_evidence']['first_party_origins'][0]['sha256'] = 'b' * 64
                with self.subTest(mutation=mutation):
                    self.assertEqual(validate_run(e, [p], Path(tmp))['gate']['outcome'], 'INSUFFICIENT_EVIDENCE')

    def test_static_scope_policy_and_unauthorised_edit(self):
        for defect in (None, 'omitted_path', 'unexpected_edit', 'unapproved_limitation'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                p, e = fixture(root)
                p['static_contract'] = {'tool': 'fixture-static', 'claim': 'Fixture scope',
                    'intended_paths': ['src/transfer.py'], 'policy_artifact_id': 'staticpolicy',
                    'config_artifact_ids': [], 'assessment_only': True}
                r = e['results'][0]['receipt']
                r['static_evidence'] = {'effective_config_artifact_ids': ['effectiveconfig'],
                    'checked_paths': ['src/transfer.py'], 'excluded': [], 'unchecked': [], 'suppressions': [],
                    'before_digest': _draft.H, 'after_digest': _draft.H, 'assessment_only': True}
                payloads = {'plan1': p, 'staticpolicy': {'schema_version': '1.0.0',
                    'policy_digest': _draft.H, 'allowed_limitations': []}, 'effectiveconfig': {'fixture': True}}
                for ident, payload in payloads.items():
                    raw = json.dumps(payload).encode()
                    (root / (ident + '.json')).write_bytes(raw)
                    collection = e['plans'] if ident == 'plan1' else e['artifacts']
                    if ident == 'plan1':
                        record = collection[0]
                    else:
                        record = dict(e['artifacts'][0], id=ident, path=ident + '.json', media_type='application/json')
                        collection.append(record)
                    record.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                if defect == 'omitted_path':
                    r['static_evidence']['checked_paths'] = []
                elif defect == 'unexpected_edit':
                    r['static_evidence']['after_digest'] = 'b' * 64
                elif defect == 'unapproved_limitation':
                    r['static_evidence']['unchecked'] = [{'path': 'src/transfer.py', 'region': 'f',
                        'reason': 'Body unchecked', 'policy_ref': 'staticpolicy'}]
                with self.subTest(defect=defect):
                    self.assertEqual(validate_run(e, [p], root)['gate']['outcome'],
                                     'ACCEPTED' if defect is None else 'INSUFFICIENT_EVIDENCE')

    def test_failed_tool_count_overrides_passing_assertion(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            self.assertEqual(validate_run(e, [p], Path(tmp))['gate']['outcome'], 'ACCEPTED')
            e['results'][0]['counts'].update(passed=0, failed=1)
            result = validate_run(e, [p], Path(tmp))
            self.assertEqual(result['gate']['outcome'], 'REJECTED')
            self.assertEqual(result['results'][0]['assessment'], 'FAILED')

    def test_required_inputs_must_be_registered_available_and_consistent(self):
        for defect in (None, 'missing', 'different_hash', 'duplicate'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                p, e = fixture(root)
                item = copy.deepcopy(e['artifacts'][0])
                if defect == 'missing':
                    item.update(id='missing-input', path='absent.txt')
                elif defect == 'different_hash':
                    item['sha256'] = 'b' * 64
                p['inputs'] = [item]
                if defect == 'duplicate':
                    p['inputs'].append(copy.deepcopy(item))
                raw = json.dumps(p).encode()
                (root / 'plan1.json').write_bytes(raw)
                e['plans'][0].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                with self.subTest(defect=defect):
                    if defect in ('different_hash', 'duplicate'):
                        with self.assertRaises(ContractError):
                            validate_run(e, [p], root)
                    else:
                        self.assertEqual(validate_run(e, [p], root)['gate']['outcome'],
                                         'ACCEPTED' if defect is None else 'INSUFFICIENT_EVIDENCE')

    def test_gate_policy_identity_and_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            result = validate_run(e, [p], Path(tmp))
            self.assertEqual(result['evaluation']['policy_digest'], e['provenance']['policy_digest'])
            expected = hashlib.sha256(json.dumps(e, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(result['evaluation']['source_evidence_digest'], expected)
            self.assertEqual(result['evaluation']['evaluator_version'], '0.1.0')
            self.assertNotIn('evaluation', e)
            e['gate']['policy_digest'] = 'b' * 64
            with self.assertRaises(ContractError):
                validate_run(e, [p], Path(tmp))

    def test_revalidation_preserves_derivation_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p, e = fixture(root)
            first = validate_run(e, [p], root)
            saved = copy.deepcopy(first)
            self.assertEqual(validate_run(first, [p], root), first)
            self.assertEqual(first, saved)
            for mutation in ('digest', 'version', 'assessment', 'missing_artifact'):
                altered = copy.deepcopy(first)
                if mutation == 'digest':
                    altered['evaluation']['assessed_evidence_digest'] = 'b' * 64
                elif mutation == 'version':
                    altered['evaluation']['evaluator_version'] = '2.0.0'
                elif mutation == 'assessment':
                    altered['results'][0]['reason'] = 'Changed after evaluation'
                else:
                    (root / 'a1.txt').unlink()
                with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                    validate_run(altered, [p], root)

    def test_unbound_authoring_config(self):
        p, e, _ = _draft.fixture()
        excluded = {'schema_version', 'plan_id', 'run_id', 'candidate_digest', 'policy_digest',
                    'inputs', 'execution_contract', 'static_contract', 'evidence_import'}
        request = {k: v for k, v in p.items() if k not in excluded}
        request.update(input_paths=['src/transfer.py'], execution_request={
            'mode': 'checkout', 'distribution_path': None,
            'first_party_paths': {'transfer': 'src/transfer.py'},
            'expected_test_ids': ['tests/unit/test_transfer.py::test_known']},
            static_request=None, evidence_import_path=None)
        config = {'schema_version': '1.0.0', 'project_root': '.', 'focus': 'development',
                  'default_profile': 'standard', 'environment_command': ['python'],
                  'lock_digest': _draft.H, 'supported_os': ['fixture'], 'runner_version': '0.1.0',
                  'profiles': [{'name': 'standard', 'capability_ids': ['unit'], 'limits': p['limits']}],
                  'requirements': [{'path': 'requirements.md', 'sha256': _draft.H,
                                    'criterion_ids': ['c1'], 'authorised_owner': 'fixture-owner'}],
                  'modules': [request], 'capabilities': e['capabilities'], 'references': [],
                  'operations': ['imports/observation.json'],
                  'adoption': {'runner_argv': ['./run_tests.sh'], 'instruction_paths': ['AGENTS.md'],
                               'supported_workflows': ['direct_completion'], 'enforcement': 'cooperative'},
                  'change_impact_path': '.test-suite/control/impact.json',
                  'reporting': {'retention_days': 30, 'redact': True, 'include_raw_artifacts': True,
                                'output_path': '.test-suite/reports'}}
        validate_record('config', config)
        self.assertNotIn('candidate_digest', request)
        for mutate in ('bound', 'escape', 'missing_command'):
            altered = copy.deepcopy(config)
            if mutate == 'bound':
                altered['modules'][0]['candidate_digest'] = _draft.H
            elif mutate == 'escape':
                altered['modules'][0]['execution_request']['first_party_paths']['transfer'] = '../outside.py'
            else:
                altered['modules'][0]['command'] = None
            with self.subTest(mutate=mutate), self.assertRaises(ContractError):
                validate_record('config', altered)

    def test_empty_acceptance_policy_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            p['required'] = False
            e['capabilities'][0]['required'] = False
            with self.assertRaises(ContractError):
                validate_run(e, [p], Path(tmp))

    def test_supplied_plan_must_match_frozen_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            p['criteria'][0]['justification'] = 'Changed frozen criterion.'
            with self.assertRaises(ContractError):
                validate_run(e, [p], Path(tmp))

    def test_documentation_exclusion_does_not_require_new_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            p, e = fixture(Path(tmp))
            e['change_impact']['changes'][0].update(path='docs/guide.md', kind='documentation', change='renamed', previous_path='guide.md')
            e['change_impact']['behaviours'][0].update(changed_paths=['docs/guide.md'], disposition='excluded', module_ids=[], requirement_ids=[])
            inventory = {'schema_version': '1.0.0', 'baseline_digest': None, 'candidate_digest': _draft.H,
                         'changes': [dict(e['change_impact']['changes'][0], before_digest=_draft.H, after_digest=_draft.H)]}
            raw = json.dumps(inventory).encode()
            (Path(tmp) / 'inventory1.json').write_bytes(raw)
            metadata = next(a for a in e['artifacts'] if a['id'] == 'inventory1')
            metadata.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            self.assertEqual(validate_run(e, [p], Path(tmp))['gate']['outcome'], 'ACCEPTED')


if __name__ == '__main__':
    unittest.main()
