from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version as package_version
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from . import SCHEMA_VERSION, __version__
from .acceptance import summarize_acceptance_run
from .canonical import CanonicalizationError, artifact_hash, canonical_bytes, parse_json_strict, sha256_file, source_tree_hash
from .compatibility import LEGACY_AUDIT_TYPES, inspect_legacy_artifact, require_executable_schema
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
from .policy_models import PolicyConfirmation, PolicyPreview, ProjectPolicyProposal
from .project_policy import (
    apply_confirmed_policy,
    build_policy_preview,
    load_project_policy,
    policy_confirmation_statement,
)
from .proposal_models import (
    ApprovalV2,
    AssessmentBundleV2,
    DeterministicPreflightV2,
    HostCapabilitiesV2,
    LowLevelPlanV2,
    PlanAssessmentRequest,
    PlanAssessmentResponse,
    ProviderGrant,
    RepositorySnapshotV2,
    RepairAttemptV2,
    RoleCallRecord,
    RunResourceGrant,
    SemanticAssessmentProposalV2,
    VerificationProposalV2,
)
from .readiness import (
    confirm_run_preparation,
    load_confirmed_run_preparation,
    prepare_run_authority,
    run_doctor,
)
from .readiness_models import (
    DoctorRequest,
    RunPreparationConfirmation,
    RunPreparationPreview,
    RunPreparationRequest,
)
from .patches import capture_file_metadata, metadata_fingerprint_hash
from .role_hosts import JsonLineProposalRoleHost, StreamJsonLineTransport
from .planning import discover_instruction_files_policy, select_markdown_phase
from .schemas import MODELS, MODEL_SCHEMAS, check_drift, export_schemas, model_for
from .state import capture_policy_snapshot, capture_snapshot, snapshot_materially_equal
from .workflow import ExecutionCoordinator, assess_plan, assess_plan_with_host, canonical_semantic_proposal, canonical_semantic_proposal_for_plan, default_host_capabilities_v2, deterministic_preflight, hash_ref


DIAGNOSTICS = {
    "missing_runtime_skill", "missing_runtime_environment", "missing_runtime_manifest", "missing_pydantic",
    "missing_runtime_dependency",
    "unsupported_python_version", "unsupported_pydantic_version", "runtime_source_hash_mismatch",
    "runtime_schema_version_mismatch", "generated_schema_drift", "unsupported_artifact_version",
    "unsupported_host_capability", "copy_install_dependency_missing",
    "unsupported_pydantic_ai_version", "legacy_artifact_not_executable",
    "missing_openai_provider_dependency", "unsupported_openai_provider_version",
    "unavailable_openai_provider_adapter", "unsupported_framework_provider",
    "unsupported_openai_provider_profile",
}


def _load(path: str) -> Any:
    return parse_json_strict(Path(path).read_bytes())


def _write(value: Any, destination: str | None) -> None:
    data = canonical_bytes(value) + b"\n"
    if destination:
        Path(destination).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def _model(name: str, schema_version: str | None = None):
    if schema_version is not None:
        return model_for(name, schema_version)
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


def _load_fixed_plan(path: str, *, executable: bool = True):
    payload = _load(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("schema_version"), str):
        raise ValueError("unsupported_artifact_version: plan requires a string schema_version")
    if executable:
        require_executable_schema("low-level-plan", payload, expected_version="3.0")
    plan = _canonical_model(path, _model("low-level-plan", payload["schema_version"]))
    expected = _fixed_artifact_path(plan, "low-level-plan")
    supplied = Path(path)
    if not supplied.is_absolute() or supplied.is_symlink() or supplied.resolve(strict=True) != expected:
        raise ValueError(f"low-level plan must be loaded from its fixed create-only path: {expected}")
    if plan.current_artifact_locations != [str(expected)]:
        raise ValueError("low-level plan does not bind its fixed durable artifact location")
    return plan


def _load_fixed_assessment_bundle(path: str, plan: Any, *, executable: bool = True):
    payload = _load(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("schema_version"), str):
        raise ValueError("unsupported_artifact_version: assessment bundle requires a string schema_version")
    if executable:
        require_executable_schema("assessment-bundle", payload, expected_version="3.0")
    bundle = _canonical_model(path, _model("assessment-bundle", payload["schema_version"]))
    expected = _fixed_artifact_path(plan, "assessment-bundle")
    supplied = Path(path)
    if not supplied.is_absolute() or supplied.is_symlink() or supplied.resolve(strict=True) != expected:
        raise ValueError(f"assessment bundle must be loaded from its fixed create-only path: {expected}")
    if bundle.assessment.plan_hash.value != artifact_hash(
        "low-level-plan", plan.schema_version, plan.model_dump(mode="json")
    ):
        raise ValueError("assessment bundle is not bound to the fixed low-level plan")
    if plan.schema_version == "1.0" and bundle.semantic_proposal != canonical_semantic_proposal(bundle.semantic_proposal):
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
    directory = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {"artifact_type": artifact_type, "path": str(target), "sha256": sha256_file(target)}


def _create_only_canonical_at(directory_fd: int, filename: str, artifact: Any) -> None:
    """Persist one typed control artifact relative to a verified directory."""
    data = canonical_bytes(artifact.model_dump(mode="json")) + b"\n"
    descriptor = os.open(
        filename,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=directory_fd,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.fsync(directory_fd)


def _open_control_directory(path_or_name: Path | str, *, parent_fd: int | None = None) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path_or_name, flags, dir_fd=parent_fd)
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        os.close(descriptor)
        raise ValueError("semantic-call control component is not a directory")
    return descriptor


