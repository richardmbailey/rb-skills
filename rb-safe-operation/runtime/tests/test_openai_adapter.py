from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rb_safe_operation.readiness import prepare_run_authority
from rb_safe_operation.readiness_models import RunPreparationRequest
from rb_safe_operation.workflow import hash_ref


class OpenAIAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def preview(self, **updates: object):
        payload = {
            "schema_version": "1.0",
            "preparation_id": "prep-openai",
            "run_id": "run-openai",
            "project_root": str(self.root),
            "adapter": "pydantic_ai",
            "provider": "openai",
            "endpoint": "https://api.openai.com/v1/responses",
            "model": "gpt-5-mini-2025-08-07",
            "model_revision": "2025-08-07",
            "credential_handle": "OPENAI_API_KEY",
            "credential_status": "available",
            "credential_audience": "api.openai.com",
            "roles": ["plan_assessor", "proposer", "patch_assessor", "verifier"],
            "request_data_classes": ["internal_source"],
            "response_data_classes": ["typed_role_result"],
            "maximum_data_classification": "internal",
            "retention_disclosure": "up to 30 days abuse monitoring; store=false",
            "training_use": "disallowed",
            "issued_at": "2026-07-28T10:00:00Z",
            "expires_at": "2026-07-28T12:00:00Z",
            "max_provider_calls": 8,
            "max_proposer_calls": 4,
            "max_assessor_calls": 4,
            "max_model_requests": 8,
            "max_read_tool_calls": 4,
            "max_read_tool_bytes": 100_000,
            "max_patch_bytes": 100_000,
            "max_request_bytes": 200_000,
            "max_response_bytes": 100_000,
            "max_input_tokens": 50_000,
            "max_output_tokens": 20_000,
            "max_elapsed_seconds": 600,
            "max_cost_decimal": "0.25",
            "cost_accounting": "observed",
            "temperature_decimal": "0",
            "seed": None,
            "structured_output_mode": "tool",
            "redirect_endpoints": [],
            "authorization_hash": hash_ref("human-authorization", {"test": True}, "1.0"),
        }
        payload.update(updates)
        return prepare_run_authority(RunPreparationRequest.model_validate(payload))

    def test_reviewed_profile_rejects_transport_data_and_retention_drift(self) -> None:
        from rb_safe_operation.openai_adapter import OpenAIProfileError, validate_reviewed_openai_profile
        from rb_safe_operation.proposal_models import ProviderGrant

        grant = self.preview().provider_grant
        validate_reviewed_openai_profile(grant)
        for update, field in (
            ({"endpoint": "https://example.invalid/v1/responses"}, "endpoint"),
            ({"model": "gpt-5-mini"}, "model"),
            ({"maximum_data_classification": "personal"}, "maximum_data_classification"),
            ({"training_use": "unknown"}, "training_use"),
            ({"retention_disclosure": "unknown"}, "retention_disclosure"),
            ({"redirect_endpoints": ["https://api.openai.com/redirect"]}, "redirect_endpoints"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(OpenAIProfileError, field):
                changed = ProviderGrant.model_validate(grant.model_dump(mode="json") | update)
                validate_reviewed_openai_profile(changed)

        with self.assertRaisesRegex(OpenAIProfileError, "endpoint"):
            self.preview(endpoint="https://example.invalid/v1/responses")

    def test_explicit_environment_handle_has_no_fallback(self) -> None:
        from rb_safe_operation.openai_adapter import CredentialResolutionError, resolve_environment_credential

        environment = {"OPENAI_API_KEY": "CANARY-EXPLICIT-SECRET", "OTHER_KEY": "wrong"}
        self.assertEqual(
            resolve_environment_credential("OPENAI_API_KEY", environment),
            "CANARY-EXPLICIT-SECRET",
        )
        with self.assertRaisesRegex(CredentialResolutionError, "unavailable"):
            resolve_environment_credential("MISSING_KEY", environment)
        with self.assertRaisesRegex(CredentialResolutionError, "invalid"):
            resolve_environment_credential("../OPENAI_API_KEY", environment)

    def test_observed_cost_uses_the_reviewed_token_price_table(self) -> None:
        from types import SimpleNamespace
        from rb_safe_operation.openai_adapter import observed_openai_cost

        self.assertEqual(
            observed_openai_cost(SimpleNamespace(input_tokens=1_000_000, output_tokens=1_000_000)),
            "2.25",
        )

    def test_host_factory_resolves_only_after_validation_and_forces_no_storage(self) -> None:
        from rb_safe_operation.openai_adapter import build_openai_role_host

        calls: list[str] = []

        def resolver(handle: str) -> str:
            calls.append(handle)
            return "CANARY-RESOLVED-SECRET"

        class FakeProvider:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeModel:
            def __init__(self, model_name, **kwargs):
                self.model_name = model_name
                self.kwargs = kwargs

        class FakeHost:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        with patch("rb_safe_operation.openai_adapter.OpenAIProvider", FakeProvider), patch(
            "rb_safe_operation.openai_adapter.OpenAIResponsesModel", FakeModel
        ), patch("rb_safe_operation.openai_adapter.PydanticAIProposalRoleHost", FakeHost):
            host = build_openai_role_host(self.preview(), resolver)

        self.assertEqual(calls, ["OPENAI_API_KEY"])
        model = host.kwargs["model"]
        self.assertEqual(model.kwargs["settings"]["openai_store"], False)
        self.assertEqual(model.kwargs["settings"]["openai_native_tools"], ())
        self.assertEqual(model.kwargs["provider"].kwargs, {"api_key": "CANARY-RESOLVED-SECRET"})
        persisted = repr({key: value for key, value in host.kwargs.items() if key != "model"})
        self.assertNotIn("CANARY-RESOLVED-SECRET", persisted)

        calls.clear()
        invalid = self.preview()
        invalid = invalid.model_copy(update={
            "provider_grant": invalid.provider_grant.model_copy(update={
                "endpoint": "https://example.invalid/v1/responses"
            })
        })
        with self.assertRaises(Exception):
            build_openai_role_host(invalid, resolver)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
