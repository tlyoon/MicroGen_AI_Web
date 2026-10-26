"""Stage five ACTUAL Thomas 8.4 Slide-4 source-backed corrected TTS segments.

Real source geometry is rendered to review-only PNGs, then each *revised*
utterance SHA is joined to one source-verified original highlight region.
No provider request, WAV timing, independent academic approval or MP4 is
invented by this step. A second independent source review is still mandatory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .automatic_math_semantic_qa import inspect_math_semantics
from .original_slide4_math_correction_pilot import (
    prepare_corrected_original_slide4,
)
from .original_slide4_untimed_highlight_preview import (
    render_five_untimed_original_slide4_previews,
)

def stage_corrected_five_unit_handoff(*, folder:Path, output_dir:Path)->dict:
    original=Path(folder).absolute()
    dest=Path(output_dir).absolute()
    require(original.is_dir() and not original.is_symlink()
            and not dest.exists() and dest.parent.is_dir()
            and not dest.is_relative_to(original),
            "Fresh separate review-only staging directory required")
    before={n:_sha(original/n) for n in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
    plan=prepare_corrected_original_slide4(folder=original)
    require((plan["source_sha256"],plan["slides_sha256"],plan["script_sha256"])==
            (before["source.pdf"],before["slides.pdf"],before["script.txt"]),
            "Original source/slide/script drift")
    corrected=plan["corrected_utterances"]
    require(len(corrected)==5 and
            all(row["new_same_voice_TTS_wav_received"] is False for row in corrected),
            "Expect exactly five unrecorded corrected narration units")
    # We can detect known risks but cannot certify mathematical truth.
    check=inspect_math_semantics(
        "\n\n".join(x["revised_narration"] for x in corrected),
        source_sha256=before["source.pdf"])
    require(check["blocking_count"]==0,
            "Corrected narration still has known mathematical sign/domain hazards")
    # Three geometric boundary explanations must be explicit; textual
    # evidence does not by itself prove the original source PDF's notation.
    require(all("degenerate" in corrected[i]["revised_narration"].lower()
                for i in range(4))
            and "negative" in corrected[0]["revised_narration"].lower()
            and all("absolute value of x" in corrected[i]["revised_narration"].lower()
                    for i in (0,1,2)) is False,
            "Corrected narration lost zero-leg / sign branch explanation")
    dest.mkdir()
    images=dest/"source_visual_preview"
    images.mkdir()
    preview=render_five_untimed_original_slide4_previews(
        folder=original,output_dir=images)
    require(preview["source_based_png_preview_count"]==len(corrected)
            and preview["source_sha256"]==before["source.pdf"]
            and preview["slides_sha256"]==before["slides.pdf"]
            and preview["script_sha256"]==before["script.txt"],
            "Source visual preview or narration changed")
    units=[]
    for i,(row,frame) in enumerate(zip(corrected,
                                       preview["review_only_preview_frames"]),1):
        require(row["original_utterance_id"]==frame["original_utterance_id"]
                and row["original_spoken_sha256"]==frame["original_spoken_sha256"]
                and row["original_source_verified_target_id"]==frame["review_target_id"],
                "Corrected spoken text and source highlight target differ")
        request=row["new_same_voice_tts_request_candidate"]
        require(request["tts_text_sha256"]==row["revised_text_sha256"]
                and request["preferred_voice"]=="Kore"
                and request["no_request_submitted"] is True
                and _sha(images/f"UNAPPROVED_source_slide4_candidate_{i:03d}.png")
                     ==frame["preview_png_sha256"],
                "Missing real source visual pixels or exact corrected text hash")
        units.append({
            "original_utterance_id":row["original_utterance_id"],
            "old_spoken_sha256":row["original_spoken_sha256"],
            "corrected_tts_text":row["revised_narration"],
            "corrected_tts_text_sha256":row["revised_text_sha256"],
            "source_verified_visual_target_id":frame["review_target_id"],
            "bbox_pdf_pt":frame["original_slide_bbox_pdf_pt"],
            "preview_png_relative_path":
                f"source_visual_preview/UNAPPROVED_source_slide4_candidate_{i:03d}.png",
            "preview_png_sha256":frame["preview_png_sha256"],
            "preferred_voice":"Kore",
            "preferred_provider":"Gemini web Flash-Lite TTS",
            "tts_audio_relative_path_expected":f"new_Kore_utterance_{i:03d}.wav",
            "original_source_math_review_passes":0,
            "revised_text_independently_approved":False,
            "corrected_real_WAV_exists":False,
            "corrected_speech_content_verified":False,
            "actual_chunk_start_ms":None,
            "actual_chunk_end_ms":None,
            "encoded_highlighted_video_verified":False,
        })
    require(all(_sha(original/name)==sha for name,sha in before.items()),
            "Protected original changed during visual/TTS staging")
    result={
        "schema_version":1,
        "status":"GENUINE_ORIGINAL_FIVE_CORRECTED_SEGMENTS_VISUALLY_STAGED_NOT_APPROVED",
        "source_sha256":before["source.pdf"],
        "slides_sha256":before["slides.pdf"],
        "script_sha256":before["script.txt"],
        "historical_slide4_WAV_sha256":before["slide4.wav"],
        "slide":4,"segment_count":5,
        "mathematical_endpoint_sign_guard_findings":check["blocking_count"],
        "source_verified_tts_highlight_units":units,
        "real_new_TTS_WAV_count":0,
        "genuine_tts_provider_request_sent":False,
        "independent_two_pass_math_acceptance":False,
        "timing_or_speech_content_accepted":False,
        "actual_MP4_accepted":False,
        "student_publication_authorized":False,
        "source_files_modified":False,
    }
    out=dest/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json"
    with out.open("x",encoding="utf-8") as file:
        json.dump(result,file,indent=2,ensure_ascii=False)
        file.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    args=p.parse_args(argv)
    result=stage_corrected_five_unit_handoff(
        folder=args.folder,output_dir=args.output_dir)
    print(json.dumps({"status":result["status"],
                      "source_verified_segments":result["segment_count"],
                      "corrected_WAV_received":result["real_new_TTS_WAV_count"],
                      "mathematics_two_pass_approved":False,
                      "out":str(args.output_dir)},ensure_ascii=True))
if __name__=="__main__":
    main()
