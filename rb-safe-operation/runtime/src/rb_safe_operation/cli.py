from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from . import SCHEMA_VERSION, __version__
from .canonical import CanonicalizationError, artifact_hash, canonical_bytes, parse_json_strict, sha256_file, source_tree_hash
from .models import (
    ActivePolicy,
    Approval,
    AssessmentBundle,
    DeterministicPreflight,
    Finding,
    HostCapabilities,
    LowLevelPlan,
    ProjectPolicy,
    RepairAttempt,
    SemanticAssessmentProposal,
    VerificationProposal,
)
from .policy import default_global_policy, merge_policy
from .planning import discover_instruction_files, select_markdown_phase
from .schemas import MODELS, check_drift, export_schemas
from .state import capture_snapshot
from .workflow import ExecutionCoordinator, assess_plan, canonical_semantic_proposal, canonical_semantic_proposal_for_plan, default_host_capabilities, deterministic_preflight, hash_ref


DIAGNOSTICS = {
    "missing_runtime_skill", "missing_runtime_environment", "missing_runtime_manifest", "missing_pydantic",
    "unsupported_python_version", "unsupported_pydantic_version", "runtime_source_hash_mismatch",
    "runtime_schema_version_mismatch", "generated_schema_drift", "unsupported_artifact_version",
    "unsupported_host_capability", "copy_install_dependency_missing",
}


def _load(path: str) -> Any:
    return parse_json_strict(Path(path).read_bytes())


def _write(value: Any, destination: str | None) -> None:
    data = canonical_bytes(value) + b"\n"
    if destination:
        Path(destination).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def _model(name: str):
    try:
        return MODELS[name]
    except KeyError as exc:
        raise ValueError(f"unsupported artifact type: {name}") from exc


def _canonical_model(path: str, model_type):
    artifact_path = Path(path)
    payload = _load(path)
    model = model_type.model_validate(payload)
    if artifact_path.read_bytes() != canonical_bytes(model.model_dump(mode="json")) + b"\n":
        raise ValueError(f"artifact is not exact canonical JSON with one trailing newline: {artifact_path}")
    return model


def _fixed_artifact_path(plan: LowLevelPlan, artifact_type: str) -> Path:
    control = Path(plan.snapshot.project_root) / ".rb-safe-operation"
    if plan.snapshot.control_plane_roots != [str(control)]:
        raise ValueError("plan does not use the canonical project control root")
    return control / "artifacts" / plan.run_id / f"{artifact_type}.json"


def _load_fixed_plan(path: str) -> LowLevelPlan:
    plan = _canonical_model(path, LowLevelPlan)
    expected = _fixed_artifact_path(plan, "low-level-plan")
    supplied = Path(path)
    if not supplied.is_absolute() or supplied.is_symlink() or supplied.resolve(strict=True) != expected:
        raise ValueError(f"low-level plan must be loaded from its fixed create-only path: {expected}")
    if plan.current_artifact_locations != [str(expected)]:
        raise ValueError("low-level plan does not bind its fixed durable artifact location")
    return plan


def _load_fixed_assessment_bundle(path: str, plan: LowLevelPlan) -> AssessmentBundle:
    bundle = _canonical_model(path, AssessmentBundle)
    expected = _fixed_artifact_path(plan, "assessment-bundle")
    supplied = Path(path)
    if not supplied.is_absolute() or supplied.is_symlink() or supplied.resolve(strict=True) != expected:
        raise ValueError(f"assessment bundle must be loaded from its fixed create-only path: {expected}")
    if bundle.assessment.plan_hash.value != artifact_hash("low-level-plan", "1.0", plan.model_dump(mode="json")):
        raise ValueError("assessment bundle is not bound to the fixed low-level plan")
    if bundle.semantic_proposal != canonical_semantic_proposal(bundle.semantic_proposal):
        raise ValueError("assessment bundle semantic proposal is not persistence-safe canonical form")
    return bundle


