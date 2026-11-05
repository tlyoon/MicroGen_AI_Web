"""Read-only Gemini API key-pool metadata verification on native Windows.

Check EACH configured numbered key against the vetted model's models.get()
endpoint. Unlike legacy first-key-only preflight, an independently observed
fallback key is distinguished from an untested fallback. This never performs
generate_content(), retries a prior ambiguous content request, prints key
material, changes the .env file, or authorizes billing/publication.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from .windows_provider_readiness_probe import CONTENT_MODEL, _safe_code

MAX_KEYS = 6


def inspect_key_pool(*, probe_metadata: bool = False,
                     transport: Callable[[str, str], object] | None = None,
                     configured_keys: list[str] | None = None) -> dict:
    """Test one metadata GET per unique key, in deterministic pool order."""
    base = {
        "schema_version": 1,
        "status": "GEMINI_API_KEY_POOL_READ_ONLY_NO_GENERATION",
        "verified_model": CONTENT_MODEL,
        "configured_key_count_nonsecret": 0,
        "per_key_metadata_results": [],
        "metadata_eligible_new_source_key_ordinals": [],
        "first_eligible_key_ordinal": None,
        "fallback_key_metadata_confirmed": False,
        "api_content_generation_success_proven": False,
        "automatic_replay_or_key_rotation_after_uncertain_send": False,
        "paid_api_content_generation_authorized": False,
        "model_generate_content_calls": 0,
        "new_tts_calls": 0,
        "student_publication_authorized": False,
    }
    if sys.platform != "win32":
        return {**base, "status": "NATIVE_WINDOWS_REQUIRED"}
    if configured_keys is None:
        try:
            from .runner import load_microvid_env
            from gemini_keys import get_gemini_api_keys
            load_microvid_env()
            keys = get_gemini_api_keys()
        except (OSError, RuntimeError, ImportError):
            keys = []
    else:
        keys = configured_keys
    if type(keys) is not list or any(type(x) is not str for x in keys):
        raise ValueError("Gemini key-pool must be an ordered list")
    # Suppress secrets even when bogus/malformed credential values are given.
    unique = list(dict.fromkeys(key.strip() for key in keys if key.strip()))
    base["configured_key_count_nonsecret"] = len(unique)
    if not unique:
        base["status"] = "NO_CONFIGURED_KEYS_NO_PROVIDER_CALLS"
        return base
    if len(unique) > MAX_KEYS:
        base["status"] = "KEY_POOL_EXCEEDS_BOUNDED_METADATA_INSPECTION"
        return base
    if not probe_metadata:
        base["status"] = "KEY_POOL_IDENTIFIED_METADATA_NOT_CHECKED"
        return base
    if transport is None:
        from google import genai
        from google.genai import types

        def transport(key: str, model: str) -> object:
            # No SDK retries, no model content. Client is closed on either result.
            opts = types.HttpOptions(
                timeout=10000,
                retry_options=types.HttpRetryOptions(attempts=1),
            )
            client = genai.Client(api_key=key, http_options=opts)
            try:
                return client.models.get(model=model)
            finally:
                client.close()

    for ordinal, key in enumerate(unique, 1):
        try:
            metadata = transport(key, CONTENT_MODEL)
            model_name = str(getattr(metadata, "name", ""))
            reached = model_name in (CONTENT_MODEL, "models/" + CONTENT_MODEL)
            code = None
            outcome = ("VETTED_MODEL_METADATA_REACHABLE"
                       if reached else "MODEL_NAME_MISMATCH")
            error_type = None
        except Exception as exc:
            reached = False
            outcome = "METADATA_LOOKUP_FAILED"
            code = _safe_code(exc)
            error_type = type(exc).__name__
        base["per_key_metadata_results"].append({
            "key_ordinal": ordinal,
            "metadata_status": outcome,
            "verified_vetted_model": reached,
            "structured_http_code": code,
            "exception_type": error_type,
            "key_material_in_report": False,
        })
        if reached:
            base["metadata_eligible_new_source_key_ordinals"].append(ordinal)

    good = base["metadata_eligible_new_source_key_ordinals"]
    base["first_eligible_key_ordinal"] = good[0] if good else None
    base["fallback_key_metadata_confirmed"] = any(x > 1 for x in good)
    base["status"] = ("KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE"
                      if good else "KEY_POOL_METADATA_CHECKED_NONE_REACHABLE")
    # Nothing here proves content-generation quota or success.
    return base


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify-each-key-model-metadata", action="store_true",
                   help="Opt-in up to six non-generating models.get requests")
    a = p.parse_args(argv)
    try:
        result = inspect_key_pool(probe_metadata=a.verify_each_key_model_metadata)
    except (ValueError, OSError, TypeError, ImportError) as exc:
        result = {"status": "GEMINI_API_KEY_METADATA_INSPECTION_REJECTED",
                  "error_type": type(exc).__name__,
                  "model_generate_content_calls": 0,
                  "automatic_replay_or_key_rotation_after_uncertain_send": False,
                  "student_publication_authorized": False}
    print(json.dumps(result, indent=2))
    return (0 if result.get("status") in {
        "KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE",
        "KEY_POOL_IDENTIFIED_METADATA_NOT_CHECKED",
    } else 2)


if __name__ == "__main__":
    raise SystemExit(main())
