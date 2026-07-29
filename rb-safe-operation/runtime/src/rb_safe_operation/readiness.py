from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from .canonical import artifact_hash, canonical_bytes, parse_json_strict
from .proposal_models import HostCapabilitiesV2, ProviderGrant, RunResourceGrant
from .policy import default_global_policy
from .project_policy import ProjectPolicyError, load_project_policy
from .codex_cli_transport import (
    REVIEWED_CODEX_CLI_VERSION,
    REVIEWED_CODEX_EXECUTABLE,
)
from .provider_profiles import (
    CODEX_CLI_PROVIDER,
    CodexCliProfileError,
    OpenAIProfileError,
    validate_reviewed_codex_cli_profile,
    validate_reviewed_openai_profile,
)
from .readiness_models import (
    DoctorRequest,
    ReadinessDiagnostic,
    ReadinessResult,
    RunPreparationConfirmation,
    RunPreparationPreview,
    RunPreparationRequest,
)
from .workflow import default_host_capabilities_v2, hash_ref


CONFIRMATION_PREFIX = "CONFIRM RUN AUTHORITY "
OPENAI_PROVIDER_VERSION = "2.45.0"
TIKTOKEN_VERSION = "0.12.0"


def _diagnostic(
    code: str,
    summary: str,
    remediation: str,
    *,
    blocking: bool = True,
    provenance: str = "coordinator_observed",
) -> ReadinessDiagnostic:
    return ReadinessDiagnostic(
        code=code,
        blocking=blocking,
        summary=summary,
        remediation=remediation,
        provenance=provenance,
    )