def _persist_handoff(plan: LowLevelPlan, artifact_type: str, artifact: Any) -> dict[str, str]:
    target = _fixed_artifact_path(plan, artifact_type)
    control = target.parents[2]
    if control.is_symlink():
        raise ValueError("canonical control root must not be a symbolic link")
    control.mkdir(mode=0o700, exist_ok=True)
    if not control.is_dir():
        raise ValueError("canonical control root is not a directory")
    current = control
    for component in ("artifacts", plan.run_id):
        current = current / component
        if current.is_symlink():
            raise ValueError("artifact root component must not be a symbolic link")
        current.mkdir(mode=0o700, exist_ok=True)
        if not current.is_dir():
            raise ValueError("artifact root component is not a directory")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical_bytes(artifact.model_dump(mode="json")) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {"artifact_type": artifact_type, "path": str(target), "sha256": sha256_file(target)}


def _installed_package_hash(package_root: Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted(package_root.rglob("*")):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and not path.name.endswith(".pyc")
            and path.name != "_source_identity.json"
        ):
            entries.append({"path": path.relative_to(package_root).as_posix(), "sha256": sha256_file(path)})
    body = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"rb-safe-operation\0installed-package-tree\0" + b"1.0\0" + body).hexdigest()


def cmd_runtime_info(args: argparse.Namespace) -> None:
    import pydantic

    identity_path = Path(__file__).with_name("_source_identity.json")
    identity = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.is_file() else {}
    runtime_root = Path(__file__).resolve().parents[2]
    installed_package_hash = _installed_package_hash(Path(__file__).resolve().parent)
    _write({
        "runtime_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "pydantic_version": pydantic.__version__,
        "runtime_source_hash": identity.get("runtime_source_hash", source_tree_hash(runtime_root)),
        "runtime_lock_hash": identity.get("runtime_lock_hash"),
        "recorded_installed_package_hash": identity.get("installed_package_hash"),
        "installed_package_hash": installed_package_hash,
        "supported_artifacts": sorted(MODELS),
    }, args.output)


def cmd_host_capabilities(args: argparse.Namespace) -> None:
    """Emit the immutable first-release capability profile accepted by assessment."""
    _write(default_host_capabilities().model_dump(mode="json"), args.output)


def cmd_validate(args: argparse.Namespace) -> None:
    payload = _load(args.input)
    if isinstance(payload, dict) and payload.get("schema_version") != "1.0":
        raise ValueError(f"unsupported_artifact_version: expected 1.0, observed {payload.get('schema_version')}")
    instance = _model(args.artifact_type).model_validate(payload)
    _write(instance.model_dump(mode="json"), args.output)


def cmd_canonicalize(args: argparse.Namespace) -> None:
    payload = _load(args.input)
    _write(payload, args.output)


def cmd_hash(args: argparse.Namespace) -> None:
    payload = _load(args.input)
    value = artifact_hash(args.artifact_type, args.schema_version, payload)
    _write({"algorithm": "sha256", "artifact_type": args.artifact_type, "schema_version": args.schema_version, "value": value}, args.output)


def cmd_merge_policy(args: argparse.Namespace) -> None:
    global_policy = default_global_policy(args.project_root)
    project_policy = ProjectPolicy.model_validate(_load(args.project_policy)) if args.project_policy else None
    _write(merge_policy(global_policy, project_policy).model_dump(mode="json"), args.output)


def cmd_snapshot(args: argparse.Namespace) -> None:
    snapshot = capture_snapshot(args.project_root, args.selected_path, args.instruction_path, args.expected_change)
    _write(snapshot.model_dump(mode="json"), args.output)


def cmd_select_phase(args: argparse.Namespace) -> None:
    selection = select_markdown_phase(args.plan, args.phase_id)
    _write({"source_phase": selection.source.model_dump(mode="json"), "later_phase_ids": selection.later_phase_ids}, args.output)


def cmd_discover_instructions(args: argparse.Namespace) -> None:
    _write({"instruction_hashes": discover_instruction_files(args.project_root, args.target_path)}, args.output)


def _assessment_inputs(args: argparse.Namespace, plan: LowLevelPlan):
    global_policy = default_global_policy(plan.snapshot.project_root)
    project_policy = ProjectPolicy.model_validate(_load(args.project_policy)) if args.project_policy else None
    policy = merge_policy(global_policy, project_policy).active_policy
    current_snapshot = capture_snapshot(
        plan.snapshot.project_root,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
    )
    capabilities = HostCapabilities.model_validate(_load(args.capabilities))
    approvals = TypeAdapter(list[Approval]).validate_python(_load(args.approvals)) if args.approvals else []
    return global_policy, policy, current_snapshot, capabilities, approvals


