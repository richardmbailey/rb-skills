"""Filesystem integration and harmless wrapper bootstrap; no real runner claim."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from rb_test_suite.project import inspect_project, snapshot, compare_snapshots
from rb_test_suite.scaffold import scaffold_project, recover_project, rollback_project, BEGIN, END
import rb_test_suite.scaffold as implementation
from rb_test_suite.validation import ContractError
from test_contracts import _draft


def config():
    p, e, _ = _draft.fixture()
    excluded = {'schema_version', 'plan_id', 'run_id', 'candidate_digest', 'policy_digest',
                'inputs', 'execution_contract', 'static_contract', 'evidence_import'}
    request = {k: v for k, v in p.items() if k not in excluded}
    request.update(input_paths=['src/transfer.py'], execution_request={
        'mode': 'checkout', 'distribution_path': None,
        'first_party_paths': {'transfer': 'src/transfer.py'},
        'expected_test_ids': ['tests/unit/test_transfer.py::test_known']},
        static_request=None, evidence_import_path=None)
    return {'schema_version': '1.0.0', 'project_root': '.', 'focus': 'development',
            'default_profile': 'standard', 'environment_command': ['existing-python'],
            'lock_digest': _draft.H, 'supported_os': ['fixture'], 'runner_version': '0.1.0',
            'profiles': [{'name': 'standard', 'capability_ids': ['unit'], 'limits': p['limits']}],
            'requirements': [{'path': 'requirements.md', 'sha256': _draft.H,
                              'criterion_ids': ['c1'], 'authorised_owner': 'fixture-owner'}],
            'modules': [request], 'capabilities': e['capabilities'], 'references': [], 'operations': [],
            'adoption': {'runner_argv': ['./run_tests.sh'], 'instruction_paths': ['AGENTS.md'],
                         'supported_workflows': ['ordinary_implementation', 'scientific_implementation',
                                                 'plan_execution', 'direct_completion'], 'enforcement': 'cooperative'},
            'change_impact_path': '.rb-tests/control/impact.json',
            'reporting': {'retention_days': 30, 'redact': True, 'include_raw_artifacts': True,
                          'output_path': '.rb-tests/output'}}


class ProjectCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def apply(self, files=None, **kwargs):
        return scaffold_project(self.root, config(), files or {'tests/unit/test_known.py': 'def test_known():\n    assert 2 + 2 == 4\n'}, **kwargs)

    def test_discovery_is_read_only_no_import_or_hook(self):
        self.write('pyproject.toml', '[project]\nname="fixture"\n[tool.pytest.ini_options]\ntestpaths=["tests"]\n')
        self.write('package.json', '{"scripts":{"postinstall":"touch SHOULD_NOT_EXIST"}}')
        self.write('setup.py', 'raise RuntimeError("must never import")')
        self.write('.github/workflows/test.yaml', 'jobs:\n  check:\n    steps: []\n')
        self.write('uv.lock', 'version=1\n')
        before = snapshot(self.root)
        result = inspect_project(self.root)
        self.assertEqual(result['manifests']['pyproject.toml']['project']['name'], 'fixture')
        self.assertEqual(result['lock_paths'], ['uv.lock'])
        self.assertEqual(result['semantic_impact'], 'requires_host_review')
        self.assertEqual(before, snapshot(self.root))
        self.assertFalse((self.root / 'SHOULD_NOT_EXIST').exists())

    def test_inventory_add_modify_delete_rename_and_ambiguous_copy(self):
        for path, text in [('a.py', 'a'), ('b.py', 'b'), ('c.py', 'c'), ('d.py', 'same'), ('e.py', 'same')]:
            self.write(path, text)
        before = snapshot(self.root)
        (self.root / 'a.py').rename(self.root / 'new.py')
        self.write('b.py', 'changed')
        (self.root / 'c.py').unlink()
        (self.root / 'd.py').unlink()
        (self.root / 'e.py').unlink()
        self.write('f.py', 'same')
        self.write('input.csv', 'untracked')
        changes = compare_snapshots(before, snapshot(self.root))
        self.assertEqual({c['path']: c['change'] for c in changes}, {
            'new.py': 'renamed', 'b.py': 'modified', 'c.py': 'deleted',
            'd.py': 'deleted', 'e.py': 'deleted', 'f.py': 'added', 'input.csv': 'added'})
        self.assertTrue(all(c['change'] == 'added' for c in compare_snapshots(None, before)))

    def test_control_and_output_identity_no_self_reference(self):
        self.apply()
        self.write('.rb-tests/control/impact.json', '{}')
        before = snapshot(self.root, config=config())
        self.write('.rb-tests/output/report.json', 'derived')
        self.write('.rb-tests/control/impact.json', '{"review":"changed"}')
        after = snapshot(self.root, config=config())
        self.assertEqual(before['candidate_digest'], after['candidate_digest'])
        self.assertNotEqual(before['controls_digest'], after['controls_digest'])
        self.assertIn('.rb-tests/config.yaml', before['files'])
        self.write('untracked.csv', 'new data')
        self.assertNotEqual(after['candidate_digest'], snapshot(self.root, config=config())['candidate_digest'])
        with self.assertRaises(ContractError):
            snapshot(self.root, config=config(), exclusions=['tests', 'src'])

    def test_nested_caches_and_large_data_are_handled_explicitly(self):
        self.write('src/code.py', 'one')
        before = snapshot(self.root)
        self.write('tests/rb_assurance/__pycache__/test_known.pyc', 'generated')
        self.write('.rb-tests/runner/.venv/cache', 'installed transient')
        after = snapshot(self.root)
        self.assertEqual(before['candidate_digest'], after['candidate_digest'])
        self.assertIn('tests/rb_assurance/__pycache__', after['observed_exclusions'])
        data = self.root / 'large.csv'
        with data.open('wb') as stream:
            stream.truncate(17 * 1024 * 1024)
        self.assertIn('large.csv', snapshot(self.root)['files'])
        from rb_test_suite.project import read_file
        with self.assertRaisesRegex(ContractError, 'read limit'):
            read_file(self.root, 'large.csv')
        self.write('src/code.py', 'two')
        self.assertNotEqual(after['candidate_digest'], snapshot(self.root)['candidate_digest'])
        altered = config()
        altered['modules'][0]['input_paths'] = ['src/__pycache__/declared.py']
        with self.assertRaises(ContractError):
            snapshot(self.root, config=altered)

    def test_concurrent_lock_rejects_without_waiting(self):
        with implementation._lock(self.root):
            with self.assertRaisesRegex(ContractError, 'writer holds'):
                self.apply()

    def test_reject_symlink_special_and_traversal(self):
        (self.root / 'escape').symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaises(ContractError):
            inspect_project(self.root)
        (self.root / 'escape').unlink()
        os.mkfifo(self.root / 'pipe')
        with self.assertRaises(ContractError):
            snapshot(self.root)
        (self.root / 'pipe').unlink()
        with self.assertRaises(ContractError):
            self.apply({'../escape.py': 'no'})
        self.assertFalse((self.root / '.rb-tests').exists())

    def test_preservation_idempotency_and_selected_directories(self):
        original = 'Human instructions.\n'
        self.write('AGENTS.md', original)
        self.write('tests/old.py', 'handwritten')
        first = self.apply()
        self.assertEqual(first['runner_state'], 'bootstrap_only')
        self.assertTrue((self.root / 'AGENTS.md').read_text().startswith(original))
        self.assertFalse((self.root / 'tests/integration').exists())
        before = snapshot(self.root)
        self.assertEqual(self.apply()['status'], 'unchanged')
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual((self.root / 'tests/old.py').read_text(), 'handwritten')
        self.assertEqual((self.root / 'AGENTS.md').read_text().count(BEGIN), 1)
        for phrase in ('ACCEPTED', 'current source', 'missing required deep', 'incomplete', 'cooperative'):
            self.assertIn(phrase, (self.root / 'AGENTS.md').read_text())

    def test_conflicts_and_upgrade_preserve_hand_edits(self):
        self.write('run_tests.sh', '# user wrapper')
        with self.assertRaisesRegex(ContractError, 'user file'):
            self.apply()
        self.assertFalse((self.root / 'AGENTS.md').exists())
        (self.root / 'run_tests.sh').unlink()
        self.apply()
        self.write('tests/unit/test_known.py', '# hand edit')
        with self.assertRaisesRegex(ContractError, 'hand edits'):
            self.apply(upgrade=True)
        self.assertEqual((self.root / 'tests/unit/test_known.py').read_text(), '# hand edit')

    def test_upgrade_and_rollback(self):
        self.apply()
        original = (self.root / 'tests/unit/test_known.py').read_bytes()
        with self.assertRaisesRegex(ContractError, 'explicit upgrade'):
            self.apply({'tests/unit/test_known.py': 'updated'})
        self.apply({'tests/unit/test_known.py': 'updated'}, upgrade=True)
        self.assertEqual(rollback_project(self.root)['status'], 'rolled_back')
        self.assertEqual((self.root / 'tests/unit/test_known.py').read_bytes(), original)
        self.assertEqual(self.apply()['status'], 'unchanged')

    def test_adoption_preserves_outside_changes_rejects_inside_changes(self):
        self.apply()
        path = self.root / 'AGENTS.md'
        path.write_text('New human prefix.\n' + path.read_text() + '\nNew human suffix.\n')
        self.assertEqual(self.apply()['status'], 'committed')
        self.assertEqual(self.apply()['status'], 'unchanged')
        path.write_text(path.read_text().replace('ACCEPTED', 'OVERRIDDEN'))
        with self.assertRaisesRegex(ContractError, 'edited adoption'):
            self.apply(upgrade=True)

    def test_failure_rollback_and_interruption_recovery(self):
        self.write('AGENTS.md', 'Before\n')
        original = implementation._atomic
        count = 0
        def failure(root, path, data, mode=0o644):
            nonlocal count
            if path == 'run_tests.sh' and count == 0:
                count += 1
                raise OSError('simulated write failure')
            return original(root, path, data, mode)
        with patch.object(implementation, '_atomic', failure), self.assertRaisesRegex(ContractError, 'rolled_back'):
            self.apply()
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'Before\n')
        self.assertFalse((self.root / 'run_tests.sh').exists())
        def interruption(root, path, data, mode=0o644):
            if path == 'run_tests.sh':
                raise KeyboardInterrupt()
            return original(root, path, data, mode)
        with patch.object(implementation, '_atomic', interruption), self.assertRaises(KeyboardInterrupt):
            self.apply()
        with self.assertRaisesRegex(ContractError, 'recovery'):
            self.apply()
        self.assertEqual(recover_project(self.root)['status'], 'rolled_back')
        self.assertEqual((self.root / 'AGENTS.md').read_text(), 'Before\n')
        self.assertEqual(self.apply()['status'], 'committed')

    def test_rollback_does_not_overwrite_later_edit(self):
        self.apply()
        self.write('tests/unit/test_known.py', 'later edit')
        result = rollback_project(self.root)
        self.assertEqual(result['status'], 'rollback_conflict')
        self.assertIn('tests/unit/test_known.py', result['conflicts'])
        self.assertEqual((self.root / 'tests/unit/test_known.py').read_text(), 'later edit')

    def test_corrupted_backup_cannot_restore_untrusted_bytes(self):
        self.apply()
        path = self.root / implementation.JOURNAL
        journal = json.loads(path.read_text())
        journal['operations'][0]['before'] = 'dGFtcGVyZWQ='
        path.write_text(json.dumps(journal))
        before = (self.root / 'run_tests.sh').read_bytes()
        with self.assertRaisesRegex(ContractError, 'corrupted journal'):
            rollback_project(self.root)
        self.assertEqual((self.root / 'run_tests.sh').read_bytes(), before)

    def test_wrapper_harmless_bootstrap_fixture_forwarding_and_relocation(self):
        self.apply()
        missing = subprocess.run([str(self.root / 'run_tests.sh')], capture_output=True)
        self.assertEqual(missing.returncode, 3)
        self.write('.rb-tests/runner/run_checks.py', 'import json,sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(7)\n')
        moved = self.root / 'project with spaces;literal'
        moved.mkdir()
        for path in list(self.root.iterdir()):
            if path != moved:
                path.rename(moved / path.name)
        args = ['two words', '$(touch should-not-exist)', 'semi;colon', '--profile', 'deep']
        run = subprocess.run([str(moved / 'run_tests.sh'), *args], cwd='/',
                             env={**os.environ, 'RB_TEST_SUITE_PYTHON': sys.executable}, capture_output=True, text=True)
        self.assertEqual(run.returncode, 7)
        self.assertEqual(json.loads(run.stdout), ['--project-root', str(moved), *args])
        self.assertFalse((moved / 'should-not-exist').exists())

if __name__ == '__main__':
    unittest.main()
