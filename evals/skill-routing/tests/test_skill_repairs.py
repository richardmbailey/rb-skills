from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[3]


def load_module(relative_path: str, name: str):
    path = REPO / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CodexDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sync = load_module(
            "rb-sync-skills-repo/scripts/sync_skills_repo.py", "sync_skills_repo"
        )
        cls.install = load_module(
            "rb-install-skills/scripts/install_skills.py", "install_skills"
        )

    def test_codex_uses_agents_skills_independently_of_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(
            os.environ, {"CODEX_HOME": "/custom/control-plane"}, clear=False
        ), mock.patch.object(Path, "home", return_value=Path(temp)):
            expected = Path(temp) / ".agents" / "skills"
            self.assertEqual(self.sync.codex_dest(), expected)
            self.assertEqual(self.install.codex_skills_dest(), expected)

    def test_legacy_codex_skills_remain_searchable_but_are_not_install_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            Path, "home", return_value=Path(temp)
        ):
            modern = Path(temp) / ".agents" / "skills"
            legacy = Path(temp) / ".codex" / "skills"
            self.assertEqual(self.install.agent_skill_dirs("codex"), [modern, legacy])
            self.assertEqual(self.install.default_skills_destination("codex").path, modern)

    def test_project_resources_do_not_create_ignored_codex_md(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            results = self.install.install_flat_project_resources(
                target, force=False, claude=False, cursor=False
            )
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "CONTEXT.md").is_file())
            self.assertFalse((target / "CODEX.md").exists())
            self.assertEqual(len(results), 2)

    def test_codex_restart_is_only_a_visibility_fallback(self) -> None:
        sync_skill = (REPO / "rb-sync-skills-repo/SKILL.md").read_text(encoding="utf-8")
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("Codex detects skill changes automatically", sync_skill)
        self.assertIn("restart only when", sync_skill.lower())
        self.assertIn("Codex detects skill changes automatically", readme)
        self.assertNotIn("Restart Codex after", readme)


class ManualInvocationMetadataTests(unittest.TestCase):
    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["ruby", str(REPO / "evals/skill-routing/validate_skill_metadata.rb"), str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_manual_skill(self, root: Path, policy: str = "") -> None:
        skill = root / "rb-manual"
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: rb-manual\n"
            "description: Manual invocation only. Use only when the human explicitly requests $rb-manual.\n"
            "---\n\n# Manual\n",
            encoding="utf-8",
        )
        (skill / "agents/openai.yaml").write_text(
            "interface:\n"
            "  display_name: \"Manual\"\n"
            "  short_description: \"Run the requested manual workflow only\"\n"
            "  default_prompt: \"Use $rb-manual only when explicitly requested.\"\n"
            f"{policy}",
            encoding="utf-8",
        )

    def test_manual_only_skill_requires_implicit_invocation_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_manual_skill(root)
            result = self.run_validator(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("allow_implicit_invocation must be false", result.stderr)

    def test_manual_only_skill_accepts_explicit_false_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_manual_skill(
                root, "policy:\n  allow_implicit_invocation: false\n"
            )
            result = self.run_validator(root)
            self.assertEqual(result.returncode, 0, result.stderr)


class InstructionBoundaryTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (REPO / relative_path).read_text(encoding="utf-8")

    def test_no_literal_tilde_codex_home_fallback_remains(self) -> None:
        offenders = []
        for path in REPO.rglob("*.md"):
            if "retired-skills" in path.parts or "plans" in path.parts:
                continue
            if "${CODEX_HOME:-~/.codex}" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [])

    def test_diagnosis_only_does_not_author_test_edits(self) -> None:
        text = self.read("rb-diagnose/SKILL.md")
        self.assertIn("Do not create or edit that test during diagnosis-only work", text)
        self.assertIn("Do not edit implementation or tests during diagnosis-only work", text)

    def test_isolated_reviews_do_not_require_diary_writes(self) -> None:
        for skill in (
            "rb-architecture-review",
            "rb-explain-codebase",
            "rb-review-pr-or-diff",
            "rb-diagnose",
        ):
            text = self.read(f"{skill}/SKILL.md")
            self.assertIn("Do not write diary entries for an isolated one-turn", text, skill)

    def test_architecture_review_permits_no_findings(self) -> None:
        text = self.read("rb-architecture-review/SKILL.md")
        self.assertIn("Do not invent risks or refactoring work", text)
        self.assertIn("If no actionable architecture risks are supported by evidence", text)

    def test_multi_agent_skill_excludes_single_agent_components(self) -> None:
        text = self.read("rb-multi-agent-systems/SKILL.md")
        self.assertIn("Do not select this skill for a single-agent system", text)
        self.assertIn("references/test-and-review-checklists.md", text)


if __name__ == "__main__":
    unittest.main()
