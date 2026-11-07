"""Classify exact provider UI error text from OWNED Gemini model replies.

Do not infer a global Gemini server outage, billing, API 503/504, or user
permission to resubmit from a browser model error. Never inspect unrelated
tabs, user prompts, or return the raw response text.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

_KNOWN_ERRORS = {
    # All variants have been observed in actual owned model replies.
    # Exact matching, not substring matching, avoids treating user prompts,
    # normal physics discussion, or the browser interface as an outage.
    "I seem to be encountering an error. Can I try something else for you?":
        "OLDER_GEMINI_MODEL_ERROR",
    "Sorry, something went wrong. Please try your request again.":
        "GEMINI_MODEL_REQUEST_ERROR",
    "I'm having a hard time fulfilling your request. Can I help you with something else instead?":
        "GEMINI_MODEL_COULD_NOT_FULFILL_REQUEST",
}


class GeminiOwnedVisibleTerminalError(RuntimeError):
    """A model-attributed terminal UI error after Send, never retry evidence."""


def require_no_owned_terminal_error(driver, owned_handle: str | None) -> None:
    """Fail early ONLY for an exact terminal reply in our current Gemini tab.

    Reuse the existing strict owned-response reader; do not inspect page text,
    the user's other tabs or generic clipboard contents. Never submit a prompt.
    """
    from .gemini_response_recovery import latest_owned_response

    snapshot = latest_owned_response(driver, owned_handle)
    evidence = classify_visible_reply(
        text=snapshot.get("text", ""),
        capture_status=snapshot.get("capture_status", "unavailable"),
        generating=bool(snapshot.get("generating")),
    )
    if evidence["known_gemini_ui_error_text_observed"]:
        raise GeminiOwnedVisibleTerminalError(
            "GEMINI_OWNED_VISIBLE_TERMINAL_ERROR_NO_RESEND"
        )


def classify_visible_reply(*, text: str, capture_status: str,
                           generating: bool = False) -> dict:
    raw = text if isinstance(text, str) else ""
    visible = capture_status in (
        "visible_model_response", "vendor_verified_response_copy")
    normalized = raw.replace("\r\n", "\n").strip()
    if normalized.startswith("Gemini said\n"):
        normalized = normalized[len("Gemini said\n"):].strip()
    variant = _KNOWN_ERRORS.get(normalized) if visible and not generating else None
    known = variant is not None
    return {
        "schema_version": 1,
        "status": (
            "GEMINI_OWNED_MODEL_VISIBLE_UI_ERROR_NOT_API_OUTAGE_PROOF"
            if known else "NO_CONFIRMED_KNOWN_PROVIDER_UI_ERROR"),
        "known_gemini_ui_error_text_observed": bool(known),
        "known_gemini_ui_error_code": variant,
        "owned_visible_model_response_text_observed":
            bool(visible and raw.strip()),
        "gemini_api_generation_tested": False,
        "provider_server_outage_proven": False,
        "browser_capture_total_failure_proven": False,
        "original_source_retry_authorized": False,
        "raw_model_reply_in_report": False,
        "student_publication_authorized": False,
    }


def inspect_quarantine(*, metadata_path: Path,
                       allowed_root: Path | None = None) -> dict:
    """Independently re-check existing hash-bound quarantine; no modifications."""
    from .gemini_response_recovery import read_quarantined_response
    root_arg = (Path(allowed_root) if allowed_root is not None else
                Path(os.environ.get("LOCALAPPDATA", "")) /
                "Microvid" / "gemini_quarantine")
    meta_arg = Path(metadata_path)
    # quarantine_snapshot writes to .resolve(); .absolute() retains '..'
    # segments and Windows temporary-root/junction aliases. Both inputs
    # must be canonicalized the SAME way before comparing their parents.
    # Keep the direct symlink checks before resolution, and still require
    # the canonical metadata file to be an immediate child of the
    # explicitly trusted canonical root.
    if root_arg.is_symlink() or meta_arg.is_symlink():
        raise ValueError("Quarantine metadata must be in trusted local root")
    root = root_arg.resolve(strict=True)
    meta_path = meta_arg.resolve(strict=True)
    if (not root.is_dir() or root.is_symlink()
            or meta_path.parent != root
            or meta_path.is_symlink() or not meta_path.is_file()
            or not meta_path.name.endswith(".meta.json")
            or meta_path.stat().st_size > 4096):
        raise ValueError("Quarantine metadata must be in trusted local root")
    data = json.loads(meta_path.read_text(encoding="utf8"))
    if (data.get("schema_version") != 1
            or data.get("status") != "incomplete_untrusted"
            or not isinstance(data.get("raw_filename"), str)
            or Path(data["raw_filename"]).name != data["raw_filename"]):
        raise ValueError("Quarantined Gemini response metadata invalid")
    raw = root / data["raw_filename"]
    if raw.is_symlink() or not raw.is_file():
        raise ValueError("Quarantined reply must be a real local file")
    text = read_quarantined_response(raw)  # checks byte SHA and length
    evidence = classify_visible_reply(
        text=text, capture_status=data.get("capture_status"),
        generating=bool(data.get("generation_active_at_capture")))
    return {
        **evidence,
        "quarantine_payload_sha256_verified": True,
        "quarantined_model_response_chars": len(text),
        "capture_status": data.get("capture_status"),
        "source_pdf_or_prompt_reopened": False,
        "new_model_or_tts_calls": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--quarantine-meta", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = inspect_quarantine(metadata_path=args.quarantine_meta)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError) as exc:
        report = {
            "status": "OWNED_GEMINI_QUARANTINE_EVIDENCE_REJECTED",
            "reason_type": type(exc).__name__,
            "provider_server_outage_proven": False,
            "original_source_retry_authorized": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(report, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
