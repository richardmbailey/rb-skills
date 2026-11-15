#!/usr/bin/env python3
"""Local, cooperative builder/auditor gate. No LLM calls or sandbox guarantees."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def fields(value, required, optional=()):
    require(isinstance(value, dict), 'expected object')
    require(set(required) <= set(value) <= set(required) | set(optional), 'missing or unknown fields')


def string(value):
    return isinstance(value, str) and bool(value.strip()) and '\x00' not in value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def log_digest(path):
    require(path.resolve() == path and path.is_file(), f'missing or nonregular command log: {path}')
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(), object_pairs_hook=unique)
    except (OSError, ValueError) as exc:
        raise Invalid(f'cannot read valid JSON: {path}: {exc}') from exc


def atomic(path, value):
    temp = path.with_suffix('.tmp')
    with temp.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def immutable(path, value):
    require(not path.exists(), f'evidence already exists: {path}')
    atomic(path, value)


def safe_path(root, name):
    require(string(name), 'empty path')
    part = Path(name)
    require(not part.is_absolute() and '..' not in part.parts, 'paths must be relative without traversal')
    current = root
    for item in part.parts:
        current /= item
        require(not current.is_symlink(), f'symlink forbidden: {current}')
    require(current.exists(), f'missing input: {name}')
    return current


def plan_validate(plan):
    fields(plan, ['version', 'builder_id', 'input_paths', 'protected_paths', 'checks'], ['max_rounds'])
    require(type(plan['version']) is int and plan['version'] == 1, 'unsupported plan version')
    require(string(plan['builder_id']), 'invalid builder identity')
    maximum = plan.get('max_rounds', 3)
    require(type(maximum) is int and 1 <= maximum <= 100, 'invalid max_rounds')
    for key in ('input_paths', 'protected_paths'):
        require(isinstance(plan[key], list) and plan[key] and all(string(x) for x in plan[key]), f'invalid {key}')
        require(len(set(plan[key])) == len(plan[key]), 'duplicate paths')
    require(isinstance(plan['checks'], list) and plan['checks'], 'checks required')
    ids, kinds = set(), set()
    for check in plan['checks']:
        fields(check, ['id', 'kind', 'argv', 'timeout_seconds'])
        require(string(check['id']) and check['id'] not in ids, 'invalid or duplicate check ID')
        ids.add(check['id'])
        require(check['kind'] in ('project', 'audit'), 'invalid check kind')
        kinds.add(check['kind'])
        require(isinstance(check['argv'], list) and check['argv'] and all(string(x) for x in check['argv']), 'argv must be nonempty string array')
        timeout = check['timeout_seconds']
        require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 86400, 'invalid timeout')
    require(kinds == {'project', 'audit'}, 'both project and audit checks required')
    return plan


def snapshot(root, paths, control):
    result = {}
    def visit(path):
        require(not path.is_symlink(), f'symlink forbidden: {path}')
        if path == control or control in path.parents:
            return
        key = path.relative_to(root).as_posix() or '.'
        if path.is_dir():
            result[key] = {'type': 'directory'}
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            require(path.is_file(), f'not a regular file: {path}')
            result[key] = {'type': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': path.stat().st_mode & 0o777}
    for name in paths:
        path = safe_path(root, name)
        require(path != control and control not in path.parents, 'input is inside control state')
        visit(path)
    return result


@contextmanager
def locked(control):
    require(control.is_dir() and not control.is_symlink(), 'invalid state directory')
    lock = control / 'lock'
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Invalid('locked; another command or stale process owns the state; do not resume blindly') from exc
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


STATUSES = {'ready', 'running', 'awaiting_review', 'needs_repair', 'exhausted', 'verified_local', 'cancelled'}


def load(control):
    state = read(control / 'state.json')
    fields(state, ['version', 'project', 'plan', 'policy_digest', 'protected', 'rounds', 'status'])
    require(type(state['version']) is int and state['version'] == 1 and state['status'] in STATUSES, 'corrupt state')
    plan_validate(state['plan'])
    require(digest(state['plan']) == state['policy_digest'], 'policy changed')
    require(isinstance(state['protected'], dict) and isinstance(state['rounds'], list), 'corrupt state')
    require(len(state['rounds']) <= state['plan'].get('max_rounds', 3), 'round budget corrupt')
    require(string(state['project']) and Path(state['project']).is_absolute(), 'corrupt project')
    require(read(control / 'plan.json') == state['plan'], 'frozen plan changed')
    require(read(control / 'protected.json') == state['protected'], 'frozen protection changed')
    for index, round_ in enumerate(state['rounds'], 1):
        fields(round_, ['number', 'candidate_digest', 'before', 'started', 'checks'], ['finished', 'after', 'error', 'review'])
        require(round_['number'] == index and digest(round_['before']) == round_['candidate_digest'], 'corrupt round')
        require(isinstance(round_['checks'], list), 'corrupt checks')
        if 'finished' in round_:
            assessment = {key: value for key, value in round_.items() if key != 'review'}
            require(read(control / f'round-{index:03d}' / 'assessment.json') == assessment, 'assessment evidence changed')
        if 'review' in round_:
            review_validate(round_['review'])
            require(read(control / f'round-{index:03d}' / 'review.json') == round_['review'], 'review evidence changed')
        for offset, check in enumerate(round_['checks']):
            fields(check, ['id', 'argv', 'cwd', 'started', 'finished', 'exit_code', 'outcome', 'stdout', 'stderr', 'stdout_sha256', 'stderr_sha256'])
            require(offset < len(state['plan']['checks']), 'extra check')
            expected = state['plan']['checks'][offset]
            require(check['id'] == expected['id'] and check['argv'] == expected['argv'] and check['cwd'] == state['project'], 'check mismatch')
            require(check['outcome'] in ('passed', 'failed', 'timeout', 'missing', 'interrupted'), 'bad check outcome')
            require(check['outcome'] != 'passed' or type(check['exit_code']) is int and check['exit_code'] == 0, 'false success')
            for stream in ('stdout', 'stderr'):
                path = control / f'round-{index:03d}' / f'{offset}.{stream}.log'
                require(check[stream] == str(path), 'command log path changed')
                require(log_digest(path) == check[f'{stream}_sha256'], f'command log changed: {path}')
    require(state['status'] == 'ready' or state['rounds'] or state['status'] == 'cancelled', 'missing rounds')
    if state['status'] in ('awaiting_review', 'verified_local'):
        require(success(state, state['rounds'][-1]), 'required checks not successful')
    if state['status'] == 'ready':
        require(not state['rounds'], 'ready state cannot have prior rounds')
    if state['status'] == 'verified_local':
        last = state['rounds'][-1]
        value = last.get('review', {})
        review_validate(value)
        require(value['decision'] == 'approve' and value['round'] == last['number']
                and value['candidate_digest'] == last['candidate_digest']
                and value['reviewer_id'] != state['plan']['builder_id']
                and not any(x['severity'] == 'blocking' for x in value['findings']), 'invalid accepted review')
    return state


def current(state, control):
    root = Path(state['project'])
    require(root.is_dir() and root.resolve() == root, 'project moved or symlinked')
    require(snapshot(root, state['plan']['protected_paths'], control) == state['protected'], 'protected inputs changed')
    return snapshot(root, state['plan']['input_paths'], control)


def success(state, round_):
    return ('error' not in round_ and 'finished' in round_ and round_.get('after') == round_['before']
            and len(round_['checks']) == len(state['plan']['checks'])
            and all(x['outcome'] == 'passed' and x['exit_code'] == 0 for x in round_['checks']))


def stop(process):
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait()


def execute(check, root, folder, index):
    out, err = folder / f'{index}.stdout.log', folder / f'{index}.stderr.log'
    record = dict(id=check['id'], argv=check['argv'], cwd=str(root), started=time.time(),
                  finished=None, exit_code=None, outcome='interrupted', stdout=str(out), stderr=str(err))
    with out.open('xb') as stdout, err.open('xb') as stderr:
        try:
            process = subprocess.Popen(check['argv'], cwd=root, stdout=stdout, stderr=stderr, start_new_session=os.name == 'posix')
        except OSError as exc:
            stderr.write(str(exc).encode())
            record['outcome'] = 'missing'
        else:
            try:
                record['exit_code'] = process.wait(timeout=check['timeout_seconds'])
                record['outcome'] = 'passed' if record['exit_code'] == 0 else 'failed'
            except subprocess.TimeoutExpired:
                stop(process)
                record['outcome'] = 'timeout'
                record['exit_code'] = process.returncode
            except KeyboardInterrupt:
                stop(process)
                record['exit_code'] = process.returncode
                record['outcome'] = 'interrupted'
    record['finished'] = time.time()
    record['stdout_sha256'] = log_digest(out)
    record['stderr_sha256'] = log_digest(err)
    return record


def initialise(project, plan_path, control):
    root = project.absolute()
    require(root.is_dir() and root.resolve() == root, 'project must be a real directory without symlinks')
    require(not control.exists() and control.parent.resolve() == control.parent, 'state directory must be new without symlinks')
    plan = plan_validate(read(plan_path))
    protected = snapshot(root, plan['protected_paths'], control)
    snapshot(root, plan['input_paths'], control)
    control.mkdir()
    atomic(control / 'plan.json', plan)
    atomic(control / 'protected.json', protected)
    state = dict(version=1, project=str(root), plan=plan, policy_digest=digest(plan), protected=protected, rounds=[], status='ready')
    atomic(control / 'state.json', state)
    return state


def run(control, state):
    require(state['status'] in ('ready', 'needs_repair'), 'run forbidden in current state (stale running state must not resume)')
    require(len(state['rounds']) < state['plan'].get('max_rounds', 3), 'round budget exhausted')
    before = current(state, control)
    require(not state['rounds'] or digest(before) != state['rounds'][-1]['candidate_digest'], 'unchanged candidate cannot be rerun')
    number = len(state['rounds']) + 1
    folder = control / f'round-{number:03d}'
    folder.mkdir()
    round_ = dict(number=number, candidate_digest=digest(before), before=before, started=time.time(), checks=[])
    state['rounds'].append(round_)
    state['status'] = 'running'
    atomic(control / 'state.json', state)
    try:
        for index, check in enumerate(state['plan']['checks']):
            round_['checks'].append(execute(check, Path(state['project']), folder, index))
            atomic(control / 'state.json', state)
            if round_['checks'][-1]['outcome'] == 'interrupted':
                break
        round_['after'] = current(state, control)
    except BaseException as exc:
        round_['error'] = f'{type(exc).__name__}: {exc}'
    round_['finished'] = time.time()
    state['status'] = 'awaiting_review' if success(state, round_) else repair_status(state)
    immutable(folder / 'assessment.json', round_)
    atomic(control / 'state.json', state)
    return state


def repair_status(state):
    return 'exhausted' if len(state['rounds']) >= state['plan'].get('max_rounds', 3) else 'needs_repair'


def review_validate(value):
    fields(value, ['version', 'round', 'candidate_digest', 'reviewer_id', 'host_invocation_ref', 'decision', 'findings'])
    require(type(value['version']) is int and value['version'] == 1, 'invalid review version')
    require(type(value['round']) is int and value['round'] > 0, 'invalid review round')
    require(all(string(value[x]) for x in ('candidate_digest', 'reviewer_id', 'host_invocation_ref')), 'invalid review identity')
    require(value['decision'] in ('approve', 'revise', 'incomplete'), 'invalid decision')
    require(isinstance(value['findings'], list), 'findings must be array')
    for finding in value['findings']:
        fields(finding, ['id', 'severity', 'message', 'evidence'])
        require(all(string(finding[x]) for x in ('id', 'message', 'evidence')), 'empty finding')
        require(finding['severity'] in ('blocking', 'nonblocking'), 'invalid finding severity')
    return value


def review(control, state, path):
    require(state['status'] == 'awaiting_review', 'review forbidden in current state')
    value = review_validate(read(path))
    round_ = state['rounds'][-1]
    require(value['round'] == round_['number'] and value['candidate_digest'] == round_['candidate_digest'], 'stale or wrong candidate review')
    require(value['reviewer_id'] != state['plan']['builder_id'], 'reviewer must differ from builder')
    require(digest(current(state, control)) == round_['candidate_digest'], 'current candidate changed')
    require(success(state, round_), 'required checks failed')
    require(value['decision'] != 'approve' or not any(x['severity'] == 'blocking' for x in value['findings']), 'approval contains blocking finding')
    immutable(control / f"round-{round_['number']:03d}" / 'review.json', value)
    round_['review'] = value
    state['status'] = 'verified_local' if value['decision'] == 'approve' else repair_status(state)
    atomic(control / 'state.json', state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'run', 'review', 'status', 'cancel'):
        command = commands.add_parser(name)
        command.add_argument('--state-dir', required=True, type=Path)
        if name == 'init':
            command.add_argument('--project', required=True, type=Path)
            command.add_argument('--plan', required=True, type=Path)
        if name == 'review':
            command.add_argument('--review', required=True, type=Path)
        if name == 'status':
            command.add_argument('--require-verified', action='store_true')
    args = parser.parse_args(argv)
    control = args.state_dir.absolute()
    try:
        require(control.resolve() == control, 'symlinked state path')
        if args.command == 'init':
            state = initialise(args.project, args.plan, control)
        else:
            with locked(control):
                state = load(control)
                if args.command == 'run':
                    state = run(control, state)
                elif args.command == 'review':
                    state = review(control, state, args.review)
                elif args.command == 'cancel':
                    require(state['status'] not in ('verified_local', 'cancelled'), 'cancel forbidden')
                    state['status'] = 'cancelled'
                    atomic(control / 'state.json', state)
                elif state['status'] == 'verified_local':
                    require(digest(current(state, control)) == state['rounds'][-1]['candidate_digest'], 'verified candidate changed')
        print(json.dumps(state, indent=2))
        if args.command == 'status' and args.require_verified:
            return 0 if state['status'] == 'verified_local' else 1
        if args.command == 'run' and state['status'] == 'awaiting_review':
            return 3
        return 0 if state['status'] in ('ready', 'awaiting_review', 'verified_local', 'cancelled') else 1
    except (Invalid, OSError, TypeError, KeyError) as exc:
        print(f'test-loop: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
