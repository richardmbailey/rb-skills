"""Behavioural checks for the bounded Claude export and refresh path."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / 'platforms/claude/install.py'
SYNC = ROOT / 'rb-sync-skills-repo/scripts/sync_skills_repo.py'
spec = importlib.util.spec_from_file_location('claude_installer', INSTALLER)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ClaudeInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'source'
        self.dest = self.root / 'installed'
        platform = self.source / 'platforms/claude'
        platform.mkdir(parents=True)
        shutil.copy2(INSTALLER, platform / 'install.py')
        (platform / 'preamble.md').write_text('Claude tools apply here.\n')
        self.profile = {'schema_version': 1, 'portable_skills': ['rb-example', 'rb-simplify-language', 'rb-write-skill'], 'overrides': {'rb-delegate': 'skills/rb-delegate'}, 'excluded_skills': ['rb-safe-operation'], 'manual_only': ['rb-simplify-language']}
        self.save_profile()
        for name in ['rb-example', 'rb-simplify-language', 'rb-write-skill', 'rb-delegate', 'rb-safe-operation']:
            folder = self.source / name
            folder.mkdir()
            (folder / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Example\n---\n\nShared body.\n')
        with (self.source / 'rb-write-skill/SKILL.md').open('a') as handle:
            handle.write(installer.REVIEW_ANCHOR + '\n')
        refs = self.source / 'rb-simplify-language/references'
        refs.mkdir()
        (refs / 'simplified-language-patterns.md').write_text('All review criteria.\n')
        overlay = platform / 'skills/rb-delegate'
        overlay.mkdir(parents=True)
        (overlay / 'SKILL.md').write_text('---\nname: rb-delegate\ndescription: Claude delegation\n---\n\nClaude override.\n')
        resources = self.source / 'rb-example/scripts'
        resources.mkdir()
        (resources / 'example.py').write_text('print("resource")\n')
        (resources / 'example.py').chmod(0o755)
        self.original = self.snapshot(self.source)

    def save_profile(self):
        (self.source / 'platforms/claude/profile.json').write_text(json.dumps(self.profile))

    def snapshot(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def cli(self, *args, good=True):
        result = subprocess.run([sys.executable, str(INSTALLER), str(self.source), '--dest', str(self.dest), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, good, result.stdout + result.stderr)
        return result

    def test_generation_resources_manual_review_and_no_source_mutation(self):
        self.cli()
        self.assertEqual(self.original, self.snapshot(self.source))
        self.assertEqual({p.name for p in self.dest.iterdir()}, set(self.profile['portable_skills']) | {'rb-delegate'})
        manual = (self.dest / 'rb-simplify-language/SKILL.md').read_text()
        self.assertIn('disable-model-invocation: true\n---', manual)
        writer = (self.dest / 'rb-write-skill/SKILL.md').read_text()
        self.assertIn('read `references/claude-language-review/SKILL.md`', writer)
        self.assertNotIn(installer.REVIEW_ANCHOR, writer)
        nested = self.dest / 'rb-write-skill/references/claude-language-review'
        self.assertEqual((nested / 'SKILL.md').read_bytes(), (self.source / 'rb-simplify-language/SKILL.md').read_bytes())
        self.assertTrue((nested / 'references/simplified-language-patterns.md').is_file())
        self.assertIn('Claude override.', (self.dest / 'rb-delegate/SKILL.md').read_text())
        self.assertTrue((self.dest / 'rb-example/scripts/example.py').stat().st_mode & 0o111)
        self.assertTrue(all(not p.is_symlink() for p in self.dest.rglob('*')))

    def test_subset_and_dry_run_make_no_writes(self):
        self.cli('--skills', 'rb-example', '--dry-run')
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.original, self.snapshot(self.source))
        self.cli('--skills', 'rb-example')
        self.assertEqual([p.name for p in self.dest.iterdir()], ['rb-example'])

    def test_source_mode_only_change_refreshes(self):
        self.cli()
        source_file = self.source / 'rb-example/scripts/example.py'
        source_file.chmod(0o644)
        self.cli('--check', good=False)
        self.cli()
        self.assertEqual((self.dest / 'rb-example/scripts/example.py').stat().st_mode & 0o777, 0o644)
        self.cli('--check')

    def test_installed_mode_change_is_preserved_until_explicit_replace(self):
        self.cli()
        local_file = self.dest / 'rb-example/scripts/example.py'
        local_file.chmod(0o644)
        self.cli('--check', good=False)
        self.cli(good=False)
        self.assertEqual(local_file.stat().st_mode & 0o777, 0o644)
        self.cli('--replace')
        backup = next((self.dest / '.rb-claude-backups').glob('rb-example-*'))
        self.assertEqual((backup / 'scripts/example.py').stat().st_mode & 0o777, 0o644)
        self.assertEqual(local_file.stat().st_mode & 0o777, 0o755)

    def test_missing_modes_marker_requires_explicit_backup(self):
        self.cli()
        marker_path = self.dest / 'rb-example' / installer.MARKER
        marker = json.loads(marker_path.read_text())
        marker.pop('modes', None)
        marker_path.write_text(json.dumps(marker))
        self.cli(good=False)
        self.cli('--replace')
        backup = next((self.dest / '.rb-claude-backups').glob('rb-example-*'))
        self.assertNotIn('modes', json.loads((backup / installer.MARKER).read_text()))

    def test_embedded_review_file_modes_use_original_resources(self):
        source_file = self.source / 'rb-simplify-language/references/simplified-language-patterns.md'
        source_file.chmod(0o640)
        self.cli()
        embedded = self.dest / 'rb-write-skill/references/claude-language-review/references/simplified-language-patterns.md'
        self.assertEqual(embedded.stat().st_mode & 0o777, 0o640)
        source_file.chmod(0o600)
        self.cli()
        self.assertEqual(embedded.stat().st_mode & 0o777, 0o600)

    def test_dry_run_lists_targets_and_actions_without_writes(self):
        result = self.cli('--dry-run')
        self.assertIn(f'create {self.dest / "rb-example"}', result.stdout)
        self.assertFalse(self.dest.exists())
        self.cli()
        (self.source / 'rb-example/scripts/example.py').write_text('updated')
        target = self.dest / 'rb-write-skill/SKILL.md'
        target.write_text('local edits')
        before = self.snapshot(self.dest)
        result = self.cli('--dry-run', '--replace')
        self.assertIn(f'refresh {self.dest / "rb-example"}', result.stdout)
        self.assertIn(f'back up and replace {self.dest / "rb-write-skill"}', result.stdout)
        self.assertEqual(before, self.snapshot(self.dest))

    def test_refresh_idempotence_and_source_update(self):
        self.cli()
        before = self.snapshot(self.dest)
        self.cli()
        self.assertEqual(before, self.snapshot(self.dest))
        self.assertFalse((self.dest / '.rb-claude-backups').exists())
        path = self.source / 'rb-example/scripts/example.py'
        path.write_text('print("updated")\n')
        self.cli()
        self.assertEqual((self.dest / 'rb-example/scripts/example.py').read_bytes(), path.read_bytes())
        self.assertEqual(len(list((self.dest / '.rb-claude-backups').iterdir())), 1)
        self.cli('--check')

    def test_conflict_preflights_all_skills_and_replace_preserves_backup(self):
        self.cli()
        target = self.dest / 'rb-write-skill/SKILL.md'
        target.write_text('Local changes\n')
        (self.source / 'rb-example/scripts/example.py').write_text('upstream\n')
        before = self.snapshot(self.dest)
        self.cli(good=False)
        self.assertEqual(before, self.snapshot(self.dest))
        self.cli('--replace')
        backups = list((self.dest / '.rb-claude-backups').glob('rb-write-skill-*'))
        self.assertEqual((backups[0] / 'SKILL.md').read_text(), 'Local changes\n')

    def test_foreign_and_symlink_destinations_require_replace(self):
        self.dest.mkdir()
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'SKILL.md').write_text('Foreign content')
        (self.dest / 'rb-example').symlink_to(outside, target_is_directory=True)
        self.cli('--skills', 'rb-example', good=False)
        self.cli('--skills', 'rb-example', '--replace')
        self.assertEqual((outside / 'SKILL.md').read_text(), 'Foreign content')
        self.assertTrue(next((self.dest / '.rb-claude-backups').iterdir()).is_symlink())

    def test_check_detects_source_content_and_manual_flag_drift(self):
        self.cli()
        self.cli('--check')
        path = self.dest / 'rb-simplify-language/SKILL.md'
        path.write_text(path.read_text().replace('disable-model-invocation: true\n', ''))
        self.cli('--check', good=False)
        self.cli('--replace')
        (self.source / 'rb-example/scripts/example.py').write_text('source changed')
        self.cli('--check', good=False)

    def test_bad_profile_missing_profile_and_anchor_fail_without_writes(self):
        profile_path = self.source / 'platforms/claude/profile.json'
        profile_path.write_text('{bad')
        self.cli(good=False)
        self.assertFalse(self.dest.exists())
        profile_path.unlink()
        self.cli(good=False)
        self.save_profile()
        writer = self.source / 'rb-write-skill/SKILL.md'
        writer.write_text(writer.read_text().replace(installer.REVIEW_ANCHOR, 'Changed procedure'))
        self.cli(good=False)
        self.assertFalse(self.dest.exists())

    def test_unclassified_and_unsupported_skills_fail(self):
        self.cli('--skills', 'rb-safe-operation', good=False)
        self.cli('--skills', '../escape', good=False)
        extra = self.source / 'rb-new'
        extra.mkdir()
        (extra / 'SKILL.md').write_text('new skill')
        self.cli(good=False)
        self.assertFalse(self.dest.exists())

    def test_legacy_excluded_blocks_even_replace(self):
        legacy = self.dest / 'rb-safe-operation'
        legacy.mkdir(parents=True)
        (legacy / 'SKILL.md').write_text('old')
        self.cli('--replace', good=False)
        self.assertEqual((legacy / 'SKILL.md').read_text(), 'old')

    def test_source_symlink_and_overlap_are_rejected(self):
        (self.source / 'rb-example/scripts/link').symlink_to(self.root / 'outside')
        self.cli(good=False)
        self.assertFalse(self.dest.exists())
        with self.assertRaisesRegex(ValueError, 'overlap'):
            installer.install(self.source, self.source / 'output')

    def test_staging_failure_keeps_existing_contents(self):
        self.cli()
        before = self.snapshot(self.dest)
        (self.source / 'rb-example/scripts/example.py').write_text('new')
        original = Path.write_bytes
        def fail_stage(path, content):
            if '.rb-claude-stage-' in str(path) and path.name == 'example.py':
                raise OSError('injected staging failure')
            return original(path, content)
        with patch.object(Path, 'write_bytes', fail_stage), self.assertRaisesRegex(OSError, 'staging failure'):
            installer.install(self.source, self.dest)
        self.assertEqual(before, self.snapshot(self.dest))
        self.assertFalse(any(self.dest.glob('.rb-claude-stage-*')))

    def test_rename_failure_rolls_back_already_installed_skills(self):
        self.cli()
        before = self.snapshot(self.dest)
        for name in ['rb-example', 'rb-write-skill']:
            path = self.source / name / 'SKILL.md'
            path.write_text(path.read_text() + '\nupdated\n')
        original = Path.rename
        def fail_rename(path, target):
            if '.rb-claude-stage-' in str(path) and path.name == 'rb-write-skill':
                raise OSError('injected rename failure')
            return original(path, target)
        with patch.object(Path, 'rename', fail_rename), self.assertRaisesRegex(OSError, 'rename failure'):
            installer.install(self.source, self.dest)
        self.assertEqual(before, self.snapshot(self.dest))

    def test_sync_claude_explicit_dest_routes_to_generated_copies(self):
        result = subprocess.run([sys.executable, str(SYNC), str(self.source), '--agent', 'claude', '--dest', str(self.dest), '--skills', 'rb-example'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('generating real copies', result.stdout)
        self.assertFalse((self.dest / 'rb-example').is_symlink())
        self.assertTrue((self.dest / 'rb-example' / installer.MARKER).is_file())

    def test_malformed_marker_is_conflict_and_replacement_is_possible(self):
        self.cli()
        marker = self.dest / 'rb-example' / installer.MARKER
        marker.write_text('[]')
        self.cli(good=False)
        self.cli('--replace')
        self.cli('--check')

    def test_marker_from_another_source_cannot_refresh_unattended(self):
        self.cli()
        marker = self.dest / 'rb-example' / installer.MARKER
        contents = json.loads(marker.read_text())
        contents['source'] = str(self.root / 'other-source')
        marker.write_text(json.dumps(contents))
        self.cli(good=False)

    def test_copy_filters_apply_to_nested_review_resources(self):
        for rel in ['.env', 'references/.env.secret', 'references/cache.pyc']:
            (self.source / 'rb-simplify-language' / rel).write_text('private')
        self.cli()
        self.assertFalse(any(p.name.startswith('.env') or p.suffix == '.pyc' for p in self.dest.rglob('*')))

    def test_single_skill_sync_uses_profile_and_rejects_excluded(self):
        for name, expected in [('rb-example', 0), ('rb-safe-operation', 1)]:
            result = subprocess.run([sys.executable, str(SYNC), str(self.source / name), '--agent', 'claude', '--dest', str(self.dest)], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertTrue((self.dest / 'rb-example' / installer.MARKER).is_file())
        self.assertFalse((self.dest / 'rb-safe-operation').exists())

    def test_missing_rb_adapter_fails_closed(self):
        (self.source / 'platforms/claude/install.py').unlink()
        result = subprocess.run([sys.executable, str(SYNC), str(self.source), '--agent', 'claude', '--dest', str(self.dest)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('adapter is missing', result.stderr)
        self.assertFalse(self.dest.exists())

    def test_generic_claude_sync_retains_previous_behaviour(self):
        generic = self.root / 'generic'
        shutil.copytree(self.source / 'rb-example', generic / 'rb-example')
        result = subprocess.run([sys.executable, str(SYNC), str(generic), '--agent', 'claude', '--dest', str(self.dest)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.dest / 'rb-example').is_symlink())

    def test_bad_frontmatter_name_and_profile_override_escape_fail(self):
        path = self.source / 'rb-example/SKILL.md'
        path.write_text(path.read_text().replace('name: rb-example', 'name: rb-wrong'))
        self.cli(good=False)
        self.assertFalse(self.dest.exists())
        self.profile['overrides']['rb-delegate'] = '../../../outside'
        self.save_profile()
        self.cli(good=False)
        self.assertFalse(self.dest.exists())

    def test_auto_claude_with_custom_destination_uses_generated_copies(self):
        home = self.root / 'home'
        (home / '.claude').mkdir(parents=True)
        env = dict(os.environ, HOME=str(home))
        env.pop('CODEX_HOME', None)
        result = subprocess.run([sys.executable, str(SYNC), str(self.source), '--dest', str(self.dest), '--skills', 'rb-example'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.dest / 'rb-example' / installer.MARKER).is_file())
        self.assertFalse((self.dest / 'rb-example').is_symlink())

    def test_sync_codex_retains_symlink_behaviour(self):
        result = subprocess.run([sys.executable, str(SYNC), str(self.source), '--agent', 'codex', '--dest', str(self.dest), '--skills', 'rb-example'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.dest / 'rb-example').is_symlink())
        self.assertEqual(self.original, self.snapshot(self.source))


if __name__ == '__main__':
    unittest.main()
