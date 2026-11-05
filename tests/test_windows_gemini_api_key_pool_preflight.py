"""Key rotation metadata checks: per-key and no paid/replayed generation."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.windows_gemini_api_key_pool_preflight import inspect_key_pool


class KeyPoolMetadataPreflightTests(unittest.TestCase):
    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_real_ordinal_sequence_and_fallback_key_works_independently(self):
        received = []
        def get(key, model):
            received.append((key, model))
            if key == "first-invalid-key":
                exc = PermissionError("a secret MUST NOT leak")
                exc.code = 403
                raise exc
            return SimpleNamespace(name="models/" + model)
        r = inspect_key_pool(
            probe_metadata=True, transport=get,
            configured_keys=["first-invalid-key", "second-valid-key"])
        self.assertEqual([item[0] for item in received],
                         ["first-invalid-key", "second-valid-key"])
        self.assertEqual(r["metadata_eligible_new_source_key_ordinals"], [2])
        self.assertEqual(r["first_eligible_key_ordinal"], 2)
        self.assertTrue(r["fallback_key_metadata_confirmed"])
        self.assertEqual(r["per_key_metadata_results"][0]["structured_http_code"], 403)
        self.assertNotIn("a secret MUST NOT leak", str(r))
        self.assertNotIn("first-invalid-key", str(r))
        self.assertNotIn("second-valid-key", str(r))
        self.assertFalse(r["api_content_generation_success_proven"])
        self.assertFalse(r["paid_api_content_generation_authorized"])
        self.assertFalse(r["automatic_replay_or_key_rotation_after_uncertain_send"])

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_both_keys_get_metadata_once_without_generate_content(self):
        received = []
        def get(key, model):
            received.append(key)
            return SimpleNamespace(name="models/" + model)
        r = inspect_key_pool(
            probe_metadata=True, transport=get,
            configured_keys=["first", "second", "first"])
        self.assertEqual(received, ["first", "second"])
        self.assertEqual(r["configured_key_count_nonsecret"], 2)
        self.assertEqual(r["metadata_eligible_new_source_key_ordinals"], [1, 2])
        self.assertEqual(r["model_generate_content_calls"], 0)

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_no_network_by_default_even_with_configured_keys(self):
        def no_call(*args):
            raise AssertionError("Must not send an API GET without consent")
        r = inspect_key_pool(
            configured_keys=["first", "second"], transport=no_call)
        self.assertEqual(r["status"], "KEY_POOL_IDENTIFIED_METADATA_NOT_CHECKED")
        self.assertEqual(r["per_key_metadata_results"], [])
        self.assertFalse(r["fallback_key_metadata_confirmed"])

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_metadata_504_does_not_retry_same_key(self):
        sent = []
        def get(key, model):
            sent.append(key)
            err = TimeoutError("TOKEN_MUST_NOT_APPEAR")
            err.code = 504
            raise err
        r = inspect_key_pool(
            probe_metadata=True, transport=get,
            configured_keys=["first", "second"])
        self.assertEqual(sent, ["first", "second"])
        self.assertEqual(r["metadata_eligible_new_source_key_ordinals"], [])
        self.assertFalse(r["automatic_replay_or_key_rotation_after_uncertain_send"])
        self.assertEqual([x["structured_http_code"] for x in r["per_key_metadata_results"]],
                         [504, 504])
        self.assertNotIn("TOKEN_MUST_NOT_APPEAR", str(r))

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_more_than_six_keys_never_dispatches_metadata(self):
        r = inspect_key_pool(
            probe_metadata=True, configured_keys=[str(i) for i in range(7)],
            transport=lambda *args: self.fail("Too many keys must stop"))
        self.assertEqual(r["status"], "KEY_POOL_EXCEEDS_BOUNDED_METADATA_INSPECTION")
        self.assertEqual(r["per_key_metadata_results"], [])

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "win32")
    def test_model_identity_mismatch_fails_closed(self):
        r = inspect_key_pool(
            probe_metadata=True, configured_keys=["fake"],
            transport=lambda *_: SimpleNamespace(name="models/other"))
        self.assertEqual(r["status"], "KEY_POOL_METADATA_CHECKED_NONE_REACHABLE")
        self.assertIsNone(r["first_eligible_key_ordinal"])

    @patch("selenium_pipeline.windows_gemini_api_key_pool_preflight.sys.platform", "linux")
    def test_windows_only(self):
        r = inspect_key_pool(
            probe_metadata=True, configured_keys=["key"],
            transport=lambda *a: self.fail("No remote"))
        self.assertEqual(r["status"], "NATIVE_WINDOWS_REQUIRED")
        self.assertEqual(r["model_generate_content_calls"], 0)


if __name__ == "__main__":
    unittest.main()
