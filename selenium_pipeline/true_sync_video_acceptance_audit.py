"""Independent original figure + real WAV + encoded MP4 speech sync gate.

An inspected pause-based highlighted review MP4 is not narration-synchronized
element output; accepting speech sync requires separate reviewed element WAVs.
"""
from pathlib import Path
import json
from .figure_source_identity import require,_sha
from .reviewed_segment_tts_jobs import prepare
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .original_audio_element_reconciliation import verify_full_staged_element_coverage

def inspect(*,folder:Path,staged_review:Path|None=None,
            check_all_pixels:bool=True)->dict:
    folder=Path(folder).absolute()
    source,slides,script=(folder/x for x in ("source.pdf","slides.pdf","script.txt"))
    original=[_sha(x) for x in (source,slides,script)]
    plan=inspect_original_slide_wav_plan(folder)
    jobs=prepare(source=source,slides=slides,script=script)
    require([jobs["source_sha256"],jobs["slides_sha256"],jobs["script_sha256"]]==original
            and [plan["source_sha256"],plan["slides_sha256"]]==original[:2]
            and jobs["paid_provider_call_performed"] is False
            and jobs["student_publication_authorized"] is False,
            "Original source and input-only segment-TTS plan do not agree")
    reviewed=None
    if staged_review is not None:
        reviewed=verify_full_staged_element_coverage(
            original=folder,staged=Path(staged_review),
            check_all_pixels=check_all_pixels)
        require(reviewed["source_sha256"]==original[0]
                and reviewed["slides_sha256"]==original[1]
                and reviewed["student_publication_authorized"] is False
                and reviewed["audio_to_element_semantic_correspondence_verified"] is False,
                "Provisional figure highlight cannot become speech alignment")
    ready=(jobs["job_count"]>0
           and len(jobs["jobs"])==plan["original_wav_count"])
    # Even ready-by-count is not a verified audio sample or narrated-element
    # video: one slide may need several clips. Never promote it.
    require([_sha(p) for p in (source,slides,script)]==original,
            "Original teaching data changed during audit")
    return {"schema_version":1,
        "status":"REAL_FIGURE_AUDIO_VIDEO_TECHNICAL_REVIEW_SPEECH_ALIGNMENT_BLOCKED",
        "source_sha256":original[0],"slides_sha256":original[1],
        "script_sha256":original[2],
        "original_slide_wav_count":plan["original_wav_count"],
        "actual_staged_review_verified":reviewed is not None,
        "actual_staged_visual_events_rechecked":(
            reviewed["all_events_encoded_pixel_recheck_count"] if reviewed else 0),
        "original_narration_tts_job_count":jobs["job_count"],
        "complete_verified_source_element_wav_receipts_found":False,
        "real_spoken_element_audio_semantics_verified":False,
        "all_visual_elements_highlighted_as_spoken_verified":False,
        "all_staged_preview_parts_strictly_under_600":(
            bool(reviewed) and reviewed["verified_part_count"]>=1),
        "final_true_sync_production_encoded":False,
        "figure83_mathematical_axis_label_semantics_approved":False,
        "human_academic_and_listening_qa_verified":False,
        "original_teaching_assets_modified":False,
        "next_action":(
            "REVIEW_AND_VERIFY_ORIGINAL_EQUATION_FIGURE_UTTERANCE_MAPPINGS"
            if jobs["job_count"]==0 else
            "VERIFY_ACTUAL_ELEMENT_WAV_SAMPLES_AND_SYNCHRONIZED_ENCODED_MP4"),
        "student_publication_authorized":False}
def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--staged-review",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args(argv)
    report=inspect(folder=a.folder,staged_review=a.staged_review)
    if a.out is not None:
        dest=a.out.absolute()
        require(not dest.exists() and dest.parent.is_dir()
                and not dest.is_relative_to(a.folder.absolute()),
                "New isolated audit receipt required")
        with dest.open("x",encoding="utf8") as f:
            json.dump(report,f,indent=2,sort_keys=True)
    print(json.dumps({k:report[k] for k in (
        "status","actual_staged_visual_events_rechecked",
        "original_narration_tts_job_count","next_action",
        "student_publication_authorized")},indent=2))
    return 2
if __name__=="__main__":raise SystemExit(main())
