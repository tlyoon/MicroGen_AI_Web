"""Original G3 slide PDF page -> real encoded MP4 frame parity, no QA release.

Reuses the *existing* retrofit_image_repair._compare_frame(): an actual
decoded MP4 frame is compared to the original publisher-backed authored PDF
page, rendered at 1280x720 with proper centred 4:3 pillarboxing. Naively
resizing the original PDF to 16:9 yields false mismatches. One timestamp at
the centre of each exact original slide WAV is a TECHNICAL source-page-order
witness only; it is NOT proof of timing highlights, math/speech or acoustics.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile

import pymupdf

from .figure_source_identity import require,_sha
from .g3_source_media_technical_preflight_v1 import (
    inspect as technical_inspect,SECTION,ROOT as TECH_ROOT)
from .g3_multisection_autoforward_v71 import _verified_specs
from .recovery_registry import lookup_mechanism

KIND="g3_original_video_page_parity"
SIGNATURE="G3_FULL_VIDEO_DECODED_BUT_ORIGINAL_SLIDE_PAGES_NOT_PIXEL_WITNESSED"
MECHANISM="SAMPLE_ACTUAL_ENCODED_FRAMES_AT_ORIGINAL_WAV_MIDPOINTS_NO_RELEASE"
ROOT="g3_original_video_page_parity_v1"
STATUS="G3_ORIGINAL_AUTHORED_SLIDES_VIDEO_FRAMES_PIXEL_WITNESSED_UNAPPROVED"
MAX_RASTER_RGB_MAE=12.0
MAX_SLIDES=24


def _canon(data:dict)->bytes:
    return (json.dumps(data,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def _historical_compare(*,video:Path,second:float,
                        pdf,slide:int,scratch:Path)->float:
    # Proven historical code reuses original source PDF page geometry and
    # 4:3->16:9 centred letterboxing; no new ad-hoc guessed video transform.
    from .retrofit_image_repair import _compare_frame
    return _compare_frame(video,second,pdf,slide,scratch)


def inspect(*,spec:dict,media_root:Path,state_root:Path,
            compare=None,technical_probe=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Original encoded G3 frame parity recovery is not registered")
    require(spec["section"] in SECTION,
            "Only original G3 Serway subsection identity may be checked")
    state=Path(state_root).absolute()
    root=Path(media_root).absolute()
    media=root/SECTION[spec["section"]]
    require(root.is_dir() and state.is_dir() and media.is_dir()
            and not root.is_symlink() and not state.is_symlink()
            and not media.is_symlink(),
            "G3 original saved source and real media folders required")
    technical=technical_inspect(
        spec=spec,media_root=root,state_root=state,probe=technical_probe)
    require(technical["status"]==
            "G3_SOURCE_MEDIA_TECHNICALLY_CHECKED_UNAPPROVED"
            and technical["student_publication_authorized"] is False
            and technical["independent_video_QA_complete"] is False
            and technical["new_browser_sends"]==0,
            "Original G3 technical media decoding must precede page proof")
    prior=Path(technical["receipt"]).absolute()
    require(prior.is_file() and not prior.is_symlink()
            and prior.parent==state/TECH_ROOT/spec["section"],
            "Source/video evidence not pinned to original technical packet")
    old=json.loads(prior.read_text("utf8"))
    require(old["status"]==
            "G3_SOURCE_MEDIA_TECHNICALLY_CHECKED_UNAPPROVED"
            and old["section"]==spec["section"]
            and old["original_source_inputs_sha256"]==
                spec["identity"]["source_inputs_sha256"]
            and old["independent_video_audio_decoding_complete"] is True
            and old["student_publication_authorized"] is False
            and len(old["videos"])==3
            and len(old["original_slide_wavs"])==
                old["original_slide_count"]<=MAX_SLIDES,
            "Previous video/wav original-source receipt was not authoritative")
    slides=media/"slides.pdf"
    full=media/"slides.mp4"
    require(_sha(slides)==spec["identity"][
                "source_inputs_sha256"]["slides.pdf"]
            and _sha(full)==old["videos"][0]["sha256"],
            "Original slide PDF or full MP4 changed after technical QA")
    compare=compare or _historical_compare
    observations=[]
    elapsed=0.0
    with pymupdf.open(slides) as pdf, tempfile.TemporaryDirectory(
            prefix="microgen_g3_source_page_parity_") as temp:
        require(len(pdf)==len(old["original_slide_wavs"]),
                "Original authored G3 slide count drift")
        for n,row in enumerate(old["original_slide_wavs"],1):
            wav=media/f"slide{n}.wav"
            require(row["slide"]==n
                    and _sha(wav)==row["sha256"],
                    "Original narrated slide or WAV changed after technical QA")
            seconds=row["duration_seconds"]
            midpoint=elapsed+seconds*.5
            elapsed+=seconds
            require(0<=midpoint<old["full_video_duration_seconds"],
                    "Original narrated slide midpoint outside encoded video")
            mae=compare(video=full,second=midpoint,pdf=pdf,
                        slide=n,scratch=Path(temp))
            require(type(mae) in (float,int)
                    and 0<=mae<MAX_RASTER_RGB_MAE,
                    "Actual G3 encoded page differs from original PDF pixels")
            observations.append({
                "original_slide":n,
                "original_source_WAV_sha256":row["sha256"],
                "narration_midpoint_seconds":round(midpoint,4),
                "actual_encoded_MP4_to_original_PDF_RGB_MAE":round(mae,4),
                "physical_original_slides_pdf_sha256":_sha(slides),
                "publisher_source_scientific_meaning_verified":False,
                "within_slide_highlights_verified":False,
            })
    require(_sha(full)==old["videos"][0]["sha256"]
            and _sha(prior)==hashlib.sha256(prior.read_bytes()).hexdigest(),
            "Original video/source technical packet changed during comparison")
    record={
        "schema_version":1,"status":STATUS,
        "section":spec["section"],
        "original_source_inputs_sha256":
            spec["identity"]["source_inputs_sha256"],
        "original_full_encoded_MP4_sha256":old["videos"][0]["sha256"],
        "original_technical_packet_sha256":_sha(prior),
        "original_slide_count":len(observations),
        "original_page_witness_samples":observations,
        "maximum_encoded_frame_source_RGB_MAE":max(
            x["actual_encoded_MP4_to_original_PDF_RGB_MAE"]
            for x in observations),
        "one_narration_midpoint_sample_per_original_slide":True,
        "original_page_order_pixel_evidence_complete":True,
        "source_PDF_semantic_science_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "independent_full_video_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0}
    scope=hashlib.sha256(_canon(record)).hexdigest()
    receipt={"scope_sha256":scope,**record}
    out=state/ROOT/spec["section"]
    require(not out.is_symlink() and not out.is_relative_to(media),
            "Redirected original frame QA checkpoint")
    out.mkdir(parents=True,exist_ok=True)
    file=out/(scope+".json")
    require(not file.is_symlink(),"Redirected source frame parity receipt")
    body=_canon(receipt)
    if file.exists():
        require(file.is_file() and file.read_bytes()==body,
                "Original encoded frame/source PDF proof changed after checkpoint")
    else:
        with file.open("xb") as stream:
            stream.write(body);stream.flush()
            import os
            os.fsync(stream.fileno())
    return {
        "status":STATUS,"section":spec["section"],
        "original_slide_frames_verified":len(observations),
        "maximum_frame_RGB_MAE":record[
            "maximum_encoded_frame_source_RGB_MAE"],
        "scope_sha256":scope,"receipt":str(file),
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "source_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False}


def materialize(*,manifest:Path,media_root:Path,state_root:Path,
                compare=None,technical_probe=None)->dict:
    _,specs=_verified_specs(Path(manifest).absolute())
    require(len(specs)==len(SECTION)
            and {x["section"] for x in specs}==set(SECTION),
            "Original G3 Serway 8.2 and 8.3 source manifest required")
    items=[inspect(spec=s,media_root=media_root,state_root=state_root,
                   compare=compare,technical_probe=technical_probe)
           for s in specs]
    return {
        "status":"G3_ORIGINAL_VIDEO_SOURCE_FRAME_PAGE_ORDER_WITNESSED_NO_RELEASE",
        "sections":items,"original_slides_pixel_witnessed":sum(
            x["original_slide_frames_verified"] for x in items),
        "all_original_visual_page_order_matched":True,
        "source_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0}
