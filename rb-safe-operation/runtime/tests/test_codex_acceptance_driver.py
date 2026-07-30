from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from rb_safe_operation.patches import capture_file_metadata


DRIVER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "run_codex_acceptance.py"
SPEC = importlib.util.spec_from_file_location("run_codex_acceptance", DRIVER_PATH)
assert SPEC is not None and SPEC.loader is not None
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


class CodexAcceptanceDriverTests(unittest.TestCase):
    def test_rejected_assessment_result_is_redacted_and_does_not_need_coordinator_bundle(self) -> None:
        raw = b'{"synthetic":"canonical assessment bytes"}\n'
        finding = SimpleNamespace(
            finding_id="finding-source-context",
            category="incomplete_operation",
            invariant_id="O-001",
            explanation="synthetic source text that must not be copied",
        )
        bundle = SimpleNamespace(
            assessment=SimpleNamespace(
                findings=[finding],
                status="rejected",
                safe=False,
            )
        )
        result = DRIVER._redacted_rejection_result(
            bundle=bundle,
            raw=raw,
            scenario="bounded-one",
            run_id="codex-accept-test-rejected",
            doctor_status="ready_codex_cli",
            wall_milliseconds=123,
        )
        self.assertEqual(result["type"], "codex_acceptance_rejected")
        self.assertEqual(result["finding_ids"], ["finding-source-context"])
        self.assertEqual(result["assessment_safe"], False)
        self.assertEqual(result["assessment_bundle_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("explanation", result)
        self.assertNotIn("synthetic source text", str(result))

    def test_all_scenarios_build_and_pass_deterministic_preflight(self) -> None:
        for scenario, calls, expected in (
            ("exact-create", 3, {"created.txt": "created\n"}),
            ("bounded-one", 4, {"input.txt": "b\n"}),
            ("bounded-multi", 4, {"first.txt": "b\n", "second.txt": "y\n"}),
        ):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                run_id = f"codex-accept-test-{scenario}"
                now, preview, _ = DRIVER._authority(root, run_id, calls)
                plan, observed_expected = DRIVER._build_plan(
                    root,
                    run_id,
                    scenario,
                    preview,
                    now,
                    metadata_loader=lambda path: capture_file_metadata(
                        path,
                        acl_reader=lambda _: b"",
                        xattr_reader=lambda _: {},
                    ),
                )
                self.assertEqual(observed_expected, expected)
                self.assertEqual(plan.run_id, run_id)
                self.assertEqual(len(plan.operations), 1)
                self.assertEqual(
                    plan.operations[0].kind,
                    "exact_action" if scenario == "exact-create" else "bounded_agent_task",
                )

    def test_doctor_request_binds_confirmed_authority_and_installed_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            run_id = "codex-accept-test-doctor"
            now, _, paths = DRIVER._authority(root, run_id, 3)
            request = DRIVER._doctor_request(root, run_id, now, paths)
            self.assertEqual(request.requested_profile, "codex_cli")
            self.assertEqual(request.provider_grant_path, paths["provider_grant"])
            self.assertEqual(request.run_resource_grant_path, paths["run_resource_grant"])
            self.assertEqual(len(request.schema_mirror_roots), 4)
            self.assertEqual(
                {Path(item).parent.parent.name for item in request.schema_mirror_roots},
                {
                    "rb-create-low-level-plan",
                    "rb-assess-plan-safety",
                    "rb-safe-operation",
                    "rb-create-safe-operation-policy",
                },
            )


if __name__ == "__main__":
    unittest.main()
