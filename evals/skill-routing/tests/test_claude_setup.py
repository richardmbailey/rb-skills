from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_skill_repairs import REPO, load_module


class ClaudeSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install = load_module("rb-install-skills/scripts/install_skills.py", "claude_setup_install")

    def test_claude_resource_imports_shared_instructions(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self.install.install_flat_project_resources(target, False, True, False)
            bridge = (target / "CLAUDE.md").read_text()
            self.assertIn("@AGENTS.md", bridge)
            self.assertIn("user", bridge)
            self.assertNotEqual(bridge, (target / "AGENTS.md").read_text())

    def test_existing_project_instructions_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for name in ["CLAUDE.md", "AGENTS.md", "CONTEXT.md"]:
                (target / name).write_text("user owned " + name)
            self.install.install_flat_project_resources(target, False, True, False)
            for name in ["CLAUDE.md", "AGENTS.md", "CONTEXT.md"]:
                self.assertEqual((target / name).read_text(), "user owned " + name)

    def test_claude_target_gets_bridge_without_optional_flag(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(self.install, "run"), mock.patch.object(self.install, "audit_flat_visibility"):
            target = Path(temp)
            args = argparse.Namespace(agent="claude", replace_skills=False, force=False, claude=False, cursor=False)
            self.install.run_flat_install_skills(REPO, target, args)
            self.assertIn("@AGENTS.md", (target / "CLAUDE.md").read_text())

    def test_claude_visibility_uses_generated_content_check(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(self.install, "run") as run:
            dest = self.install.SkillsDestination(Path(temp), "claude")
            self.install.audit_flat_visibility(REPO, dest)
            command = run.call_args.args[0]
            self.assertIn("--check", command)
            self.assertIn(str(REPO / "platforms/claude/install.py"), command)

    def test_generated_marker_recovers_source(self):
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "rb-install-skills"
            skill.mkdir()
            (skill / "SKILL.md").write_text("generated")
            (skill / ".rb-claude-install.json").write_text(json.dumps({"source": str(REPO)}))
            with mock.patch.object(self.install, "agent_skill_dirs", return_value=[Path(temp)]):
                candidates = []
                self.install.add_global_skill_link_candidates(candidates, "claude")
            self.assertIn(REPO, candidates)

    def test_bad_marker_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "rb-install-skills"
            skill.mkdir()
            (skill / ".rb-claude-install.json").write_text("not JSON")
            with mock.patch.object(self.install, "agent_skill_dirs", return_value=[Path(temp)]):
                candidates = []
                self.install.add_global_skill_link_candidates(candidates, "claude")
            self.assertEqual(candidates, [])

    def test_codex_target_still_uses_existing_resources(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(self.install, "run"), mock.patch.object(self.install, "audit_flat_visibility"):
            target = Path(temp)
            args = argparse.Namespace(agent="codex", replace_skills=False, force=False, claude=False, cursor=False)
            self.install.run_flat_install_skills(REPO, target, args)
            self.assertFalse((target / "CLAUDE.md").exists())
            self.assertTrue((target / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
