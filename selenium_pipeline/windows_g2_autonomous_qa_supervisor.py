"""Finite restart-safe academic QA -> genuine G2 audio/video supervisor.

Every run rechecks original source+slide+script hashes, the immutable 2-pass
review queue, and all accepted evidence. At most three independently selected
Gemini review units; no retry of a consumed claim. Once AND ONLY once every
utterance has two-pass source-cited support, an on-flight, genuine source-bound
audio/video attempt may proceed through the existing paid-TTS authorization,
figure guard, real PCM, decoded MP4 and independent acoustic QA validators.

No human click, no forged WAV or approval, no source overwrite, no infinite
PDF-specific loop. Windows login/browser and already configured production
provider credentials are external availability requirements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import require, CampaignRecoveryBlocked


def _is_verified_folder(folder: Path, queue_root: Path) -> tuple[dict, dict]:
    folder = Path(folder).absolute()
    queue_root = Path(queue_root).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and queue_root.is_dir() and not queue_root.is_symlink()
            and not queue_root.is_relative_to(folder)
            and not folder.is_relative_to(queue_root),
            "Academic supervisor must preserve isolated original-source review")
    queue_file = queue_root / "queue.json"
    require(queue_file.is_file() and not queue_file.is_symlink(),
            "Missing original immutable source-bound review queue")
    plan = json.loads(queue_file.read_text(encoding="utf8"))
    require(plan.get("status") == "IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and plan.get("original_source_folder") == str(folder)
            and type(plan.get("slide_jobs")) is list
            and bool(plan["slide_jobs"])
            and plan.get("student_publication_authorized") is False,
            "Original review queue does not match supplied lecture")
    from .ai_academic_review_queue import _check_queue
    for row in plan["slide_jobs"]:
        _check_queue(queue_root=queue_root, folder=folder,
                     slide=row["slide"], mode="INITIAL_REVIEW")
    before = {name: file_sha256(folder / name)
              for name in ("source.pdf", "slides.pdf", "script.txt")}
    expected = {
        "source.pdf": plan["slide_jobs"][0]["original_source_sha256"],
        "slides.pdf": plan["slide_jobs"][0]["original_slides_sha256"],
        "script.txt": plan["slide_jobs"][0]["original_script_sha256"],
    }
    require(before == expected,
            "Publisher source, slides or narration changed after review queue")
    return plan, before


def _report(status: str, hashes: dict, **extra) -> dict:
    return {
        "schema_version": 1,
        "status": status,
        "original_source_sha256": hashes["source.pdf"],
        "original_slides_sha256": hashes["slides.pdf"],
        "original_script_sha256": hashes["script.txt"],
        "student_publication_authorized": False,
        "G2_academic_scientific_acceptance_claimed": False,
        **extra,
    }


def step(*, folder: Path, queue_root: Path, work_root: Path,
         execute: bool = False, max_units: int = 3, auto_media: bool = True,
         health_family: str = "flash", execute_health_probe: bool = True,
         health_inspector: Callable | None = None,
         review_advance: Callable | None = None,
         consensus_reader: Callable | None = None,
         audio_producer: Callable | None = None,
         video_producer: Callable | None = None) -> dict:
    """One finite, locked operation. Safe for repeated external invocations."""
    require(type(max_units) is int and 0 <= max_units <= 3,
            "At most three academic claim attempts per supervisor cycle")
    folder, queue_root, work_root = [
        Path(p).absolute() for p in (folder, queue_root, work_root)]
    require(work_root.is_dir() and not work_root.is_symlink()
            and not work_root.is_relative_to(folder),
            "G2 scratch root must not be inside original teaching files")
    plan, hashes = _is_verified_folder(folder, queue_root)
    from .three_pc_worker import LocalInstanceLock
    lock_name = "g2_qa_" + hashlib.sha256(
        str(queue_root).encode("utf8")).hexdigest()[:20]
    with LocalInstanceLock(lock_name, work_root / ".microgen_g2_supervisor_locks"):
        # Revalidate AFTER acquiring cross-process lock. A concurrent run
        # must not reserve a second Gemini Send against the same slide.
        plan, hashes = _is_verified_folder(folder, queue_root)
        attempt = None
        provider_health = None
        new_source_sends_deferred = False
        if execute and max_units:
            from .ai_academic_review_queue import (
                advance_bounded_safe_reviews, select_next_safe_review)
            selected = select_next_safe_review(
                queue_root=queue_root,folder=folder,health_family=health_family)
            if (selected.get("status") == "ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY"
                    and selected.get("action") == "FRESH_FIRST_ATTEMPT"):
                from .academic_queue_fresh_send_health import check as check_health
                verifier = health_inspector or check_health
                provider_health = verifier(
                    queue_root=queue_root,checkpoint_parent=work_root,
                    source_sha=hashes["source.pdf"],family=health_family,
                    execute_source_free_probe=execute_health_probe)
                new_source_sends_deferred = (
                    provider_health.get("new_source_review_send_allowed") is not True)
            if not new_source_sends_deferred:
                dispatcher = review_advance or advance_bounded_safe_reviews
                if review_advance is None:
                    attempt = dispatcher(queue_root=queue_root, folder=folder,
                                         max_units=max_units, execute=True,
                                         health_family=health_family)
                else:
                    # Keep test-only injected dispatch contract unchanged.
                    attempt = dispatcher(queue_root=queue_root, folder=folder,
                                         max_units=max_units, execute=True)
        from .ai_academic_review_consensus import reconcile_actual_review_queue
        read_consensus = consensus_reader or reconcile_actual_review_queue
        state = read_consensus(queue_root=queue_root, folder=folder)
        require(state.get("status") ==
                "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
                and state.get("original_utterances") ==
                    plan.get("expected_utterances")
                and type(state.get("accepted_ai_evidence")) is list
                and type(state.get("pending_or_disputed")) is int
                and len(state["accepted_ai_evidence"]) +
                    state["pending_or_disputed"] == plan["expected_utterances"]
                and state.get("student_publication_authorized") is False,
                "Independent academic review reconciliation incomplete/corrupt")
        agreed = len(state["accepted_ai_evidence"])
        pending = state["pending_or_disputed"]
        from .ai_academic_review_queue import select_next_safe_review
        next_safe = select_next_safe_review(
            queue_root=queue_root,folder=folder,health_family=health_family)
        common = {
            "two_pass_ai_source_agreed_segments": agreed,
            "pending_or_disputed_segments": pending,
            "expected_original_utterances": state["original_utterances"],
            "bounded_review_attempt": attempt,
            "provider_health": provider_health,
            "next_safe_academic_action": next_safe,
            "new_paid_tts_dispatched": False,
            "real_mp4_encoded_this_cycle": False,
        }
        if pending:
            return _report(
                ("G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND"
                 if new_source_sends_deferred else
                 "G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR"),
                hashes, **common)
        require(agreed > 0, "Empty consensus is not lecture acceptance")
        from .ai_academic_review_audio_bridge import prepare_real_source_ai_kore_jobs
        # Source-reviewed TTS handoff is *unpaid* and freshly source-locked.
        handoff = prepare_real_source_ai_kore_jobs(
            folder=folder,queue_root=queue_root)
        require(handoff["unresolved_source_segments"] == 0
                and handoff["AI_source_agreed_segments"] == agreed
                and len(handoff["actual_verbatim_jobs"]) == agreed
                and handoff["paid_TTS_request_made"] is False
                and handoff["student_publication_authorized"] is False,
                "Academic source-to-TTS coverage incomplete or unverified")
        if not execute or not auto_media:
            return _report("G2_ACADEMIC_TWO_PASS_SOURCE_QA_READY_FOR_REAL_AUDIO",
                           hashes, **common,
                           source_verified_tts_jobs=agreed)
        # Genuine audio generation is allowed ONLY under the existing
        # standing production TTS cost guard. An unsupported figure/semantic
        # alignment stops *before* provider billing, never invents a WAV.
        from .automatic_element_narration import (
            inspect_text_only, AutomaticElementAudioError)
        try:
            inspect_text_only(source=folder/"source.pdf",
                              slides=folder/"slides.pdf",
                              script=folder/"script.txt")
        except (AutomaticElementAudioError, OSError, ValueError) as exc:
            return _report(
                "G2_SOURCE_REVIEW_PASSED_COMPLEX_ELEMENT_AUDIO_ROUTE_REQUIRED",
                hashes, **common, source_verified_tts_jobs=agreed,
                blocked_at="REAL_SOURCE_TEXT_FIGURE_GEOMETRY_PREFLIGHT",
                reason=str(exc)[:500])
        from .automatic_element_audio_stage import produce_element_audio
        from .sourcebound_production_video import (
            verify_element_tts_batch,render_and_install_prepared)
        plan_path=folder/"element_narration_plan.json"
        audio_dir=folder/"element_wav"
        if plan_path.exists() or audio_dir.exists():
            require(plan_path.is_file() and audio_dir.is_dir(),
                    "Incomplete previous audio evidence; do not pay/resubmit")
            verify_element_tts_batch(
                source=folder/"source.pdf",slides=folder/"slides.pdf",
                authored=plan_path,audio=audio_dir)
            audio_status = "EXISTING_AUDIO_REVERIFIED_NO_REBILL"
        else:
            synth=audio_producer or produce_element_audio
            result=synth(
                source=folder/"source.pdf",slides=folder/"slides.pdf",
                script=folder/"script.txt",local_work_root=work_root)
            require(result.get("status") ==
                    "ELEMENT_AUDIO_READY_FOR_AUTOMATIC_VIDEO_STAGE",
                    "Provider did not return verified complete original PCM")
            audio_status = result["status"]
        completion=folder/"lecture_completion.json"
        if completion.exists():
            require(completion.is_file() and not completion.is_symlink(),
                    "Unsafe prior media completion")
            from .production_video_contract import verify_series
            verify_series(folder)
            media_status="EXISTING_VIDEO_REVERIFIED_NO_OVERWRITE"
        else:
            renderer=video_producer or render_and_install_prepared
            render=renderer(
                source=folder/"source.pdf", slides=folder/"slides.pdf",
                authored=plan_path, audio=audio_dir,local_work_root=work_root)
            require(type(render) is dict and render.get("status"),
                    "No actual verified encoded video evidence")
            media_status=render["status"]
        require(all(file_sha256(folder/n) == v for n,v in hashes.items()),
                "Publisher/author source changed during audio and video")
        # Full acoustic G2 requires independent original phonetic/ASR
        # receipts; these are NEVER inferred from waveform or MP4 existence.
        return _report("G2_MEDIA_GENERATED_AWAITING_INDEPENDENT_ACOUSTIC_QA",
                       hashes, **{**common,"new_paid_tts_dispatched":
                                   audio_status!="EXISTING_AUDIO_REVERIFIED_NO_REBILL",
                                   "real_mp4_encoded_this_cycle":
                                   media_status!="EXISTING_VIDEO_REVERIFIED_NO_OVERWRITE"},
                       source_verified_tts_jobs=agreed,
                       audio_stage=audio_status,media_stage=media_status,
                       acoustic_qa_accepted=False)


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--queue-root",type=Path,required=True)
    parser.add_argument("--work-root",type=Path,required=True)
    parser.add_argument("--max-units",type=int,default=3)
    parser.add_argument("--health-family",choices=("flash","pro"),default="flash")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--no-auto-media",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=step(folder=args.folder,queue_root=args.queue_root,
                    work_root=args.work_root,execute=args.execute,
                    health_family=args.health_family,
                    auto_media=not args.no_auto_media,max_units=args.max_units)
    except (CampaignRecoveryBlocked,RuntimeError,ValueError,OSError,KeyError) as exc:
        result={"status":"G2_AUTONOMOUS_SUPERVISOR_SOURCE_GATE_BLOCKED",
                "reason_type":type(exc).__name__,
                "reason":str(exc)[:500],
                "student_publication_authorized":False,
                "new_unsupported_model_sends":False}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result["status"] not in {
        "G2_AUTONOMOUS_SUPERVISOR_SOURCE_GATE_BLOCKED"} else 2


if __name__=="__main__":
    raise SystemExit(main())