def _prior_assessment_hash(path: str | None, new_plan: LowLevelPlan):
    if not path:
        return None
    supplied = Path(path)
    prior_plan_path = supplied.with_name("low-level-plan.json")
    prior_plan = _load_fixed_plan(str(prior_plan_path))
    prior_bundle = _load_fixed_assessment_bundle(path, prior_plan)
    if prior_bundle.assessment.safe:
        raise ValueError("prior assessment provenance must name an immutable rejected bundle")
    new_plan_hash = artifact_hash("low-level-plan", "1.0", new_plan.model_dump(mode="json"))
    if prior_bundle.assessment.plan_hash.value == new_plan_hash:
        raise ValueError("reassessment provenance requires a revised plan identity")
    return hash_ref("assessment", prior_bundle.assessment.model_dump(mode="json"))


def cmd_assess_preflight(args: argparse.Namespace) -> None:
    plan = _load_fixed_plan(args.plan)
    global_policy, policy, current_snapshot, capabilities, approvals = _assessment_inputs(args, plan)
    preflight = deterministic_preflight(
        plan, global_policy, policy, current_snapshot, capabilities, approvals
    )
    if preflight.deterministic_pass:
        _write(preflight.model_dump(mode="json"), None)
        return
    response: dict[str, Any] = {"preflight": preflight.model_dump(mode="json"), "rejected_bundle": None}
    if not preflight.deterministic_pass:
        semantic = canonical_semantic_proposal(SemanticAssessmentProposal(
            schema_version="1.0", semantic_pass=False, findings=[],
            covered_evidence_ids=preflight.required_semantic_evidence_ids,
            enforcement_disclosures=[],
        ))
        assessment = assess_plan(
            plan, global_policy, policy, current_snapshot, capabilities, semantic, approvals,
            prior_assessment_hash=_prior_assessment_hash(args.prior_assessment_bundle, plan),
        )
        bundle = AssessmentBundle(schema_version="1.0", assessment=assessment, semantic_proposal=semantic)
        response["rejected_bundle"] = _persist_handoff(plan, "assessment-bundle", bundle)
    _write(response, None)


def cmd_assess(args: argparse.Namespace) -> None:
    plan = _load_fixed_plan(args.plan)
    global_policy, policy, current_snapshot, capabilities, approvals = _assessment_inputs(args, plan)
    supplied_preflight = _canonical_model(args.preflight, DeterministicPreflight)
    current_preflight = deterministic_preflight(
        plan, global_policy, policy, current_snapshot, capabilities, approvals
    )
    if supplied_preflight != current_preflight or not current_preflight.deterministic_pass:
        raise ValueError("semantic assessment requires an unchanged passing deterministic preflight")
    try:
        semantic = SemanticAssessmentProposal.model_validate(_load(args.semantic_proposal))
    except Exception:
        semantic = SemanticAssessmentProposal(
            schema_version="1.0",
            semantic_pass=False,
            findings=[Finding(
                finding_id="malformed-semantic-proposal",
                invariant_id="E-004",
                operation_ids=[],
                effect_ids=[],
                category="finding_identity",
                severity="high",
                evidence_ids=[],
                evidence_provenance=[],
                finding_provenance="agent_reported",
                explanation="semantic assessor output failed bounded typed validation",
                remediation_or_human_decision="revise and reassess or leave the constrained pipeline",
                blocking=True,
            )],
            covered_evidence_ids=current_preflight.required_semantic_evidence_ids,
            enforcement_disclosures=[],
        )
    assessment = assess_plan(
        plan, global_policy, policy, current_snapshot, capabilities, semantic, approvals,
        prior_assessment_hash=_prior_assessment_hash(args.prior_assessment_bundle, plan),
    )
    semantic, _ = canonical_semantic_proposal_for_plan(plan, semantic)
    bundle = AssessmentBundle(schema_version="1.0", assessment=assessment, semantic_proposal=semantic)
    _persist_handoff(plan, "assessment-bundle", bundle)
    _write(bundle.model_dump(mode="json"), None)