def _read_regular_file_nofollow(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("artifact_not_regular_file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _load_canonical(path: str, model_type):
    source = Path(path)
    raw = _read_regular_file_nofollow(source)
    payload = parse_json_strict(raw)
    model = model_type.model_validate(payload)
    if raw != canonical_bytes(model.model_dump(mode="json")) + b"\n":
        raise ValueError(f"artifact_not_canonical: {source}")
    return model


def _is_fixed_preparation_artifact(project_root: str, path: str, filename: str) -> bool:
    source = Path(path)
    preparation_root = Path(project_root) / ".rb-safe-operation" / "preparations"
    return (
        source.name == filename
        and source.parent.parent == preparation_root
        and not source.is_symlink()
        and not source.parent.is_symlink()
        and not preparation_root.is_symlink()
    )


def _mirror_differences(roots: list[str]) -> list[str]:
    if len(roots) < 2:
        return []
    paths = [Path(item) for item in roots]
    if any(not root.is_dir() or root.is_symlink() for root in paths):
        return ["unreadable-mirror"]
    files = [list(root.glob("*.json")) for root in paths]
    if any(any(item.is_symlink() or not item.is_file() for item in group) for group in files):
        return ["unsafe-schema-entry"]
    names = [{item.name for item in group} for group in files]
    if any(not item for item in names):
        return ["empty-mirror"]
    if any(names[0] != item for item in names[1:]):
        return ["filename-set"]
    return [
        name for name in sorted(names[0])
        if len({_read_regular_file_nofollow(root / name) for root in paths}) != 1
    ]


def _append_proposal_authority_diagnostics(
    request: DoctorRequest,
    diagnostics: list[ReadinessDiagnostic],
) -> ProviderGrant | None:
    if request.credential_status == "unknown":
        diagnostics.append(_diagnostic(
            "credential_status_unknown",
            "The explicitly named credential handle has unknown availability.",
            "Supply an operator-observed available or unavailable status; doctor does not inspect ambient credentials.",
            provenance="operator_supplied",
        ))
    elif request.credential_status != "available":
        diagnostics.append(_diagnostic(
            "credential_unavailable",
            "The explicitly named credential handle is unavailable.",
            "Configure the named external handle and rerun doctor without exposing its value.",
            provenance="operator_supplied",
        ))

    provider_grant = None
    resource_grant = None
    if request.provider_grant_path is None:
        diagnostics.append(_diagnostic(
            "missing_provider_grant",
            "No explicit provider grant was supplied.",
            "Prepare and confirm a finite provider grant; doctor cannot create one.",
        ))
    else:
        try:
            if not _is_fixed_preparation_artifact(
                request.project_root, request.provider_grant_path, "provider-grant.json"
            ):
                raise ValueError("provider grant is not a fixed preparation artifact")
            provider_grant = _load_canonical(request.provider_grant_path, ProviderGrant)
            if provider_grant.adapter != request.adapter:
                raise ValueError("provider grant adapter mismatch")
            if provider_grant.expires_at <= request.observed_at:
                raise ValueError("provider grant expired")
            if set(provider_grant.roles) != {"plan_assessor", "proposer", "patch_assessor", "verifier"}:
                raise ValueError("provider grant role coverage mismatch")
        except (OSError, ValueError) as exc:
            diagnostics.append(_diagnostic(
                "invalid_provider_grant",
                f"The explicit provider grant is unavailable or invalid: {type(exc).__name__}.",
                "Prepare a fresh canonical provider grant and rerun doctor.",
            ))
    if request.run_resource_grant_path is None:
        diagnostics.append(_diagnostic(
            "missing_run_resource_grant",
            "No finite run-resource grant was supplied.",
            "Prepare and confirm a finite run-resource grant; doctor cannot create one.",
        ))
    else:
        try:
            if not _is_fixed_preparation_artifact(
                request.project_root, request.run_resource_grant_path, "run-resource-grant.json"
            ):
                raise ValueError("resource grant is not a fixed preparation artifact")
            resource_grant = _load_canonical(request.run_resource_grant_path, RunResourceGrant)
            if resource_grant.expires_at <= request.observed_at:
                raise ValueError("run resource grant expired")
        except (OSError, ValueError) as exc:
            diagnostics.append(_diagnostic(
                "invalid_run_resource_grant",
                f"The explicit run-resource grant is unavailable or invalid: {type(exc).__name__}.",
                "Prepare a fresh canonical resource grant and rerun doctor.",
            ))
    if provider_grant is not None and resource_grant is not None and (
        provider_grant.issued_at != resource_grant.issued_at
        or provider_grant.expires_at != resource_grant.expires_at
        or provider_grant.max_calls != resource_grant.max_model_requests
    ):
        diagnostics.append(_diagnostic(
            "grant_pair_mismatch",
            "The provider and run-resource grants do not describe one matching authority window and call ceiling.",
            "Prepare and confirm both grants together from one unchanged run-authority preview.",
        ))
    if provider_grant is not None and resource_grant is not None:
        try:
            provider_path = Path(request.provider_grant_path or "")
            resource_path = Path(request.run_resource_grant_path or "")
            if provider_path.parent != resource_path.parent:
                raise ValueError("prepared grants do not share one preparation directory")
            preparation = provider_path.parent
            preview = _load_canonical(
                str(preparation / "run-preparation-preview.json"), RunPreparationPreview
            )
            confirmation = _load_canonical(
                str(preparation / "confirmation.json"), RunPreparationConfirmation
            )
            capabilities = _load_canonical(
                str(preparation / "host-capabilities.json"), HostCapabilitiesV2
            )
            if preview.project_root != request.project_root:
                raise ValueError("preparation project root mismatch")
            if preview.credential_handle != request.credential_handle:
                raise ValueError("preparation credential handle mismatch")
            if preview.provider_grant != provider_grant or preview.run_resource_grant != resource_grant:
                raise ValueError("prepared grant differs from bound preview")
            if preview.host_capabilities != capabilities:
                raise ValueError("prepared capabilities differ from bound preview")
            if capabilities != default_host_capabilities_v2(request.adapter):
                raise ValueError("prepared capabilities do not match the selected adapter")
            body = preview.model_dump(mode="json")
            body.pop("confirmation_binding_hash")
            body.pop("exact_confirmation_statement")
            binding = artifact_hash("run-preparation-preview-body", "1.0", body)
            if preview.confirmation_binding_hash.value != binding:
                raise ValueError("preparation preview binding mismatch")
            statement = f"{CONFIRMATION_PREFIX}{binding}"
            if preview.exact_confirmation_statement != statement:
                raise ValueError("preparation confirmation statement mismatch")
            if confirmation.preview_hash != preview.confirmation_binding_hash:
                raise ValueError("preparation confirmation preview mismatch")
            if confirmation.statement_hash != hashlib.sha256(statement.encode("utf-8")).hexdigest():
                raise ValueError("preparation confirmation hash mismatch")
            if not provider_grant.issued_at <= confirmation.confirmed_at < provider_grant.expires_at:
                raise ValueError("preparation confirmation outside authority window")
        except (OSError, ValueError) as exc:
            diagnostics.append(_diagnostic(
                "invalid_preparation_bundle",
                f"The prepared authority bundle is incomplete, mismatched, or invalid: {type(exc).__name__}.",
                "Prepare and confirm one fresh authority preview; do not assemble or edit its artifacts manually.",
            ))
    return provider_grant


def _import_openai_provider_adapter() -> None:
    from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: F401
    from pydantic_ai.providers.openai import OpenAIProvider  # noqa: F401


def _append_framework_provider_diagnostics(
    provider_grant: ProviderGrant | None,
    diagnostics: list[ReadinessDiagnostic],
) -> None:
    if provider_grant is None:
        return
    if provider_grant.provider != "openai":
        diagnostics.append(_diagnostic(
            "unsupported_framework_provider",
            f"The reviewed framework profile does not support provider {provider_grant.provider!r}.",
            "Prepare authority for the reviewed OpenAI Responses profile; no provider fallback is available.",
        ))
        return
    try:
        validate_reviewed_openai_profile(provider_grant)
    except OpenAIProfileError as exc:
        diagnostics.append(_diagnostic(
            "unsupported_openai_provider_profile",
            f"The confirmed provider grant differs from the reviewed OpenAI profile: {exc}",
            "Prepare and confirm the exact reviewed provider, model, endpoint, data, retention, and training profile.",
        ))
        return
    observed: dict[str, str] = {}
    for distribution in ("openai", "tiktoken"):
        try:
            observed[distribution] = package_version(distribution)
        except PackageNotFoundError:
            diagnostics.append(_diagnostic(
                "missing_openai_provider_dependency",
                f"The manifest runtime does not contain the required {distribution} distribution.",
                "Provision the complete reviewed OpenAI provider lock; doctor will not install dependencies.",
            ))
            return
    expected = {"openai": OPENAI_PROVIDER_VERSION, "tiktoken": TIKTOKEN_VERSION}
    mismatches = {
        name: {"expected": expected[name], "observed": observed[name]}
        for name in expected
        if observed[name] != expected[name]
    }
    if mismatches:
        diagnostics.append(_diagnostic(
            "unsupported_openai_provider_version",
            f"The OpenAI provider dependency versions differ from the reviewed lock: {mismatches}.",
            "Provision the reviewed runtime lock; do not continue with an unreviewed provider transport.",
        ))
        return
    try:
        _import_openai_provider_adapter()
    except (ImportError, RuntimeError) as exc:
        diagnostics.append(_diagnostic(
            "unavailable_openai_provider_adapter",
            f"The pinned OpenAI Responses adapter cannot be imported: {type(exc).__name__}.",
            "Repair or reprovision the reviewed provider runtime before issuing live authority.",
        ))


def _probe_codex_cli() -> None:
    source = Path(REVIEWED_CODEX_EXECUTABLE)
    if not source.is_absolute() or source.is_symlink() or not source.is_file():
        raise ValueError("reviewed Codex CLI executable is absent or unsafe")
    if source.stat(follow_symlinks=False).st_mode & 0o111 == 0:
        raise ValueError("reviewed Codex CLI executable is not executable")
    version = subprocess.run(
        [str(source), "--version"], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False,
    )
    if version.returncode != 0 or version.stdout.decode("utf-8", errors="replace").strip() != (
        f"codex-cli {REVIEWED_CODEX_CLI_VERSION}"
    ):
        raise ValueError("reviewed Codex CLI version is unavailable")
    login = subprocess.run(
        [str(source), "login", "status"], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False,
    )
    login_text = (login.stdout + login.stderr).decode("utf-8", errors="replace")
    if login.returncode != 0 or "Logged in using ChatGPT" not in login_text:
        raise ValueError("Codex CLI is not authenticated through ChatGPT")


def _append_codex_cli_diagnostics(
    provider_grant: ProviderGrant | None,
    diagnostics: list[ReadinessDiagnostic],
) -> None:
    if provider_grant is None:
        return
    try:
        validate_reviewed_codex_cli_profile(provider_grant)
    except CodexCliProfileError as exc:
        diagnostics.append(_diagnostic(
            "unsupported_codex_cli_profile",
            f"The confirmed provider grant differs from the reviewed Codex CLI profile: {exc}",
            "Prepare and confirm the exact reviewed Codex CLI model, version, data, and tool-disabled profile.",
        ))
        return
    try:
        _probe_codex_cli()
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        diagnostics.append(_diagnostic(
            "unavailable_codex_cli",
            f"The reviewed locally authenticated Codex CLI is unavailable: {type(exc).__name__}.",
            "Restore the reviewed Codex desktop CLI and ChatGPT login, then rerun doctor.",
        ))


def run_doctor(request: DoctorRequest) -> ReadinessResult:
    root = Path(request.project_root)
    diagnostics: list[ReadinessDiagnostic] = []

    if not root.exists() or not root.is_dir() or root.is_symlink():
        diagnostics.append(_diagnostic(
            "invalid_project_root",
            "The project root is absent, not a directory, or a symbolic link.",
            "Select one existing non-symbolic-link project root and run doctor again.",
        ))

    control = root / ".rb-safe-operation"
    if control.is_symlink() or (control.exists() and not control.is_dir()):
        diagnostics.append(_diagnostic(
            "unsafe_control_root",
            "The local control root is a symbolic link.",
            "Inspect the control root manually; doctor will not repair or replace it.",
        ))
    lease = control / "execution.lease"
    if lease.exists() or lease.is_symlink():
        diagnostics.append(_diagnostic(
            "execution_lease_present",
            "An execution lease exists and its liveness cannot be assumed away.",
            "Inspect the owning run and use its documented recovery path; doctor will not remove the lease.",
        ))

    run_root = control / "runs"
    paused_runs: list[str] = []
    indeterminate_runs: list[str] = []
    unreadable_runs: list[str] = []
    if run_root.is_symlink() or (run_root.exists() and not run_root.is_dir()):
        diagnostics.append(_diagnostic(
            "unsafe_run_root",
            "The protected run root is a symbolic link or is not a directory.",
            "Inspect the protected control state manually; doctor will not follow or replace it.",
        ))
    elif run_root.is_dir():
        for bundle_path in sorted(run_root.glob("*/coordinator-bundle.json")):
            try:
                payload = parse_json_strict(_read_regular_file_nofollow(bundle_path))
                manifest = payload.get("manifest") if isinstance(payload, dict) else None
                state = manifest.get("state") if isinstance(manifest, dict) else None
                run_id = bundle_path.parent.name
                if state == "paused_resource":
                    paused_runs.append(run_id)
                elif state in {
                    "drafting", "validating", "approved", "executing", "proposing",
                    "validating_proposal", "assessing_proposal", "proposal_approved",
                    "applying_proposal", "verifying", "repairing",
                }:
                    indeterminate_runs.append(run_id)
                elif state not in {"rejected", "human_required", "verified", "failed", "abandoned"}:
                    unreadable_runs.append(run_id)
            except (OSError, ValueError):
                unreadable_runs.append(bundle_path.parent.name)
    if paused_runs:
        diagnostics.append(_diagnostic(
            "paused_run_present",
            f"{len(paused_runs)} resumable paused run(s) exist in protected control state.",
            "Review their typed handoffs separately; doctor does not resume or abandon them.",
            blocking=False,
        ))
    if indeterminate_runs:
        diagnostics.append(_diagnostic(
            "unfinished_run_state",
            f"{len(indeterminate_runs)} non-terminal run(s) exist without a proven continuous execution context.",
            "Inspect and recover the named protected run state before starting another constrained mutation.",
        ))
    if unreadable_runs:
        diagnostics.append(_diagnostic(
            "unreadable_run_state",
            f"{len(unreadable_runs)} run bundle(s) have unknown or unreadable lifecycle state.",
            "Inspect the protected control state manually; do not infer that the runs are terminal.",
        ))

    try:
        loaded_policy = load_project_policy(root, default_global_policy(str(root)))
    except ProjectPolicyError as exc:
        diagnostics.append(_diagnostic(
            "invalid_project_policy",
            f"The fixed project policy is absent from trusted authority because it is invalid: {exc}",
            "Repair or deliberately replace the fixed policy through the confirmed policy-authoring workflow.",
        ))
    else:
        diagnostics.append(_diagnostic(
            "project_policy_status",
            f"Fixed project policy status is {loaded_policy.binding.presence}; source identity "
            f"{loaded_policy.binding.source_policy_sha256}; effective identity "
            f"{loaded_policy.binding.effective_policy_hash.value}.",
            "No action is required. Any later policy change invalidates this readiness observation.",
            blocking=False,
        ))

    unsupported = sorted(set(request.requested_verification_modes) - {"static_file_state"})
    if unsupported:
        diagnostics.append(_diagnostic(
            "unsupported_verification_mode",
            f"Unsupported verification modes were requested: {', '.join(unsupported)}.",
            "Use the standard route for executable, runtime, or external validation.",
        ))

    expected_skills = {
        "rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation",
        "rb-create-safe-operation-policy",
    }
    supplied_skills = {Path(item).parent.parent.name for item in request.schema_mirror_roots}
    if supplied_skills != expected_skills:
        diagnostics.append(_diagnostic(
            "missing_runtime_skill",
            "The four supplied schema mirrors do not belong to the required constrained skills.",
            "Supply the generated-schema roots for rb-create-low-level-plan, rb-assess-plan-safety, rb-safe-operation, and rb-create-safe-operation-policy.",
        ))
    try:
        mirror_differences = _mirror_differences(request.schema_mirror_roots)
    except OSError:
        mirror_differences = ["unreadable-mirror"]
    if mirror_differences:
        diagnostics.append(_diagnostic(
            "generated_schema_drift",
            "The supplied generated schema mirrors are absent, unreadable, or not byte-identical.",
            "Regenerate every mirror through the manifest-pinned runtime and rerun doctor.",
        ))

    if request.requested_profile == "framework_proposal":
        if request.adapter != "pydantic_ai":
            diagnostics.append(_diagnostic(
                "framework_profile_adapter_mismatch",
                "The framework proposal profile requires the PydanticAI adapter.",
                "Select pydantic_ai explicitly or request the instruction-only compatibility profile.",
            ))
        try:
            installed_pydantic_ai = package_version("pydantic-ai-slim")
        except PackageNotFoundError:
            installed_pydantic_ai = None
        if installed_pydantic_ai is None:
            diagnostics.append(_diagnostic(
                "missing_pydantic_ai",
                "The PydanticAI runtime dependency is unavailable.",
                "Provision the reviewed manifest-pinned runtime; doctor will not install dependencies.",
            ))
        elif installed_pydantic_ai != "2.19.0":
            diagnostics.append(_diagnostic(
                "unsupported_pydantic_ai_version",
                "The installed PydanticAI version does not match the reviewed runtime version.",
                "Provision the reviewed manifest-pinned runtime; do not continue with version drift.",
            ))
        provider_grant = _append_proposal_authority_diagnostics(request, diagnostics)
        _append_framework_provider_diagnostics(provider_grant, diagnostics)
    elif request.requested_profile == "codex_cli":
        if request.adapter != "json_line":
            diagnostics.append(_diagnostic(
                "codex_cli_profile_adapter_mismatch",
                "The Codex CLI profile requires the typed JSON-line adapter.",
                "Select json_line explicitly for the Codex-native profile.",
            ))
        provider_grant = _append_proposal_authority_diagnostics(request, diagnostics)
        _append_codex_cli_diagnostics(provider_grant, diagnostics)
    elif request.requested_profile == "instruction_only_compatibility":
        if request.adapter != "json_line":
            diagnostics.append(_diagnostic(
                "compatibility_profile_adapter_mismatch",
                "The instruction-only compatibility profile requires the JSON-line adapter.",
                "Select json_line explicitly or request the framework proposal profile.",
            ))
        _append_proposal_authority_diagnostics(request, diagnostics)
    elif request.credential_status != "not_required":
        diagnostics.append(_diagnostic(
            "unexpected_credential_claim",
            "Exact static readiness does not require or consume provider credentials.",
            "Remove the credential claim; do not broaden exact-static authority.",
        ))

    diagnostics.sort(key=lambda item: item.code)
    blocking = any(item.blocking for item in diagnostics)
    expected_status = {
        "exact_static": "ready_exact_static",
        "framework_proposal": "ready_framework_proposal",
        "codex_cli": "ready_codex_cli",
        "instruction_only_compatibility": "ready_instruction_only_compatibility",
    }[request.requested_profile]
    status = "not_ready" if blocking else expected_status
    omitted = {
        "exact_static": [
            "semantic proposal is unavailable",
            "tests, builds, runtime observations, and external observations are unavailable",
        ],
        "framework_proposal": [
            "framework tool allocation is not an OS sandbox",
            "tests, builds, runtime observations, and external observations are unavailable",
        ],
        "codex_cli": [
            "Codex CLI process isolation and disabled tools are not an operating-system proof of model non-observation",
            "interactive mediated reads are unavailable; exact source bundles are required",
            "tests, builds, runtime observations, and external observations are unavailable",
        ],
        "instruction_only_compatibility": [
            "role and context restriction is instruction-only",
            "interactive mediated reads are unavailable",
            "tests, builds, runtime observations, and external observations are unavailable",
        ],
    }[request.requested_profile]
    assurance = {
        "exact_static": "deterministic_coordinator_exact_static",
        "framework_proposal": "framework_tool_enforced_proposer",
        "codex_cli": "instruction_only_proposal_host",
        "instruction_only_compatibility": "instruction_only_proposal_host",
    }[request.requested_profile]
    next_action = (
        "Resolve every blocking diagnostic and rerun doctor; no fallback or repair was performed."
        if blocking
        else "Prepare or execute only the exact requested profile under separately validated plan authority."
    )
    return ReadinessResult(
        schema_version="1.0",
        request_id=request.request_id,
        request_hash=hash_ref("doctor-request", request.model_dump(mode="json"), "1.0"),
        observed_at=request.observed_at,
        project_root=request.project_root,
        requested_profile=request.requested_profile,
        adapter=request.adapter,
        requested_verification_modes=request.requested_verification_modes,
        status=status,
        effective_assurance_profile=assurance,
        omitted_capabilities=omitted,
        diagnostics=diagnostics,
        exact_next_action=next_action,
    )


def load_confirmed_run_preparation(
    preview_path: str,
    *,
    project_root: str,
    run_id: str,
    observed_at: str,
) -> RunPreparationPreview:
    """Load one unchanged, confirmed, currently valid run-authority bundle."""

    root = Path(project_root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("invalid project root for confirmed run preparation")
    source = Path(preview_path)
    if not source.is_absolute():
        raise ValueError("run preparation preview path must be absolute")
    preview = _load_canonical(str(source), RunPreparationPreview)
    expected = (
        root / ".rb-safe-operation" / "preparations" /
        preview.preparation_id / "run-preparation-preview.json"
    )
    if source != expected or source.is_symlink() or source.parent.is_symlink():
        raise ValueError("run preparation preview is not at its fixed confirmed path")
    if preview.project_root != str(root) or preview.run_id != run_id:
        raise ValueError("run preparation project or run identity differs")
    observed_root = root.stat(follow_symlinks=False)
    if (observed_root.st_dev, observed_root.st_ino) != (
        preview.project_root_device, preview.project_root_inode
    ):
        raise ValueError("run preparation project root identity changed")

    confirmation = _load_canonical(
        str(source.with_name("confirmation.json")), RunPreparationConfirmation
    )
    capabilities = _load_canonical(
        str(source.with_name("host-capabilities.json")), HostCapabilitiesV2
    )
    provider_grant = _load_canonical(
        str(source.with_name("provider-grant.json")), ProviderGrant
    )
    resource_grant = _load_canonical(
        str(source.with_name("run-resource-grant.json")), RunResourceGrant
    )
    if (
        preview.host_capabilities != capabilities
        or preview.provider_grant != provider_grant
        or preview.run_resource_grant != resource_grant
    ):
        raise ValueError("confirmed run preparation artifacts differ from the preview")
    if capabilities != default_host_capabilities_v2(provider_grant.adapter):
        raise ValueError("confirmed host capabilities differ from the reviewed adapter")

    body = preview.model_dump(mode="json")
    body.pop("confirmation_binding_hash")
    body.pop("exact_confirmation_statement")
    binding = artifact_hash("run-preparation-preview-body", "1.0", body)
    statement = f"{CONFIRMATION_PREFIX}{binding}"
    if (
        preview.confirmation_binding_hash.value != binding
        or preview.exact_confirmation_statement != statement
        or confirmation.preview_hash != preview.confirmation_binding_hash
        or confirmation.statement_hash != hashlib.sha256(statement.encode("utf-8")).hexdigest()
    ):
        raise ValueError("confirmed run preparation binding is invalid")
    if not provider_grant.issued_at <= confirmation.confirmed_at < provider_grant.expires_at:
        raise ValueError("confirmed run preparation confirmation is outside its authority window")
    if not provider_grant.issued_at <= observed_at < provider_grant.expires_at:
        raise ValueError("confirmed run preparation is not yet valid or has expired")
    if (
        resource_grant.issued_at != provider_grant.issued_at
        or resource_grant.expires_at != provider_grant.expires_at
        or resource_grant.max_model_requests != provider_grant.max_calls
    ):
        raise ValueError("confirmed provider and resource grants do not share one authority window")
    return preview


def prepare_run_authority(request: RunPreparationRequest) -> RunPreparationPreview:
    root = Path(request.project_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("invalid_project_root")
    control = root / ".rb-safe-operation"
    if control.is_symlink() or (control.exists() and not control.is_dir()):
        raise ValueError("unsafe_control_root")
    lease = control / "execution.lease"
    if lease.exists() or lease.is_symlink():
        raise ValueError("execution_lease_present")
    root_stat = root.stat(follow_symlinks=False)
    capabilities = default_host_capabilities_v2(request.adapter)
    provider_grant = ProviderGrant(
        schema_version="1.0",
        grant_id=f"{request.preparation_id}-provider",
        issued_at=request.issued_at,
        expires_at=request.expires_at,
        roles=request.roles,
        adapter=request.adapter,
        provider=request.provider,
        endpoint=request.endpoint,
        model=request.model,
        model_revision=request.model_revision,
        host_revision=request.host_revision,
        credential_audience=request.credential_audience,
        request_data_classes=request.request_data_classes,
        response_data_classes=request.response_data_classes,
        maximum_data_classification=request.maximum_data_classification,
        retention_disclosure=request.retention_disclosure,
        training_use=request.training_use,
        max_calls=request.max_provider_calls,
        max_request_bytes=request.max_request_bytes,
        max_input_tokens=request.max_input_tokens,
        max_output_tokens=request.max_output_tokens,
        max_seconds=request.max_elapsed_seconds,
        max_cost_decimal=request.max_cost_decimal,
        cost_accounting=request.cost_accounting,
        temperature_decimal=request.temperature_decimal,
        seed=request.seed,
        structured_output_mode=request.structured_output_mode,
        redirect_endpoints=request.redirect_endpoints,
        approval_hash=None,
    )
    if request.adapter == "pydantic_ai":
        validate_reviewed_openai_profile(provider_grant)
    elif provider_grant.provider == CODEX_CLI_PROVIDER:
        validate_reviewed_codex_cli_profile(provider_grant)
    resource_grant = RunResourceGrant(
        schema_version="1.0",
        grant_id=f"{request.preparation_id}-resource",
        issued_at=request.issued_at,
        expires_at=request.expires_at,
        max_proposer_calls=request.max_proposer_calls,
        max_assessor_calls=request.max_assessor_calls,
        max_model_requests=request.max_model_requests,
        max_read_tool_calls=request.max_read_tool_calls,
        max_read_tool_bytes=request.max_read_tool_bytes,
        max_patch_bytes=request.max_patch_bytes,
        max_input_tokens=request.max_input_tokens,
        max_output_tokens=request.max_output_tokens,
        max_request_bytes=request.max_request_bytes,
        max_response_bytes=request.max_response_bytes,
        max_elapsed_seconds=request.max_elapsed_seconds,
        max_cost_decimal=request.max_cost_decimal,
        replenishes_grant_id=None,
        authorization_hash=request.authorization_hash,
    )
    request_hash = hash_ref("run-preparation-request", request.model_dump(mode="json"), "1.0")
    body = {
        "schema_version": "1.0",
        "preparation_id": request.preparation_id,
        "run_id": request.run_id,
        "project_root": request.project_root,
        "project_root_device": root_stat.st_dev,
        "project_root_inode": root_stat.st_ino,
        "request_hash": request_hash.model_dump(mode="json"),
        "credential_handle": request.credential_handle,
        "credential_status": "available",
        "host_capabilities": capabilities.model_dump(mode="json"),
        "provider_grant": provider_grant.model_dump(mode="json"),
        "run_resource_grant": resource_grant.model_dump(mode="json"),
        "assurance_statements": [
            "The provider and aggregate resource ceilings are finite.",
            "The credential remains an external handle; its value is not persisted.",
            "Framework tool allocation is not an OS sandbox.",
        ],
    }
    binding = hash_ref("run-preparation-preview-body", body, "1.0")
    return RunPreparationPreview.model_validate(body | {
        "confirmation_binding_hash": binding.model_dump(mode="json"),
        "exact_confirmation_statement": f"{CONFIRMATION_PREFIX}{binding.value}",
    })


def _directory_open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _open_or_create_directory(parent_fd: int, name: str, mode: int) -> tuple[int, bool]:
    try:
        return os.open(name, _directory_open_flags(), dir_fd=parent_fd), False
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=mode, dir_fd=parent_fd)
            os.fsync(parent_fd)
            created = True
        except FileExistsError:
            created = False
        return os.open(name, _directory_open_flags(), dir_fd=parent_fd), created


def _write_create_only_at(directory_fd: int, filename: str, payload: object) -> None:
    descriptor = os.open(
        filename,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=directory_fd,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            value = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
            handle.write(canonical_bytes(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.unlink(filename, dir_fd=directory_fd)
        except OSError:
            pass
        raise


def confirm_run_preparation(
    preview: RunPreparationPreview,
    confirmation: RunPreparationConfirmation,
    statement: str,
) -> dict[str, str]:
    body = preview.model_dump(mode="json")
    body.pop("confirmation_binding_hash")
    body.pop("exact_confirmation_statement")
    preview_hash = artifact_hash("run-preparation-preview-body", "1.0", body)
    if preview.confirmation_binding_hash.value != preview_hash:
        raise ValueError("run_preparation_preview_binding_mismatch")
    if confirmation.preview_hash != preview.confirmation_binding_hash:
        raise ValueError("stale_run_preparation_confirmation: preview hash differs")
    expected = f"{CONFIRMATION_PREFIX}{preview_hash}"
    if statement != expected:
        raise ValueError("run_preparation_confirmation_statement_mismatch")
    if hashlib.sha256(statement.encode("utf-8")).hexdigest() != confirmation.statement_hash:
        raise ValueError("run_preparation_confirmation_hash_mismatch")
    confirmed_at = datetime.strptime(confirmation.confirmed_at, "%Y-%m-%dT%H:%M:%SZ")
    issued_at = datetime.strptime(preview.provider_grant.issued_at, "%Y-%m-%dT%H:%M:%SZ")
    expires_at = datetime.strptime(preview.provider_grant.expires_at, "%Y-%m-%dT%H:%M:%SZ")
    if not issued_at <= confirmed_at < expires_at:
        raise ValueError("confirmation_outside_authority_window")
    if (
        preview.run_resource_grant.issued_at != preview.provider_grant.issued_at
        or preview.run_resource_grant.expires_at != preview.provider_grant.expires_at
    ):
        raise ValueError("run_preparation_authority_window_mismatch")

    root = Path(preview.project_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("invalid_project_root")
    root_stat = root.stat(follow_symlinks=False)
    if (root_stat.st_dev, root_stat.st_ino) != (
        preview.project_root_device, preview.project_root_inode
    ):
        raise ValueError("stale_run_preparation_project_root")
    target = root / ".rb-safe-operation" / "preparations" / preview.preparation_id

    artifacts = {
        "run_preparation_preview": ("run-preparation-preview.json", preview),
        "host_capabilities": ("host-capabilities.json", preview.host_capabilities),
        "provider_grant": ("provider-grant.json", preview.provider_grant),
        "run_resource_grant": ("run-resource-grant.json", preview.run_resource_grant),
        "run_preparation_confirmation": ("confirmation.json", confirmation),
    }
    paths: dict[str, str] = {}
    root_fd = os.open(root, _directory_open_flags())
    control_fd: int | None = None
    preparations_fd: int | None = None
    target_fd: int | None = None
    target_created = False
    try:
        bound_root = os.fstat(root_fd)
        if (bound_root.st_dev, bound_root.st_ino) != (
            preview.project_root_device, preview.project_root_inode
        ):
            raise ValueError("stale_run_preparation_project_root")
        try:
            control_fd, _ = _open_or_create_directory(root_fd, ".rb-safe-operation", 0o700)
        except OSError as exc:
            raise ValueError("unsafe_control_root") from exc
        try:
            os.stat("execution.lease", dir_fd=control_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError("execution_lease_present")
        try:
            preparations_fd, _ = _open_or_create_directory(control_fd, "preparations", 0o700)
        except OSError as exc:
            raise ValueError("unsafe_preparation_root") from exc
        try:
            os.mkdir(preview.preparation_id, mode=0o700, dir_fd=preparations_fd)
            target_created = True
        except FileExistsError as exc:
            raise FileExistsError(f"preparation already exists: {target}") from exc
        os.fsync(preparations_fd)
        target_fd = os.open(preview.preparation_id, _directory_open_flags(), dir_fd=preparations_fd)
        for name, (filename, artifact) in artifacts.items():
            path = target / filename
            _write_create_only_at(target_fd, filename, artifact)
            paths[name] = str(path)
        os.fsync(target_fd)
    except Exception:
        if target_fd is not None:
            for _, (filename, _) in artifacts.items():
                try:
                    os.unlink(filename, dir_fd=target_fd)
                except FileNotFoundError:
                    pass
            os.fsync(target_fd)
            os.close(target_fd)
            target_fd = None
        if target_created and preparations_fd is not None:
            try:
                os.rmdir(preview.preparation_id, dir_fd=preparations_fd)
                os.fsync(preparations_fd)
            except OSError:
                pass
        raise
    finally:
        if target_fd is not None:
            os.close(target_fd)
        if preparations_fd is not None:
            os.close(preparations_fd)
        if control_fd is not None:
            os.close(control_fd)
        os.close(root_fd)
    return paths
