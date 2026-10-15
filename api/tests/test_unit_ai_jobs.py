"""AI Job scaffold: phần không cần database (envelope lỗi, giả lập lỗi provider, chuẩn hóa đầu vào)."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from support import configured, real_config

from app.core.ai_jobs import (
    DenyAllPolicy,
    JobOutcome,
    job_fingerprint,
    normalize_source_ids,
    policy_for,
    record_usage,
    register_policy,
    timeout_for,
    _POLICIES,
)
from app.core.errors import AiRateLimited, ProviderError, ProviderRateLimited, ProviderTimeout, RequestInvalid
from app.core.fault_injection import check_fixture_fault, inject_provider_faults
from app.core.providers import post_json
from app.main import app

DEEPSEEK = "https://api.deepseek.com/chat/completions"


class ErrorEnvelopeTests(unittest.TestCase):
    def test_validation_error_lists_fields_without_echoing_input(self):
        response = TestClient(app).post("/chat", json={"question": "q", "top_k": 0, "secret_field": "do-not-echo"})
        body = response.json()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(body["code"], "validation_error")
        self.assertEqual(body["message"], body["detail"])
        self.assertTrue(body["request_id"])
        fields = {item["field"] for item in body["fields"]}
        self.assertIn("top_k", fields)
        self.assertIn("secret_field", fields)
        self.assertNotIn("do-not-echo", response.text)

    def test_rate_limit_error_has_retry_after_header_and_field(self):
        from app.core.auth import CurrentUser, current_user
        app.dependency_overrides[current_user] = lambda: CurrentUser("u-1", "a@insighthub.test", "A", True)
        try:
            with patch("app.routers.ai_jobs.get_job", side_effect=AiRateLimited(retry_after_seconds=17)):
                response = TestClient(app).get("/ai-jobs/00000000-0000-0000-0000-000000000000")
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "17")
        self.assertEqual(response.json()["retry_after_seconds"], 17)
        self.assertEqual(response.json()["code"], "ai_rate_limited")
        self.assertEqual(response.json()["fields"], [])

    def test_ai_job_status_requires_session(self):
        response = TestClient(app).get("/ai-jobs/00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "not_authenticated")

    def test_unknown_route_uses_envelope(self):
        response = TestClient(app).get("/no-such-route")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "http_404")


class FaultInjectionTests(unittest.TestCase):
    def call(self):
        return post_json(DEEPSEEK, headers={}, payload={}, timeout_seconds=5)

    def test_plan_exercises_existing_retry_then_returns_canned_response(self):
        with configured(), inject_provider_faults({"deepseek": ["timeout", "503", {"json": {"ok": True}}]}) as plan:
            self.assertEqual(self.call(), {"ok": True})
            self.assertEqual(plan["deepseek"], [])

    def test_exhausted_retries_raise_public_errors(self):
        cases = {"timeout": ProviderTimeout, "429": ProviderRateLimited, "503": ProviderTimeout}
        for fault, error in cases.items():
            with self.subTest(fault=fault), configured(provider_retry_attempts=2), \
                    inject_provider_faults({"api.deepseek.com": [fault, fault]}), self.assertRaises(error):
                self.call()
        with configured(), inject_provider_faults({"deepseek": ["invalid_json"]}), self.assertRaises(ProviderError):
            self.call()

    def test_other_providers_are_not_affected(self):
        with configured(), inject_provider_faults({"gemini": ["timeout"]}), \
                patch("app.core.providers.httpx.Client") as client:
            client.return_value.__enter__.return_value.post.side_effect = RuntimeError("real transport used")
            with self.assertRaises(RuntimeError):
                self.call()
            self.assertIsNone(client.call_args.kwargs["transport"])

    def test_fixture_branch_check_and_environment_switch(self):
        with inject_provider_faults({"deepseek": ["429"]}):
            with self.assertRaises(ProviderRateLimited):
                check_fixture_fault("deepseek")
            check_fixture_fault("deepseek")  # hết kế hoạch: chạy bình thường
        with configured(), patch.dict(os.environ, {"AI_FIXTURE_FAULTS": "deepseek:timeout"}):
            with self.assertRaises(ProviderTimeout):
                check_fixture_fault("deepseek")
            check_fixture_fault("gemini")
        with real_config(embedding_model="test-embed", embedding_dim=1024), patch.dict(os.environ, {"AI_FIXTURE_FAULTS": "deepseek:timeout"}):
            check_fixture_fault("deepseek")  # biến môi trường chỉ có hiệu lực ở fixture

    def test_unknown_fault_is_rejected(self):
        with self.assertRaises(ValueError), inject_provider_faults({"deepseek": ["boom"]}):
            pass


class NormalizationTests(unittest.TestCase):
    def test_source_ids_are_a_set_without_duplicates(self):
        self.assertEqual(normalize_source_ids([3, 1, 2]), [1, 2, 3])
        self.assertEqual(normalize_source_ids(["b", "a"]), ["a", "b"])
        for value, code in (([], "required"), (None, "required"), ([1, 1], "duplicate"), ([1, "2"], "invalid"), ([True], "invalid")):
            with self.subTest(value=value), self.assertRaises(RequestInvalid) as caught:
                normalize_source_ids(value)
            self.assertEqual(caught.exception.fields[0]["code"], code)

    def test_fingerprint_ignores_key_order_but_not_values(self):
        a = job_fingerprint("summary", None, {"source_ids": [1, 2], "length": "short"})
        b = job_fingerprint("summary", None, {"length": "short", "source_ids": [1, 2]})
        self.assertEqual(a, b)
        self.assertNotEqual(a, job_fingerprint("summary", None, {"length": "detailed", "source_ids": [1, 2]}))
        self.assertNotEqual(a, job_fingerprint("quiz", None, {"length": "short", "source_ids": [1, 2]}))

    def test_deadlines_follow_lim_11(self):
        self.assertEqual(timeout_for("chat"), 60)
        self.assertEqual(timeout_for("summary"), 120)
        self.assertEqual(timeout_for("quiz"), 120)

    def test_policy_registry_defaults_to_deny(self):
        self.assertIsInstance(policy_for("summary"), DenyAllPolicy)
        self.assertFalse(policy_for("summary").can_publish(None, None))
        allow = type("Allow", (), {"can_read": lambda *_: True, "can_publish": lambda *_: True})()
        register_policy("unit_test_job", allow)
        try:
            self.assertIs(policy_for("unit_test_job"), allow)
        finally:
            _POLICIES.pop("unit_test_job")

    def test_usage_rejects_unknown_or_content_fields(self):
        for usage in ({"prompt": "toàn văn"}, {"provider": "x" * 200}, {"model": ["list"]}):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                record_usage("00000000-0000-0000-0000-000000000000", usage)

    def test_outcome_status_is_limited(self):
        self.assertEqual(JobOutcome("NoEvidence").status, "NoEvidence")


if __name__ == "__main__":
    unittest.main()
