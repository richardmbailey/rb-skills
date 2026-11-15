"""Packaged reference-schema checks; these do not implement or validate a runner.

Run with jsonschema[format-nongpl] installed:
python -m unittest discover -s docs/rb-build-test-suite-specification/checks -v
"""
import copy
import json
import os
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(os.environ.get('RB_TEST_SUITE_PACKAGE_ROOT',
                              ROOT.parents[1] / 'rb-build-test-suite'))
SCHEMAS = {p.name: json.loads(p.read_text()) for p in (PACKAGE / 'schemas').glob('*.json')}
REGISTRY = Registry().with_resources(
    (s['$id'], Resource.from_contents(s)) for s in SCHEMAS.values()
)
DEFS = SCHEMAS['contracts.schema.json']['$defs']
IDS = DEFS['ModulePlan']['properties']['capability_id']['enum']
H = 'a' * 64
T = '2026-11-15T12:00:00Z'


def validator(name):
    return Draft202012Validator(SCHEMAS[name + '.schema.json'],
                                registry=REGISTRY, format_checker=FormatChecker())


def fixture():
    artifact = {'id': 'a1', 'path': 'raw/unit.xml', 'sha256': H,
                'media_type': 'application/xml', 'bytes': 100,
                'sensitivity': 'ordinary', 'redacted': False, 'access': 'local'}
    command = {'argv': ['python', '-m', 'pytest', 'tests/unit'],
               'cwd': '.', 'environment_names': []}
    criterion = {'id': 'c1', 'requirement_id': 'mass_transfer', 'type': 'assertion',
                 'predicate': 'is_true', 'expected': True, 'unit': None,
                 'justification': 'Independent hand calculation for a known transfer.'}
    plan = {'schema_version': '1.0.0', 'plan_id': 'plan1', 'run_id': 'run1',
            'module_id': 'unit.transfer', 'capability_id': 'unit', 'kind': 'executable',
            'adapter': {'name': 'pytest', 'version': 'example'},
            'candidate_digest': H, 'policy_digest': H,
            'requirement_ids': ['mass_transfer'], 'subtypes': ['analytical_reference'],
            'required': True, 'profile': 'standard', 'inputs': [], 'depends_on': [],
            'command': command, 'target': {'environment': 'sandbox', 'identity': 'fixture',
                                         'config_digest': H},
            'effects': ['local_read', 'disposable_write'], 'authority_refs': ['fixture-authority'],
            'limits': {'timeout_seconds': 30, 'termination_grace_seconds': 2,
                       'max_output_bytes': 100000, 'max_concurrency': 1,
                       'max_model_calls': 0, 'max_tool_calls': 1, 'max_spend': None},
            'criteria': [criterion], 'evidence_import': None}
    tool = {'name': 'pytest', 'version': 'example', 'parser_version': 'example'}
    receipt = {'id': 'receipt1', 'producer': 'fixture-runner', 'authentication': 'local',
               'started_at': T, 'finished_at': T, 'duration_seconds': 0,
               'exit_code': 0, 'tool': tool, 'command': command, 'termination': 'normal',
               'artifact_ids': ['a1'], 'authority_refs': ['fixture-authority']}
    result = {'module_id': 'unit.transfer', 'plan_id': 'plan1', 'attempt': 1,
              'execution': 'completed', 'assessment': 'PASSED', 'reason': 'Known case satisfied.',
              'receipt': receipt, 'criteria': [{'criterion_id': 'c1', 'outcome': 'satisfied',
               'observed': True, 'unit': None, 'artifact_ids': ['a1'], 'rationale': 'Fixture only.'}],
              'counts': {'collected': 1, 'passed': 1, 'failed': 0, 'skipped': 0,
                         'xfailed': 0, 'xpassed': 0, 'errors': 0},
              'artifact_ids': ['a1'], 'reused_from': None}
    capabilities = [{'id': x, 'disposition': 'deferred', 'reason': 'Outside this fixture run.',
                     'required': x == 'independent_verification', 'module_ids': [],
                     'assessment': 'NOT_RUN'} for x in IDS]
    capabilities[0].update(disposition='selected', reason='Known transfer check.',
                           required=True, module_ids=['unit.transfer'], assessment='PASSED')
    provenance = {k: H for k in DEFS['Provenance']['properties']}
    environment = {'os': 'fixture', 'architecture': 'fixture',
                   'runtime_versions': [{'name': 'python', 'version': 'example'}],
                   'lock_digest': H, 'isolation_requested': [], 'isolation_enforced': [],
                   'hardware': None, 'limitations': ['Synthetic schema fixture, never executed.']}
    independence = {'status': 'not_run', 'session_ref': None, 'packet_digest': None,
                    'context_separation': 'None in fixture.', 'write_isolation': 'None in fixture.',
                    'enforcement': 'unavailable', 'oracle_refs': [], 'receipt_artifact_ids': [],
                    'limitations': ['No verifier was invoked.'], 'recommendation': 'unavailable'}
    gate = {'outcome': 'INSUFFICIENT_EVIDENCE', 'policy_digest': H,
            'required_failures': [], 'required_gaps': ['independent_verification'],
            'blocking_finding_ids': [], 'rationale': 'Required independent review absent.'}
    evidence = {'schema_version': '1.0.0', 'run_id': 'run1', 'started_at': T, 'finished_at': T,
                'state': 'finalised', 'focus': 'development', 'profile': 'standard',
                'candidate': {'snapshot_digest': H, 'git_commit': None, 'dirty': None,
                              'scope': ['src/transfer.py'], 'excluded_inputs': []},
                'provenance': provenance, 'environment': environment,
                'capabilities': capabilities, 'plans': [dict(artifact, id='plan1', path='plans/plan1.json',
                                                            media_type='application/json')],
                'results': [result], 'artifacts': [artifact], 'findings': [],
                'independence': independence, 'gate': gate,
                'limitations': ['Synthetic example: no program or agent was executed.']}
    states = DEFS['Summary']['properties']['capability_counts']['properties']
    report = {'schema_version': '1.0.0', 'run_id': 'run1', 'evidence_digest': H, 'rendered_at': T,
              'candidate': evidence['candidate'], 'focus': 'development', 'profile': 'standard',
              'run_started_at': T, 'run_finished_at': T, 'gate': gate,
              'summary': {'capability_counts': {k: sum(c['assessment'] == k for c in capabilities)
                                               for k in states},
                          'logical_checks': 1, 'attempts': 1, 'test_counts': result['counts'],
                          'required_failed': 0, 'optional_failed': 0},
              'sections': [{'id': x, 'title': x, 'availability': 'present', 'explanation': 'Fixture.'}
                           for x in DEFS['Section']['properties']['id']['enum']],
              'capabilities': capabilities,
              'modules': [{'module_id': 'unit.transfer', 'attempt': 1, 'capability_id': 'unit',
                           'required': True, 'tool': tool, 'execution': 'completed',
                           'assessment': 'PASSED', 'duration_seconds': 0, 'reason': 'Fixture.',
                           'criteria': result['criteria'], 'criterion_definitions': [criterion],
                           'artifact_ids': ['a1']}],
              'findings': [], 'scientific_checks': [], 'independence': independence,
              'charts': [], 'provenance': provenance, 'environment': environment,
              'artifact_links': [artifact], 'limitations': evidence['limitations']}
    execution_contract = {'mode': 'checkout', 'source_digest': H,
                          'distribution_digest': None, 'manifest_artifact_ids': ['origins1'],
                          'expected_test_ids': ['tests/unit/test_transfer.py::test_known']}
    execution_evidence = {'mode': 'checkout', 'source_digest': H,
                          'distribution_digest': None, 'manifest_artifact_ids': ['origins1'],
                          'first_party_origins': [{'name': 'transfer', 'path': 'src/transfer.py',
                                                  'sha256': H}],
                          'collected_test_ids': execution_contract['expected_test_ids'][:],
                          'executed_test_ids': execution_contract['expected_test_ids'][:]}
    plan.update(execution_contract=execution_contract, static_contract=None)
    receipt.update(execution_evidence=execution_evidence, static_evidence=None)
    adoption = {'schema_version': '1.0.0', 'candidate_digest': H, 'policy_digest': H,
                'run_id': 'run1', 'instruction_artifact_ids': ['instructions1'],
                'runner_argv': ['./run_tests.sh'],
                'supported_workflows': ['ordinary_implementation', 'direct_completion'],
                'enforcement': 'cooperative', 'protection_receipt_ids': [],
                'completion': 'incomplete', 'required_gap_ids': ['independent_verification']}
    impact = {'schema_version': '1.0.0', 'baseline_digest': None, 'candidate_digest': H,
              'inventory_artifact_id': 'inventory1', 'requirement_inventory_digest': H,
              'status': 'reviewed', 'review_artifact_id': 'impact-review1',
              'changes': [{'path': 'src/transfer.py', 'kind': 'source',
                           'change': 'added', 'previous_path': None}],
              'behaviours': [{'id': 'transfer', 'description': 'Transfer preserves mass.',
                             'changed_paths': ['src/transfer.py'], 'interface_refs': ['transfer'],
                             'requirement_ids': ['mass_transfer'], 'module_ids': ['unit.transfer'],
                             'disposition': 'covered', 'justification': 'Known analytical case.',
                             'scientific_effects': ['implementation'],
                             'review_artifact_id': 'impact-review1'}],
              'unresolved_behavior_ids': []}
    for record in (evidence, report):
        record.update(adoption=copy.deepcopy(adoption), change_impact=copy.deepcopy(impact))
    report['modules'][0].update(execution_contract=execution_contract,
                               execution_evidence=execution_evidence,
                               static_contract=None, static_evidence=None)
    return plan, evidence, report


