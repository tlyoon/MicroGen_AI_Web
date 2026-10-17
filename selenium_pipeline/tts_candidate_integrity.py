"""Fail-closed TTS candidate resume with immutable model/voice/text and WAV hashes.

Never adopt a legacy candidate solely because it has a RIFF header. Unverified
WAVs, partial files and mismatched job identities remain in place for review.
This utility is local/offline and makes no API or Google Cloud requests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


class CandidateIntegrityError(RuntimeError):
    pass


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()



def reject_existing_final_audio(folder: Path) -> None:
    """Abort before credentials or paid TTS when any final audio exists.

    Final artifacts can be old, manually repaired, or generated under another
    model. A matching manifest or RIFF header is *not* proof that a new TTS
    invocation may reuse or replace them. Preserve every original byte and
    require a separately reviewed reconciliation in an isolated workspace.
    """
    protected = []
    for item in folder.iterdir():
        if (re.fullmatch(r"slide[0-9]+\.wav", item.name, re.IGNORECASE)
                or item.name.lower() == "tts_input_manifest.json"):
            protected.append(item.name)
    if protected:
        raise CandidateIntegrityError(
            "Existing final TTS outputs require reviewed reconciliation "
            "before any paid regeneration; preserved: "
            + ", ".join(sorted(protected)))

def job_identity(items: list[tuple[int, str]], *,
                 provider: str, model: str, voice: str,
                 script_sha256: str) -> dict:
    if len({number for number, _ in items}) != len(items):
        raise CandidateIntegrityError("Repeated candidate slide numbers")
    return {
        "schema_version": 1,
        "provider": provider,
        "model": model,
        "voice": voice,
        "script_sha256": script_sha256,
        "narration_sha256_by_slide": {
            f"slide{number}.wav": sha(text.encode("utf-8"))
            for number, text in items
        },
    }


def _read_exact(path: Path, expected: dict) -> None:
    if not path.is_file() or path.is_symlink():
        raise CandidateIntegrityError("Missing, unsafe or symlinked candidate proof: " + path.name)
    try:
        observed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CandidateIntegrityError("Unreadable candidate proof: " + path.name) from exc
    if observed != expected:
        raise CandidateIntegrityError("Candidate model/voice/narration or WAV hash mismatch: " + path.name)


def prepare(candidate: Path, identity: dict) -> None:
    """Bind cache before any billable TTS request or candidate byte reuse."""
    if not candidate.is_dir() or candidate.is_symlink():
        raise CandidateIntegrityError("Unusable candidate folder")
    proof = candidate / "candidate_job_identity.json"
    existing = list(candidate.iterdir())
    if proof.exists() or proof.is_symlink():
        _read_exact(proof, identity)
    elif existing:
        raise CandidateIntegrityError(
            "Unverified legacy TTS candidates preserved; cannot adopt or delete without review")
    else:
        with proof.open("x", encoding="utf-8") as file:
            json.dump(identity, file, indent=2, sort_keys=True)
            file.write("\n")
    expected = identity["narration_sha256_by_slide"]
    for item in candidate.iterdir():
        if item.name == "candidate_job_identity.json":
            continue
        if item.name.endswith(".partial") or item.is_symlink():
            raise CandidateIntegrityError("Unverified interrupted candidate preserved: " + item.name)
        if item.name.endswith(".wav"):
            if item.name not in expected:
                raise CandidateIntegrityError("Stale candidate WAV preserved: " + item.name)
            verify_one(candidate, item.name, identity)
        elif item.name.endswith(".wav.verified.json"):
            name = item.name.removesuffix(".verified.json")
            if name not in expected or not (candidate / name).is_file():
                raise CandidateIntegrityError("Orphaned TTS candidate receipt preserved: " + item.name)


def receipt_for(candidate: Path, filename: str, identity: dict) -> dict:
    source = candidate / filename
    if filename not in identity["narration_sha256_by_slide"]:
        raise CandidateIntegrityError("Unexpected candidate slide number")
    if not source.is_file() or source.is_symlink():
        raise CandidateIntegrityError("Missing/symlinked candidate WAV")
    audio = source.read_bytes()
    if len(audio) <= 44 or audio[:4] not in (b"RIFF", b"RF64"):
        raise CandidateIntegrityError("Invalid candidate WAV")
    return {
        "schema_version": 1,
        "job_sha256": sha(json.dumps(identity, sort_keys=True).encode("utf-8")),
        "filename": filename,
        "wav_sha256": sha(audio),
        "narration_sha256": identity["narration_sha256_by_slide"][filename],
        "provider": identity["provider"],
        "model": identity["model"],
        "voice": identity["voice"],
    }


def record_one(candidate: Path, filename: str, identity: dict) -> None:
    """One-shot receipt after a newly generated WAV is atomically published."""
    with (candidate / (filename + ".verified.json")).open("x", encoding="utf-8") as file:
        json.dump(receipt_for(candidate, filename, identity),
                  file, indent=2, sort_keys=True)
        file.write("\n")


def verify_one(candidate: Path, filename: str, identity: dict) -> None:
    actual = receipt_for(candidate, filename, identity)
    _read_exact(candidate / (filename + ".verified.json"), actual)
