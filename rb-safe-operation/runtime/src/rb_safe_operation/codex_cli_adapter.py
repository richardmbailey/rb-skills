from __future__ import annotations

from typing import Any, Callable
import subprocess

from .codex_cli_transport import (
    REVIEWED_CODEX_CLI_VERSION,
    REVIEWED_CODEX_EXECUTABLE,
    CodexCliTransport,
)
from .provider_profiles import validate_reviewed_codex_cli_profile
from .readiness_models import RunPreparationPreview
from .role_hosts import JsonLineProposalRoleHost


def build_codex_cli_role_host(
    preview: RunPreparationPreview,
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    now: Any | None = None,
) -> JsonLineProposalRoleHost:
    """Build the reviewed Codex-native, tool-disabled semantic role host."""

    provider_grant = preview.provider_grant
    validate_reviewed_codex_cli_profile(provider_grant)
    if preview.credential_handle != "CODEX_CHATGPT_LOGIN":
        raise ValueError("confirmed Codex CLI authority names an unsupported login handle")
    transport = CodexCliTransport(
        cli_path=REVIEWED_CODEX_EXECUTABLE,
        model=provider_grant.model,
        expected_cli_version=REVIEWED_CODEX_CLI_VERSION,
        max_response_bytes=min(
            provider_grant.max_request_bytes,
            preview.run_resource_grant.max_response_bytes,
        ),
        runner=runner,
    )
    timeout_seconds = min(
        provider_grant.max_seconds,
        preview.run_resource_grant.max_elapsed_seconds,
    )
    transport.validate_identity(timeout_seconds)
    return JsonLineProposalRoleHost(
        transport,
        timeout_seconds=timeout_seconds,
        provider_grant=provider_grant,
        run_resource_grant=preview.run_resource_grant,
        now=now,
    )