def cmd_persist_artifact(args: argparse.Namespace) -> None:
    if args.artifact_type != "low-level-plan":
        raise ValueError("public durable handoff persistence is limited to low-level-plan")
    plan = LowLevelPlan.model_validate(_load(args.plan))
    model_type = _model(args.artifact_type)
    artifact = model_type.model_validate(_load(args.input))
    if args.artifact_type == "low-level-plan" and artifact != plan:
        raise ValueError("persisted low-level plan must equal the authoritative plan argument")
    target = _fixed_artifact_path(plan, args.artifact_type)
    if args.artifact_type == "low-level-plan" and plan.current_artifact_locations != [str(target)]:
        raise ValueError("low-level plan must name its one fixed durable artifact location")
    _write(_persist_handoff(plan, args.artifact_type, artifact), None)


class _StdioAgentHost:
    """Synchronous JSON-line bridge while the verified coordinator retains its lease."""

    def invoke(self, role: str, packet: dict[str, Any]) -> Any:
        sys.stdout.buffer.write(canonical_bytes({"type": "agent_request", "role": role, "packet": packet}) + b"\n")
        sys.stdout.buffer.flush()
        line = sys.stdin.buffer.readline()
        if not line:
            raise RuntimeError("coordinator_driver_closed: agent response stream ended")
        response = parse_json_strict(line)
        if not isinstance(response, dict) or set(response) != {"type", "role", "payload"}:
            raise ValueError("coordinator_driver_protocol: malformed agent response")
        if response["type"] != "agent_response" or response["role"] != role:
            raise ValueError("coordinator_driver_protocol: response role mismatch")
        return response["payload"]


def cmd_coordinate(args: argparse.Namespace) -> None:
    if getattr(args, "output", None) is not None:
        raise ValueError("coordinator output is stdout-only to prevent post-verification product mutation")
    plan = _load_fixed_plan(args.plan)
    assessment_bundle = _load_fixed_assessment_bundle(args.assessment_bundle, plan)
    assessment = assessment_bundle.assessment
    capabilities = HostCapabilities.model_validate(_load(args.capabilities))
    semantic = assessment_bundle.semantic_proposal
    global_policy = default_global_policy(plan.snapshot.project_root)
    project_policy = ProjectPolicy.model_validate(_load(args.project_policy)) if args.project_policy else None
    active_policy = merge_policy(global_policy, project_policy).active_policy
    host = _StdioAgentHost()
    coordinator = ExecutionCoordinator(
        plan, assessment, global_policy, active_policy, capabilities, semantic, agent_host=host
    )
    _drive_coordinate(coordinator, args, capabilities)


def cmd_coordinate_resume(args: argparse.Namespace) -> None:
    if getattr(args, "output", None) is not None:
        raise ValueError("coordinator output is stdout-only to prevent post-verification product mutation")
    capabilities = HostCapabilities.model_validate(_load(args.capabilities))
    coordinator = ExecutionCoordinator.reload(
        args.project_root, args.run_id, capabilities, agent_host=_StdioAgentHost()
    )
    repair_attempt = None
    if coordinator.manifest.suspended_from == "repairing":
        if not args.repair_attempt:
            raise RuntimeError("coordinator_incomplete: repairing resume requires --repair-attempt")
        repair_attempt = RepairAttempt.model_validate(_load(args.repair_attempt))
    try:
        coordinator.resume_after_pause(args.resume_evidence_id)
        if coordinator.manifest.state == "repairing":
            coordinator.resume_repair(repair_attempt)
    except Exception:
        if coordinator.manifest.state in {"executing", "verifying", "repairing"} and coordinator.lease is not None:
            coordinator.pause_resource("coordinator-resume-driver-interrupted")
        _write({"type": "coordinator_incomplete", **_coordinator_handoff(coordinator, capabilities)}, None)
        raise
    _drive_coordinate(coordinator, args, capabilities)