def _read_canonical_at(directory_fd: int, filename: str, model_type):
    descriptor = os.open(
        filename,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
            raise ValueError("semantic-call artifact is not a single-link regular file")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
    finally:
        os.close(descriptor)
    model = model_type.model_validate(parse_json_strict(raw))
    if raw != canonical_bytes(model.model_dump(mode="json")) + b"\n":
        raise ValueError("semantic-call artifact is not exact canonical JSON")
    return model


def _plan_assessment_call_root(plan: LowLevelPlanV2, request_token: str) -> Path:
    return _fixed_artifact_path(plan, "low-level-plan").parent / "semantic-calls" / request_token


def _checkpoint_plan_assessment_request(plan: LowLevelPlanV2, request: PlanAssessmentRequest) -> None:
    artifact_root = _fixed_artifact_path(plan, "low-level-plan").parent
    artifact_fd = _open_control_directory(artifact_root)
    try:
        try:
            os.mkdir("semantic-calls", mode=0o700, dir_fd=artifact_fd)
            os.fsync(artifact_fd)
        except FileExistsError:
            pass
        semantic_fd = _open_control_directory("semantic-calls", parent_fd=artifact_fd)
        try:
            try:
                os.mkdir(request.context.request_token, mode=0o700, dir_fd=semantic_fd)
                os.fsync(semantic_fd)
            except FileExistsError as exc:
                raise RuntimeError(
                    "plan_assessment_human_required: a durable request already exists without a reusable complete response; the provider call will not be repeated"
                ) from exc
            call_fd = _open_control_directory(request.context.request_token, parent_fd=semantic_fd)
            try:
                _create_only_canonical_at(call_fd, "request.json", request)
            finally:
                os.close(call_fd)
        finally:
            os.close(semantic_fd)
    finally:
        os.close(artifact_fd)


def _load_completed_plan_assessment_call(
    plan: LowLevelPlanV2,
    request: PlanAssessmentRequest,
) -> tuple[PlanAssessmentResponse, RoleCallRecord] | None:
    artifact_root = _fixed_artifact_path(plan, "low-level-plan").parent
    try:
        artifact_fd = _open_control_directory(artifact_root)
        try:
            try:
                semantic_fd = _open_control_directory("semantic-calls", parent_fd=artifact_fd)
            except FileNotFoundError:
                return None
            try:
                try:
                    call_fd = _open_control_directory(
                        request.context.request_token, parent_fd=semantic_fd
                    )
                except FileNotFoundError:
                    return None
                try:
                    persisted_request = _read_canonical_at(
                        call_fd, "request.json", PlanAssessmentRequest
                    )
                    comparable = persisted_request.model_copy(update={
                        "context": persisted_request.context.model_copy(update={
                            "created_at": request.context.created_at,
                        })
                    })
                    if comparable != request:
                        raise ValueError(
                            "persisted request differs from current canonical assessment inputs"
                        )
                    response = _read_canonical_at(
                        call_fd, "response.json", PlanAssessmentResponse
                    )
                    record = _read_canonical_at(
                        call_fd, "role-call-record.json", RoleCallRecord
                    )
                finally:
                    os.close(call_fd)
            finally:
                os.close(semantic_fd)
        finally:
            os.close(artifact_fd)
    except Exception as exc:
        raise RuntimeError(
            "plan_assessment_human_required: persisted semantic-call state is incomplete, stale, or malformed; the provider call will not be repeated"
        ) from exc
    return response, record


def _checkpoint_completed_plan_assessment_call(
    plan: LowLevelPlanV2,
    request: PlanAssessmentRequest,
    response: PlanAssessmentResponse,
    record: RoleCallRecord,
) -> None:
    artifact_root = _fixed_artifact_path(plan, "low-level-plan").parent
    artifact_fd = _open_control_directory(artifact_root)
    try:
        semantic_fd = _open_control_directory("semantic-calls", parent_fd=artifact_fd)
        try:
            call_fd = _open_control_directory(
                request.context.request_token, parent_fd=semantic_fd
            )
            try:
                _create_only_canonical_at(call_fd, "response.json", response)
                _create_only_canonical_at(call_fd, "role-call-record.json", record)
            finally:
                os.close(call_fd)
        finally:
            os.close(semantic_fd)
    finally:
        os.close(artifact_fd)


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
        "pydantic_ai_version": package_version("pydantic-ai-slim"),
        "openai_version": package_version("openai"),
        "tiktoken_version": package_version("tiktoken"),
        "runtime_source_hash": identity.get("runtime_source_hash", source_tree_hash(runtime_root)),
        "runtime_lock_hash": identity.get("runtime_lock_hash"),
        "recorded_installed_package_hash": identity.get("installed_package_hash"),
        "installed_package_hash": installed_package_hash,
        "supported_artifacts": sorted(MODELS),
        "supported_artifact_versions": {
            name: sorted(version for artifact_type, version in MODEL_SCHEMAS if artifact_type == name)
            for name in sorted(MODELS)
        },
    }, args.output)


def cmd_host_capabilities(args: argparse.Namespace) -> None:
    """Emit the immutable first-release capability profile accepted by assessment."""
    _write(default_host_capabilities_v2(getattr(args, "adapter", "pydantic_ai")).model_dump(mode="json"), args.output)


def _plain_readiness(result) -> str:
    headline = {
        "ready_exact_static": "Ready for exact static operations",
        "ready_framework_proposal": "Ready for framework-mediated proposals",
        "ready_instruction_only_compatibility": "Ready for instruction-only compatibility operation",
        "not_ready": "Not ready",
    }[result.status]
    lines = [
        f"Readiness: {headline}",
        f"Status code: {result.status}",
        f"Requested profile: {result.requested_profile}",
        f"Adapter: {result.adapter}",
        f"Observed at: {result.observed_at}",
        f"Assurance profile: {result.effective_assurance_profile}",
        "",
    ]
    if result.diagnostics:
        lines.append("Diagnostics:")
        for item in result.diagnostics:
            label = "BLOCKING" if item.blocking else "INFORMATION"
            lines.append(f"- [{label}] {item.code}: {item.summary} Next: {item.remediation}")
        lines.append("")
    lines.append("Unavailable or limited capabilities:")
    lines.extend(f"- {item}" for item in result.omitted_capabilities)
    lines.extend(["", f"Next: {result.exact_next_action}"])
    return "\n".join(lines) + "\n"


def _plain_preparation(preview: RunPreparationPreview) -> str:
    provider = preview.provider_grant
    resource = preview.run_resource_grant
    lines = [
        f"Run authority preview: {preview.preparation_id}",
        f"Run: {preview.run_id}",
        f"Provider: {provider.provider} / {provider.model}",
        f"Endpoint: {provider.endpoint}",
        f"Credential handle: {preview.credential_handle} (value is not stored)",
        f"Expires: {provider.expires_at}",
        f"Maximum calls: {provider.max_calls}",
        f"Maximum tokens: {resource.max_input_tokens} input, {resource.max_output_tokens} output",
        f"Maximum cost: {resource.max_cost_decimal}",
        "",
        "Assurance limits:",
        *[f"- {item}" for item in preview.assurance_statements],
        "",
        "Exact confirmation statement:",
        preview.exact_confirmation_statement,
    ]
    return "\n".join(lines) + "\n"


def cmd_doctor(args: argparse.Namespace) -> None:
    request = DoctorRequest(
        schema_version="1.0",
        request_id=args.request_id,
        observed_at=args.observed_at,
        project_root=str(Path(args.project_root).resolve()),
        requested_profile=args.profile,
        adapter=args.adapter,
        requested_verification_modes=args.verification_mode,
        credential_handle=args.credential_handle,
        credential_status=args.credential_status,
        provider_grant_path=args.provider_grant,
        run_resource_grant_path=args.run_resource_grant,
        schema_mirror_roots=args.schema_mirror_root,
    )
    result = run_doctor(request)
    if args.format == "plain":
        sys.stdout.write(_plain_readiness(result))
    else:
        _write(result.model_dump(mode="json"), None)


