"""Explicit file proposals, conservative ownership and recoverable transactions.

No project code executes. A journal makes multi-file changes recoverable, not
simultaneously visible. Cooperative writers are serialized; unrelated edits are
checked before each replacement and never silently restored over during rollback.
"""
from __future__ import annotations
import base64
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import yaml
from .project import safe_path, read_file, digest
from .validation import ContractError, parse_json, validate_record

STATE = '.rb-tests/state'
MANIFEST = STATE + '/managed-files.json'
JOURNAL = STATE + '/transaction.json'
BEGIN = '<!-- rb-build-test-suite:begin -->'
END = '<!-- rb-build-test-suite:end -->'
ASSETS = Path(__file__).resolve().parents[2] / 'assets'
VERSION = '0.1.0'


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _current(root, path):
    p = safe_path(root, path)
    if not p.exists():
        return None
    if not p.is_file():
        raise ContractError('file proposal collides with directory: ' + path)
    return read_file(root, path)


def _atomic(root, path, data, mode=0o644):
    dest = safe_path(root, path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, path)
    fd, temporary = tempfile.mkstemp(prefix='.rb-stage-', dir=dest.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        safe_path(root, path)
        os.replace(temporary, dest)
        dirfd = os.open(dest.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _json(data):
    return (json.dumps(data, sort_keys=True, indent=2) + '\n').encode()


@contextmanager
def _lock(root):
    state = safe_path(root, STATE)
    state.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, STATE + '/lock')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'r+b') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError('another scaffold writer holds the project lock') from exc
        yield


def _load(root, path, default):
    raw = _current(root, path)
    return parse_json(raw, max_bytes=32 * 1024 * 1024) if raw is not None else default


def _section(text):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ContractError('conflicting adoption delimiters')
    if BEGIN not in text:
        return None
    start, stop = text.index(BEGIN), text.index(END) + len(END)
    if stop < start:
        raise ContractError('reversed adoption delimiters')
    return text[start:stop]


def _adopt(current, block, prior_hash):
    text = current.decode('utf-8') if current is not None else ''
    section = _section(text)
    if section is not None:
        if prior_hash is None or _hash(section.encode()) != prior_hash:
            raise ContractError('existing or edited adoption section needs explicit integration')
        return text.replace(section, block, 1).encode()
    if prior_hash is not None:
        raise ContractError('managed adoption section was removed')
    return (text + ('\n\n' if text and not text.endswith('\n\n') else '') + block + '\n').encode()


def _validate_journal(root, journal):
    if journal.get('version') != VERSION or journal.get('status') not in ('pending', 'committed', 'rolled_back', 'rollback_conflict'):
        raise ContractError('unsupported or corrupted transaction journal')
    paths = set()
    if not isinstance(journal.get('operations'), list):
        raise ContractError('corrupted transaction operations')
    for op in journal['operations']:
        if not isinstance(op, dict) or set(op) != {'path', 'before', 'after', 'before_hash', 'after_hash', 'before_mode', 'after_mode'}:
            raise ContractError('corrupted transaction operation')
        for label in ('before', 'after'):
            if op[label] is not None and not isinstance(op[label], str):
                raise ContractError('corrupted transaction bytes')
            mode = op[label + '_mode']
            if mode is not None and (type(mode) is not int or not 0 <= mode <= 0o777):
                raise ContractError('corrupted transaction mode')
        safe_path(root, op['path'])
        if op['path'] in paths or op['path'] == JOURNAL or (op['path'].startswith(STATE + '/') and op['path'] != MANIFEST):
            raise ContractError('unsafe journal operation')
        paths.add(op['path'])
        for label in ('before', 'after'):
            data = base64.b64decode(op[label], validate=True) if op[label] is not None else None
            if (None if data is None else _hash(data)) != op[label + '_hash']:
                raise ContractError('corrupted journal backup')
    return journal


def _restore(root, journal):
    _validate_journal(root, journal)
    conflicts, restored = [], []
    for op in reversed(journal['operations']):
        try:
            current = _current(root, op['path'])
            actual = _hash(current) if current is not None else None
            if actual == op['before_hash']:
                continue
            if actual != op['after_hash']:
                conflicts.append(op['path'])
                continue
            before = base64.b64decode(op['before']) if op['before'] is not None else None
            if before is None:
                safe_path(root, op['path']).unlink()
            else:
                _atomic(root, op['path'], before, op['before_mode'])
            restored.append(op['path'])
        except (OSError, ValueError) as exc:
            conflicts.append(op['path'] + ': ' + str(exc))
    journal['status'] = 'rollback_conflict' if conflicts else 'rolled_back'
    journal['conflicts'] = conflicts
    _atomic(root, JOURNAL, _json(journal), 0o600)
    return {'status': journal['status'], 'restored': restored, 'conflicts': conflicts}


def recover_project(root):
    """Explicitly undo an interrupted transaction, preserving intervening edits."""
    root = Path(root).absolute()
    with _lock(root):
        journal = _load(root, JOURNAL, None)
        if journal is None:
            return {'status': 'no_transaction', 'conflicts': []}
        _validate_journal(root, journal)
        if journal['status'] in ('committed', 'rolled_back'):
            return {'status': journal['status'], 'conflicts': []}
        return _restore(root, journal)


def rollback_project(root):
    """Undo the most recent transaction only where generated bytes still match."""
    root = Path(root).absolute()
    with _lock(root):
        journal = _load(root, JOURNAL, None)
        return _restore(root, journal) if journal else {'status': 'no_transaction', 'conflicts': []}


