"""Read-only source-bound per-slide audio candidate inventory for G2 closure.

A WAV without its verified receipt, a mixed/unverified voice contract, or an
unmatched source script must never be promoted into a production lecture.
This inventory diagnoses gaps; it cannot create missing TTS evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import wave

import pymupdf

from .evidence_reuse_contract import file_sha256


def inventory(*, lecture_dir: Path, audio_job: Path) -> dict:
    lecture_dir, audio_job = Path(lecture_dir).absolute(), Path(audio_job).absolute()
    for root in (lecture_dir, audio_job):
        if not root.is_dir() or root.is_symlink():
            raise ValueError("Source lecture/audio job directory invalid")
    triad = {k: lecture_dir / f for k, f in (
        ("source_sha256", "source.pdf"),
        ("slides_sha256", "slides.pdf"),
        ("script_sha256", "script.txt"))}
    if any(not p.is_file() or p.is_symlink() for p in triad.values()):
        raise ValueError("Actual source/slides/script triad missing")
    meta = audio_job / "source_audio_stage_manifest.json"
    if not meta.is_file() or meta.is_symlink():
        raise ValueError("Audio candidate provenance missing")
    data = json.loads(meta.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        raise ValueError("Audio candidate provenance invalid")
    hashes = {key: file_sha256(path) for key, path in triad.items()}
    if any(data.get(key) != value for key, value in hashes.items()):
        raise ValueError("Audio candidate is from a different source/slide/script")
    with pymupdf.open(triad["slides_sha256"]) as doc:
        count = len(doc)
    if count < 1 or count > 250 or data.get("slide_count") != count:
        raise ValueError("Wrong slide count in source-bound audio candidate")
    candidate = audio_job / ".tts_candidate"
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("No exact source-bound candidate WAV directory")
    identity_path = candidate / "candidate_job_identity.json"
    if not identity_path.is_file() or identity_path.is_symlink():
        raise ValueError("Missing source/script-bound Gemini candidate identity")
    identity = json.loads(identity_path.read_text(encoding="utf8"))
    if (not isinstance(identity, dict)
            or identity.get("script_sha256") != hashes["script_sha256"]
            or identity.get("provider") != "gemini"
            or identity.get("model") != data.get("model")
            or identity.get("voice") != data.get("voice")
            or not isinstance(identity.get("narration_sha256_by_slide"), dict)):
        raise ValueError("Audio job voice/model/narration identity mismatch")
    exact_job_sha = hashlib.sha256(json.dumps(
        identity, sort_keys=True).encode("utf-8")).hexdigest()
    existing = sorted(candidate.glob("slide*.wav"))
    verified = []
    missing = []
    incomplete = []
    expected = {f"slide{n}.wav" for n in range(1, count + 1)}
    if any(p.name not in expected or p.is_symlink() for p in existing):
        raise ValueError("Unexpected or unsafe candidate WAV")
    for n in range(1, count + 1):
        name = f"slide{n}.wav"
        path = candidate / name
        proof = candidate / (name + ".verified.json")
        if not path.is_file() or path.is_symlink() or path.stat().st_size <= 44:
            missing.append(n)
            continue
        if not proof.is_file() or proof.is_symlink():
            incomplete.append(n)
            continue
        try:
            receipt = json.loads(proof.read_text(encoding="utf8"))
            with wave.open(str(path), "rb") as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                channels = audio.getnchannels()
            if (not isinstance(receipt, dict)
                    or receipt.get("schema_version") != 1
                    or receipt.get("filename") != name
                    or receipt.get("provider") != identity["provider"]
                    or receipt.get("model") != identity["model"]
                    or receipt.get("voice") != identity["voice"]
                    or receipt.get("narration_sha256") !=
                        identity["narration_sha256_by_slide"].get(name)
                    or receipt.get("wav_sha256") != file_sha256(path)
                    or receipt.get("job_sha256") != exact_job_sha
                    or frames <= 0 or rate < 8000 or channels not in (1, 2)):
                incomplete.append(n)
                continue
        except (ValueError, OSError, TypeError, KeyError, wave.Error):
            incomplete.append(n)
            continue
        verified.append(n)
    missing_proof = sorted(set(range(1, count + 1)) - set(verified))
    return {
        "schema_version": 1,
        "status": ("ALL_SLIDE_WAV_PROOF_PRESENT_TECHNICAL_ONLY"
                   if not missing_proof else
                   "INCOMPLETE_SOURCE_BOUND_WAV_PROOF_NO_MEDIA_PROMOTION"),
        **hashes,
        "slide_count": count,
        "verified_wav_count": len(verified),
        "verified_slides": verified,
        "missing_audio_slides": missing,
        "incomplete_proof_slides": incomplete,
        "missing_proof_slides": missing_proof,
        "per_element_audio_alignment_verified": False,
        "independent_acoustic_qa_verified": False,
        "production_media_approved": False,
        "student_publication_authorized": False,
        "new_tts_or_model_calls": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--lecture-dir", type=Path, required=True)
    parser.add_argument("--audio-job", type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        result = inventory(lecture_dir=a.lecture_dir, audio_job=a.audio_job)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        result = {"status": "AUDIO_SOURCE_PROVENANCE_REJECTED",
                  "reason": str(exc), "new_tts_or_model_calls": False}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ALL_SLIDE_WAV_PROOF_PRESENT_TECHNICAL_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