class SchemaContracts(unittest.TestCase):
    def test_schema_metaschemas(self):
        for name, schema in SCHEMAS.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_all_roots_accept_representative_records(self):
        for name, record in zip(('module-plan', 'evidence', 'report'), fixture()):
            with self.subTest(schema=name):
                validator(name).validate(record)

    def test_catalogue_matches_exact_schema_order(self):
        text = (PACKAGE / 'references' / 'catalogue.md').read_text()
        entries = re.findall(r'^### (\d+)\. `([^`]+)`', text, flags=re.M)
        self.assertEqual(entries, [(str(i), name) for i, name in enumerate(IDS, 1)])
        self.assertEqual(len(IDS), 43)
        self.assertEqual(len(set(IDS)), 43)

    def test_rejected_contract_shapes(self):
        cases = [
            ('module-plan', ('command',), None),
            ('module-plan', ('capability_id',), 'imaginary_test'),
            ('module-plan', ('limits', 'timeout_seconds'), 0),
            ('module-plan', ('criteria',), []),
            ('module-plan', ('candidate_digest',), 'bad-hash'),
            ('evidence', ('results', 0, 'criteria', 0, 'outcome'), 'unknown'),
            ('evidence', ('results', 0, 'execution'), 'timed_out'),
            ('evidence', ('results', 0, 'receipt'), None),
            ('evidence', ('capabilities', 0, 'disposition'), 'not_applicable'),
            ('evidence', ('gate', 'outcome'), 'ACCEPTED'),
            ('evidence', ('started_at',), 'yesterday'),
            ('evidence', ('started_at',), '2026-02-30T12:00:00Z'),
            ('evidence', ('capabilities',), []),
            ('report', ('summary', 'logical_checks'), -1),
            ('report', ('sections',), []),
            ('report', ('modules', 0, 'criterion_definitions'), []),
            ('report', ('html',), '<script>alert(1)</script>'),
        ]
        names = ('module-plan', 'evidence', 'report')
        for name, path, value in cases:
            with self.subTest(schema=name, path=path):
                record = copy.deepcopy(fixture()[names.index(name)])
                target = record
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertTrue(list(validator(name).iter_errors(record)))

    def test_text_payload_is_data_not_raw_html(self):
        # Structural acceptance of text is deliberate. Browser escaping remains unimplemented.
        report = fixture()[2]
        report['limitations'] = ['</script><img src=x onerror=alert(1)>']
        validator('report').validate(report)

    def test_evidence_import_contracts(self):
        base = fixture()[0]
        base.update(kind='human_review', command=None, execution_contract=None, evidence_import={
            'source_identity': 'fixture-reviewer', 'source_artifact_ids': ['review1'],
            'receipt_artifact_id': 'receipt1', 'expected_candidate_digest': H,
            'expected_policy_digest': H, 'target': base['target'],
            'reviewer_identity': 'reviewer1', 'host_invocation_ref': None,
            'observation': None})
        validator('module-plan').validate(base)
        base['evidence_import']['reviewer_identity'] = None
        self.assertTrue(list(validator('module-plan').iter_errors(base)))
        base['kind'] = 'agent_review'
        self.assertTrue(list(validator('module-plan').iter_errors(base)))
        base['evidence_import']['host_invocation_ref'] = 'host1'
        validator('module-plan').validate(base)
        base['kind'] = 'observation'
        self.assertTrue(list(validator('module-plan').iter_errors(base)))
        base['evidence_import']['observation'] = {
            'window_start': T, 'window_end': T, 'minimum_samples': 1,
            'maximum_age_seconds': 0, 'evaluated_at': T}
        validator('module-plan').validate(base)

    def test_blocked_and_failed_shapes(self):
        evidence = fixture()[1]
        result = evidence['results'][0]
        result.update(execution='blocked', assessment='BLOCKED', receipt=None,
                      criteria=[], counts=None, artifact_ids=[])
        validator('evidence').validate(evidence)
        result.update(execution='completed', assessment='FAILED', receipt=fixture()[1]['results'][0]['receipt'],
                      criteria=[dict(fixture()[1]['results'][0]['criteria'][0], outcome='violated')])
        validator('evidence').validate(evidence)

    def test_unknown_fields_rejected_at_roots(self):
        for name, record in zip(('module-plan', 'evidence', 'report'), fixture()):
            with self.subTest(schema=name):
                record['silently_ignore_required_checks'] = True
                self.assertTrue(list(validator(name).iter_errors(record)))

    def test_acceptance_requires_finalisation(self):
        evidence = fixture()[1]
        evidence['capabilities'][-1]['required'] = False
        evidence['gate'].update(outcome='ACCEPTED', required_gaps=[],
                                rationale='Only the unit claim is required in this fixture.')
        validator('evidence').validate(evidence)
        for state in ('in_progress', 'cancelled', 'interrupted'):
            with self.subTest(state=state):
                evidence['state'] = state
                self.assertTrue(list(validator('evidence').iter_errors(evidence)))


    def test_adoption_completion_and_protection_shapes(self):
        evidence = fixture()[1]
        evidence['adoption'].update(completion='verified', required_gap_ids=[])
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))
        evidence['gate'].update(outcome='ACCEPTED', required_gaps=[])
        validator('evidence').validate(evidence)
        evidence['adoption']['enforcement'] = 'protected_ci_verified'
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))
        evidence['adoption']['protection_receipt_ids'] = ['protection1']
        validator('evidence').validate(evidence)
        # Receipts' truth and cross-record identity are future semantic checks.

    def test_change_impact_review_and_coverage_shapes(self):
        for path, value in [
            (('review_artifact_id',), None),
            (('behaviours', 0, 'module_ids'), []),
            (('behaviours', 0, 'requirement_ids'), []),
            (('behaviours', 0, 'scientific_effects'), ['confidence']),
            (('changes', 0, 'change'), 'renamed'),
        ]:
            with self.subTest(path=path):
                record = fixture()[1]
                target = record['change_impact']
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertTrue(list(validator('evidence').iter_errors(record)))
        evidence = fixture()[1]
        evidence['change_impact']['behaviours'][0].update(
            disposition='unresolved', requirement_ids=[], module_ids=[], review_artifact_id=None)
        evidence['change_impact']['unresolved_behavior_ids'] = ['transfer']
        validator('evidence').validate(evidence)
        evidence['gate'].update(outcome='ACCEPTED', required_gaps=[])
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))

    def test_docs_exclusion_and_rename_records(self):
        evidence = fixture()[1]
        evidence['change_impact']['changes'][0].update(
            path='docs/guide.md', kind='documentation', change='renamed', previous_path='guide.md')
        evidence['change_impact']['behaviours'][0].update(
            description='Guide relocation; no code behaviour changes.',
            changed_paths=['docs/guide.md'], interface_refs=[], disposition='excluded',
            requirement_ids=[], module_ids=[], scientific_effects=[],
            justification='Documentation-only scope under reviewed project policy.')
        validator('evidence').validate(evidence)
        evidence['change_impact']['behaviours'][0]['review_artifact_id'] = None
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))

    def test_execution_modes_and_exact_identity_shapes(self):
        for mode in ('checkout', 'editable', 'script', 'not_applicable', 'distribution'):
            with self.subTest(mode=mode):
                plan = fixture()[0]
                contract = plan['execution_contract']
                contract['mode'] = mode
                if mode == 'distribution':
                    self.assertTrue(list(validator('module-plan').iter_errors(plan)))
                    contract['distribution_digest'] = H
                validator('module-plan').validate(plan)
        evidence = fixture()[1]
        actual = evidence['results'][0]['receipt']['execution_evidence']
        actual['collected_test_ids'] *= 2
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))
        actual['collected_test_ids'] = ['different_test_with_same_count']
        # Equality to frozen selection is semantic, not a JSON Schema comparison.
        validator('evidence').validate(evidence)
        actual['first_party_origins'][0]['sha256'] = 'unknown'
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))

    def test_static_scope_and_read_only_plan_shapes(self):
        plan, evidence, report = fixture()
        contract = {'tool': 'ruff', 'claim': 'Selected project lint rules.',
                    'intended_paths': ['src/transfer.py'], 'policy_artifact_id': 'policy1',
                    'config_artifact_ids': ['config1'], 'assessment_only': True}
        scope = {'effective_config_artifact_ids': ['effective1'], 'checked_paths': [],
                 'excluded': [], 'unchecked': [
                     {'path': 'src/transfer.py', 'region': 'dynamic_transfer',
                      'reason': 'Untyped body outside the gradual-typing claim.',
                      'policy_ref': 'policy1'}], 'suppressions': [],
                 'before_digest': H, 'after_digest': H, 'assessment_only': True}
        plan['static_contract'] = contract
        evidence['results'][0]['receipt']['static_evidence'] = scope
        report['modules'][0].update(static_contract=contract, static_evidence=scope)
        for name, record in zip(('module-plan', 'evidence', 'report'), (plan, evidence, report)):
            validator(name).validate(record)
        contract['assessment_only'] = False
        self.assertTrue(list(validator('module-plan').iter_errors(plan)))
        scope['unchecked'][0].pop('reason')
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))

    def test_assurance_fields_required_and_closed(self):
        for name, record, field in [('module-plan', fixture()[0], 'execution_contract'),
                                    ('evidence', fixture()[1], 'adoption'),
                                    ('report', fixture()[2], 'change_impact')]:
            with self.subTest(schema=name, field=field):
                record.pop(field)
                self.assertTrue(list(validator(name).iter_errors(record)))
        evidence = fixture()[1]
        evidence['change_impact']['assume_all_changes_covered'] = True
        self.assertTrue(list(validator('evidence').iter_errors(evidence)))


if __name__ == '__main__':
    unittest.main()
