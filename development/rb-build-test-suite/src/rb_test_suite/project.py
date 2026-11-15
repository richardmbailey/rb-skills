"""Read-only, non-executing project discovery and content identities.

All ordinary files (including untracked inputs) participate unless explicitly
excluded. Inventory kinds describe file structure, never semantic impact.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat
import tomllib
from .validation import ContractError, parse_json, parse_yaml, relative_path, validate_record

DEFAULT_EXCLUSIONS = ('.git', '.venv', 'venv', '__pycache__', '.pytest_cache',
                      '.mypy_cache', '.ruff_cache', '.rb-tests/state', '.rb-tests/output',
                      '.rb-tests/evidence', '.rb-tests/reports', '.rb-tests/plans')
DEFAULT_CONTROL_PATHS = ('.rb-tests/control',)
MAX_TEXT_BYTES = 16 * 1024 * 1024
CACHE_DIRECTORY_NAMES = frozenset(('.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'))

def _cache_path(path):
    return any(part in CACHE_DIRECTORY_NAMES for part in Path(path).parts)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def safe_path(root, value):
    """Reject symlinks, special files, traversal and cross-device paths."""
    root = Path(root).absolute()
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ContractError('project root must be a real directory without symlink ancestors')
    relative_path(value)
    if not value or str(Path(value)) != value or value == '.':
        raise ContractError('path must be a canonical relative file path: ' + value)
    current = root
    device = root.stat().st_dev
    for part in Path(value).parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or info.st_dev != device:
            raise ContractError('symlink or device boundary: ' + value)
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ContractError('special file: ' + value)
    return root / value


def read_file(root, value, *, max_bytes=MAX_TEXT_BYTES):
    path = safe_path(root, value)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_dev != Path(root).stat().st_dev:
            raise ContractError('not an ordinary project file: ' + value)
        if before.st_size > max_bytes:
            raise ContractError('file exceeds explicit read limit: ' + value)
        data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ContractError('file exceeds explicit read limit: ' + value)
        after = os.fstat(stream.fileno())
        current = safe_path(root, value).stat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ContractError('file changed during read: ' + value)
        return data


def _file_record(root, value):
    """Stream arbitrary-size source/data files without silently excluding inputs."""
    path = safe_path(root, value)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_dev != Path(root).stat().st_dev:
            raise ContractError('not an ordinary project file: ' + value)
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
        current = safe_path(root, value).stat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise ContractError('file changed during hash: ' + value)
    return {'sha256': sha, 'bytes': after.st_size,
            'mode': stat.S_IMODE(after.st_mode), 'kind': _kind(value)}


def _under(path, prefixes):
    return any(path == prefix or path.startswith(prefix + '/') for prefix in prefixes)


def _kind(path):
    p = Path(path)
    if 'tests' in p.parts or p.name.startswith('test_'):
        return 'test'
    if p.suffix in ('.toml', '.yaml', '.yml', '.json', '.ini', '.cfg', '.lock') or p.name in ('requirements.txt', 'Dockerfile'):
        return 'configuration'
    if p.suffix in ('.md', '.rst', '.txt'):
        return 'documentation'
    if p.suffix in ('.csv', '.tsv', '.npy', '.npz', '.parquet'):
        return 'data'
    return 'source'


def snapshot(root, *, exclusions=(), control_paths=(), config=None):
    """Hash source and control records separately; never bind a request in-place.