def cmd_prepare_run_authority(args: argparse.Namespace) -> None:
    request = RunPreparationRequest(
        schema_version="1.0",
        preparation_id=args.preparation_id,
        run_id=args.run_id,
        project_root=str(Path(args.project_root).resolve()),
        adapter=args.adapter,
        provider=args.provider,
        endpoint=args.endpoint,
        model=args.model,
        model_revision=args.model_revision,
        host_revision=args.host_revision,
        credential_handle=args.credential_handle,
        credential_status=args.credential_status,
        credential_audience=args.credential_audience,
        roles=args.role,
        request_data_classes=args.request_data_class,
        response_data_classes=args.response_data_class,
        maximum_data_classification=args.maximum_data_classification,
        retention_disclosure=args.retention_disclosure,
        training_use=args.training_use,
        issued_at=args.issued_at,
        expires_at=args.expires_at,
        max_provider_calls=args.max_provider_calls,
        max_proposer_calls=args.max_proposer_calls,
        max_assessor_calls=args.max_assessor_calls,
        max_model_requests=args.max_model_requests,
        max_read_tool_calls=args.max_read_tool_calls,
        max_read_tool_bytes=args.max_read_tool_bytes,
        max_patch_bytes=args.max_patch_bytes,
        max_request_bytes=args.max_request_bytes,
        max_response_bytes=args.max_response_bytes,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
        max_elapsed_seconds=args.max_elapsed_seconds,
        max_cost_decimal=args.max_cost_decimal,
        cost_accounting=args.cost_accounting,
        temperature_decimal=args.temperature_decimal,
        seed=args.seed,
        structured_output_mode=args.structured_output_mode,
        redirect_endpoints=args.redirect_endpoint,
        authorization_hash={
            "artifact_type": "human-authorization",
            "schema_version": "1.0",
            "algorithm": "sha256",
            "value": args.authorization_hash,
        },
    )
    preview = prepare_run_authority(request)
    if args.format == "plain":
        sys.stdout.write(_plain_preparation(preview))
    else:
        _write(preview.model_dump(mode="json"), None)


def cmd_confirm_run_authority(args: argparse.Namespace) -> None:
    preview = _canonical_model(args.preview, RunPreparationPreview)
    confirmation = RunPreparationConfirmation.from_statement(
        confirmation_id=args.confirmation_id,
        preview_hash=preview.confirmation_binding_hash.value,
        statement=args.statement,
        confirmed_at=args.confirmed_at,
    )
    paths = confirm_run_preparation(preview, confirmation, args.statement)
    _write({"preparation_id": preview.preparation_id, "artifact_paths": paths}, None)


def cmd_validate(args: argparse.Namespace) -> None:
    payload = _load(args.input)
    if not isinstance(payload, dict) or not isinstance(payload.get("schema_version"), str):
        raise ValueError("unsupported_artifact_version: artifact requires a string schema_version")
    instance = _model(args.artifact_type, payload["schema_version"]).model_validate(payload)
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
    requested_version = getattr(args, "schema_version", "3.0")
    if requested_version == "3.0":
        loaded = load_project_policy(args.project_root, default_global_policy(args.project_root))
        snapshot = capture_policy_snapshot(
            loaded, args.selected_path, args.instruction_path, args.expected_change
        )
    else:
        snapshot = capture_snapshot(args.project_root, args.selected_path, args.instruction_path, args.expected_change)
    _write(snapshot.model_dump(mode="json"), args.output)


def cmd_inspect_legacy(args: argparse.Namespace) -> None:
    payload = _load(args.input)
    record = inspect_legacy_artifact(args.artifact_type, payload)
    safe = record.model_dump(mode="json", exclude={"original_payload"})
    safe["original_sha256"] = sha256_file(Path(args.input))
    _write(safe, args.output)


def cmd_select_phase(args: argparse.Namespace) -> None:
    selection = select_markdown_phase(args.plan, args.phase_id)
    _write({"source_phase": selection.source.model_dump(mode="json"), "later_phase_ids": selection.later_phase_ids}, args.output)


def cmd_discover_instructions(args: argparse.Namespace) -> None:
    loaded = load_project_policy(args.project_root, default_global_policy(args.project_root))
    _write({
        "instruction_hashes": discover_instruction_files_policy(loaded, args.target_path)
    }, args.output)


def _assessment_inputs(args: argparse.Namespace, plan: Any):
    global_policy = default_global_policy(plan.snapshot.project_root)
    loaded = load_project_policy(plan.snapshot.project_root, global_policy)
    policy = loaded.effective_policy
    current_snapshot = capture_policy_snapshot(
        loaded,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
    )
    current_snapshot = RepositorySnapshotV2.model_validate(
        current_snapshot.model_dump(mode="json") | {
            "proposal_context_observation_hashes": dict(
                plan.snapshot.proposal_context_observation_hashes
            )
        }
    )
    capabilities = HostCapabilitiesV2.model_validate(_load(args.capabilities))
    provider_grant = ProviderGrant.model_validate(_load(args.provider_grant))
    resource_grant = RunResourceGrant.model_validate(_load(args.run_resource_grant))
    approvals = TypeAdapter(list[ApprovalV2]).validate_python(_load(args.approvals)) if args.approvals else []
    return global_policy, policy, current_snapshot, capabilities, approvals, provider_grant, resource_grant


def _assessment_inputs_from_preparation(
    plan: Any,
    preview: RunPreparationPreview,
    approvals_path: str | None,
):
    global_policy = default_global_policy(plan.snapshot.project_root)
    loaded = load_project_policy(plan.snapshot.project_root, global_policy)
    current_snapshot = capture_policy_snapshot(
        loaded,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
    )
    current_snapshot = RepositorySnapshotV2.model_validate(
        current_snapshot.model_dump(mode="json") | {
            "proposal_context_observation_hashes": dict(
                plan.snapshot.proposal_context_observation_hashes
            )
        }
    )
    approvals = (
        TypeAdapter(list[ApprovalV2]).validate_python(_load(approvals_path))
        if approvals_path else []
    )
    return (
        global_policy,
        loaded.effective_policy,
        current_snapshot,
        preview.host_capabilities,
        approvals,
        preview.provider_grant,
        preview.run_resource_grant,
    )


def _prior_assessment_hash(path: str | None, new_plan: LowLevelPlan):
    if not path:
        return None
    supplied = Path(path)
    prior_plan_path = supplied.with_name("low-level-plan.json")
    prior_plan = _load_fixed_plan(str(prior_plan_path))
    prior_bundle = _load_fixed_assessment_bundle(path, prior_plan)
    if prior_bundle.assessment.safe:
        raise ValueError("prior assessment provenance must name an immutable rejected bundle")
    new_plan_hash = artifact_hash("low-level-plan", new_plan.schema_version, new_plan.model_dump(mode="json"))
    if prior_bundle.assessment.plan_hash.value == new_plan_hash:
        raise ValueError("reassessment provenance requires a revised plan identity")
    return hash_ref("assessment", prior_bundle.assessment.model_dump(mode="json"), prior_bundle.assessment.schema_version)


def _current_assessment_snapshot(plan: LowLevelPlanV2) -> RepositorySnapshotV2:
    global_policy = default_global_policy(plan.snapshot.project_root)
    loaded = load_project_policy(plan.snapshot.project_root, global_policy)
    base = capture_policy_snapshot(
        loaded,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
    )
    return RepositorySnapshotV2.model_validate(base.model_dump(mode="json") | {
        "proposal_context_observation_hashes": dict(
            plan.snapshot.proposal_context_observation_hashes
        ),
    })


