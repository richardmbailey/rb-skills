"""External evaluation harness; not supporting code shipped with either project."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from defusedxml import ElementTree

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / 'examples/numerical-assurance'
REPEAT = ROOT / 'examples/numerical-assurance-repeat'
FAULTS = {
    'wrong_direction': ('previous.a_kg - transfer, previous.b_kg + transfer',
                        'previous.a_kg + transfer, previous.b_kg - transfer'),
    'wrong_receiver': ('previous.b_kg + transfer', 'previous.b_kg - transfer'),
    'wrong_rate': ('transfer = rate * step * previous.a_kg',
                   'transfer = 0.5 * rate * step * previous.a_kg'),
    'wrong_final_step': ('step = min(dt, time - previous.time_days)', 'step = dt'),
    'wrong_units': ('return (self.a_kg + self.b_kg) / 1000',
                    'return (self.a_kg + self.b_kg) / 100'),
    'missing_stability': ('if rate * dt > 1:', 'if False:'),
    'historical_rounded_step': ('step = min(dt, time - previous.time_days)',
                               'step = time - previous.time_days'),
    'historical_underflow': ('count = 0 if duration == 0 else max(1, math.ceil(steps))',
                             'count = math.ceil(steps)'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def classify(returncode, cases, imported_correctly):
    """Errors/skips/timeouts cannot stand in for a behavioural detection."""
    if not imported_correctly:
        return 'INVALID_IDENTITY'
    if returncode is None or any(c['outcome'] == 'error' for c in cases):
        return 'INVALID_EXECUTION'
    if any(c['outcome'] == 'skipped' for c in cases):
        return 'INCOMPLETE'
    failures = [c for c in cases if c['outcome'] == 'failure']
    if returncode == 1 and failures and all(c['assertion'] for c in failures):
        return 'ASSERTION_FAILURE'
    if returncode == 0 and cases and not failures:
        return 'PASS'
    return 'INVALID_EXECUTION'


def run(suite_name, source, candidate_name, candidate, out):
    target = out / suite_name / candidate_name
    target.mkdir(parents=True)
    project = target / 'project'
    (project / 'tests').mkdir(parents=True)
    for filename in ('test_model.py', 'test_independent.py'):
        shutil.copyfile(source / 'tests' / filename, project / 'tests' / filename)
    # An identical observer records the actually imported candidate for both suites.
    shutil.copyfile(ORIGINAL / 'conftest.py', project / 'conftest.py')
    (project / 'model.py').write_text(candidate)
    (project / 'pytest.ini').write_text('[pytest]\npythonpath = .\naddopts = -ra\n')
    target = target.resolve()
    project = project.resolve()
    capture = target / 'capture.json'
    command = [sys.executable, '-m', 'pytest', '-c', str(project / 'pytest.ini'),
               '--confcutdir', str(project), '--basetemp', str(target / 'tmp'),
               '--junitxml', str(target / 'junit.xml'), '-q',
               'tests/test_model.py', 'tests/test_independent.py']
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               RB_TRIAL_CAPTURE=str(capture), PYTHONPATH=str(project))
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=project, env=env, capture_output=True,
                                text=True, timeout=120)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code = None
        stdout = str(exc.stdout or '')
        stderr = str(exc.stderr or '') + '\nTIMEOUT'
    (target / 'stdout.log').write_text(stdout)
    (target / 'stderr.log').write_text(stderr)
    cases = []
    xml = target / 'junit.xml'
    if xml.exists():
        for item in ElementTree.parse(xml).iter('testcase'):
            failure, error, skipped = item.find('failure'), item.find('error'), item.find('skipped')
            outcome = ('error' if error is not None else 'failure' if failure is not None
                       else 'skipped' if skipped is not None else 'pass')
            message = '' if failure is None else failure.get('message', '')
            cases.append({'id': item.get('classname', '') + '::' + item.get('name', ''),
                          'outcome': outcome,
                          'assertion': failure is not None and
                          ('assert ' in (failure.text or '') or 'DID NOT RAISE' in message),
                          'message': message})
    observed = json.loads(capture.read_text()) if capture.exists() else {}
    expected_hash = digest(candidate.encode())
    record = {'suite': suite_name, 'candidate': candidate_name,
              'candidate_sha256': expected_hash, 'command': command,
              'cwd': str(project), 'returncode': code,
              'duration_seconds': time.monotonic() - started,
              'status': classify(code, cases, observed.get('model_sha256') == expected_hash),
              'tests': cases, 'capture': observed,
              'test_hashes': {p.name: digest(p.read_bytes()) for p in (project / 'tests').glob('*.py')}}
    (target / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    # Known-good / assertion / infrastructure controls exercise evaluator classification.
    assert classify(0, [{'outcome': 'pass'}], True) == 'PASS'
    assert classify(1, [{'outcome': 'failure', 'assertion': True}], True) == 'ASSERTION_FAILURE'
    assert classify(1, [{'outcome': 'error'}], True) == 'INVALID_EXECUTION'
    assert classify(None, [], True) == 'INVALID_EXECUTION'
    assert classify(0, [{'outcome': 'pass'}], False) == 'INVALID_IDENTITY'
    healthy = (ORIGINAL / 'model.py').read_text()
    candidates = {'healthy': healthy}
    for name, (before, after) in FAULTS.items():
        if healthy.count(before) != 1:
            raise ValueError(f'{name}: expected one replacement site')
        candidates[name] = healthy.replace(before, after)
        compile(candidates[name], name, 'exec')
    out = Path(tempfile.mkdtemp(prefix='paired-', dir=HERE))
    records = []
    for name, candidate in candidates.items():
        for suite_name, source in (('original', ORIGINAL), ('repeat', REPEAT)):
            record = run(suite_name, source, name, candidate, out)
            records.append(record)
            print(suite_name, name, record['status'], flush=True)
    for record in records:
        baseline = next(r for r in records if r['suite'] == record['suite'] and r['candidate'] == 'healthy')
        record['eligible_detection'] = (record['candidate'] != 'healthy' and
                                       baseline['status'] == 'PASS' and
                                       record['status'] == 'ASSERTION_FAILURE')
    summary = {'run_directory': str(out), 'records': records,
               'note': 'Eligible failures still require human inspection for fault-relevant assertions.'}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(out, flush=True)


if __name__ == '__main__':
    main()
