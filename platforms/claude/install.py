#!/usr/bin/env python3
"""Generate owned, reviewable Claude Code copies without changing shared skills."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

MARKER = '.rb-claude-install.json'
REVIEW_ANCHOR = '4. After the first complete draft, apply `$rb-simplify-language` to `SKILL.md` and any agent-facing reference text. This user-owned procedure is an explicit instruction to invoke the manual-only language-review skill for the completed draft; the skill must not be selected during initial routing merely because the task is skill authoring. Preserve the intended trigger boundary, requirements, permissions, outputs, rationale, examples, and useful redundancy. If the review exposes a missing decision that would change behaviour, ask the human instead of inventing the answer.'
REVIEW_STEP = '4. After the first complete draft, read `references/claude-language-review/SKILL.md` and apply its complete review method to `SKILL.md` and any agent-facing reference text. This authored procedure explicitly authorises this post-draft review. Read and apply the reference directly; do not invoke the manual-only skill through the Skill tool or select it during initial routing merely because the task is skill authoring. Preserve the intended trigger boundary, requirements, permissions, outputs, rationale, examples, and useful redundancy. If the review exposes a missing decision that would change behaviour, ask the human instead of inventing the answer.'


def fail(message):
    raise ValueError(message)


def safe_tree(path):
    if path.is_symlink():
        fail(f'Unsafe source symlink: {path}')
    if not path.is_dir():
        fail(f'Missing source directory: {path}')
    for root, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            item = Path(root) / name
            if item.is_symlink() or (not item.is_dir() and not item.is_file()):
                fail(f'Unsafe source entry: {item}')


def ignored(relative):
    return any(part in {'.git', '__pycache__', '.DS_Store'} or part.startswith('.env') for part in relative.parts) or relative.suffix == '.pyc' or relative.as_posix() == 'agents/openai.yaml'


def load_profile(source):
    for path in (source / 'platforms', source / 'platforms/claude'):
        if path.is_symlink():
            fail(f'Unsafe profile directory symlink: {path}')
    profile_path = source / 'platforms/claude/profile.json'
    if profile_path.is_symlink():
        fail('Unsafe profile symlink')
    profile = json.loads(profile_path.read_text())
    if not isinstance(profile, dict) or profile.get('schema_version') != 1:
        fail('Unsupported Claude profile schema')
    groups = []
    for key in ('portable_skills', 'excluded_skills', 'manual_only'):
        value = profile.get(key)
        if not isinstance(value, list) or not all(isinstance(x, str) and x.startswith('rb-') and '/' not in x and '\\' not in x for x in value) or len(value) != len(set(value)):
            fail(f'Invalid profile {key}')
        groups.append(set(value))
    portable, excluded, manual = groups
    overrides = profile.get('overrides')
    if not isinstance(overrides, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in overrides.items()):
        fail('Invalid profile overrides')
    supported = portable | set(overrides)
    if portable & set(overrides) or supported & excluded or not manual <= supported:
        fail('Overlapping or invalid profile classifications')
    active = {p.name for p in source.glob('rb-*') if (p / 'SKILL.md').is_file()}
    if supported | excluded != active:
        fail(f'Profile does not classify active skills exactly: {sorted((supported | excluded) ^ active)}')
    for name, relative in overrides.items():
        path = source / 'platforms/claude' / relative
        if not path.resolve().is_relative_to((source / 'platforms/claude').resolve()) or '..' in Path(relative).parts or Path(relative).is_absolute():
            fail(f'Unsafe override path: {relative}')
        for ancestor in (path, *path.parents):
            if ancestor == source:
                break
            if ancestor.is_symlink():
                fail(f'Unsafe override symlink: {ancestor}')
        safe_tree(path)
    return profile, supported


def generated_files(source, profile, name):
    base = source / name
    if name in profile['overrides']:
        base = source / 'platforms/claude' / profile['overrides'][name]
    safe_tree(base)
    files = {}
    for path in sorted(base.rglob('*')):
        rel = path.relative_to(base)
        if ignored(rel):
            continue
        if path.is_file():
            files[rel.as_posix()] = path.read_bytes()
    body = files['SKILL.md'].decode('utf-8')
    lines = body.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        fail(f'Missing frontmatter: {name}')
    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
    if closing is None:
        fail(f'Unclosed frontmatter: {name}')
    declared_names = [line.split(':', 1)[1].strip().strip("\"'") for line in lines[1:closing] if line.startswith('name:')]
    if declared_names != [name]:
        fail(f'Frontmatter name does not match skill: {name}')
    if name in profile['manual_only']:
        lines[1:closing] = [x for x in lines[1:closing] if not x.startswith('disable-model-invocation:')]
        closing = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
        lines.insert(closing, 'disable-model-invocation: true\n')
        closing += 1
    preamble_path = source / 'platforms/claude/preamble.md'
    if preamble_path.is_symlink():
        fail('Unsafe preamble symlink')
    preamble = preamble_path.read_text().strip()
    if not preamble:
        fail('Empty Claude preamble')
    body = ''.join(lines[:closing + 1]) + '\n' + preamble + '\n' + ''.join(lines[closing + 1:])
    if name == 'rb-write-skill':
        if body.count(REVIEW_ANCHOR) != 1:
            fail('Missing or duplicate rb-write-skill post-draft review anchor')
        review = source / 'rb-simplify-language'
        safe_tree(review)
        for resource in review.rglob('*'):
            if resource.is_file() and not ignored(resource.relative_to(review)):
                files['references/claude-language-review/' + resource.relative_to(review).as_posix()] = resource.read_bytes()
        body = body.replace(REVIEW_ANCHOR, REVIEW_STEP)
    files['SKILL.md'] = body.encode()
    return files


def hashes(files):
    return {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}


def actual_files(path):
    safe_tree(path)
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob('*') if p.is_file() and p.relative_to(path).as_posix() != MARKER}


def required_modes(source, profile, name, files):
    base = source / 'platforms/claude' / profile['overrides'][name] if name in profile['overrides'] else source / name
    modes = {}
    review_prefix = 'references/claude-language-review/'
    for relative in files:
        if name == 'rb-write-skill' and relative.startswith(review_prefix):
            original = source / 'rb-simplify-language' / relative[len(review_prefix):]
        else:
            original = base / relative
        modes[relative] = original.stat().st_mode & 0o777
    return modes


def actual_modes(path):
    safe_tree(path)
    return {p.relative_to(path).as_posix(): p.stat().st_mode & 0o7777 for p in path.rglob('*') if p.is_file() and p.relative_to(path).as_posix() != MARKER}


def owned_clean(target, source):
    try:
        if target.is_symlink() or (target / MARKER).is_symlink():
            return False
        marker = json.loads((target / MARKER).read_text())
        return isinstance(marker, dict) and marker.get('schema_version') == 1 and marker.get('source') == str(source) and marker.get('hashes') == hashes(actual_files(target)) and marker.get('modes') == actual_modes(target)
    except (OSError, ValueError, TypeError):
        return False


def install(source, dest, names=None, dry_run=False, replace=False, check=False):
    if source.is_symlink():
        fail('Source root must not be a symlink')
    source = source.resolve()
    if dest.is_symlink():
        fail(f'Destination root is a symlink: {dest}')
    dest = dest.resolve()
    if dest.is_relative_to(source) or source.is_relative_to(dest):
        fail('Source and destination must not overlap')
    backup_root = dest / '.rb-claude-backups'
    if backup_root.is_symlink() or (backup_root.exists() and not backup_root.is_dir()):
        fail(f'Unsafe backup directory: {backup_root}')
    profile, supported = load_profile(source)
    selected = sorted(set(names or supported))
    unknown = set(selected) - supported
    if unknown:
        fail(f'Unsupported Claude skills: {", ".join(sorted(unknown))}')
    for name in profile['excluded_skills']:
        path = dest / name
        if path.exists() or path.is_symlink():
            fail(f'Excluded legacy Claude skill blocks installation: {path}; review and move it manually')
    outputs = {name: generated_files(source, profile, name) for name in selected}
    modes = {name: required_modes(source, profile, name, files) for name, files in outputs.items()}
    changes = []
    actions = {}
    for name, files in outputs.items():
        target = dest / name
        exists = target.exists() or target.is_symlink()
        clean = exists and owned_clean(target, source)
        same = clean and hashes(actual_files(target)) == hashes(files) and actual_modes(target) == modes[name]
        if check and not same:
            fail(f'Claude installation drift: {target}')
        if exists and not clean and not replace:
            fail(f'Local edits or foreign destination: {target}; use --replace to back up and replace')
        if not same:
            changes.append(name)
            actions[name] = 'create' if not exists else ('refresh' if clean else 'back up and replace')
    if check:
        print(f'Checked {len(selected)} Claude skills: current')
        return
    print(f'{"Dry-run: " if dry_run else ""}Generated copies: {len(selected)} skills, {len(changes)} updates')
    if dry_run:
        for name in selected:
            print(f'Dry-run: {actions.get(name, "already current")} {dest / name}')
        return
    if not changes:
        return
    dest.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.rb-claude-stage-', dir=dest))
    completed = []
    try:
        for name in changes:
            staged = stage / name
            staged.mkdir()
            for relative, content in outputs[name].items():
                path = staged / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                path.chmod(modes[name][relative])
            (staged / MARKER).write_text(json.dumps({'schema_version': 1, 'source': str(source), 'skill': name, 'hashes': hashes(outputs[name]), 'modes': modes[name]}, indent=2) + '\n')
        for name in changes:
            target = dest / name
            backup = None
            if target.exists() or target.is_symlink():
                backup_root.mkdir(exist_ok=True)
                backup = backup_root / f'{name}-{uuid.uuid4().hex}'
                target.rename(backup)
            completed.append((target, backup))
            (stage / name).rename(target)
            print(f'Installed {name}' + (f'; backup: {backup}' if backup else ''))
    except BaseException:
        for target, backup in reversed(completed):
            if target.is_symlink():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            if backup is not None:
                backup.rename(target)
        raise
    finally:
        shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--dest', type=Path, default=Path.home() / '.claude/skills')
    parser.add_argument('--skills', nargs='+')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--replace', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        install(args.source.expanduser(), args.dest.expanduser(), args.skills, args.dry_run, args.replace, args.check)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Claude install failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