Exclusions are exact relative paths or subtree prefixes, not glob patterns.
The returned controls digest must also be checked at finalisation.
"""
    root = Path(root).absolute()
    excluded = set(DEFAULT_EXCLUSIONS) | set(exclusions)
    controls = set(DEFAULT_CONTROL_PATHS) | set(control_paths)
    if config is not None:
        config = validate_record('config', config)
        controls.add(config['change_impact_path'])
        controls.update(m['evidence_import_path'] for m in config['modules'] if m['evidence_import_path'])
        excluded.add(config['reporting']['output_path'])
        # Requirement, test and policy inputs must never disappear via controls.
        required = ['.rb-tests/config.yaml'] + [r['path'] for r in config['requirements']]
        for m in config['modules']:
            required.extend(m['input_paths'])
            if m['static_request']:
                required += [m['static_request']['policy_path']] + m['static_request']['config_paths']
        for path in required:
            if _under(path, excluded | controls) or _cache_path(path):
                raise ContractError('source input overlaps exclusion/control: ' + path)
    for path in excluded | controls:
        safe_path(root, path)
    files, control_files = {}, {}
    observed_exclusions = []
    def walk(directory):
        for entry in sorted(os.scandir(directory), key=lambda e: e.name):
            path = Path(entry.path).relative_to(root).as_posix()
            safe_path(root, path)
            if (_under(path, excluded) or _cache_path(path)) and not _under(path, controls) and not any(c.startswith(path + '/') for c in controls):
                observed_exclusions.append(path)
                continue
            if entry.is_dir(follow_symlinks=False):
                walk(entry.path)
            else:
                record = _file_record(root, path)
                (control_files if _under(path, controls) else files)[path] = record
    walk(root)
    return {'schema_version': '1.0.0', 'files': files, 'candidate_digest': digest(files),
            'control_files': control_files, 'controls_digest': digest(control_files),
            'exclusions': sorted(excluded), 'cache_directory_exclusions': sorted(CACHE_DIRECTORY_NAMES),
            'control_paths': sorted(controls),
            'observed_exclusions': sorted(observed_exclusions),
            'missing_controls': sorted(p for p in controls if not any(_under(f, [p]) for f in control_files))}


def compare_snapshots(old, new):
    """Exact content matches yield renames only when the pairing is unique."""
    before, after = (old['files'] if old else {}), new['files']
    removed, added = set(before) - set(after), set(after) - set(before)
    changes = []
    def record(path, change, previous=None):
        b = before.get(previous or path)
        a = after.get(path)
        changes.append({'path': path, 'kind': (a or b)['kind'], 'change': change,
                        'previous_path': previous, 'before_digest': b['sha256'] if b else None,
                        'after_digest': a['sha256'] if a else None})
    for path in sorted(set(before) & set(after)):
        if before[path] != after[path]:
            record(path, 'modified')
    for path in sorted(tuple(removed)):
        matches = [p for p in added if before[path] == after[p]]
        peers = [p for p in removed if before[p] == before[path]]
        if len(matches) == len(peers) == 1:
            target = matches[0]
            record(target, 'renamed', path)
            removed.remove(path)
            added.remove(target)
    for path in sorted(removed):
        record(path, 'deleted')
    for path in sorted(added):
        record(path, 'added')
    changes.sort(key=lambda c: c['path'])
    validate_record('change-inventory', {'schema_version': '1.0.0',
                    'baseline_digest': old['candidate_digest'] if old else None,
                    'candidate_digest': new['candidate_digest'], 'changes': changes})
    return changes


def inspect_project(root):
    """Discover manifests/locks/CI without imports, hooks, subprocesses or writes."""
    root = Path(root).absolute()
    snap = snapshot(root)
    manifests, errors = {}, {}
    names = {'pyproject.toml', 'package.json', 'Pipfile', 'Cargo.toml', 'composer.json',
             'environment.yml', 'environment.yaml', '.rb-tests/config.yaml'}
    for path in snap['files']:
        ci = path.startswith('.github/workflows/') and Path(path).suffix in ('.yaml', '.yml')
        if Path(path).name not in names and path not in names and not ci:
            continue
        try:
            data = read_file(root, path, max_bytes=1048576)
            if len(data) > 1048576:
                raise ContractError('manifest exceeds byte limit')
            suffix = Path(path).suffix
            manifests[path] = (parse_json(data) if suffix == '.json' else
                               parse_yaml(data) if suffix in ('.yaml', '.yml') else
                               tomllib.loads(data.decode('utf-8')))
        except (ValueError, UnicodeError) as exc:
            errors[path] = str(exc)
    locks = [p for p in snap['files'] if Path(p).name in
             ('uv.lock', 'poetry.lock', 'Pipfile.lock', 'package-lock.json', 'pnpm-lock.yaml',
              'yarn.lock', 'Cargo.lock', 'requirements.lock', 'requirements.txt')]
    return {'snapshot': snap, 'manifests': manifests, 'parse_errors': errors,
            'lock_paths': sorted(locks), 'ci_paths': sorted(p for p in snap['files'] if p.startswith('.github/workflows/')),
            'semantic_impact': 'requires_host_review', 'environment_action': 'preserve_existing'}
