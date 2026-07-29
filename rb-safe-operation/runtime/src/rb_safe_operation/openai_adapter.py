from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
import os
import re
from typing import Any

from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from .canonical import canonical_decimal
from .provider_profiles import (
    INPUT_USD_PER_MILLION,
    OUTPUT_USD_PER_MILLION,
    REVIEWED_CREDENTIAL_AUDIENCE,
    REVIEWED_ENDPOINT,
    REVIEWED_MODEL_REVISION,
    REVIEWED_PROVIDER,
    OpenAIProfileError,
    validate_reviewed_openai_profile,
)
from .readiness_models import RunPreparationPreview
from .role_hosts import PydanticAIProposalRoleHost


_ENVIRONMENT_HANDLE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class CredentialResolutionError(RuntimeError):
    """An explicitly named external credential handle could not be resolved."""


def resolve_environment_credential(
    credential_handle: str,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Resolve only the exact environment handle named by confirmed run authority."""

    if _ENVIRONMENT_HANDLE.fullmatch(credential_handle) is None:
        raise CredentialResolutionError("invalid environment credential handle")
    source = os.environ if environment is None else environment
    value = source.get(credential_handle)
    if value is None or not value.strip():
        raise CredentialResolutionError(f"explicit credential handle {credential_handle!r} is unavailable")
    return value


def observed_openai_cost(usage: Any) -> str:
    input_cost = Decimal(usage.input_tokens) * INPUT_USD_PER_MILLION / Decimal(1_000_000)
    output_cost = Decimal(usage.output_tokens) * OUTPUT_USD_PER_MILLION / Decimal(1_000_000)
    return canonical_decimal(format(input_cost + output_cost, "f"))


def build_openai_role_host(
    preview: RunPreparationPreview,
    credential_resolver: Callable[[str], str],
    *,
    now: Any | None = None,
) -> PydanticAIProposalRoleHost:
    """Build the reviewed live role host after validating non-secret authority."""

    provider_grant = preview.provider_grant
    validate_reviewed_openai_profile(provider_grant)
    credential_value = credential_resolver(preview.credential_handle)
    if not isinstance(credential_value, str) or not credential_value.strip():
        raise CredentialResolutionError("the explicit credential resolver returned no usable value")

    provider = OpenAIProvider(api_key=credential_value)
    model = OpenAIResponsesModel(
        provider_grant.model,
        provider=provider,
        settings={
            "openai_store": False,
            "openai_native_tools": (),
            "parallel_tool_calls": False,
        },
    )
    return PydanticAIProposalRoleHost(
        model=model,
        provider_grant=provider_grant,
        run_resource_grant=preview.run_resource_grant,
        observed_provider=REVIEWED_PROVIDER,
        observed_endpoint=REVIEWED_ENDPOINT,
        observed_credential_audience=REVIEWED_CREDENTIAL_AUDIENCE,
        observed_model_revision=REVIEWED_MODEL_REVISION,
        cost_observer=observed_openai_cost,
        now=now,
    )