def _assessment_control_inventory(plan: LowLevelPlanV2) -> dict[str, str]:
    control = Path(plan.snapshot.control_plane_roots[0])
    if control.is_symlink() or not control.is_dir():
        raise ValueError("assessment control root is missing or unsafe")
    inventory: dict[str, str] = {}
    for path in sorted(control.rglob("*")):
        relative = path.relative_to(control).as_posix()
        observed = path.lstat()
        identity = (
            f"mode={observed.st_mode}:uid={observed.st_uid}:gid={observed.st_gid}:"
            f"dev={observed.st_dev}:ino={observed.st_ino}:nlink={observed.st_nlink}"
        )
        if path.is_symlink():
            inventory[relative] = f"symlink:{os.readlink(path)}:{identity}"
        elif path.is_file():
            inventory[relative] = f"file:{sha256_file(path)}:{identity}"
        elif path.is_dir():
            inventory[relative] = f"directory:{identity}"
        else:
            inventory[relative] = f"other:{identity}"
    return inventory


def cmd_assess_preflight(args: argparse.Namespace) -> None:
    plan = _load_fixed_plan(args.plan)
    global_policy, policy, current_snapshot, capabilities, approvals, provider_grant, resource_grant = _assessment_inputs(args, plan)
    preflight = deterministic_preflight(
        plan, global_policy, policy, current_snapshot, capabilities, approvals,
        provider_grant=provider_grant, run_resource_grant=resource_grant,
    )
    if preflight.deterministic_pass:
        _write(preflight.model_dump(mode="json"), None)
        return
    response: dict[str, Any] = {"preflight": preflight.model_dump(mode="json"), "rejected_bundle": None}
    if not preflight.deterministic_pass:
        semantic = SemanticAssessmentProposalV2(
            schema_version="3.0", semantic_pass=False, findings=[],
            covered_evidence_ids=preflight.required_semantic_evidence_ids,
            enforcement_disclosures=[],
            provider_grant_hash=hash_ref("provider-grant", provider_grant.model_dump(mode="json"), "1.0"),
            required_role_assurance_profiles=sorted({
                item.required_assurance_profile for item in plan.operations if item.kind == "bounded_agent_task"
            }),
            policy_binding=plan.policy_binding,
        )
        assessment = assess_plan(
            plan, global_policy, policy, current_snapshot, capabilities, semantic, approvals,
            prior_assessment_hash=_prior_assessment_hash(args.prior_assessment_bundle, plan),
            provider_grant=provider_grant, run_resource_grant=resource_grant,
        )
        bundle = AssessmentBundleV2(schema_version="3.0", assessment=assessment, semantic_proposal=semantic)
        response["rejected_bundle"] = _persist_handoff(plan, "assessment-bundle", bundle)
    _write(response, None)


def cmd_assess(args: argparse.Namespace) -> None:
    plan = _load_fixed_plan(args.plan)
    global_policy, policy, current_snapshot, capabilities, approvals, provider_grant, resource_grant = _assessment_inputs(args, plan)
    if provider_grant.adapter != "json_line":
        raise ValueError(
            "the assess command owns the JSON-line compatibility host; use the in-process PydanticAI library boundary for pydantic_ai"
        )
    host = JsonLineProposalRoleHost(
        StreamJsonLineTransport(
            sys.stdin.buffer, sys.stdout.buffer,
            max_response_bytes=resource_grant.max_response_bytes,
        ),
        timeout_seconds=min(provider_grant.max_seconds, resource_grant.max_elapsed_seconds),
        provider_grant=provider_grant,
        run_resource_grant=resource_grant,
    )
    guard_product: RepositorySnapshotV2 | None = None
    guard_control: dict[str, str] | None = None

    def state_guard(stage: str) -> None:
        nonlocal guard_product, guard_control
        if stage == "before_plan_assessor":
            guard_product = _current_assessment_snapshot(plan)
            guard_control = _assessment_control_inventory(plan)
            return
        if stage != "after_plan_assessor" or guard_product is None or guard_control is None:
            raise ValueError("plan-assessor state guard received an invalid lifecycle stage")
        current_product = _current_assessment_snapshot(plan)
        equal, differences = snapshot_materially_equal(guard_product, current_product)
        if not equal:
            raise ValueError(f"plan assessor changed product state: {differences}")
        if _assessment_control_inventory(plan) != guard_control:
            raise ValueError("plan assessor changed protected control state")

    outcome = assess_plan_with_host(
        plan, global_policy, policy, current_snapshot, capabilities, approvals,
        prior_assessment_hash=_prior_assessment_hash(args.prior_assessment_bundle, plan),
        provider_grant=provider_grant, run_resource_grant=resource_grant, role_host=host,
        now=datetime.now(timezone.utc),
        state_guard=state_guard,
        request_checkpoint=lambda request: _checkpoint_plan_assessment_request(plan, request),
        completed_call_loader=lambda request: _load_completed_plan_assessment_call(plan, request),
        completed_call_checkpoint=lambda request, response, record: (
            _checkpoint_completed_plan_assessment_call(plan, request, response, record)
        ),
    )
    _persist_handoff(plan, "assessment-bundle", outcome.bundle)
    _write(outcome.bundle.model_dump(mode="json"), None)


def _persist_or_reuse_assessment_bundle(plan: LowLevelPlanV2, bundle: AssessmentBundleV2) -> None:
    target = _fixed_artifact_path(plan, "assessment-bundle")
    if target.exists():
        existing = _load_fixed_assessment_bundle(str(target), plan)
        if existing != bundle:
            raise ValueError("existing fixed assessment bundle differs from the recovered semantic result")
        return
    _persist_handoff(plan, "assessment-bundle", bundle)


def _execute_confirmed_role_host(
    args: argparse.Namespace,
    plan,
    preview,
    host,
    *,
    rejection_type: str,
) -> None:
    """Run the shared deterministic workflow around one confirmed semantic host."""

    (
        global_policy, policy, current_snapshot, capabilities, approvals,
        provider_grant, resource_grant,
    ) = _assessment_inputs_from_preparation(plan, preview, args.approvals)
    guard_product: RepositorySnapshotV2 | None = None
    guard_control: dict[str, str] | None = None

    def state_guard(stage: str) -> None:
        nonlocal guard_product, guard_control
        if stage == "before_plan_assessor":
            guard_product = _current_assessment_snapshot(plan)
            guard_control = _assessment_control_inventory(plan)
            return
        if stage != "after_plan_assessor" or guard_product is None or guard_control is None:
            raise ValueError("plan-assessor state guard received an invalid lifecycle stage")
        current_product = _current_assessment_snapshot(plan)
        equal, differences = snapshot_materially_equal(guard_product, current_product)
        if not equal:
            raise ValueError(f"plan assessor changed product state: {differences}")
        if _assessment_control_inventory(plan) != guard_control:
            raise ValueError("plan assessor changed protected control state")

    outcome = assess_plan_with_host(
        plan, global_policy, policy, current_snapshot, capabilities, approvals,
        prior_assessment_hash=_prior_assessment_hash(args.prior_assessment_bundle, plan),
        provider_grant=provider_grant, run_resource_grant=resource_grant,
        role_host=host, now=datetime.now(timezone.utc), state_guard=state_guard,
        request_checkpoint=lambda request: _checkpoint_plan_assessment_request(plan, request),
        completed_call_loader=lambda request: _load_completed_plan_assessment_call(plan, request),
        completed_call_checkpoint=lambda request, response, record: (
            _checkpoint_completed_plan_assessment_call(plan, request, response, record)
        ),
    )
    _persist_or_reuse_assessment_bundle(plan, outcome.bundle)
    if not outcome.assessment.safe:
        _write({
            "type": rejection_type,
            "run_id": plan.run_id,
            "assessment_bundle": str(_fixed_artifact_path(plan, "assessment-bundle")),
            "safe": False,
            "exact_next_action": "human review is required; do not execute this rejected run",
        }, None)
        return
    proposal_approvals = (
        TypeAdapter(list[ApprovalV2]).validate_python(_load(args.proposal_approvals))
        if args.proposal_approvals else []
    )
    coordinator = ExecutionCoordinator(
        plan, outcome.assessment, global_policy, policy, capabilities,
        semantic_proposal=outcome.bundle.semantic_proposal,
        agent_host=host, provider_grant=provider_grant,
        run_resource_grant=resource_grant, proposal_approvals=proposal_approvals,
        metadata_loader=capture_file_metadata,
    )
    _drive_coordinate(coordinator, args, capabilities)