def scaffold_project(root, config, files, *, upgrade=False):
    """Apply explicit selected file proposals; refuse conflicts before any writes.

The config is the unbound authoring record. This returns adoption locations and
hashes for P3 to freeze, not an assertion of verified completion or actual runs.
"""
    root = Path(root).absolute()
    if hasattr(config, 'model_dump'):
        config = config.model_dump(mode='json')
    config = validate_record('config', config)
    if config['project_root'] != '.':
        raise ContractError('scaffolding requires project_root relative to supplied root: .')
    if config['adoption']['runner_argv'] != ['./run_tests.sh']:
        raise ContractError('bootstrap adoption runner_argv must be [./run_tests.sh]')
    if len(config['adoption']['instruction_paths']) != len(set(config['adoption']['instruction_paths'])):
        raise ContractError('duplicate instruction path')
    proposals = {}
    for path, content in files.items():
        safe_path(root, path)
        if path.startswith('.rb-tests/') or path == 'run_tests.sh' or path in config['adoption']['instruction_paths']:
            raise ContractError('proposal overlaps reserved scaffold path: ' + path)
        if not isinstance(content, (str, bytes)):
            raise ContractError('proposal must contain UTF-8 text or bytes')
        proposals[path] = content.encode() if isinstance(content, str) else content
        if len(proposals[path]) > 16 * 1024 * 1024:
            raise ContractError('proposal exceeds 16 MiB limit: ' + path)
    proposals['.rb-tests/config.yaml'] = yaml.safe_dump(config, sort_keys=True).encode()
    proposals['run_tests.sh'] = (ASSETS / 'run_tests.sh').read_bytes()
    block = BEGIN + '\n' + (ASSETS / 'project-completion.md').read_text() + '\nSaved runner: `./run_tests.sh`\nSupported workflows: ' + ', '.join(config['adoption']['supported_workflows']) + '\n' + END
    with _lock(root):
        previous = _load(root, JOURNAL, None)
        if previous and _validate_journal(root, previous)['status'] in ('pending', 'rollback_conflict'):
            raise ContractError('pending transaction requires explicit recovery')
        manifest = _load(root, MANIFEST, {'version': VERSION, 'files': {}, 'sections': {}})
        if manifest.get('version') != VERSION:
            raise ContractError('unsupported managed manifest version')
        for path, record in manifest['files'].items():
            validate_record('managed-file', record)
            if record['path'] != path:
                raise ContractError('managed manifest path mismatch')
        section_hashes = dict(manifest['sections'])
        for path in config['adoption']['instruction_paths']:
            safe_path(root, path)
            if path.startswith('.rb-tests/') or path == 'run_tests.sh':
                raise ContractError('instruction path overlaps scaffold control path')
            proposals[path] = _adopt(_current(root, path), block, section_hashes.get(path))
            section_hashes[path] = _hash(block.encode())
        operations, records = [], dict(manifest['files'])
        for path, after in sorted(proposals.items()):
            before = _current(root, path)
            old = records.get(path)
            adoption = path in config['adoption']['instruction_paths']
            if before is not None and not adoption:
                if old is None:
                    raise ContractError('existing user file conflicts: ' + path)
                if _hash(before) != old['sha256']:
                    raise ContractError('managed file has hand edits: ' + path)
            if old and before is None:
                raise ContractError('managed file was deleted: ' + path)
            if before != after and old and not upgrade:
                raise ContractError('changed managed proposal requires explicit upgrade: ' + path)
            mode = 0o755 if path == 'run_tests.sh' else (safe_path(root, path).stat().st_mode & 0o777 if before is not None else 0o644)
            if before != after:
                operations.append(_operation(root, path, before, after, mode))
            records[path] = {'path': path, 'sha256': _hash(after), 'owner': 'generated',
                             'version': VERSION, 'backup_path': (JOURNAL if before is not None else None) if before != after else (old['backup_path'] if old else None),
                             'previous_sha256': (_hash(before) if before is not None else None) if before != after else (old['previous_sha256'] if old else None)}
        new_manifest = {'version': VERSION, 'files': records, 'sections': section_hashes}
        # Stable no-op must preserve the last rollback journal.
        if not operations and new_manifest == manifest:
            return {'status': 'unchanged', 'managed_files': records, 'adoption': config['adoption'], 'completion': 'incomplete'}
        operations.append(_operation(root, MANIFEST, _current(root, MANIFEST), _json(new_manifest), 0o600))
        journal = {'version': VERSION, 'status': 'pending', 'operations': operations, 'conflicts': []}
        if len(_json(journal)) > 16 * 1024 * 1024:
            raise ContractError('transaction exceeds 16 MiB journal limit; split proposals')
        _atomic(root, JOURNAL, _json(journal), 0o600)
        try:
            for op in operations:
                current = _current(root, op['path'])
                if (_hash(current) if current is not None else None) != op['before_hash']:
                    raise ContractError('file changed after staging: ' + op['path'])
                _atomic(root, op['path'], base64.b64decode(op['after']), op['after_mode'])
            journal['status'] = 'committed'
            _atomic(root, JOURNAL, _json(journal), 0o600)
        except Exception as exc:
            result = _restore(root, journal)
            raise ContractError('transaction failed; ' + result['status'] + ': ' + str(exc)) from exc
        return {'status': 'committed', 'managed_files': records, 'adoption': config['adoption'],
                'instruction_hashes': {p: records[p]['sha256'] for p in config['adoption']['instruction_paths']},
                'completion': 'incomplete', 'runner_state': 'bootstrap_only'}


def _operation(root, path, before, after, mode):
    return {'path': path, 'before': base64.b64encode(before).decode() if before is not None else None,
            'after': base64.b64encode(after).decode(), 'before_hash': _hash(before) if before is not None else None,
            'after_hash': _hash(after), 'before_mode': (safe_path(root, path).stat().st_mode & 0o777) if before is not None else None,
            'after_mode': mode}