def _coordinator_handoff(coordinator: ExecutionCoordinator, capabilities: HostCapabilities) -> dict[str, Any]:
    plan = coordinator.plan
    assessment = coordinator.assessment
    assessment_bundle = AssessmentBundle(
        schema_version="1.0", assessment=assessment, semantic_proposal=coordinator.semantic_proposal
    )
    state = coordinator.manifest.state
    if state == "verified":
        exact_next = "record the verified phase overlay in the external diary, then let rb-execute-plan select the first remaining phase ID"
        human_decision = None
    elif state == "paused_resource":
        exact_next = "resolve the named resource condition and invoke coordinate-resume with fresh evidence"
        human_decision = None
    elif state == "human_required":
        exact_next = "human must choose revise_and_reassess, leave_constrained_pipeline, or abandon; continuation uses a new run"
        human_decision = "revise_and_reassess|leave_constrained_pipeline|abandon"
    else:
        exact_next = "inspect the durable run state and follow its typed lifecycle transition"
        human_decision = None
    return {
        "execution_route": "constrained",
        "run_id": plan.run_id,
        "current_phase_id": plan.source_phase.phase_id,
        "remaining_phase_ids": plan.later_phase_ids,
        "artifact_locations": [
            str(_fixed_artifact_path(plan, "low-level-plan")),
            str(_fixed_artifact_path(plan, "assessment-bundle")),
            str(coordinator.bundle_path),
        ],
        "artifact_hashes": {
            "low_level_plan": coordinator.plan_hash.model_dump(mode="json"),
            "assessment": coordinator.assessment_hash.model_dump(mode="json"),
            "assessment_bundle": hash_ref("assessment-bundle", assessment_bundle.model_dump(mode="json")).model_dump(mode="json"),
            "active_policy": assessment.policy_hash.model_dump(mode="json"),
            "repository_snapshot": assessment.snapshot_hash.model_dump(mode="json"),
        },
        "lifecycle_state": state,
        "suspended_from": coordinator.manifest.suspended_from,
        "event_head_hash": coordinator.manifest.event_head_hash,
        "exact_next_action": exact_next,
        "enforcement_limitations": {
            "role_read_only": capabilities.role_read_only,
            "fresh_context": capabilities.fresh_context_enforcement,
            "bounded_resources": capabilities.bounded_resource_enforcement,
            "complete_child_trace": capabilities.complete_child_trace,
            "atomic_path_enforcement": capabilities.atomic_path_enforcement,
        },
        "human_decision_required": human_decision,
    }


def _drive_coordinate(coordinator: ExecutionCoordinator, args: argparse.Namespace, capabilities: HostCapabilities) -> None:
    plan = coordinator.plan
    assessment = coordinator.assessment
    try:
        if coordinator.manifest.state == "executing":
            reports = coordinator.execute()
        elif coordinator.manifest.state == "verifying":
            reports = list(coordinator.reports)
        else:
            raise RuntimeError(f"coordinator_incomplete: cannot drive state {coordinator.manifest.state}")
    except Exception:
        _write({"type": "coordinator_incomplete", **_coordinator_handoff(coordinator, capabilities)}, None)
        raise
    try:
        context = coordinator.open_verification(args.verifier_context_id)
        request = {
            "type": "verification_request",
            "packet": {
                "plan": plan.model_dump(mode="json"),
                "assessment": assessment.model_dump(mode="json"),
                "reports": [item.model_dump(mode="json") for item in reports],
                "verifier_context_id": context.context_id,
                "plan_hash": context.plan_hash.model_dump(mode="json"),
                "assessment_hash": context.assessment_hash.model_dump(mode="json"),
                "snapshot_hash": context.snapshot_hash.model_dump(mode="json"),
                "fresh_context_assurance": capabilities.fresh_context_enforcement,
            },
        }
        sys.stdout.buffer.write(canonical_bytes(request) + b"\n")
        sys.stdout.buffer.flush()
        line = sys.stdin.buffer.readline()
        if not line:
            raise RuntimeError("coordinator_driver_closed: verifier response stream ended")
        response = parse_json_strict(line)
        if not isinstance(response, dict) or set(response) != {"type", "payload"} or response["type"] != "verification_response":
            raise ValueError("coordinator_driver_protocol: malformed verifier response")
        try:
            proposal = VerificationProposal.model_validate(response["payload"])
        except ValidationError:
            raise RuntimeError("coordinator_driver_protocol: verifier response failed typed validation") from None
        report = coordinator.verify(proposal, context)
    except Exception:
        if coordinator.manifest.state in {"executing", "verifying", "repairing"} and coordinator.lease is not None:
            coordinator.pause_resource("coordinator-driver-interrupted")
        _write({"type": "coordinator_incomplete", **_coordinator_handoff(coordinator, capabilities)}, None)
        raise
    if not report.verified:
        coordinator.pause_resource("verification-repair-required")
        _write({
            "type": "coordinator_incomplete",
            **_coordinator_handoff(coordinator, capabilities),
            "manifest": coordinator.manifest.model_dump(mode="json"),
            "verification_report": report.model_dump(mode="json"),
        }, None)
        raise RuntimeError("coordinator_incomplete: verification requires repair; run is paused_resource")
    _write({
        "type": "coordinator_result",
        **_coordinator_handoff(coordinator, capabilities),
        "manifest": coordinator.manifest.model_dump(mode="json"),
        "verification_report": report.model_dump(mode="json"),
    }, None)