def cmd_framework_run(args: argparse.Namespace) -> None:
    """Assess and execute one confirmed PydanticAI run without manual protocol envelopes."""

    if not args.enable_live_provider:
        raise ValueError("live provider execution is disabled; pass --enable-live-provider only under explicit authority")
    from .openai_adapter import build_openai_role_host, resolve_environment_credential

    plan = _load_fixed_plan(args.plan)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = load_confirmed_run_preparation(
        args.run_preparation_preview,
        project_root=plan.snapshot.project_root,
        run_id=plan.run_id,
        observed_at=observed_at,
    )
    host = build_openai_role_host(preview, resolve_environment_credential)
    _execute_confirmed_role_host(
        args,
        plan,
        preview,
        host,
        rejection_type="framework_assessment_rejected",
    )


def cmd_codex_run(args: argparse.Namespace) -> None:
    """Assess and execute one confirmed Codex-native run without an API key."""

    if not args.enable_codex_cli:
        raise ValueError("Codex CLI execution is disabled; pass --enable-codex-cli only under explicit authority")
    from .codex_cli_adapter import build_codex_cli_role_host

    plan = _load_fixed_plan(args.plan)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = load_confirmed_run_preparation(
        args.run_preparation_preview,
        project_root=plan.snapshot.project_root,
        run_id=plan.run_id,
        observed_at=observed_at,
    )
    host = build_codex_cli_role_host(preview)
    _execute_confirmed_role_host(
        args,
        plan,
        preview,
        host,
        rejection_type="codex_assessment_rejected",
    )


def cmd_framework_resume(args: argparse.Namespace) -> None:
    """Resume one confirmed PydanticAI run without resetting recorded provider usage."""

    if not args.enable_live_provider:
        raise ValueError("live provider execution is disabled; pass --enable-live-provider only under explicit authority")
    from .openai_adapter import build_openai_role_host, resolve_environment_credential

    observed_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = load_confirmed_run_preparation(
        args.run_preparation_preview,
        project_root=str(Path(args.project_root).resolve()),
        run_id=args.run_id,
        observed_at=observed_at,
    )
    host = build_openai_role_host(preview, resolve_environment_credential)
    coordinator = ExecutionCoordinator.reload(
        str(Path(args.project_root).resolve()),
        args.run_id,
        preview.host_capabilities,
        agent_host=host,
        provider_grant=preview.provider_grant,
        run_resource_grant=preview.run_resource_grant,
        metadata_loader=capture_file_metadata,
    )
    repair_attempt = None
    if coordinator.manifest.suspended_from == "repairing":
        if not args.repair_attempt:
            raise RuntimeError("coordinator_incomplete: repairing resume requires --repair-attempt")
        repair_attempt = RepairAttemptV2.model_validate(_load(args.repair_attempt))
    try:
        coordinator.resume_after_pause(args.resume_evidence_id)
        if coordinator.manifest.state == "repairing":
            coordinator.resume_repair(repair_attempt)
    except Exception:
        if coordinator.manifest.state in {"executing", "verifying", "repairing"} and coordinator.lease is not None:
            coordinator.pause_resource("framework-resume-driver-interrupted")
        _write({
            "type": "coordinator_incomplete",
            **_coordinator_handoff(coordinator, preview.host_capabilities),
        }, None)
        raise
    _drive_coordinate(coordinator, args, preview.host_capabilities)


def cmd_codex_resume(args: argparse.Namespace) -> None:
    """Resume one confirmed Codex-native run without resetting recorded usage."""

    if not args.enable_codex_cli:
        raise ValueError("Codex CLI execution is disabled; pass --enable-codex-cli only under explicit authority")
    from .codex_cli_adapter import build_codex_cli_role_host

    observed_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    project_root = str(Path(args.project_root).resolve())
    preview = load_confirmed_run_preparation(
        args.run_preparation_preview,
        project_root=project_root,
        run_id=args.run_id,
        observed_at=observed_at,
    )
    host = build_codex_cli_role_host(preview)
    coordinator = ExecutionCoordinator.reload(
        project_root, args.run_id, preview.host_capabilities,
        agent_host=host, provider_grant=preview.provider_grant,
        run_resource_grant=preview.run_resource_grant,
        metadata_loader=capture_file_metadata,
    )
    repair_attempt = None
    if coordinator.manifest.suspended_from == "repairing":
        if not args.repair_attempt:
            raise RuntimeError("coordinator_incomplete: repairing resume requires --repair-attempt")
        repair_attempt = RepairAttemptV2.model_validate(_load(args.repair_attempt))
    try:
        coordinator.resume_after_pause(args.resume_evidence_id)
        if coordinator.manifest.state == "repairing":
            coordinator.resume_repair(repair_attempt)
    except Exception:
        if coordinator.manifest.state in {"executing", "verifying", "repairing"} and coordinator.lease is not None:
            coordinator.pause_resource("codex-resume-driver-interrupted")
        _write({"type": "coordinator_incomplete", **_coordinator_handoff(coordinator, preview.host_capabilities)}, None)
        raise
    _drive_coordinate(coordinator, args, preview.host_capabilities)


def cmd_persist_artifact(args: argparse.Namespace) -> None:
    if args.artifact_type != "low-level-plan":
        raise ValueError("public durable handoff persistence is limited to low-level-plan")
    plan_payload = _load(args.plan)
    if not isinstance(plan_payload, dict) or not isinstance(plan_payload.get("schema_version"), str):
        raise ValueError("unsupported_artifact_version: plan requires a string schema_version")
    require_executable_schema("low-level-plan", plan_payload, expected_version="3.0")
    plan = _model("low-level-plan", plan_payload["schema_version"]).model_validate(plan_payload)
    input_payload = _load(args.input)
    if not isinstance(input_payload, dict) or not isinstance(input_payload.get("schema_version"), str):
        raise ValueError("unsupported_artifact_version: artifact requires a string schema_version")
    artifact = _model(args.artifact_type, input_payload["schema_version"]).model_validate(input_payload)
    if args.artifact_type == "low-level-plan" and artifact != plan:
        raise ValueError("persisted low-level plan must equal the authoritative plan argument")
    target = _fixed_artifact_path(plan, args.artifact_type)
    if args.artifact_type == "low-level-plan" and plan.current_artifact_locations != [str(target)]:
        raise ValueError("low-level plan must name its one fixed durable artifact location")
    _write(_persist_handoff(plan, args.artifact_type, artifact), None)


