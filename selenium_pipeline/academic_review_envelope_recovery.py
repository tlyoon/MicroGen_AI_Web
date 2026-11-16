"""No-Send recovery of a model-owned, JSON-wrapped original academic reply.

Gemini sometimes returns {"job":{"status":..., "rows":[...]}} instead of
the requested top-level candidate. Unwrap ONLY this known syntactic envelope.
Never create a verdict, identity, source quote, target, row or scientific claim.
All rows subsequently pass the unchanged strict source/citation validator.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .figure_source_identity import require


def unwrap_exact_review_envelope(response: dict) -> tuple[dict, bool]:
    require(type(response) is dict, "Academic reply must be a JSON object")
    if response.get("status") == "ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE":
        return response, False
    require(set(response) == {"job"} and type(response["job"]) is dict,
            "Not an exact single-object academic-review envelope")
    inner = response["job"]
    require(set(inner) == {"status", "rows"}
            and inner["status"] == "ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
            and type(inner["rows"]) is list
            and 1 <= len(inner["rows"]) <= 40,
            "Nested academic review is missing exact status/rows identity")
    return inner, True


def _proof(checkpoint: Path, job: dict, mode: str) -> dict:
    from .academic_review_checkpoint import _load, fingerprint
    from .ai_academic_web_review import review_instructions
    require(mode in ("INITIAL_REVIEW", "INDEPENDENT_CHALLENGE"),
            "Unrecognized original review pass")
    state = _load(checkpoint)
    expected = fingerprint(
        request_text=review_instructions(job, mode=mode),
        source_hashes={
            name: job[field] for name, field in (
                ("source.pdf", "source_sha256"),
                ("slides.pdf", "slides_sha256"),
                ("script.txt", "script_sha256"),
            )
        }, review_mode=mode)
    require(state.get("request_fingerprint") == expected
            and state.get("status") in {
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"}
            and state.get("source_sha256") == job["source_sha256"]
            and state.get("slides_sha256") == job["slides_sha256"]
            and state.get("script_sha256") == job["script_sha256"]
            and state.get("can_auto_retry") is False,
            "Recovery requires identical rejected original request")
    raw_path = checkpoint / "model_response_untrusted.txt"
    identity_path = checkpoint / "model_response_identity.json"
    send_path = checkpoint / "dispatch_attempted.claim"
    require(checkpoint.is_dir() and not checkpoint.is_symlink()
            and raw_path.is_file() and not raw_path.is_symlink()
            and identity_path.is_file() and not identity_path.is_symlink()
            and send_path.is_file() and not send_path.is_symlink()
            and raw_path.stat().st_size <= 500_000,
            "Recovery requires the original owned response and Send witness")
    raw = raw_path.read_bytes().decode("utf8")
    digest = hashlib.sha256(raw.encode("utf8")).hexdigest()
    witness = json.loads(identity_path.read_text(encoding="utf8"))
    require(raw.strip() and state.get("response_sha256") == digest
            and state.get("response_length_chars") == len(raw)
            and witness.get("schema_version") == 1
            and witness.get("kind") == "SAVED_POST_CLAIM_MODEL_REPLY_V1"
            and witness.get("response_sha256") == digest
            and witness.get("request_fingerprint") == expected
            and witness.get("review_mode") == mode
            and witness.get("source_sha256") == job["source_sha256"]
            and witness.get("slides_sha256") == job["slides_sha256"]
            and witness.get("script_sha256") == job["script_sha256"]
            and witness.get("new_model_requests") is False
            and witness.get("approved") is False,
            "Envelope reply not independently bound to original Send/source")
    return {"raw": raw, "sha256": digest, "fingerprint": expected}


def inspect_owned_nested_envelope(*, checkpoint: Path,
                                  job: dict, mode: str) -> dict | None:
    """Read-only incident classifier; no model interaction or alterations."""
    checkpoint = Path(checkpoint).absolute()
    witness = _proof(checkpoint, job, mode)
    try:
        candidate = json.loads(witness["raw"])
        inner, wrapped = unwrap_exact_review_envelope(candidate)
    except (ValueError, TypeError, KeyError):
        return None
    if not wrapped:
        return None
    expected_ids = {u["id"] for slide in job["slides"]
                    for u in slide["utterances"]}
    ids = [x.get("utterance_id") for x in inner["rows"]
           if type(x) is dict]
    if not (len(ids) == len(inner["rows"])
            and len(ids) == len(set(ids))
            and set(ids).issubset(expected_ids)):
        return None
    return {"status": "VERIFIED_WRAPPED_SOURCE_REVIEW_NO_SEND",
            "response_sha256": witness["sha256"],
            "request_fingerprint": witness["fingerprint"],
            "model_rows": len(ids),
            "original_utterances": job["utterance_count"],
            "new_provider_requests": 0,
            "academic_approval": False,
            "student_publication_authorized": False}