def cmd_render(args: argparse.Namespace) -> None:
    if getattr(args, "output", None) is not None:
        raise ValueError("human rendering is stdout-only to avoid undeclared product mutation")
    if args.artifact_type == "assessment":
        raise ValueError("render the fixed assessment-bundle, not a caller-supplied bare assessment")
    if args.artifact_type == "low-level-plan":
        model = _load_fixed_plan(args.input)
    elif args.artifact_type == "assessment-bundle":
        prior_plan = _load_fixed_plan(str(Path(args.input).with_name("low-level-plan.json")))
        model = _load_fixed_assessment_bundle(args.input, prior_plan)
    else:
        model = _canonical_model(args.input, _model(args.artifact_type))
    value = model.model_dump(mode="json")
    digest = artifact_hash(args.artifact_type, value.get("schema_version", "1.0"), value)
    lines = [f"# {args.artifact_type.replace('-', ' ').title()}", "", f"Artifact hash: `{digest}`", ""]
    if args.artifact_type == "low-level-plan":
        lines.extend([f"Run: `{value['run_id']}`", f"Phase: `{value['source_phase']['phase_id']}`", "", "## Operations", ""])
        for operation in value["operations"]:
            label = operation.get("adapter", operation["kind"])
            lines.append(f"- `{operation['operation_id']}`: {label}")
        lines.extend(["", "## Later phases", "", *[f"- `{item}`" for item in value["later_phase_ids"]], "", f"Next: {value['exact_next_action']}"])
    elif args.artifact_type in {"assessment", "assessment-bundle"}:
        assessment = value if args.artifact_type == "assessment" else value["assessment"]
        lines.extend([f"Verdict: **{'TRUE' if assessment['safe'] else 'FALSE'}**", "", "## Findings", ""])
        lines.extend([f"- `{item['invariant_id']}` {item['explanation']}" for item in assessment["findings"]] or ["- None"])
    else:
        lines.extend(["```json", canonical_bytes(value).decode("utf-8"), "```"])
    rendered = "\n".join(lines) + "\n"
    sys.stdout.write(rendered)


def cmd_export_schemas(args: argparse.Namespace) -> None:
    runtime_root = Path(__file__).resolve().parents[2]
    written = export_schemas(Path(args.destination), runtime_root, _runtime_source_identity(runtime_root))
    _write({"written": [str(item) for item in written]}, args.output)


def cmd_check_schema_drift(args: argparse.Namespace) -> None:
    runtime_root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="rb-schema-drift-") as temporary:
        generated = Path(temporary)
        export_schemas(generated, runtime_root, _runtime_source_identity(runtime_root))
        differences = check_drift(Path(args.expected), generated)
    if differences:
        raise RuntimeError(f"generated_schema_drift: {', '.join(differences)}")
    _write({"drift": False}, args.output)