def cmd_coordinate(args: argparse.Namespace) -> None:
    if getattr(args, "output", None) is not None:
        raise ValueError("coordinator output is stdout-only to prevent post-verification product mutation")
    plan = _load_fixed_plan(args.plan)
    assessment_bundle = _load_fixed_assessment_bundle(args.assessment_bundle, plan)
    assessment = assessment_bundle.assessment
    capabilities = HostCapabilitiesV2.model_validate(_load(args.capabilities))
    provider_grant = ProviderGrant.model_validate(_load(args.provider_grant))
    resource_grant = RunResourceGrant.model_validate(_load(args.run_resource_grant))
    proposal_approvals = TypeAdapter(list[ApprovalV2]).validate_python(
        _load(args.proposal_approvals)
    ) if args.proposal_approvals else []
    global_policy = default_global_policy(plan.snapshot.project_root)
    active_policy = load_project_policy(
        plan.snapshot.project_root, global_policy
    ).effective_policy
    host = JsonLineProposalRoleHost(
        StreamJsonLineTransport(
            sys.stdin.buffer, sys.stdout.buffer,
            max_response_bytes=resource_grant.max_response_bytes,
        ),
        timeout_seconds=min(provider_grant.max_seconds, resource_grant.max_elapsed_seconds),
        provider_grant=provider_grant, run_resource_grant=resource_grant,
    )
    coordinator = ExecutionCoordinator(
        plan, assessment, global_policy, active_policy, capabilities,
        semantic_proposal=assessment_bundle.semantic_proposal,
        agent_host=host, provider_grant=provider_grant,
        run_resource_grant=resource_grant, proposal_approvals=proposal_approvals,
    )
    _drive_coordinate(coordinator, args, capabilities)


def cmd_coordinate_resume(args: argparse.Namespace) -> None:
    if getattr(args, "output", None) is not None:
        raise ValueError("coordinator output is stdout-only to prevent post-verification product mutation")
    bundle_path = (
        Path(args.project_root) / ".rb-safe-operation" / "runs" / args.run_id / "coordinator-bundle.json"
    )
    if bundle_path.is_file():
        persisted = _load(str(bundle_path))
        manifest = persisted.get("manifest") if isinstance(persisted, dict) else None
        if isinstance(manifest, dict):
            require_executable_schema("run-manifest", manifest, expected_version="3.0")
    capabilities = HostCapabilitiesV2.model_validate(_load(args.capabilities))
    provider_grant = ProviderGrant.model_validate(_load(args.provider_grant))
    resource_grant = RunResourceGrant.model_validate(_load(args.run_resource_grant))
    host = JsonLineProposalRoleHost(
        StreamJsonLineTransport(sys.stdin.buffer, sys.stdout.buffer, max_response_bytes=resource_grant.max_response_bytes),
        timeout_seconds=min(provider_grant.max_seconds, resource_grant.max_elapsed_seconds),
        provider_grant=provider_grant, run_resource_grant=resource_grant,
    )
    coordinator = ExecutionCoordinator.reload(
        args.project_root, args.run_id, capabilities, agent_host=host,
        provider_grant=provider_grant, run_resource_grant=resource_grant,
    )
    repair_attempt = None
    if coordinator.manifest.suspended_from == "repairing":
        if not args.repair_attempt:
            raise RuntimeError("coordinator_incomplete: repairing resume requires --repair-attempt")
        repair_attempt = RepairAttemptV2.model_validate(_load(args.repair_attempt))
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


def _coordinator_handoff(coordinator: ExecutionCoordinator, capabilities: Any) -> dict[str, Any]:
    plan = coordinator.plan
    assessment = coordinator.assessment
    assessment_bundle = AssessmentBundleV2(
        schema_version="3.0", assessment=assessment,
        semantic_proposal=coordinator.semantic_proposal,
    )
    state = coordinator.manifest.state
    if state == "verified":
        status_summary = "The constrained run finished and its declared static file-state checks passed. Executable correctness still requires the standard route."
        exact_next = "record the verified phase overlay in the external diary, then let rb-execute-plan select the first remaining phase ID"
        human_decision = None
    elif state == "paused_resource":
        status_summary = "The run stopped before continuing because its finite resource authority is exhausted or unavailable. Product work is not continuing in the background."
        exact_next = "resolve the named resource condition and invoke coordinate-resume with fresh evidence"
        human_decision = None
    elif state == "human_required":
        status_summary = "This run is terminal because the coordinator could not safely establish the next state. It cannot be resumed or relabelled; a human must choose what happens next."
        exact_next = "human must choose revise_and_reassess, leave_constrained_pipeline, or abandon; continuation uses a new run"
        human_decision = "revise_and_reassess|leave_constrained_pipeline|abandon"
    else:
        status_summary = "The constrained run has durable state but has not reached a terminal result. Follow only the typed next action for its current lifecycle state."
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
            "assessment_bundle": hash_ref("assessment-bundle", assessment_bundle.model_dump(mode="json"), "3.0").model_dump(mode="json"),
            "active_policy": assessment.policy_hash.model_dump(mode="json"),
            "repository_snapshot": assessment.snapshot_hash.model_dump(mode="json"),
        },
        "lifecycle_state": state,
        "status_summary": status_summary,
        "terminal": state in {"human_required", "verified", "failed", "abandoned", "rejected"},
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


def _drive_coordinate(coordinator: ExecutionCoordinator, args: argparse.Namespace, capabilities: Any) -> None:
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
        report = coordinator.verify_with_host(context)
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
        model = _load_fixed_plan(args.input, executable=False)
    elif args.artifact_type == "assessment-bundle":
        prior_plan = _load_fixed_plan(
            str(Path(args.input).with_name("low-level-plan.json")), executable=False
        )
        model = _load_fixed_assessment_bundle(args.input, prior_plan, executable=False)
    else:
        payload = _load(args.input)
        if not isinstance(payload, dict) or not isinstance(payload.get("schema_version"), str):
            raise ValueError("unsupported_artifact_version: artifact requires a string schema_version")
        model = _canonical_model(args.input, _model(args.artifact_type, payload["schema_version"]))
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


def cmd_acceptance_summary(args: argparse.Namespace) -> None:
    summary = summarize_acceptance_run(
        str(Path(args.project_root).resolve()), args.run_id
    )
    _write(summary.model_dump(mode="json"), args.output)


