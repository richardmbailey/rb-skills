from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rb_safe_operation.canonical import canonical_bytes
from rb_safe_operation.models import HashRef
from rb_safe_operation.patches import capture_file_metadata
from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.policy_models import (
    PathRule,
    PolicyConfirmation,
    ProjectPolicyProposal,
    ProjectPolicyV2,
)
from rb_safe_operation.project_policy import (
    ABSENT_POLICY_BYTES,
    POLICY_FILENAME,
    PolicyDenied,
    ProjectPolicyError,
    apply_confirmed_policy,
    build_policy_preview,
    evaluate_path,
    load_project_policy,
    policy_confirmation_statement,
    require_path,
)
from rb_safe_operation.state import capture_policy_snapshot


def policy(*rules: dict) -> ProjectPolicyV2:
    return ProjectPolicyV2.model_validate(
        {
            "schema_version": "2.0",
            "policy_version": "fixture-1",
            "path_rules": list(rules),
            "deny_operations": [],
            "deny_adapters": [],
            "deny_effect_classes": [],
            "deny_command_forms": [],
            "intersect_path_roots": None,
            "intersect_executable_hashes": None,
            "intersect_network_grants": None,
            "intersect_environment_names": None,
            "lower_maximums": {},
            "require_approvals": [],
            "require_minimum_enforcement": {},
            "require_minimum_observation": {},
            "require_evidence_sources": [],
            "require_verification": [],
        }
    )


def rule(rule_id: str, path: str, scope: str = "exact", deny=None) -> dict:
    return {
        "rule_id": rule_id,
        "path": path,
        "scope": scope,
        "deny": sorted(deny or ["create", "delete", "modify", "read"]),
        "reason": "fixture restriction",
    }


def portable_metadata(path: Path):
    return capture_file_metadata(path, acl_reader=lambda _: b"", xattr_reader=lambda _: {})


