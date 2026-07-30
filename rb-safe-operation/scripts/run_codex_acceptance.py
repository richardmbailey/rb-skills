#!/usr/bin/env python3
"""Run a disposable Codex-native constrained acceptance scenario.

This driver belongs to the skill and must be invoked with the manifest-pinned
runtime interpreter. It never targets the skill repository itself.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time

from rb_safe_operation.acceptance import summarize_acceptance_run
from rb_safe_operation.canonical import artifact_hash, canonical_bytes, parse_json_strict
from rb_safe_operation.cli import cmd_codex_run
from rb_safe_operation.models import HashRef
from rb_safe_operation.patches import capture_file_metadata, metadata_fingerprint_hash
from rb_safe_operation.planning import select_markdown_phase
from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.project_policy import load_project_policy
from rb_safe_operation.proposal_models import (
    ApplyPatchActionV2,
    AssessmentBundleV2,
    BoundedAgentTaskV2,
    LowLevelPlanV2,
    RepositorySnapshotV2,
)
from rb_safe_operation.readiness import (
    confirm_run_preparation,
    prepare_run_authority,
    run_doctor,
)
from rb_safe_operation.readiness_models import (
    DoctorRequest,
    RunPreparationConfirmation,
    RunPreparationRequest,
)
from rb_safe_operation.state import capture_policy_snapshot
from rb_safe_operation.workflow import deterministic_preflight


def _ref(kind: str, version: str, payload: object) -> HashRef:
    return HashRef(
        artifact_type=kind,
        schema_version=version,
        value=artifact_hash(kind, version, payload),
    )


def _effect(effect_id: str, effect_class: str, targets: list[str]) -> dict[str, object]:
    return {
        "effect_id": effect_id,
        "kind": "direct",
        "effect_class": effect_class,
        "affected_party": "synthetic fixture owner",
        "data_classification": "internal",
        "security_sensitive": False,
        "unmitigated_severity": "low",
        "residual_severity": "low",
        "likelihood": "possible",
        "exposure": "repository",
        "reversibility": "full",
        "detectability": "full",
        "mitigation": "verified",
        "recovery": "tested",
        "cost_impact": "none",
        "availability_impact": "none",
        "approval_class": None,
        "targets": targets,
        "observation_sources": ["coordinator_observed"],
        "cumulative_interaction": "none",
        "cumulative_member_effect_ids": [],
        "evidence_ids": ["evidence-source"],
    }


def _operation_base(root: Path, operation_id: str) -> dict[str, object]:
    return {
        "operation_id": operation_id,
        "dependencies": [],
        "preconditions": ["the selected snapshot still matches"],
        "success_criteria": ["static_file_state::all declared target contents match"],
        "verifier_checks": [
            "static_file_state::target hashes equal the declared postimages",
            "static_file_state::product_diff",
            "static_file_state::undeclared_effects",
        ],
        "stop_conditions": ["identity mismatch", "policy denial", "unexpected path"],
        "path_contract": {
            "read_roots": [],
            "create_roots": [],
            "modify_roots": [],
            "delete_roots": [],
            "protected_roots": [
                str(root / ".rb-safe-operation"),
                str(root / ".rb-safe-operation-policy.json"),
            ],
            "working_directories": [str(root)],
        },
        "environment": [],
        "network_grants": [],
        "subprocesses": [],
        "delegation": [],
        "approval_classes": [],
        "effects": [],
        "effect_inventory_complete": True,
        "policy_references": ["O-001", "E-002"],
        "resource_limits": {
            "max_seconds": 600,
            "max_processes": 1,
            "max_bytes": 200_000,
            "max_calls": 1,
            "max_cost_decimal": "0",
            "attempt_limit": "unbounded",
        },
    }


def _authority(root: Path, run_id: str, model_calls: int):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ")
    request = RunPreparationRequest(
        schema_version="1.0",
        preparation_id=f"prep-{run_id}",
        run_id=run_id,
        project_root=str(root),
        adapter="json_line",
        provider="codex-cli",
        endpoint="host-mediated://codex-cli/exec",
        model="gpt-5.6-sol",
        model_revision=None,
        host_revision="0.146.0-alpha.3.1",
        credential_handle="CODEX_CHATGPT_LOGIN",
        credential_status="available",
        credential_audience="chatgpt-local-auth",
        roles=["plan_assessor", "proposer", "patch_assessor", "verifier"],
        request_data_classes=["internal_source"],
        response_data_classes=["patch_proposal", "patch_assessment", "typed_verification"],
        maximum_data_classification="internal",
        retention_disclosure=(
            "ephemeral local Codex thread; service retention follows the authenticated ChatGPT account"
        ),
        training_use="unknown",
        issued_at=stamp(now - timedelta(minutes=1)),
        expires_at=stamp(now + timedelta(hours=2)),
        max_provider_calls=model_calls,
        max_proposer_calls=1,
        max_assessor_calls=3 if model_calls == 4 else 2,
        max_model_requests=model_calls,
        max_read_tool_calls=0,
        max_read_tool_bytes=0,
        max_patch_bytes=200_000,
        max_request_bytes=2_000_000,
        max_response_bytes=1_000_000,
        max_input_tokens=250_000,
        max_output_tokens=40_000,
        max_elapsed_seconds=2_400,
        max_cost_decimal="0",
        cost_accounting="declared_zero",
        temperature_decimal="0",
        seed=None,
        structured_output_mode="native",
        redirect_endpoints=[],
        authorization_hash=_ref(
            "human-authorization", "1.0", {"authority": "codex-safe-acceptance"}
        ),
    )
    preview = prepare_run_authority(request)
    confirmation = RunPreparationConfirmation.from_statement(
        confirmation_id=f"confirm-{run_id}",
        preview_hash=preview.confirmation_binding_hash.value,
        statement=preview.exact_confirmation_statement,
        confirmed_at=stamp(now),
    )
    paths = confirm_run_preparation(preview, confirmation, preview.exact_confirmation_statement)
    return now, preview, paths


def _doctor_request(root: Path, run_id: str, observed_at: datetime, paths: dict[str, str]) -> DoctorRequest:
    repository_root = Path(__file__).resolve().parents[2]
    return DoctorRequest(
        schema_version="1.0",
        request_id=f"doctor-{run_id}",
        observed_at=observed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        project_root=str(root),
        requested_profile="codex_cli",
        adapter="json_line",
        requested_verification_modes=["static_file_state"],
        credential_handle="CODEX_CHATGPT_LOGIN",
        credential_status="available",
        provider_grant_path=paths["provider_grant"],
        run_resource_grant_path=paths["run_resource_grant"],
        schema_mirror_roots=[
            str(repository_root / skill / "references" / "generated")
            for skill in (
                "rb-create-low-level-plan",
                "rb-assess-plan-safety",
                "rb-safe-operation",
                "rb-create-safe-operation-policy",
            )
        ],
    )


def _build_plan(
    root: Path,
    run_id: str,
    scenario: str,
    preview,
    now: datetime,
    *,
    metadata_loader=capture_file_metadata,
) -> tuple[LowLevelPlanV2, dict[str, str]]:
    plan_file = root / "PLAN.md"
    expected: dict[str, str]
    if scenario == "exact-create":
        expected = {"created.txt": "created\n"}
        plan_file.write_text("# Plan\n\n## Phase 1: Create\nCreate created.txt exactly.\n", encoding="utf-8")
        selected = [str(plan_file)]
    elif scenario == "bounded-multi":
        expected = {"first.txt": "b\n", "second.txt": "y\n"}
        (root / "first.txt").write_text("a\n", encoding="utf-8")
        (root / "second.txt").write_text("x\n", encoding="utf-8")
        plan_file.write_text(
            "# Plan\n\n## Phase 1: Edit\nChange first.txt from a to b and second.txt from x to y.\n",
            encoding="utf-8",
        )
        selected = [str(plan_file), str(root / "first.txt"), str(root / "second.txt")]
    else:
        expected = {"input.txt": "b\n"}
        (root / "input.txt").write_text("a\n", encoding="utf-8")
        plan_file.write_text(
            "# Plan\n\n## Phase 1: Edit\nReplace the complete text a with b in input.txt only.\n",
            encoding="utf-8",
        )
        selected = [str(plan_file), str(root / "input.txt")]

    target_paths = [str(root / relative) for relative in expected]
    global_policy = default_global_policy(str(root))
    loaded_policy = load_project_policy(root, global_policy)
    snapshot_base = capture_policy_snapshot(
        loaded_policy,
        selected,
        [],
        target_paths,
        [str(root / ".rb-safe-operation")],
        metadata_loader=metadata_loader,
    )
    snapshot = RepositorySnapshotV2.model_validate(snapshot_base.model_dump(mode="json") | {
        "selected_file_metadata_hashes": {
            path: metadata_fingerprint_hash(metadata_loader(Path(path)))
            for path in snapshot_base.selected_file_hashes
        },
        "proposal_context_observation_hashes": {},
    })
    operation_data = _operation_base(root, "operation-1")
    if scenario == "exact-create":
        target = root / "created.txt"
        patch = "--- /dev/null\n+++ b/created.txt\n@@ -0,0 +1 @@\n+created\n"
        operation_data.update({
            "kind": "exact_action",
            "adapter": "apply_patch",
            "patch": patch,
            "patch_hash": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
            "preimage_hashes": {},
            "expected_created_paths": [str(target)],
            "expected_modified_paths": [],
            "expected_deleted_paths": [],
            "created_file_mode": 0o600,
        })
        operation_data["path_contract"]["create_roots"] = [str(root)]
        operation_data["effects"] = [_effect("effect-create", "repository_create", [str(target)])]
        operation = ApplyPatchActionV2.model_validate(operation_data)
    else:
        operation_data.update({
            "kind": "bounded_agent_task",
            "proposal_protocol": "unified_diff_v1",
            "goal": (
                "Replace first.txt content a newline with b newline and second.txt content x newline "
                "with y newline, changing no other file."
                if scenario == "bounded-multi"
                else "Replace input.txt content a newline with b newline, changing no other file."
            ),
            "non_goals": ["do not change PLAN.md or any undeclared path"],
            "evidence_ids": ["evidence-source"],
            "source_data_classification": "internal",
            "allowed_read_tools": [],
            "allowed_patch_actions": ["modify"],
            "created_file_mode": 0o600,
            "forbidden_actions": ["direct write", "shell", "network", "tools"],
            "permitted_adaptations": ["revise_local_code"],
            "diagnostic_checkpoint_rules": ["record a changed strategy"],
            "completion_evidence": ["completion-operation-1"],
            "escalation_conditions": ["scope change", "ambiguous source"],
            "required_adapter": "json_line",
            "required_assurance_profile": "instruction_only_proposal_host",
            "provider_grant_id": preview.provider_grant.grant_id,
            "run_resource_grant_id": preview.run_resource_grant.grant_id,
        })
        operation_data["path_contract"]["read_roots"] = [str(root)]
        operation_data["path_contract"]["modify_roots"] = [str(root)]
        operation_data["effects"] = [
            _effect("effect-modify", "repository_modify", [str(root)]),
            _effect("effect-read", "repository_read", [str(root)]),
        ]
        operation = BoundedAgentTaskV2.model_validate(operation_data)

    plan = LowLevelPlanV2.model_validate({
        "schema_version": "3.0",
        "plan_id": f"plan-{run_id}",
        "run_id": run_id,
        "source_phase": select_markdown_phase(str(plan_file), "phase-1").source.model_dump(mode="json"),
        "snapshot": snapshot.model_dump(mode="json"),
        "global_policy_hash": _ref("active-policy", "1.0", global_policy.model_dump(mode="json")).model_dump(mode="json"),
        "merged_policy_hash": _ref("active-policy", "2.0", loaded_policy.effective_policy.model_dump(mode="json")).model_dump(mode="json"),
        "operations": [operation.model_dump(mode="json")],
        "evidence": [{
            "evidence_id": "evidence-source",
            "provenance": "coordinator_observed",
            "locator": str(plan_file),
            "summary": "The selected synthetic source files are bound by the repository snapshot.",
        }],
        "later_phase_ids": [],
        "current_artifact_locations": [
            str(root / ".rb-safe-operation" / "artifacts" / run_id / "low-level-plan.json")
        ],
        "exact_next_action": "assess and execute through the confirmed Codex CLI profile",
        "semantic_guidance": ["This is a disposable static acceptance fixture with no external effects."],
        "provider_grant_hash": _ref("provider-grant", "1.0", preview.provider_grant.model_dump(mode="json")).model_dump(mode="json"),
        "run_resource_grant_hash": _ref("run-resource-grant", "1.0", preview.run_resource_grant.model_dump(mode="json")).model_dump(mode="json"),
        "policy_binding": loaded_policy.binding.model_dump(mode="json"),
    })
    current_snapshot_base = capture_policy_snapshot(
        loaded_policy,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
        metadata_loader=metadata_loader,
    )
    current_snapshot = RepositorySnapshotV2.model_validate(
        current_snapshot_base.model_dump(mode="json")
        | {
            "proposal_context_observation_hashes": dict(
                plan.snapshot.proposal_context_observation_hashes
            )
        }
    )
    preflight = deterministic_preflight(
        plan,
        global_policy,
        loaded_policy.effective_policy,
        current_snapshot,
        preview.host_capabilities,
        [],
        now=now,
        provider_grant=preview.provider_grant,
        run_resource_grant=preview.run_resource_grant,
    )
    if not preflight.deterministic_pass:
        raise RuntimeError(
            "acceptance fixture failed deterministic preflight: "
            + ", ".join(item.finding_id for item in preflight.findings)
        )
    return plan, expected


def _redacted_rejection_result(
    *,
    bundle: AssessmentBundleV2,
    raw: bytes,
    scenario: str,
    run_id: str,
    doctor_status: str,
    wall_milliseconds: int,
) -> dict[str, object]:
    """Describe a safe plan-assessment stop without copying finding prose or paths."""

    findings = bundle.assessment.findings
    return {
        "type": "codex_acceptance_rejected",
        "scenario": scenario,
        "run_id": run_id,
        "doctor_status": doctor_status,
        "assessment_bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "assessment_status": bundle.assessment.status,
        "assessment_safe": bundle.assessment.safe,
        "finding_ids": sorted(item.finding_id for item in findings),
        "finding_categories": sorted({item.category for item in findings}),
        "invariant_ids": sorted({item.invariant_id for item in findings}),
        "wall_milliseconds": wall_milliseconds,
        "manual_protocol_repair": False,
    }


def _load_rejected_assessment_result(
    *,
    root: Path,
    scenario: str,
    run_id: str,
    doctor_status: str,
    wall_milliseconds: int,
) -> dict[str, object] | None:
    path = root / ".rb-safe-operation" / "artifacts" / run_id / "assessment-bundle.json"
    if not path.is_file() or path.is_symlink():
        return None
    raw = path.read_bytes()
    bundle = AssessmentBundleV2.model_validate(parse_json_strict(raw))
    if raw != canonical_bytes(bundle.model_dump(mode="json")) + b"\n":
        raise ValueError("acceptance assessment bundle is not canonical")
    if bundle.assessment.safe or bundle.assessment.status != "rejected":
        return None
    return _redacted_rejection_result(
        bundle=bundle,
        raw=raw,
        scenario=scenario,
        run_id=run_id,
        doctor_status=doctor_status,
        wall_milliseconds=wall_milliseconds,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=("exact-create", "bounded-one", "bounded-multi"), required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id.startswith("codex-accept-"):
        raise ValueError("acceptance run IDs must start with codex-accept-")
    root = Path(tempfile.mkdtemp(prefix=f"rb-safe-{args.run_id}-")).resolve()
    calls = 3 if args.scenario == "exact-create" else 4
    now, preview, paths = _authority(root, args.run_id, calls)
    doctor = run_doctor(_doctor_request(root, args.run_id, now, paths))
    if doctor.status != "ready_codex_cli":
        codes = ", ".join(item.code for item in doctor.diagnostics if item.blocking)
        raise RuntimeError(f"Codex CLI readiness failed closed: {codes}")
    plan, expected = _build_plan(root, args.run_id, args.scenario, preview, now)
    fixed_plan = Path(plan.current_artifact_locations[0])
    fixed_plan.parent.mkdir(parents=True)
    fixed_plan.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
    started = time.monotonic()
    cmd_codex_run(SimpleNamespace(
        enable_codex_cli=True,
        plan=str(fixed_plan),
        run_preparation_preview=paths["run_preparation_preview"],
        approvals=None,
        prior_assessment_bundle=None,
        proposal_approvals=None,
        verifier_context_id=f"verifier-{args.run_id}",
    ))
    wall_milliseconds = round((time.monotonic() - started) * 1000)
    coordinator_bundle = (
        root / ".rb-safe-operation" / "runs" / args.run_id / "coordinator-bundle.json"
    )
    if not coordinator_bundle.is_file():
        rejected = _load_rejected_assessment_result(
            root=root,
            scenario=args.scenario,
            run_id=args.run_id,
            doctor_status=doctor.status,
            wall_milliseconds=wall_milliseconds,
        )
        if rejected is not None:
            print(json.dumps(rejected, sort_keys=True, separators=(",", ":")))
            return 2
    summary = summarize_acceptance_run(str(root), args.run_id)
    observed = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in expected
    }
    expected_hashes = {
        relative: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for relative, content in expected.items()
    }
    if summary.lifecycle_state != "verified" or observed != expected_hashes:
        raise RuntimeError("acceptance scenario did not reach the exact expected verified state")
    print(json.dumps({
        "type": "codex_acceptance_result",
        "scenario": args.scenario,
        "doctor_status": doctor.status,
        "run": summary.model_dump(mode="json"),
        "wall_milliseconds": wall_milliseconds,
        "expected_target_hashes": expected_hashes,
        "manual_protocol_repair": False,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