def cmd_policy_explain(args: argparse.Namespace) -> None:
    loaded = load_project_policy(args.project_root, default_global_policy(args.project_root))
    payload = {
        "binding": loaded.binding.model_dump(mode="json"),
        "project_policy": None if loaded.project_policy is None else loaded.project_policy.model_dump(mode="json"),
        "effective_policy_hash": loaded.binding.effective_policy_hash.model_dump(mode="json"),
        "prospective_only": (
            "Path rules govern future safe-operation activity. They cannot erase content already present in "
            "conversations, provider logs, Git history, copies, backups, or process memory."
        ),
    }
    if args.format == "json":
        _write(payload, None)
        return
    lines = [
        "# Safe-operation project policy",
        "",
        f"Policy status: {loaded.binding.presence}",
        f"Fixed path: {loaded.binding.policy_path}",
        f"Source identity: {loaded.binding.source_policy_sha256}",
        f"Effective identity: {loaded.binding.effective_policy_hash.value}",
        "",
    ]
    if loaded.project_policy is None:
        lines.append("No project policy file exists. The canonical absence identity preserves baseline behaviour.")
    else:
        lines.extend(["## Path rules", ""])
        for rule in loaded.project_policy.path_rules:
            lines.append(
                f"- {rule.rule_id}: deny {', '.join(rule.deny)} for {rule.path} ({rule.scope}). {rule.reason}"
            )
    lines.extend(["", payload["prospective_only"]])
    sys.stdout.write("\n".join(lines) + "\n")


def cmd_policy_preview(args: argparse.Namespace) -> None:
    loaded = load_project_policy(args.project_root, default_global_policy(args.project_root))
    proposal = _canonical_model(args.proposal, ProjectPolicyProposal)
    preview = build_policy_preview(loaded, proposal, args.assurance_profile)
    _write(preview.model_dump(mode="json"), args.output)


def cmd_policy_confirm(args: argparse.Namespace) -> None:
    proposal = _canonical_model(args.proposal, ProjectPolicyProposal)
    preview = _canonical_model(args.preview, PolicyPreview)
    proposal_ref = hash_ref("project-policy-proposal", proposal.model_dump(mode="json"), "1.0")
    if preview.proposal_hash != proposal_ref:
        raise ValueError("preview is not bound to the supplied project-policy proposal")
    expected_statement = policy_confirmation_statement(preview)
    if args.statement != expected_statement:
        raise ValueError(f"confirmation statement must exactly equal: {expected_statement}")
    expected_relaxation = preview.change_classification in {"relaxation", "mixed"}
    if args.confirm_relaxation != expected_relaxation:
        raise ValueError("relaxation confirmation flag does not match the deterministic preview")
    confirmation = PolicyConfirmation(
        schema_version="1.0",
        proposal_hash=proposal_ref,
        preview_hash=hash_ref("policy-preview", preview.model_dump(mode="json"), "1.0"),
        confirmation_token=preview.confirmation_token,
        statement_sha256=hashlib.sha256(args.statement.encode("utf-8")).hexdigest(),
        relaxation_explicitly_confirmed=args.confirm_relaxation,
        confirmed_at=args.confirmed_at,
        confirmation_assurance="instruction_only",
    )
    _write(confirmation.model_dump(mode="json"), args.output)


