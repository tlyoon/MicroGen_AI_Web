"""Only sanitized provider-request metadata may cross the TTS subprocess boundary.

The audio worker never invents request IDs. An SDK response_id is NOT an HTTP
request_id and must not be relabeled as one. No raw provider errors, API keys,
headers, prompts or billing payloads enter this optional sidecar.
"""
from __future__ import annotations

import json
from pathlib import Path

from .tts_attempt_evidence import safe_provider_request_id


class TTSWorkerEvidenceError(ValueError):
    pass


def _assert_safe_paths(audio_path: Path, evidence_path: Path) -> None:
    if (audio_path.parent.resolve(strict=True) !=
            evidence_path.parent.resolve(strict=True)
            or evidence_path.name == audio_path.name
            or evidence_path.exists() or evidence_path.is_symlink()):
        raise TTSWorkerEvidenceError(
            "Worker evidence must be an unoccupied sibling of its temporary WAV")


def write_observation(audio_path: Path, evidence_path: Path, *,
                      outcome: str, exception: BaseException | None = None) -> None:
    _assert_safe_paths(audio_path, evidence_path)
    if outcome not in ("success", "exception") or (
        outcome == "success" and exception is not None
    ) or (outcome == "exception" and exception is None):
        raise TTSWorkerEvidenceError("Invalid worker event")
    data = {
        "schema_version": 1,
        "outcome": outcome,
        "provider_request_id": (
            safe_provider_request_id(exception) if exception else None),
        "error_type": type(exception).__name__ if exception else "",
    }
    with evidence_path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")


def read_observation(evidence_path: Path, *, outcome: str) -> str | None:
    if not evidence_path.is_file() or evidence_path.is_symlink():
        raise TTSWorkerEvidenceError("Missing or symlinked worker observation")
    try:
        observed = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise TTSWorkerEvidenceError("Malformed worker observation") from exc
    if (not isinstance(observed, dict)
            or set(observed) != {"schema_version", "outcome",
                                "provider_request_id", "error_type"}
            or observed["schema_version"] != 1
            or observed["outcome"] != outcome
            or not isinstance(observed["error_type"], str)
            or len(observed["error_type"]) > 100
            or not observed["error_type"].isidentifier()
               and observed["error_type"] != ""
            or (outcome == "success") != (observed["error_type"] == "")):
        raise TTSWorkerEvidenceError("Worker observation status mismatch")
    provider_id = observed["provider_request_id"]
    if provider_id is None:
        return None
    # Recheck against same extraction allowlist to prevent arbitrary JSON from
    # being accepted as an identifier. Never treat a generated UUID as provider ID.
    class Recorded:
        request_id = provider_id
    if safe_provider_request_id(Recorded()) != provider_id:
        raise TTSWorkerEvidenceError("Unsafe worker provider request identifier")
    return provider_id
