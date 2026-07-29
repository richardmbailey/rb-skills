from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.workflow import _assess_plan_legacy_compatible as assess_plan

from helpers import capabilities, current_snapshot, safe_plan, semantic


class VerificationModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _assess(self, plan):
        policy = default_global_policy(str(self.root))
        return assess_plan(
            plan,
            policy,
            policy,
            current_snapshot(plan),
            capabilities(),
            semantic(),
            [],
        )

    def test_typed_static_requirements_pass(self):
        assessment = self._assess(safe_plan(self.root))
        self.assertTrue(assessment.safe)
        self.assertTrue(assessment.deterministic_pass)

    def test_untyped_requirement_fails_deterministically(self):
        plan = safe_plan(self.root)
        operation = plan.operations[0].model_copy(
            update={"success_criteria": ["operation completes"]}
        )
        assessment = self._assess(plan.model_copy(update={"operations": [operation]}))
        self.assertFalse(assessment.safe)
        self.assertFalse(assessment.deterministic_pass)
        self.assertTrue(
            any(item.finding_id.startswith("verification-format-") for item in assessment.findings)
        )

    def test_executable_and_runtime_modes_fail_deterministically(self):
        for mode in ("executable_test", "runtime_observation", "external_observation"):
            with self.subTest(mode=mode):
                plan = safe_plan(self.root)
                operation = plan.operations[0].model_copy(
                    update={
                        "verifier_checks": [
                            *plan.operations[0].verifier_checks,
                            f"{mode}::service reports healthy",
                        ]
                    }
                )
                assessment = self._assess(plan.model_copy(update={"operations": [operation]}))
                self.assertFalse(assessment.safe)
                self.assertFalse(assessment.deterministic_pass)
                self.assertTrue(
                    any(item.finding_id.startswith("verification-mode-") for item in assessment.findings)
                )


if __name__ == "__main__":
    unittest.main()
