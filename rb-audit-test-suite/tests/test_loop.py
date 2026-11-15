"""Executable coordinator acceptance checks, including a deliberately faulty gate."""
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'test_loop.py'
spec = importlib.util.spec_from_file_location('test_loop_runtime', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'
        self.project.mkdir()
        (self.project / 'candidate.py').write_text('candidate = 1\n')
        (self.project / 'requirements.md').write_text('All requirements remain binding.\n')
        self.control = self.project / 'control'
        self.plan_path = self.base / 'plan.json'
        audit_code = (
            'import subprocess,sys; '
            'healthy=subprocess.run([sys.executable,"-c","assert 2 + 2 == 4"],capture_output=True); '
            f'faulty=subprocess.run([sys.executable,"-c",{repr("assert 2 + 2 == 5, 'wrong sum'")}],capture_output=True); '
            'assert healthy.returncode == 0; '
            'assert faulty.returncode != 0 and b"AssertionError: wrong sum" in faulty.stderr'
        )
        self.plan = dict(version=1, builder_id='builder-1', input_paths=['candidate.py'],
                         protected_paths=['requirements.md'], checks=[
                             self.check('project', 'print("healthy project")'),
                             self.check('audit', audit_code)])


    def check(self, kind, code, timeout=5):
        return dict(id=kind, kind=kind, argv=[sys.executable, '-c', code], timeout_seconds=timeout)

    def cli(self, command, expected=None, extra=()):
        if expected is None:
            expected = 3 if command == 'run' else 0
        result = subprocess.run([sys.executable, str(SCRIPT), command, '--state-dir', str(self.control), *extra], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return result

    def init(self):
        self.plan_path.write_text(json.dumps(self.plan))
        return self.cli('init', extra=['--project', str(self.project), '--plan', str(self.plan_path)])

    def state(self):
        return json.loads((self.control / 'state.json').read_text())

    def review_value(self, decision='approve'):
        round_ = self.state()['rounds'][-1]
        return dict(version=1, round=round_['number'], candidate_digest=round_['candidate_digest'], reviewer_id='auditor-1', host_invocation_ref='host:agent-invocation-2026-001', decision=decision, findings=[])

    def review(self, value=None, expected=0):
        path = self.base / 'review.json'
        path.write_text(json.dumps(self.review_value() if value is None else value))
        return self.cli('review', expected, ['--review', str(path)])

    def test_success_requires_review_and_records_commands(self):
        self.init()
        self.cli('run')
        state = self.state()
        self.assertEqual(state['status'], 'awaiting_review')
        self.cli('status', 1, ['--require-verified'])
        checks = state['rounds'][0]['checks']
        self.assertEqual(len(checks), 2)
        self.assertIn('healthy project', Path(checks[0]['stdout']).read_text())
        self.assertEqual(checks[0]['cwd'], str(self.project))
        self.assertLessEqual(checks[0]['started'], checks[0]['finished'])
        self.review()
        self.assertEqual(self.state()['status'], 'verified_local')
        self.cli('run', 2)
        self.cli('status', 0, ['--require-verified'])
        (self.project / 'candidate.py').write_text('changed')
        self.cli('status', 2, ['--require-verified'])

    def test_early_failure_later_success_is_failure_and_unchanged_retry_rejected(self):
        self.plan['checks'][0] = self.check('project', 'raise SystemExit(7)')
        self.init()
        self.cli('run', 1)
        state = self.state()
        self.assertEqual([x['exit_code'] for x in state['rounds'][0]['checks']], [7, 0])
        self.assertEqual(state['status'], 'needs_repair')
        self.cli('run', 2)
        self.review(expected=2)
        self.assertTrue((self.control / 'round-001' / 'assessment.json').exists())

    def test_missing_logs_block_review(self):
        self.init()
        self.cli('run')
        for check in self.state()['rounds'][0]['checks']:
            for stream in ('stdout', 'stderr'):
                path = Path(check[stream])
                original = path.read_bytes()
                with self.subTest(check=check['id'], stream=stream):
                    path.unlink()
                    self.review(expected=2)
                    path.write_bytes(original)
        self.review()

    def test_changed_logs_revoke_acceptance(self):
        self.init()
        self.cli('run')
        self.review()
        for check in self.state()['rounds'][0]['checks']:
            for stream in ('stdout', 'stderr'):
                path = Path(check[stream])
                original = path.read_bytes()
                with self.subTest(check=check['id'], stream=stream):
                    path.write_bytes(original + b'altered evidence\n')
                    self.cli('status', 2, ['--require-verified'])
                    path.write_bytes(original)
        self.cli('status', 0, ['--require-verified'])

    def test_missing_logs_revoke_acceptance(self):
        self.init()
        self.cli('run')
        self.review()
        for check in self.state()['rounds'][0]['checks']:
            Path(check['stdout']).unlink()
            Path(check['stderr']).unlink()
        self.cli('status', 2, ['--require-verified'])

    def test_symlinked_log_is_rejected_even_with_identical_bytes(self):
        self.init()
        self.cli('run')
        path = Path(self.state()['rounds'][0]['checks'][0]['stdout'])
        replacement = self.base / 'replacement.log'
        path.rename(replacement)
        path.symlink_to(replacement)
        self.review(expected=2)

    def test_redirected_log_and_legacy_records_are_rejected(self):
        self.init()
        self.cli('run')
        original = self.state()
        for change in ('redirect', 'legacy'):
            with self.subTest(change=change):
                state = json.loads(json.dumps(original))
                check = state['rounds'][0]['checks'][0]
                if change == 'redirect':
                    replacement = self.base / 'replacement.log'
                    replacement.write_bytes(Path(check['stdout']).read_bytes())
                    check['stdout'] = str(replacement)
                else:
                    del check['stdout_sha256']
                    del check['stderr_sha256']
                (self.control / 'state.json').write_text(json.dumps(state))
                (self.control / 'round-001' / 'assessment.json').write_text(json.dumps(state['rounds'][0]))
                self.review(expected=2)

    def test_missing_executable_is_failure(self):
        self.plan['checks'][0]['argv'] = [str(self.base / 'nonexistent-command')]
        self.init()
        self.cli('run', 1)
        self.assertEqual(self.state()['rounds'][0]['checks'][0]['outcome'], 'missing')

    @unittest.skipUnless(os.name == 'posix', 'POSIX process-group containment')
    def test_timeout_stops_child_and_keeps_partial_logs(self):
        marker = self.base / 'child-survived'
        child = f'import time,pathlib; time.sleep(0.8); pathlib.Path({str(marker)!r}).write_text("bad")'
        code = f'import subprocess,sys,time; print("partial",flush=True); subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(5)'
        self.plan['checks'][0] = self.check('project', code, 0.2)
        self.init()
        self.cli('run', 1)
        check = self.state()['rounds'][0]['checks'][0]
        self.assertEqual(check['outcome'], 'timeout')
        self.assertIn('partial', Path(check['stdout']).read_text())
        time.sleep(0.9)
        self.assertFalse(marker.exists())

    def test_review_identity_current_candidate_and_blockers(self):
        self.init()
        self.cli('run')
        for patch in ({'round': 2}, {'candidate_digest': 'wrong'}, {'reviewer_id': 'builder-1'}, {'host_invocation_ref': ''}, {'extra': True}, {'findings': [{'id': 'f1', 'severity': 'blocking', 'message': 'gap', 'evidence': 'case absent'}]}):
            with self.subTest(patch=patch):
                value = self.review_value()
                value.update(patch)
                self.review(value, 2)
        (self.project / 'candidate.py').write_text('candidate = 2')
        self.review(expected=2)
        self.assertEqual(self.state()['status'], 'awaiting_review')

    def test_review_revise_and_incomplete_never_accept(self):
        self.init()
        self.cli('run')
        self.review(self.review_value('revise'), 1)
        self.cli('run', 2)
        (self.project / 'candidate.py').write_text('candidate = 2')
        self.cli('run')
        self.review(self.review_value('incomplete'), 1)
        self.assertEqual(self.state()['status'], 'needs_repair')
        self.assertTrue((self.control / 'round-001' / 'review.json').exists())

    def test_protected_and_policy_tamper(self):
        self.init()
        self.cli('run')
        (self.project / 'requirements.md').write_text('weakened')
        self.review(expected=2)
        (self.project / 'requirements.md').write_text('All requirements remain binding.\n')
        (self.control / 'plan.json').write_text('{}')
        self.review(expected=2)

    def test_changed_inputs_during_checks_fail(self):
        self.plan['checks'][0] = self.check('project', 'from pathlib import Path; Path("candidate.py").write_text("changed")')
        self.init()
        self.cli('run', 1)
        self.assertEqual(self.state()['status'], 'needs_repair')

    def test_input_directory_excludes_control_files(self):
        self.plan['input_paths'] = ['.']
        self.init()
        self.cli('run')
        self.review()
        self.assertFalse(any('control' in name for name in self.state()['rounds'][0]['before']))

    def test_symlinks_and_traversal_rejected(self):
        for name in ('../plan.json', '/tmp', 'alias'):
            with self.subTest(name=name):
                alias = self.project / 'alias'
                if not alias.exists():
                    alias.symlink_to(self.base)
                self.plan['input_paths'] = [name]
                self.plan_path.write_text(json.dumps(self.plan))
                self.cli('init', 2, ['--project', str(self.project), '--plan', str(self.plan_path)])

    def test_malformed_plan_and_state(self):
        for patch in ({'extra': 1}, {'max_rounds': True}, {'checks': []}, {'version': 2}, {'input_paths': []}):
            value = dict(self.plan)
            value.update(patch)
            self.plan_path.write_text(json.dumps(value))
            self.cli('init', 2, ['--project', str(self.project), '--plan', str(self.plan_path)])
        self.init()
        (self.control / 'state.json').write_text('{"status":"verified_local"}')
        self.cli('status', 2)

    def test_timeout_and_command_schema_boundaries(self):
        for timeout in (True, 0, -1, float('nan'), float('inf'), '5'):
            with self.subTest(timeout=timeout):
                value = json.loads(json.dumps(self.plan))
                value['checks'][0]['timeout_seconds'] = timeout
                with self.assertRaises(module.Invalid):
                    module.plan_validate(value)
        for argv in ('echo okay', [], [5]):
            value = json.loads(json.dumps(self.plan))
            value['checks'][0]['argv'] = argv
            with self.assertRaises(module.Invalid):
                module.plan_validate(value)

    def test_skipped_check_cannot_be_accepted(self):
        self.init()
        self.cli('run')
        state = self.state()
        state['rounds'][0]['checks'].pop(0)
        (self.control / 'state.json').write_text(json.dumps(state))
        self.cli('status', 2)

    def test_lock_stale_running_and_cancellation(self):
        self.init()
        (self.control / 'lock').write_text('123')
        self.cli('run', 2)
        (self.control / 'lock').unlink()
        state = self.state()
        state['status'] = 'running'
        # A stale interrupted attempt has a round but no final result.
        before = module.snapshot(self.project, self.plan['input_paths'], self.control)
        state['rounds'] = [dict(number=1, before=before, candidate_digest=module.digest(before), started=time.time(), checks=[])]
        (self.control / 'state.json').write_text(json.dumps(state))
        self.cli('run', 2)
        self.cli('status', 1)
        self.cli('cancel')
        self.cli('run', 2)

    def test_concurrent_run_rejected(self):
        self.plan['checks'][0] = self.check('project', 'import time; time.sleep(0.6)')
        self.init()
        first = subprocess.Popen([sys.executable, str(SCRIPT), 'run', '--state-dir', str(self.control)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not (self.control / 'lock').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((self.control / 'lock').exists())
            self.cli('run', 2)
            first.communicate(timeout=5)
            self.assertEqual(first.returncode, 3)
        finally:
            if first.poll() is None:
                first.kill()
                first.wait()

    @unittest.skipUnless(os.name == 'posix', 'POSIX interruption')
    def test_interrupt_records_failure_and_partial_logs(self):
        self.plan['checks'][0] = self.check('project', 'import time; print("started",flush=True); time.sleep(8)')
        self.init()
        process = subprocess.Popen([sys.executable, str(SCRIPT), 'run', '--state-dir', str(self.control)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            log = self.control / 'round-001' / '0.stdout.log'
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                if log.exists() and 'started' in log.read_text():
                    break
                time.sleep(0.01)
            self.assertTrue(log.exists() and 'started' in log.read_text())
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 1)
            state = self.state()
            self.assertEqual(state['status'], 'needs_repair')
            self.assertEqual(state['rounds'][0]['checks'][0]['outcome'], 'interrupted')
            self.cli('status', 1, ['--require-verified'])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_round_exhaustion_preserves_all_attempts(self):
        self.plan['max_rounds'] = 2
        self.plan['checks'][0] = self.check('project', 'raise SystemExit(1)')
        self.init()
        self.cli('run', 1)
        (self.project / 'candidate.py').write_text('candidate = 2')
        self.cli('run', 1)
        self.assertEqual(self.state()['status'], 'exhausted')
        self.cli('run', 2)
        self.assertTrue((self.control / 'round-001' / 'assessment.json').exists())
        self.assertTrue((self.control / 'round-002' / 'assessment.json').exists())

    def test_aggregation_acceptance_case_detects_faulty_gate(self):
        """The same expected-behaviour assertion accepts healthy and rejects bad gates."""
        def acceptance(gate):
            state = {'plan': {'checks': [{}, {}]}}
            round_ = {'finished': 1, 'before': {}, 'after': {}, 'checks': [
                {'outcome': 'failed', 'exit_code': 1}, {'outcome': 'passed', 'exit_code': 0}]}
            self.assertFalse(gate(state, round_), 'an earlier failed required check was ignored')
            round_['checks'][0] = {'outcome': 'passed', 'exit_code': 0}
            self.assertTrue(gate(state, round_))
        acceptance(module.success)
        with self.assertRaisesRegex(AssertionError, 'earlier failed required check'):
            acceptance(lambda state, round_: round_['checks'][-1]['exit_code'] == 0)
        with self.assertRaisesRegex(AssertionError, 'earlier failed required check'):
            acceptance(lambda state, round_: any(x['exit_code'] == 0 for x in round_['checks']))


if __name__ == '__main__':
    unittest.main()