def _runtime_source_identity(runtime_root: Path) -> str:
    identity_path = Path(__file__).with_name("_source_identity.json")
    if identity_path.is_file():
        identity = parse_json_strict(identity_path.read_bytes())
        recorded = identity.get("runtime_source_hash") if isinstance(identity, dict) else None
        if isinstance(recorded, str):
            return recorded
    return source_tree_hash(runtime_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rb-safe-operation")
    sub = parser.add_subparsers(dest="command", required=True)

    runtime = sub.add_parser("runtime-info")
    runtime.add_argument("--output")
    runtime.set_defaults(func=cmd_runtime_info)

    host_capabilities = sub.add_parser("host-capabilities")
    host_capabilities.add_argument("--output")
    host_capabilities.set_defaults(func=cmd_host_capabilities)

    validate = sub.add_parser("validate")
    validate.add_argument("--artifact-type", choices=sorted(MODELS), required=True)
    validate.add_argument("--input", required=True)
    validate.add_argument("--output")
    validate.set_defaults(func=cmd_validate)

    canonicalize = sub.add_parser("canonicalize")
    canonicalize.add_argument("--input", required=True)
    canonicalize.add_argument("--output")
    canonicalize.set_defaults(func=cmd_canonicalize)

    hasher = sub.add_parser("hash")
    hasher.add_argument("--artifact-type", required=True)
    hasher.add_argument("--schema-version", default="1.0")
    hasher.add_argument("--input", required=True)
    hasher.add_argument("--output")
    hasher.set_defaults(func=cmd_hash)

    merge = sub.add_parser("merge-policy")
    merge.add_argument("--project-root", required=True)
    merge.add_argument("--project-policy")
    merge.add_argument("--output")
    merge.set_defaults(func=cmd_merge_policy)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--project-root", required=True)
    snapshot.add_argument("--selected-path", action="append", default=[])
    snapshot.add_argument("--instruction-path", action="append", default=[])
    snapshot.add_argument("--expected-change", action="append", default=[])
    snapshot.add_argument("--output")
    snapshot.set_defaults(func=cmd_snapshot)

    select = sub.add_parser("select-phase")
    select.add_argument("--plan", required=True)
    select.add_argument("--phase-id", required=True)
    select.add_argument("--output")
    select.set_defaults(func=cmd_select_phase)

    instructions = sub.add_parser("discover-instructions")
    instructions.add_argument("--project-root", required=True)
    instructions.add_argument("--target-path", action="append", required=True)
    instructions.add_argument("--output")
    instructions.set_defaults(func=cmd_discover_instructions)

    preflight = sub.add_parser("assess-preflight")
    preflight.add_argument("--plan", required=True)
    preflight.add_argument("--project-policy")
    preflight.add_argument("--capabilities", required=True)
    preflight.add_argument("--approvals")
    preflight.add_argument("--prior-assessment-bundle")
    preflight.set_defaults(func=cmd_assess_preflight)

    assess = sub.add_parser("assess")
    assess.add_argument("--plan", required=True)
    assess.add_argument("--project-policy")
    assess.add_argument("--capabilities", required=True)
    assess.add_argument("--preflight", required=True)
    assess.add_argument("--semantic-proposal", required=True)
    assess.add_argument("--approvals")
    assess.add_argument("--prior-assessment-bundle")
    assess.set_defaults(func=cmd_assess)

    persist = sub.add_parser("persist-artifact")
    persist.add_argument("--artifact-type", choices=["low-level-plan"], required=True)
    persist.add_argument("--input", required=True)
    persist.add_argument("--plan", required=True)
    persist.set_defaults(func=cmd_persist_artifact)

    coordinate = sub.add_parser("coordinate")
    coordinate.add_argument("--plan", required=True)
    coordinate.add_argument("--assessment-bundle", required=True)
    coordinate.add_argument("--project-policy")
    coordinate.add_argument("--capabilities", required=True)
    coordinate.add_argument("--verifier-context-id", required=True)
    coordinate.set_defaults(func=cmd_coordinate)

    resume = sub.add_parser("coordinate-resume")
    resume.add_argument("--project-root", required=True)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--capabilities", required=True)
    resume.add_argument("--resume-evidence-id", required=True)
    resume.add_argument("--repair-attempt")
    resume.add_argument("--verifier-context-id", required=True)
    resume.set_defaults(func=cmd_coordinate_resume)

    render = sub.add_parser("render")
    render.add_argument("--artifact-type", choices=sorted(MODELS), required=True)
    render.add_argument("--input", required=True)
    render.set_defaults(func=cmd_render)

    schemas = sub.add_parser("export-schemas")
    schemas.add_argument("--destination", required=True)
    schemas.add_argument("--output")
    schemas.set_defaults(func=cmd_export_schemas)

    drift = sub.add_parser("check-schema-drift")
    drift.add_argument("--expected", required=True)
    drift.add_argument("--output")
    drift.set_defaults(func=cmd_check_schema_drift)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except (CanonicalizationError, ValidationError, ValueError, RuntimeError) as exc:
        if isinstance(exc, ValidationError):
            detail = "typed validation failed"
        elif isinstance(exc, CanonicalizationError):
            detail = "canonical input validation failed"
        else:
            detail = str(exc)
        print(f"rb-safe-operation: {type(exc).__name__}: {detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