def cmd_policy_apply(args: argparse.Namespace) -> None:
    loaded = load_project_policy(args.project_root, default_global_policy(args.project_root))
    proposal = _canonical_model(args.proposal, ProjectPolicyProposal)
    preview = _canonical_model(args.preview, PolicyPreview)
    confirmation = _canonical_model(args.confirmation, PolicyConfirmation)
    record = apply_confirmed_policy(
        loaded,
        proposal,
        preview,
        confirmation,
        control_root=Path(args.project_root).resolve(strict=True) / ".rb-safe-operation",
    )
    _write(record.model_dump(mode="json"), None)


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
    host_capabilities.add_argument("--adapter", choices=["pydantic_ai", "json_line"], default="pydantic_ai")
    host_capabilities.add_argument("--output")
    host_capabilities.set_defaults(func=cmd_host_capabilities)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--request-id", required=True)
    doctor.add_argument("--observed-at", required=True)
    doctor.add_argument("--project-root", required=True)
    doctor.add_argument(
        "--profile",
        choices=["exact_static", "framework_proposal", "codex_cli", "instruction_only_compatibility"],
        required=True,
    )
    doctor.add_argument("--adapter", choices=["pydantic_ai", "json_line"], required=True)
    doctor.add_argument("--verification-mode", action="append", required=True)
    doctor.add_argument("--credential-handle")
    doctor.add_argument(
        "--credential-status",
        choices=["available", "unavailable", "unknown", "not_required"],
        required=True,
    )
    doctor.add_argument("--provider-grant")
    doctor.add_argument("--run-resource-grant")
    doctor.add_argument("--schema-mirror-root", action="append", default=[])
    doctor.add_argument("--format", choices=["json", "plain"], default="plain")
    doctor.set_defaults(func=cmd_doctor)

    prepare = sub.add_parser("prepare-run-authority")
    prepare.add_argument("--preparation-id", required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--project-root", required=True)
    prepare.add_argument("--adapter", choices=["pydantic_ai", "json_line"], required=True)
    prepare.add_argument("--provider", required=True)
    prepare.add_argument("--endpoint", required=True)
    prepare.add_argument("--model", required=True)
    prepare.add_argument("--model-revision")
    prepare.add_argument("--host-revision")
    prepare.add_argument("--credential-handle", required=True)
    prepare.add_argument(
        "--credential-status",
        choices=["available", "unavailable", "unknown", "not_required"],
        required=True,
    )
    prepare.add_argument("--credential-audience", required=True)
    prepare.add_argument(
        "--role", action="append",
        choices=["plan_assessor", "proposer", "patch_assessor", "verifier"], required=True,
    )
    prepare.add_argument("--request-data-class", action="append", required=True)
    prepare.add_argument("--response-data-class", action="append", required=True)
    prepare.add_argument(
        "--maximum-data-classification",
        choices=["public", "internal", "personal", "sensitive", "secret"],
        required=True,
    )
    prepare.add_argument("--retention-disclosure", required=True)
    prepare.add_argument("--training-use", choices=["allowed", "disallowed", "unknown"], required=True)
    prepare.add_argument("--issued-at", required=True)
    prepare.add_argument("--expires-at", required=True)
    prepare.add_argument("--max-provider-calls", type=int, required=True)
    prepare.add_argument("--max-proposer-calls", type=int, required=True)
    prepare.add_argument("--max-assessor-calls", type=int, required=True)
    prepare.add_argument("--max-model-requests", type=int, required=True)
    prepare.add_argument("--max-read-tool-calls", type=int, required=True)
    prepare.add_argument("--max-read-tool-bytes", type=int, required=True)
    prepare.add_argument("--max-patch-bytes", type=int, required=True)
    prepare.add_argument("--max-request-bytes", type=int, required=True)
    prepare.add_argument("--max-response-bytes", type=int, required=True)
    prepare.add_argument("--max-input-tokens", type=int, required=True)
    prepare.add_argument("--max-output-tokens", type=int, required=True)
    prepare.add_argument("--max-elapsed-seconds", type=int, required=True)
    prepare.add_argument("--max-cost-decimal", required=True)
    prepare.add_argument("--cost-accounting", choices=["observed", "declared_zero", "unavailable"], required=True)
    prepare.add_argument("--temperature-decimal", required=True)
    prepare.add_argument("--seed", type=int)
    prepare.add_argument("--structured-output-mode", choices=["tool", "native", "prompted"], required=True)
    prepare.add_argument("--redirect-endpoint", action="append", default=[])
    prepare.add_argument("--authorization-hash", required=True)
    prepare.add_argument("--format", choices=["json", "plain"], default="plain")
    prepare.set_defaults(func=cmd_prepare_run_authority)

    confirm = sub.add_parser("confirm-run-authority")
    confirm.add_argument("--preview", required=True)
    confirm.add_argument("--confirmation-id", required=True)
    confirm.add_argument("--statement", required=True)
    confirm.add_argument("--confirmed-at", required=True)
    confirm.set_defaults(func=cmd_confirm_run_authority)

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
    snapshot.add_argument("--schema-version", choices=["1.0", "3.0"], default="3.0")
    snapshot.add_argument("--output")
    snapshot.set_defaults(func=cmd_snapshot)

    policy_explain = sub.add_parser("policy-explain")
    policy_explain.add_argument("--project-root", required=True)
    policy_explain.add_argument("--format", choices=["json", "plain"], default="plain")
    policy_explain.set_defaults(func=cmd_policy_explain)

    policy_preview = sub.add_parser("policy-preview")
    policy_preview.add_argument("--project-root", required=True)
    policy_preview.add_argument("--proposal", required=True)
    policy_preview.add_argument(
        "--assurance-profile",
        choices=["instruction_only_authoring", "framework_tool_enforced_authoring"],
        required=True,
    )
    policy_preview.add_argument("--output")
    policy_preview.set_defaults(func=cmd_policy_preview)

    policy_confirm = sub.add_parser("policy-confirm")
    policy_confirm.add_argument("--proposal", required=True)
    policy_confirm.add_argument("--preview", required=True)
    policy_confirm.add_argument("--statement", required=True)
    policy_confirm.add_argument("--confirmed-at", required=True)
    policy_confirm.add_argument("--confirm-relaxation", action="store_true")
    policy_confirm.add_argument("--output")
    policy_confirm.set_defaults(func=cmd_policy_confirm)

    policy_apply = sub.add_parser("policy-apply")
    policy_apply.add_argument("--project-root", required=True)
    policy_apply.add_argument("--proposal", required=True)
    policy_apply.add_argument("--preview", required=True)
    policy_apply.add_argument("--confirmation", required=True)
    policy_apply.set_defaults(func=cmd_policy_apply)

    inspect_legacy = sub.add_parser("inspect-legacy")
    inspect_legacy.add_argument("--artifact-type", choices=sorted(LEGACY_AUDIT_TYPES), required=True)
    inspect_legacy.add_argument("--input", required=True)
    inspect_legacy.add_argument("--output")
    inspect_legacy.set_defaults(func=cmd_inspect_legacy)

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
    preflight.add_argument("--capabilities", required=True)
    preflight.add_argument("--provider-grant", required=True)
    preflight.add_argument("--run-resource-grant", required=True)
    preflight.add_argument("--approvals")
    preflight.add_argument("--prior-assessment-bundle")
    preflight.set_defaults(func=cmd_assess_preflight)

    assess = sub.add_parser("assess")
    assess.add_argument("--plan", required=True)
    assess.add_argument("--capabilities", required=True)
    assess.add_argument("--provider-grant", required=True)
    assess.add_argument("--run-resource-grant", required=True)
    assess.add_argument("--approvals")
    assess.add_argument("--prior-assessment-bundle")
    assess.set_defaults(func=cmd_assess)

    framework_run = sub.add_parser("framework-run")
    framework_run.add_argument("--plan", required=True)
    framework_run.add_argument("--run-preparation-preview", required=True)
    framework_run.add_argument("--approvals")
    framework_run.add_argument("--prior-assessment-bundle")
    framework_run.add_argument("--proposal-approvals")
    framework_run.add_argument("--verifier-context-id", required=True)
    framework_run.add_argument("--enable-live-provider", action="store_true")
    framework_run.set_defaults(func=cmd_framework_run)

    framework_resume = sub.add_parser("framework-resume")
    framework_resume.add_argument("--project-root", required=True)
    framework_resume.add_argument("--run-id", required=True)
    framework_resume.add_argument("--run-preparation-preview", required=True)
    framework_resume.add_argument("--resume-evidence-id", required=True)
    framework_resume.add_argument("--repair-attempt")
    framework_resume.add_argument("--verifier-context-id", required=True)
    framework_resume.add_argument("--enable-live-provider", action="store_true")
    framework_resume.set_defaults(func=cmd_framework_resume)

    codex_run = sub.add_parser("codex-run")
    codex_run.add_argument("--plan", required=True)
    codex_run.add_argument("--run-preparation-preview", required=True)
    codex_run.add_argument("--approvals")
    codex_run.add_argument("--prior-assessment-bundle")
    codex_run.add_argument("--proposal-approvals")
    codex_run.add_argument("--verifier-context-id", required=True)
    codex_run.add_argument("--enable-codex-cli", action="store_true")
    codex_run.set_defaults(func=cmd_codex_run)

    codex_resume = sub.add_parser("codex-resume")
    codex_resume.add_argument("--project-root", required=True)
    codex_resume.add_argument("--run-id", required=True)
    codex_resume.add_argument("--run-preparation-preview", required=True)
    codex_resume.add_argument("--resume-evidence-id", required=True)
    codex_resume.add_argument("--repair-attempt")
    codex_resume.add_argument("--verifier-context-id", required=True)
    codex_resume.add_argument("--enable-codex-cli", action="store_true")
    codex_resume.set_defaults(func=cmd_codex_resume)

    persist = sub.add_parser("persist-artifact")
    persist.add_argument("--artifact-type", choices=["low-level-plan"], required=True)
    persist.add_argument("--input", required=True)
    persist.add_argument("--plan", required=True)
    persist.set_defaults(func=cmd_persist_artifact)

    coordinate = sub.add_parser("coordinate")
    coordinate.add_argument("--plan", required=True)
    coordinate.add_argument("--assessment-bundle", required=True)
    coordinate.add_argument("--capabilities", required=True)
    coordinate.add_argument("--provider-grant", required=True)
    coordinate.add_argument("--run-resource-grant", required=True)
    coordinate.add_argument("--proposal-approvals")
    coordinate.add_argument("--verifier-context-id", required=True)
    coordinate.set_defaults(func=cmd_coordinate)

    resume = sub.add_parser("coordinate-resume")
    resume.add_argument("--project-root", required=True)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--capabilities", required=True)
    resume.add_argument("--provider-grant", required=True)
    resume.add_argument("--run-resource-grant", required=True)
    resume.add_argument("--resume-evidence-id", required=True)
    resume.add_argument("--repair-attempt")
    resume.add_argument("--verifier-context-id", required=True)
    resume.set_defaults(func=cmd_coordinate_resume)

    render = sub.add_parser("render")
    render.add_argument("--artifact-type", choices=sorted(MODELS), required=True)
    render.add_argument("--input", required=True)
    render.set_defaults(func=cmd_render)

    acceptance_summary = sub.add_parser("acceptance-summary")
    acceptance_summary.add_argument("--project-root", required=True)
    acceptance_summary.add_argument("--run-id", required=True)
    acceptance_summary.add_argument("--output")
    acceptance_summary.set_defaults(func=cmd_acceptance_summary)

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
