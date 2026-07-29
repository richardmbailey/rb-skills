from __future__ import annotations

from decimal import Decimal

from .proposal_models import ProviderGrant


CODEX_CLI_PROVIDER = "codex-cli"
CODEX_CLI_ENDPOINT = "host-mediated://codex-cli/exec"
CODEX_CLI_MODEL = "gpt-5.6-sol"
CODEX_CLI_VERSION = "0.146.0-alpha.3.1"
CODEX_CLI_CREDENTIAL_AUDIENCE = "chatgpt-local-auth"
CODEX_CLI_CREDENTIAL_HANDLE = "CODEX_CHATGPT_LOGIN"
CODEX_CLI_RETENTION_DISCLOSURE = (
    "ephemeral local Codex thread; service retention follows the authenticated ChatGPT account"
)


REVIEWED_PROVIDER = "openai"
REVIEWED_ENDPOINT = "https://api.openai.com/v1/responses"
REVIEWED_MODEL = "gpt-5-mini-2025-08-07"
REVIEWED_MODEL_REVISION = "2025-08-07"
REVIEWED_CREDENTIAL_AUDIENCE = "api.openai.com"
REVIEWED_RETENTION_DISCLOSURE = "up to 30 days abuse monitoring; store=false"
INPUT_USD_PER_MILLION = Decimal("0.25")
OUTPUT_USD_PER_MILLION = Decimal("2.00")
_CLASSIFICATION_ORDER = {"public": 0, "internal": 1, "personal": 2, "sensitive": 3, "secret": 4}


class OpenAIProfileError(ValueError):
    """The supplied provider grant is outside the one reviewed live profile."""


class CodexCliProfileError(ValueError):
    """The supplied provider grant is outside the reviewed Codex-native profile."""


def validate_reviewed_codex_cli_profile(provider_grant: ProviderGrant) -> None:
    expected = {
        "adapter": "json_line",
        "provider": CODEX_CLI_PROVIDER,
        "endpoint": CODEX_CLI_ENDPOINT,
        "model": CODEX_CLI_MODEL,
        "model_revision": None,
        "host_revision": CODEX_CLI_VERSION,
        "credential_audience": CODEX_CLI_CREDENTIAL_AUDIENCE,
        "retention_disclosure": CODEX_CLI_RETENTION_DISCLOSURE,
        "training_use": "unknown",
        "structured_output_mode": "native",
        "cost_accounting": "declared_zero",
        "temperature_decimal": "0",
        "seed": None,
    }
    mismatches = {
        field: {"expected": value, "observed": getattr(provider_grant, field)}
        for field, value in expected.items()
        if getattr(provider_grant, field) != value
    }
    if mismatches:
        raise CodexCliProfileError(f"reviewed Codex CLI profile mismatch: {sorted(mismatches)}")
    if _CLASSIFICATION_ORDER[provider_grant.maximum_data_classification] > _CLASSIFICATION_ORDER["internal"]:
        raise CodexCliProfileError("maximum_data_classification exceeds the reviewed internal ceiling")
    if provider_grant.redirect_endpoints:
        raise CodexCliProfileError("redirect_endpoints are not permitted by the reviewed Codex CLI profile")
    if provider_grant.max_cost_decimal != "0":
        raise CodexCliProfileError("the ChatGPT-authenticated Codex CLI profile has no metered API cost grant")


def validate_reviewed_openai_profile(provider_grant: ProviderGrant) -> None:
    expected = {
        "adapter": "pydantic_ai",
        "provider": REVIEWED_PROVIDER,
        "endpoint": REVIEWED_ENDPOINT,
        "model": REVIEWED_MODEL,
        "model_revision": REVIEWED_MODEL_REVISION,
        "host_revision": None,
        "credential_audience": REVIEWED_CREDENTIAL_AUDIENCE,
        "retention_disclosure": REVIEWED_RETENTION_DISCLOSURE,
        "training_use": "disallowed",
        "structured_output_mode": "tool",
        "cost_accounting": "observed",
    }
    mismatches = {
        field: {"expected": value, "observed": getattr(provider_grant, field)}
        for field, value in expected.items()
        if getattr(provider_grant, field) != value
    }
    if mismatches:
        raise OpenAIProfileError(f"reviewed OpenAI profile mismatch: {sorted(mismatches)}")
    if _CLASSIFICATION_ORDER[provider_grant.maximum_data_classification] > _CLASSIFICATION_ORDER["internal"]:
        raise OpenAIProfileError("maximum_data_classification exceeds the reviewed internal ceiling")
    if provider_grant.redirect_endpoints:
        raise OpenAIProfileError("redirect_endpoints are not permitted by the reviewed OpenAI profile")
