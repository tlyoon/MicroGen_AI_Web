"""Windows-only source generation provider readiness, WITHOUT paid generation.

Provider metadata probe (explicit opt-in) sends only one models.get request,
never generate_content, never a source PDF, never user prompts or secrets.
Existing browser readiness check inspects a configured authenticated Chrome
session read-only. A timed-out/uncertain previous job can never be auto-retried
merely because this read-only preflight returns metadata.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable


CONTENT_MODEL = "gemini-3.8-flash"


def _safe_code(exc: Exception) -> int | None:
    try:
        value = getattr(exc, "code", None)
        if callable(value):
            value = value()
        value = int(value)
        return value if 100 <= value <= 599 else None
    except (ValueError, TypeError):
        return None


def inspect(*, metadata_probe: bool = False,
            inspect_gemini_browser: bool = False,
            model: str = CONTENT_MODEL,
            metadata_transport: Callable[[str, str], object] | None = None,
            available_key_count: int | None = None,
            browser_check=None) -> dict:
    if sys.platform != "win32":
        return {
            "status": "WINDOWS_ONLY",
            "new_model_generation_calls": 0,
            "student_publication_authorized": False,
        }
    if model != CONTENT_MODEL:
        return {
            "status": "VETTED_MODEL_ONLY",
            "new_model_generation_calls": 0,
            "student_publication_authorized": False,
        }
    # Never materialize environment secrets in result. Count may be supplied
    # by a deterministic offline unit test.
    try:
        if available_key_count is None:
            from .runner import load_microvid_env
            load_microvid_env()
            from gemini_keys import get_gemini_api_keys
            keys = get_gemini_api_keys()
            key_count = len(keys)
        else:
            keys = []
            key_count = available_key_count
    except (ImportError, OSError, RuntimeError):
        keys = []
        key_count = 0
    details = {
        "schema_version": 1,
        "status": "PROVIDER_READINESS_NOT_A_LESSON_GENERATION",
        "windows_native": True,
        "content_model": model,
        "api_key_configured": key_count > 0,
        "api_key_count_nonsecret": key_count,
        "api_model_metadata": "NOT_CHECKED_NO_NETWORK",
        "browser_ui_readiness": "NOT_CHECKED_NO_BROWSER_ATTACH",
        "new_model_generation_calls": 0,
        "paid_api_content_generation_performed": False,
        "new_tts_calls": 0,
        "source_pdf_transmitted": False,
        "student_publication_authorized": False,
        "existing_ambiguous_model_submission_retry_permitted": False,
        "full_end_to_end_generation_certified": False,
    }
    if inspect_gemini_browser:
        try:
            if browser_check is None:
                from .rich_mapping_provider_readiness import inspect_provider
                health = inspect_provider("gemini")
            else:
                health = browser_check("gemini")
            details["browser_ui_readiness"] = (
                "AUTHENTICATED_COMPOSER_READY" if
                health["authenticated_ui_ready"] else
                health["status"])
        except Exception:
            details["browser_ui_readiness"] = "BROWSER_READINESS_ERROR"
    if metadata_probe:
        if not key_count:
            details["api_model_metadata"] = "NO_CONFIGURED_API_KEY"
        else:
            try:
                if metadata_transport is None:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(
                        api_key=keys[0],
                        http_options=types.HttpOptions(timeout=10000),
                    )
                    try:
                        metadata = client.models.get(model=model)
                    finally:
                        client.close()
                else:
                    # Only offline tests may supply this callable.
                    metadata = metadata_transport("test_key", model)
                name = str(getattr(metadata, "name", ""))
                details["api_model_metadata"] = (
                    "VETTED_MODEL_METADATA_REACHABLE"
                    if name.endswith("/" + model) or name == model
                    else "API_METADATA_MODEL_ID_UNEXPECTED")
            except Exception as exc:
                details["api_model_metadata"] = "API_METADATA_LOOKUP_FAILED"
                details["api_model_metadata_error_type"] = type(exc).__name__
                details["api_model_metadata_status_code"] = _safe_code(exc)
    return details


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-api-model-metadata-once", action="store_true",
                        help="Explicit non-generation GET model metadata")
    parser.add_argument("--inspect-browser", action="store_true",
                        help="Read-only inspection of existing Chrome UI")
    args = parser.parse_args(argv)
    report = inspect(metadata_probe=args.probe_api_model_metadata_once,
                     inspect_gemini_browser=args.inspect_browser)
    print(json.dumps(report, indent=2))
    return (0 if report.get("status") ==
            "PROVIDER_READINESS_NOT_A_LESSON_GENERATION" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