class ProjectPolicyModelTests(unittest.TestCase):
    def test_rejects_parent_absolute_control_and_noncanonical_capabilities(self):
        for path in ("../secret", "/secret", ".rb-safe-operation-policy.json", ".rb-safe-operation/run"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                PathRule.model_validate(rule("r1", path))
        noncanonical = rule("r1", "secret")
        noncanonical["deny"] = ["read", "create"]
        with self.assertRaises(ValueError):
            PathRule.model_validate(noncanonical)

    def test_rejects_duplicate_semantic_and_case_alias_rules(self):
        with self.assertRaises(ValueError):
            policy(rule("r1", "Secret.txt"), rule("r2", "secret.txt"))
        with self.assertRaises(ValueError):
            policy(rule("r1", "secret.txt"), rule("r2", "secret.txt"))


class ProjectPolicyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.global_policy = default_global_policy(str(self.root))

    def tearDown(self):
        self.temporary.cleanup()

    def write_policy(self, value: ProjectPolicyV2) -> None:
        (self.root / POLICY_FILENAME).write_bytes(canonical_bytes(value.model_dump(mode="json")) + b"\n")

    def test_fixed_root_discovery_and_canonical_absence_identity(self):
        nested = self.root / "nested"
        nested.mkdir()
        (nested / POLICY_FILENAME).write_text("not authoritative", encoding="utf-8")
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertEqual(loaded.binding.presence, "absent")
        self.assertEqual(
            loaded.binding.source_policy_sha256,
            hashlib.sha256(ABSENT_POLICY_BYTES).hexdigest(),
        )

    def test_rejects_noncanonical_symlink_hardlink_and_oversized_policy(self):
        target = self.root / "target.json"
        target.write_text("{}", encoding="utf-8")
        (self.root / POLICY_FILENAME).symlink_to(target)
        with self.assertRaises(ProjectPolicyError):
            load_project_policy(self.root, self.global_policy)
        (self.root / POLICY_FILENAME).unlink()
        (self.root / POLICY_FILENAME).hardlink_to(target)
        with self.assertRaises(ProjectPolicyError):
            load_project_policy(self.root, self.global_policy)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO fixtures require os.mkfifo")
    def test_policy_fifo_is_rejected_without_waiting_for_a_writer(self):
        fifo = self.root / POLICY_FILENAME
        os.mkfifo(fifo)
        with self.assertRaisesRegex(ProjectPolicyError, "regular file"):
            load_project_policy(self.root, self.global_policy)

    def test_exact_and_future_path_capabilities_are_independent(self):
        self.write_policy(policy(rule("deny-read", "future.txt", deny=["read"])))
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertFalse(evaluate_path(loaded, self.root / "future.txt", "read").allowed)
        self.assertTrue(evaluate_path(loaded, self.root / "future.txt", "create").allowed)
        (self.root / "future.txt").write_text("secret", encoding="utf-8")
        self.assertFalse(evaluate_path(loaded, self.root / "future.txt", "read").allowed)

    def test_subtree_is_component_aware(self):
        self.write_policy(policy(rule("deny-tree", "private", scope="subtree", deny=["read"])))
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertFalse(evaluate_path(loaded, self.root / "private" / "x", "read").allowed)
        self.assertTrue(evaluate_path(loaded, self.root / "private-copy" / "x", "read").allowed)

    def test_ancestor_mutation_cannot_bypass_governed_descendant(self):
        self.write_policy(policy(rule("deny-child", "directory/protected.txt", deny=["delete", "modify"])))
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertFalse(evaluate_path(loaded, self.root / "directory", "delete").allowed)
        self.assertFalse(evaluate_path(loaded, self.root / "directory", "modify").allowed)
        self.assertFalse(evaluate_path(loaded, self.root, "delete").allowed)

    def test_parent_traversal_and_outside_aliases_are_rejected_before_normalisation(self):
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        alias = outside / "project-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        loaded = load_project_policy(self.root, self.global_policy)
        try:
            with self.assertRaisesRegex(ProjectPolicyError, "parent traversal"):
                evaluate_path(loaded, self.root / "directory" / ".." / "x.txt", "read")
            with self.assertRaisesRegex(ProjectPolicyError, "outside the authoritative project root"):
                evaluate_path(loaded, alias / "x.txt", "read")
        finally:
            alias.unlink()
            outside.rmdir()

    def test_symlink_and_hardlink_uncertainty_fail_closed(self):
        target = self.root / "target.txt"
        target.write_text("value", encoding="utf-8")
        alias = self.root / "alias.txt"
        alias.symlink_to(target)
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertFalse(evaluate_path(loaded, alias, "read").allowed)
        alias.unlink()
        alias.hardlink_to(target)
        self.assertFalse(evaluate_path(loaded, target, "read").allowed)

    def test_snapshot_never_opens_denied_file_and_never_descends_denied_subtree(self):
        secret = self.root / "secret.txt"
        secret.write_text("CANARY-CONTENT", encoding="utf-8")
        private = self.root / "private"
        private.mkdir()
        descendant = private / "UNSEEN-NAME.txt"
        descendant.write_text("SECOND-CANARY", encoding="utf-8")
        allowed = self.root / "allowed.txt"
        allowed.write_text("allowed", encoding="utf-8")
        self.write_policy(
            policy(
                rule("deny-secret", "secret.txt", deny=["read"]),
                rule("deny-private", "private", scope="subtree", deny=["read"]),
            )
        )
        loaded = load_project_policy(self.root, self.global_policy)
        import rb_safe_operation.state as state
        original = state.sha256_file
        opened: list[str] = []

        def observed_hash(path):
            opened.append(str(path))
            if Path(path) in {secret, descendant}:
                raise AssertionError("denied content was opened")
            return original(path)

        with patch.object(state, "sha256_file", side_effect=observed_hash):
            snapshot = capture_policy_snapshot(
                loaded,
                [str(secret), str(allowed)],
                [str(secret)],
                [],
                metadata_loader=portable_metadata,
            )
        serialized = canonical_bytes(snapshot.model_dump(mode="json"))
        self.assertNotIn(b"CANARY-CONTENT", serialized)
        self.assertNotIn(b"UNSEEN-NAME", serialized)
        self.assertNotIn(str(secret), snapshot.selected_file_hashes)
        self.assertIn(str(allowed), snapshot.selected_file_hashes)
        self.assertEqual(snapshot.unobserved_subtree_rule_ids, ["deny-private"])
        self.assertEqual(
            snapshot.full_file_inventory["secret.txt"],
            "unobserved-policy-denied:rules=deny-secret",
        )
        self.assertEqual(
            snapshot.full_file_inventory["private"],
            "unobserved-policy-denied:rules=deny-private",
        )
        self.assertNotIn(str(secret), opened)
        self.assertNotIn(str(descendant), opened)

    def test_require_path_raises_typed_denial(self):
        self.write_policy(policy(rule("deny-delete", "x.txt", deny=["delete"])))
        loaded = load_project_policy(self.root, self.global_policy)
        with self.assertRaises(PolicyDenied) as caught:
            require_path(loaded, self.root / "x.txt", "delete")
        self.assertEqual(caught.exception.decision.matched_rule_ids, ["deny-delete"])

    def test_policy_file_and_control_state_have_fixed_protection(self):
        loaded = load_project_policy(self.root, self.global_policy)
        self.assertFalse(evaluate_path(loaded, self.root / POLICY_FILENAME, "modify").allowed)
        self.assertTrue(evaluate_path(loaded, self.root / POLICY_FILENAME, "read").allowed)
        self.assertFalse(
            evaluate_path(loaded, self.root / ".rb-safe-operation" / "runs" / "x", "read").allowed
        )

    def test_preview_expands_write_and_classifies_tightening(self):
        loaded = load_project_policy(self.root, self.global_policy)
        proposed = policy(rule("deny-x", "x.txt"))
        proposal = ProjectPolicyProposal(
            schema_version="1.0",
            request_token="request-fixture",
            proposed_policy=proposed,
            ambiguity_questions=[],
            interpretation_summary="Deny all content and mutation operations for x.txt.",
            no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        self.assertEqual(preview.change_classification, "create")
        self.assertIn("User-facing write means create, modify, and delete.", preview.plain_language_lines)

    def test_preview_classifies_exact_to_subtree_as_tightening_only(self):
        self.write_policy(policy(rule("deny-x", "private", deny=["read"])))
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(rule("deny-x", "private", scope="subtree", deny=["read"])),
            ambiguity_questions=[], interpretation_summary="Extend the read denial to the subtree.",
            no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        self.assertEqual(preview.change_classification, "tightening")

    def test_preview_classifies_subtree_to_exact_as_relaxation_only(self):
        self.write_policy(policy(rule("deny-x", "private", scope="subtree", deny=["read"])))
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(rule("deny-x", "private", deny=["read"])),
            ambiguity_questions=[], interpretation_summary="Limit the read denial to the exact path.",
            no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        self.assertEqual(preview.change_classification, "relaxation")

    def test_preview_refuses_ambiguity(self):
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(), ambiguity_questions=["Does touch include reading?"],
            interpretation_summary="Ambiguous request.", no_protected_content_observed=True,
        )
        with self.assertRaises(ProjectPolicyError):
            build_policy_preview(loaded, proposal, "instruction_only_authoring")

    def test_preview_classifies_non_path_relaxation_from_complete_effective_authority(self):
        existing = policy().model_copy(update={"deny_operations": ["dangerous-operation"]})
        self.write_policy(existing)
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(), ambiguity_questions=[],
            interpretation_summary="Remove the operation denial.",
            no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        self.assertEqual(preview.change_classification, "relaxation")

    def test_apply_recomputes_preview_and_rejects_forged_relaxation_classification(self):
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        existing = policy(rule("deny-x", "x.txt"))
        self.write_policy(existing)
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(), ambiguity_questions=[],
            interpretation_summary="Remove the x.txt restriction.",
            no_protected_content_observed=True,
        )
        real_preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        forged_preview = real_preview.model_copy(update={"change_classification": "reason_only"})
        from rb_safe_operation.canonical import artifact_hash
        confirmation = PolicyConfirmation(
            schema_version="1.0", proposal_hash=forged_preview.proposal_hash,
            preview_hash=HashRef(
                artifact_type="policy-preview", schema_version="1.0",
                value=artifact_hash("policy-preview", "1.0", forged_preview.model_dump(mode="json")),
            ),
            confirmation_token=forged_preview.confirmation_token,
            statement_sha256=hashlib.sha256(
                policy_confirmation_statement(forged_preview).encode("utf-8")
            ).hexdigest(),
            relaxation_explicitly_confirmed=False,
            confirmed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            confirmation_assurance="instruction_only",
        )
        with self.assertRaisesRegex(ProjectPolicyError, "deterministic current preview"):
            apply_confirmed_policy(
                loaded, proposal, forged_preview, confirmation, control_root=control
            )
        self.assertEqual((self.root / POLICY_FILENAME).read_bytes(), canonical_bytes(existing.model_dump(mode="json")) + b"\n")

    def test_confirmed_compare_and_swap_create(self):
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(rule("deny-x", "x.txt")), ambiguity_questions=[],
            interpretation_summary="Deny x.txt.", no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        confirmation = PolicyConfirmation(
            schema_version="1.0", proposal_hash=preview.proposal_hash,
            preview_hash=HashRef(artifact_type="policy-preview", schema_version="1.0", value=(
                __import__("rb_safe_operation.canonical", fromlist=["artifact_hash"]).artifact_hash(
                    "policy-preview", "1.0", preview.model_dump(mode="json")
                )
            )),
            confirmation_token=preview.confirmation_token,
            statement_sha256=hashlib.sha256(
                policy_confirmation_statement(preview).encode("utf-8")
            ).hexdigest(),
            relaxation_explicitly_confirmed=False,
            confirmed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            confirmation_assurance="instruction_only",
        )
        with self.assertRaisesRegex(ProjectPolicyError, "exact preview statement"):
            apply_confirmed_policy(
                loaded,
                proposal,
                preview,
                confirmation.model_copy(update={"statement_sha256": "0" * 64}),
                control_root=control,
            )
        record = apply_confirmed_policy(
            loaded, proposal, preview, confirmation, control_root=control
        )
        self.assertEqual(record.outcome, "committed")
        self.assertEqual(load_project_policy(self.root, self.global_policy).project_policy, proposal.proposed_policy)

    def test_stale_compare_and_swap_leaves_newer_policy_unchanged(self):
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(rule("deny-x", "x.txt")), ambiguity_questions=[],
            interpretation_summary="Deny x.txt.", no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        newer = policy(rule("deny-y", "y.txt"))
        self.write_policy(newer)
        confirmation = PolicyConfirmation(
            schema_version="1.0", proposal_hash=preview.proposal_hash,
            preview_hash=HashRef(artifact_type="policy-preview", schema_version="1.0", value=(
                __import__("rb_safe_operation.canonical", fromlist=["artifact_hash"]).artifact_hash(
                    "policy-preview", "1.0", preview.model_dump(mode="json")
                )
            )),
            confirmation_token=preview.confirmation_token,
            statement_sha256=hashlib.sha256(
                policy_confirmation_statement(preview).encode("utf-8")
            ).hexdigest(),
            relaxation_explicitly_confirmed=False,
            confirmed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            confirmation_assurance="instruction_only",
        )
        with self.assertRaises(ProjectPolicyError):
            apply_confirmed_policy(loaded, proposal, preview, confirmation, control_root=control)
        self.assertEqual((self.root / POLICY_FILENAME).read_bytes(), canonical_bytes(newer.model_dump(mode="json")) + b"\n")

    def test_post_replacement_failure_records_indeterminate_transaction(self):
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        loaded = load_project_policy(self.root, self.global_policy)
        proposal = ProjectPolicyProposal(
            schema_version="1.0", request_token="request-fixture",
            proposed_policy=policy(rule("deny-x", "x.txt")), ambiguity_questions=[],
            interpretation_summary="Deny x.txt.", no_protected_content_observed=True,
        )
        preview = build_policy_preview(loaded, proposal, "instruction_only_authoring")
        confirmation = PolicyConfirmation(
            schema_version="1.0", proposal_hash=preview.proposal_hash,
            preview_hash=HashRef(artifact_type="policy-preview", schema_version="1.0", value=(
                __import__("rb_safe_operation.canonical", fromlist=["artifact_hash"]).artifact_hash(
                    "policy-preview", "1.0", preview.model_dump(mode="json")
                )
            )),
            confirmation_token=preview.confirmation_token,
            statement_sha256=hashlib.sha256(
                policy_confirmation_statement(preview).encode("utf-8")
            ).hexdigest(),
            relaxation_explicitly_confirmed=False,
            confirmed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            confirmation_assurance="instruction_only",
        )

        from rb_safe_operation import project_policy as project_policy_module

        original_read = project_policy_module._read_regular_nofollow

        def fail_committed_policy_read(path: Path, *args, **kwargs):
            if path == loaded.policy_path and path.exists():
                raise OSError("simulated post-replacement read failure")
            return original_read(path, *args, **kwargs)

        with patch.object(
            project_policy_module,
            "_read_regular_nofollow",
            side_effect=fail_committed_policy_read,
        ), self.assertRaisesRegex(ProjectPolicyError, "human inspection is required"):
            apply_confirmed_policy(
                loaded, proposal, preview, confirmation, control_root=control
            )

        self.assertEqual(
            loaded.policy_path.read_bytes(),
            canonical_bytes(proposal.proposed_policy.model_dump(mode="json")) + b"\n",
        )
        authoring_roots = list((control / "artifacts" / "policy-authoring").iterdir())
        self.assertEqual(len(authoring_roots), 1)
        self.assertTrue((authoring_roots[0] / "indeterminate.json").is_file())
        self.assertFalse((authoring_roots[0] / "committed.json").exists())


if __name__ == "__main__":
    unittest.main()
