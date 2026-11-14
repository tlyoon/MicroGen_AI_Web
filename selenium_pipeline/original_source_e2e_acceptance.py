"""Original-source end-to-end launch gate: actionable, never a fake pass.

Use after the normal seven-stage integration. A green dry-run or GitHub CI
is NOT a complete original lecture; actual publisher/author/script and
per-element source math/figure mapping must be present before new PCM or
highlighted multipart video can be called production-ready.

This module can inspect all previously reviewed original lecture sections
without generating any Gemini/ChatGPT text, paid TTS, FFmpeg or student output.
When valid per-element PCM already exists and the actual source map is
complete, its explicit execute-prepared path calls the ALREADY implemented
production video renderer; it never synthesizes or splices slide WAVs.
"""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

from .evidence_reuse_contract import file_sha256


class SourceReleaseBlocked(ValueError):
    pass


def require(ok:bool, message:str)->None:
    if not ok:raise SourceReleaseBlocked(message)


def inspect_source_e2e(*,lecture:Path,checkpoint:Path|None=None,
                       fallback_dir:Path|None=None,
                       queue_dir:Path|None=None,
                       model_responses:Path|None=None,
                       expected_publisher_sha256:str|None=None)->dict:
    lecture=Path(lecture).absolute()
    require(lecture.is_dir() and not lecture.is_symlink(),
            "Real source-adjacent original publisher/author folder required")
    inputs={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        p=lecture/name
        require(p.is_file() and not p.is_symlink()
                and p.stat().st_size>0,
                "Missing original publisher/author/narration input: "+name)
        inputs[name]=file_sha256(p)
    if expected_publisher_sha256 is not None:
        require(inputs["source.pdf"]==expected_publisher_sha256,
                "Wrong publisher/source version for scholarly acceptance")
    from .sourcebound_completion_guard import inspect_sourcebound_completion
    prior=inspect_sourcebound_completion(lecture/"source.pdf")
    if prior["status"]=="ALREADY_COMPLETED_SOURCEBOUND_MULTIPART":
        return {
            "schema_version":1,
            "status":"REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY",
            "input_sha256":inputs,
            "part_count":prior["part_count"],
            "all_seven_stages_recomputed":False,
            "new_model_or_tts_calls":False,
            "student_publication_authorized":False,
        }

    triad=(checkpoint,fallback_dir,queue_dir)
    require(all(x is not None for x in triad),
            "Complete immutable source mapping queue required before launch")
    from .rich_unresolved_model_queue import verify_queue
    manifest,old,requests=verify_queue(
        source_folder=lecture,
        checkpoint=Path(checkpoint),fallback_dir=Path(fallback_dir),
        queue_folder=Path(queue_dir))
    require(manifest["source_inputs_sha256"]==inputs,
            "Unresolved queue references a different original source version")
    remaining=manifest["only_unresolved_utterances_requested"]
    already=manifest["already_accepted_prose_links_reused_not_sent"]
    review_ready=False
    review_reason="NO_COMPLETE_SOURCE_VERIFIED_MODEL_RESPONSE_BUNDLE"
    if model_responses is not None:
        from .rich_element_selection_compiler import compile_selection
        compiled=compile_selection(
            source_folder=lecture,checkpoint=Path(checkpoint),
            responses=Path(model_responses),
            tts_model="gemini-3.8-flash-lite-tts",tts_voice="Kore")
        require(compiled["source_inputs_sha256"]==inputs,
                "Model response belongs to different authored lecture")
        remaining=sum(
            1 for entry in compiled["remaining_technical_review_items"]
            if entry.get("utterance_id"))
        review_ready=bool(compiled["machine_technical_processing_ready"])
        review_reason=("ALL_TECHNICAL_SOURCE_TEXT_ASSOCIATIONS_ACCEPTED"
                       if review_ready else
                       "MATHEMATICAL_OR_FIGURE_OR_PARAPHRASE_REVIEW_INCOMPLETE")
    targets=(
        lecture/"element_narration_plan.json",
        lecture/"element_wav",
        lecture/"element_tts_manifest.json",
    )
    partial=[p.exists() or p.is_symlink() for p in targets]
    require(not any(partial) or all(partial),
            "Partial recorded element audio: preserve, no automatic regeneration")
    for p in targets:
        require(not p.is_symlink(),
                "Source-bound element narration/PCM cannot be symlinks")
    has_element_audio=all(partial)
    verified_audio=None
    if has_element_audio:
        # A *complete-looking* trio of paths is NOT evidence of authentic
        # source-tied element speech. The producer already has a shared,
        # physical verification route: adopt the SAME verifier here BEFORE
        # reporting render readiness, including if semantic review is still
        # incomplete. Otherwise an empty plan, empty WAV directory and '{}'
        # manifest misleadingly become "READY" whenever prose review passes.
        # Neither check generates audio, calls Gemini nor authorizes release.
        require(targets[0].is_file() and targets[1].is_dir()
                and targets[2].is_file(),
                "Element plan/WAV folder/producer manifest have wrong types")
        from .sourcebound_production_video import verify_element_tts_batch
        from .element_highlight_workflow import source_bound_plan
        try:
            attested=verify_element_tts_batch(
                source=lecture/"source.pdf",slides=lecture/"slides.pdf",
                authored=targets[0],audio=targets[1])
            physical=source_bound_plan(
                source=lecture/"source.pdf",slides=lecture/"slides.pdf",
                plan=targets[0],audio=targets[1])
            require(attested["element_count"]==physical["elements"]
                    and physical["slides"]==
                        manifest["original_slides"]
                    and physical["status"]=="review_only_preflight_complete",
                    "Element PCM provenance and original PDF coverage disagree")
        except (ValueError, OSError, KeyError, TypeError, wave.Error) as exc:
            raise SourceReleaseBlocked(
                "Existing element PCM lacks verified source/plan, producer "
                "identity, complete original WAVs or measured timings; "
                "preserve originals without re-TTS") from exc
        verified_audio={
            "status":"EXISTING_SOURCE_BOUND_ELEMENT_PCM_TECHNICALLY_VERIFIED",
            "element_count":physical["elements"],
            "source_slide_count":physical["slides"],
            "part_count":physical["parts"],
            "part_audio_seconds":physical["part_audio_s"],
            "producer_manifest_sha256":attested["manifest_sha256"],
            "source_hash_bound":True,
            "verified_audio_words_match_script":False,
            "independent_acoustic_listening_pass":False,
            "element_visual_semantics_approved":False,
            "student_publication_authorized":False,
        }
    status="BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION"
    if not remaining and review_ready and has_element_audio:
        status="READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER"
    elif not remaining and review_ready and not has_element_audio:
        status="SOURCE_MAPPING_VERIFIED_ELEMENT_PCM_REQUIRED"
    elif remaining and has_element_audio:
        status="BLOCKED_UNREVIEWED_MAPPING_WITH_EXISTING_AUDIO"
    return {
        "schema_version":1,
        "status":status,
        "source_inputs_sha256":inputs,
        "original_slide_count":manifest["original_slides"],
        "independently_previously_verified_text_links":already,
        "unresolved_source_element_mappings":remaining,
        "full_semantic_source_review_ready":review_ready,
        "full_semantic_source_review_reason":review_reason,
        "existing_per_element_recorded_audio_available":bool(verified_audio),
        "existing_element_pcm_technical_proof":verified_audio,
        "actual_audio_text_fidelity_independently_verified":False,
        "execution_allowed_without_new_paid_or_model_calls":
            status=="READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER",
        "dry_run_proves_entire_lecture_ready":False,
        "original_source_assets_modified":False,
        "new_model_or_tts_calls":False,
        "student_publication_authorized":False,
        "next_action":(
            "Complete original SHA-bound mathematical/figure source-to-visible "
            "review and obtain source-verified per-element PCM without "
            "changing frozen publisher/author assets" if remaining else
            "Render from already verified per-element PCM using existing "
            "strict multimedia contract" if has_element_audio else
            "Complete separately authorized per-element PCM synthesis and QA"),
    }


def execute_prepared(*,lecture:Path,checkpoint:Path,fallback_dir:Path,
                     queue_dir:Path,model_responses:Path)->dict:
    report=inspect_source_e2e(lecture=lecture,checkpoint=checkpoint,
        fallback_dir=fallback_dir,queue_dir=queue_dir,
        model_responses=model_responses)
    if report["status"]=="REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY":
        return report
    require(report["execution_allowed_without_new_paid_or_model_calls"],
            "Original academic lecture not ready; no new TTS or FFmpeg started: "+
            report["status"])
    from .full_pipeline_video_handoff import complete_from_published
    result=complete_from_published(source=Path(lecture).absolute()/"source.pdf",
                                   require_slide_tts_qa=False)
    require(result["status"] in {
        "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
        "REUSED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO"},
        "Existing production renderer did not accept original media")
    return {
        "status":"ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS",
        "input_sha256":report["source_inputs_sha256"],
        "video_result":result,
        "new_model_or_tts_calls":False,
        "student_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lecture",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path)
    p.add_argument("--fallback-dir",type=Path)
    p.add_argument("--queue-dir",type=Path)
    p.add_argument("--model-responses",type=Path)
    p.add_argument("--publisher-sha256")
    p.add_argument("--execute-prepared",action="store_true")
    a=p.parse_args(argv)
    if a.execute_prepared:
        require(all(x is not None for x in
            (a.checkpoint,a.fallback_dir,a.queue_dir,a.model_responses)),
            "Explicit source-bound mapping evidence mandatory before execution")
        result=execute_prepared(
            lecture=a.lecture,checkpoint=a.checkpoint,
            fallback_dir=a.fallback_dir,queue_dir=a.queue_dir,
            model_responses=a.model_responses)
    else:
        result=inspect_source_e2e(lecture=a.lecture,
            checkpoint=a.checkpoint,fallback_dir=a.fallback_dir,
            queue_dir=a.queue_dir,model_responses=a.model_responses,
            expected_publisher_sha256=a.publisher_sha256)
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
