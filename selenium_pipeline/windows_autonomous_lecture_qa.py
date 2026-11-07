"""Read-only Windows autonomous AI/source/speech/video evidence reconciliation.

Reuses the existing independent source-cited two-pass AI scientific review,
original WAV/ASR phonetic screen and actual MP4 synchronization validator.
There is NO human academic signature requirement, no local model, no dispatch,
no audio synthesis and no permission to publish or retry original sources.

Even complete source/speech/MP4 *technical* evidence is not an independent
acoustic narrator-identity or full figure-diagram semantic guarantee.
Never promote that limited scope to a production or student release.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require

_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= 4_000_000,
            "Missing or unsafe existing evidence: " + path.name)
    item = json.loads(path.read_text(encoding="utf8"))
    require(type(item) is dict, "Existing evidence must be a JSON object")
    return item


def inspect(*, folder: Path, queue_root: Path, plan: Path, audio: Path,
            asr_dir: Path, video_probe=None, review_fn=None,
            speech_fn=None, video_fn=None) -> dict:
    """Recompute evidence; never trust a saved top-level approval boolean.

    Optional validators are deterministic offline test seams ONLY. Normal
    execution uses the existing production source/audio/video validators.
    """
    require(os.name == "nt", "Native Windows-only autonomous lecture QA")
    root = Path(folder).absolute()
    queue_root = Path(queue_root).absolute()
    plan = Path(plan).absolute()
    audio = Path(audio).absolute()
    asr_dir = Path(asr_dir).absolute()
    require(all(p.is_dir() and not p.is_symlink()
                for p in (root, queue_root, audio, asr_dir))
            and plan.is_file() and not plan.is_symlink()
            and plan.parent == root,
            "Original, AI queue, narration plan, WAV and ASR evidence required")
    require(not asr_dir.is_relative_to(audio)
            and not audio.is_relative_to(asr_dir)
            and not root.is_relative_to(queue_root)
            and not queue_root.is_relative_to(root),
            "Independent review inputs must not overwrite original sources")
    files = {name: root / name
             for name in ("source.pdf", "slides.pdf", "script.txt",
                          "lecture_completion.json")}
    require(all(p.is_file() and not p.is_symlink() and p.stat().st_size > 0
                for p in files.values()), "No actual source/slide/script/media")
    sha = {name: file_sha256(p) for name, p in files.items()}
    item = _read(plan)
    media = _read(files["lecture_completion.json"])
    require(item.get("status") == "author_specified_unapproved_element_narration",
            "Exact source-bound element narration plan required")
    for key, name in (("source_sha256", "source.pdf"),
                      ("slides_sha256", "slides.pdf"),
                      ("script_sha256", "script.txt")):
        require(item.get(key) == sha[name],
                "Narration plan not anchored to current " + name)
    require(media.get("origin") ==
            "independent_fresh_decoded_pixel_reverification"
            and media.get("authored_plan_sha256") == file_sha256(plan)
            and media.get("source_sha256") == sha["source.pdf"]
            and media.get("slides_sha256") == sha["slides.pdf"]
            and media.get("original_narration_script_sha256") == sha["script.txt"],
            "Only original SHA/plan-bound pixel-reverified multipart MP4 admissible")
    from .ai_academic_review_consensus import reconcile_actual_review_queue
    from .automatic_math_semantic_qa import inspect_math_semantics
    from .tts_quality_gate import screen
    from .production_video_contract import verify_series

    reviewer = reconcile_actual_review_queue if review_fn is None else review_fn
    speech_check = screen if speech_fn is None else speech_fn
    video_check = verify_series if video_fn is None else video_fn
    consensus = reviewer(queue_root=queue_root, folder=root)
    require(consensus.get("status") ==
            "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
            and type(consensus.get("original_utterances")) is int
            and consensus["original_utterances"] > 0
            and consensus.get("pending_or_disputed") == 0
            and len(consensus.get("accepted_ai_evidence", [])) ==
                consensus["original_utterances"]
            and consensus.get("student_publication_authorized") is False,
            "Two-pass source-cited Gemini science QA is incomplete or disputed")
    script = files["script.txt"].read_text(encoding="utf8")
    math_check = inspect_math_semantics(script, source_sha256=sha["source.pdf"])
    require(math_check["blocking_count"] == 0,
            "Known domain/sign/physics hazards require source-based correction")
    try:
        elements = [element for part in item["parts"]
                    for slide in part["slides"] for element in slide["elements"]]
        spoken = [element["spoken_text"] for element in elements]
        accepted = [x["original_spoken_sha256"]
                    for x in consensus["accepted_ai_evidence"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise CampaignRecoveryBlocked(
            "Unverifiable exact element-to-AI science coverage") from exc
    import hashlib
    hashes = [hashlib.sha256(t.encode("utf8")).hexdigest() for t in spoken]
    require(all(type(t) is str and len(t.strip()) >= 4 for t in spoken)
            and len(hashes) == len(set(e["wav"] for e in elements))
            and len(hashes) == consensus["original_utterances"]
            and all(type(h) is str and _SHA.fullmatch(h) for h in accepted)
            and Counter(hashes) == Counter(accepted),
            "Original source-reviewed narration elements are missing or duplicated")
    speech = speech_check(plan=plan, audio=audio, asr_dir=asr_dir, output=None)
    require(speech.get("status") == "QUALITY_SCREEN_REVIEW_ONLY"
            and speech.get("plan_sha256") == file_sha256(plan)
            and speech.get("all_machine_checks_passed") is True
            and speech.get("total_clips") == len(hashes)
            and speech.get("machine_screen_passed") == len(hashes)
            and speech.get("pending_asr") == 0
            and speech.get("technical_rejected") == 0
            and speech.get("manual_review_required") == 0,
            "Real WAV and independent AI-ASR phonetic QA not fully verified")
    technical = video_check(root, probe=video_probe)
    require(technical.get("status") == "accepted_synchronized_series"
            and technical.get("verification_scope") == "technical_media_only"
            and type(technical.get("parts")) is list
            and len(technical["parts"]) >= 1
            and all(type(p.get("duration_s")) in (int,float)
                    and 0 < p["duration_s"] < 600
                    and type(p.get("highlight_events")) is int
                    and p["highlight_events"] > 0
                    for p in technical["parts"]),
            "Actual under-600s synchronized pixel-verified MP4 series absent")
    return {
        "schema_version": 1,
        "status": "AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED",
        "source_sha256": sha["source.pdf"],
        "slides_sha256": sha["slides.pdf"],
        "script_sha256": sha["script.txt"],
        "media_receipt_sha256": sha["lecture_completion.json"],
        "ai_source_agreed_utterances": len(accepted),
        "source_and_ai_asr_matched_wav_clips": len(hashes),
        "verified_multipart_mp4_parts": len(technical["parts"]),
        "technical_domain_semantic_lint_passed": True,
        "automatic_source_science_ai_review_complete": True,
        "independent_ai_asr_and_phonetic_screen_complete": True,
        "sourcebound_synchronized_media_technically_verified": True,
        "autonomous_scoped_technical_qa_accepted": True,
        "scientific_ai_consensus_is_mathematical_proof": False,
        "acoustic_voice_identity_independently_verified": False,
        "independent_figure_diagram_semantics_fully_verified": False,
        "final_full_lecture_academic_acceptance": False,
        "human_academic_approval_required_by_this_preflight": False,
        "student_publication_authorized": False,
        "new_model_or_tts_calls": False,
        "new_video_rendered": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("folder", "queue-root", "plan", "audio", "asr-dir"):
        parser.add_argument("--" + arg, type=Path, required=True)
    opts = vars(parser.parse_args(argv))
    try:
        report = inspect(
            folder=opts["folder"], queue_root=opts["queue_root"],
            plan=opts["plan"], audio=opts["audio"],
            asr_dir=opts["asr_dir"])
    except (CampaignRecoveryBlocked, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as exc:
        report = {"status": "AUTONOMOUS_AI_LECTURE_QA_EVIDENCE_INCOMPLETE",
                  "reason_type": type(exc).__name__,
                  "new_model_or_tts_calls": False,
                  "student_publication_authorized": False}
        print(json.dumps(report, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
