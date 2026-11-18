"""Exercise the setup CLI in a disposable home, source pack and repository."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "rb-install-skills/scripts/install_skills.py"
SYNC = Path("rb-sync-skills-repo/scripts/sync_skills_repo.py")


def snapshot(root):
    entries = {}
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        content = None
        if stat.S_ISLNK(mode):
            content = os.readlink(path)
        elif stat.S_ISREG(mode):
            content = path.read_bytes() if os.access(path, os.R_OK) else "unreadable"
        entries[path.relative_to(root)] = (mode, path.lstat().st_mtime_ns, content)
    return entries


class CheckTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.home = self.root / "home"
        self.pack = self.root / "pack"
        self.target = self.root / "project"
        self.dest = self.root / "custom"
        self.home.mkdir()
        self.target.mkdir()
        self.skill = self.pack / "rb-example"
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("---\nname: rb-example\n---\nExample\n")
        (self.pack / SYNC).parent.mkdir(parents=True)
        shutil.copyfile(ROOT / SYNC, self.pack / SYNC)
        self.env = {"HOME": str(self.home), "PATH": os.defpath}
        self.modern = self.home / ".agents/skills"
        self.legacy = self.home / ".codex/skills"

    def command(self, *options):
        return subprocess.run(
            [sys.executable, str(CLI), "--target", str(self.target),
             "--pack-root", str(self.pack), "--agent", "codex", *map(str, options)],
            cwd=self.root, env=self.env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=20,
        )

    def check(self, success, *options):
        before = snapshot(self.root)
        result = self.command("--check", *options)
        self.assertEqual(before, snapshot(self.root), result.stdout)
        self.assertEqual(result.returncode == 0, success, result.stdout)
        self.assertNotIn("continue onboarding now", result.stdout)
        self.assertNotIn("Traceback", result.stdout)
        return result.stdout

    def install(self, *options):
        result = self.command(*options)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_default_and_requested_resources(self):
        output = self.check(False)
        for path in [self.modern, self.target / "AGENTS.md", self.target / "CONTEXT.md"]:
            self.assertIn(str(path), output)
        self.install()
        self.check(True)
        output = self.check(False, "--claude", "--cursor")
        for path in ["CLAUDE.md", ".cursor/rules/rb-workflow.mdc"]:
            self.assertIn(path, output)
        self.install("--claude", "--cursor")
        self.check(True, "--claude", "--cursor")

    def test_custom_destination_and_project_local_gap(self):
        self.install("--dest", self.dest)
        self.assertEqual((self.dest / "rb-example").resolve(), self.skill)
        self.assertFalse(self.modern.exists())
        self.check(True, "--dest", self.dest)
        local = self.target / ".rb-agent/skills"
        local.parent.mkdir()
        local.symlink_to(self.root / "missing")
        self.assertIn(str(local), self.check(False, "--dest", self.dest))

    def test_use_existing_codex_installation(self):
        self.legacy.mkdir(parents=True)
        (self.legacy / self.skill.name).symlink_to(self.skill)
        self.install()
        self.assertFalse(self.modern.exists())
        self.check(True)
        self.assertIn(str(self.modern), self.check(False, "--dest", self.modern))

    def test_working_legacy_links_take_precedence_over_a_modern_name_collision(self):
        self.install("--dest", self.legacy)
        self.modern.mkdir(parents=True)
        (self.modern / self.skill.name).mkdir()
        self.assertIn(str(self.legacy), self.check(True))
        self.install()
        self.assertFalse((self.modern / self.skill.name).is_symlink())

    def test_two_separate_installations_require_a_destination(self):
        self.install("--dest", self.legacy)
        self.install("--dest", self.modern)
        self.assertIn("--dest", self.check(False))
        before = snapshot(self.root)
        result = self.command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--dest", result.stdout)
        self.assertEqual(before, snapshot(self.root))
        self.check(True, "--dest", self.legacy)
        self.check(True, "--dest", self.modern)

    def test_conflicts_in_both_directories_require_a_destination(self):
        self.modern.mkdir(parents=True)
        (self.modern / self.skill.name).mkdir()
        self.legacy.mkdir(parents=True)
        (self.legacy / self.skill.name).symlink_to(self.root / "missing")
        self.assertIn("--dest", self.check(False))
        self.assertIn("is not a symlink", self.check(False, "--dest", self.modern))
        self.assertIn("Broken link", self.check(False, "--dest", self.legacy))

    def test_aliased_skills_directories_count_as_one_installation(self):
        self.install("--dest", self.legacy)
        self.modern.parent.mkdir()
        self.modern.symlink_to(self.legacy, target_is_directory=True)
        self.check(True)

    def test_report_wrong_copied_missing_and_looping_links(self):
        self.install()
        link = self.modern / self.skill.name
        link.unlink()
        self.assertIn(self.skill.name, self.check(False))
        link.mkdir()
        self.assertIn("symlink", self.check(False))
        link.rmdir()
        link.symlink_to(self.target)
        self.assertIn(str(self.target), self.check(False))
        link.unlink()
        link.symlink_to(link.name)
        self.assertIn(link.name, self.check(False))

    @unittest.skipIf(os.geteuid() == 0, "root can read mode-000 files")
    def test_unreadable_skill(self):
        self.install()
        definition = self.skill / "SKILL.md"
        definition.chmod(0)
        self.addCleanup(definition.chmod, 0o644)
        self.assertIn("SKILL.md", self.check(False))

    def test_claude_generated_content_and_permissions(self):
        platform = self.pack / "platforms/claude"
        platform.mkdir(parents=True)
        for name in ["install.py", "preamble.md"]:
            shutil.copyfile(ROOT / "platforms/claude" / name, platform / name)
        (platform / "profile.json").write_text(json.dumps({
            "schema_version": 1, "portable_skills": [self.skill.name],
            "excluded_skills": [], "manual_only": [], "overrides": {},
        }))
        options = ["--agent", "claude", "--dest", self.dest]
        self.install(*options)
        self.check(True, *options)
        bridge = self.target / "CLAUDE.md"
        bridge.unlink()
        self.assertIn(str(bridge), self.check(False, *options))
        bridge.write_text("User instructions")
        generated = self.dest / self.skill.name / "SKILL.md"
        generated.chmod(0o700)
        self.assertIn("drift", self.check(False, *options))
        generated.write_text("Edited locally")
        generated.chmod((self.skill / "SKILL.md").stat().st_mode)
        self.assertIn("drift", self.check(False, *options))

    def test_legacy_check_never_invokes_helpers(self):
        (self.pack / "skills").mkdir()
        scripts = self.pack / "scripts"
        scripts.mkdir()
        for name in ["install_global_skills", "install_local_pack", "audit_skill_visibility"]:
            (scripts / (name + ".py")).write_text("open('helper-ran', 'w').close()")
        self.assertIn("unsupported for legacy packs", self.check(False))

    def test_explicit_destination_cannot_replace_source(self):
        before = snapshot(self.root)
        output = self.command("--dest", self.pack, "--replace-skills")
        self.assertNotEqual(output.returncode, 0)
        self.assertIn("overlap", output.stdout)
        self.assertEqual(before, snapshot(self.root))

    def test_automatically_selected_destination_cannot_replace_source(self):
        for destination, source in ((self.modern, self.skill), (self.legacy, self.pack)):
            with self.subTest(destination=destination):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(source, target_is_directory=True)
                try:
                    before = snapshot(self.root)
                    result = self.command("--replace-skills")
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("overlap", result.stdout)
                    self.assertEqual(before, snapshot(self.root))
                finally:
                    destination.unlink()

    def test_check_rejects_replacement_flags(self):
        for option in ["--force", "--replace-skills"]:
            with self.subTest(option=option):
                self.assertIn(option, self.check(False, option))
