"""Render all five original Slide4 highlight candidates as UNTIMED PNG previews.

Pixels are recomputed from original slides.pdf, not from synthetic teaching
figures or historical MP4. Never claim synchronized narration, media release
or author approval from a review-only static image.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pymupdf
from PIL import Image,ImageChops

from .figure_source_identity import require,_sha
from .highlight_frames import emphasize_source_rectangles
from .original_slide4_five_visual_candidates import (
    inspect_original_slide4_five_visual_candidates,
)


def render_five_untimed_original_slide4_previews(
    *,folder:Path,output_dir:Path,scale:float=2.0)->dict:
    root=Path(folder).absolute()
    output=Path(output_dir).absolute()
    require(type(scale) in (int,float) and math.isfinite(scale)
            and 1<=scale<=3,
            "Bounded original preview render scale required")
    require(root.is_dir() and not root.is_symlink()
            and output.is_dir() and not output.is_symlink()
            and not output.is_relative_to(root)
            and not any(output.iterdir()),
            "Review-only output must be precreated empty outside originals")
    sources=tuple(root/n for n in ("source.pdf","slides.pdf","script.txt"))
    shas=tuple(_sha(x) for x in sources)
    report=inspect_original_slide4_five_visual_candidates(folder=root)
    require(report["utterance_candidate_count"]==5
            and report["source_mathematical_review_approved"] is False
            and report["narration_timing_verified"] is False
            and report["highlighted_video_verified"] is False
            and (report["source_sha256"],report["slides_sha256"],
                 report["script_sha256"])==shas,
            "Only unapproved five-candidate exact original review allowed")
    with pymupdf.open(sources[1]) as pdf:
        require(len(pdf)>=4,"Original Slide4 PDF page not present")
        page=pdf[3]
        page_width,page_height=page.rect.width,page.rect.height
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
        clean=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    frames=[]
    for index,item in enumerate(report["utterance_candidates"],1):
        rect=item.get("candidate_highlight_bbox_pdf_pt")
        require(type(rect) is list and len(rect)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in rect)
                and 0<=rect[0]<rect[2]<=page_width
                and 0<=rect[1]<rect[3]<=page_height,
                "Original candidate highlight rectangle malformed or out of bounds")
        preview=emphasize_source_rectangles(clean,[rect],scale=scale)
        difference=ImageChops.difference(clean,preview)
        changed=difference.getbbox()
        require(changed is not None,
                "Original highlight candidate produced no visible changed pixels")
        tolerance=5*scale
        require(changed[0]>=rect[0]*scale-tolerance
                and changed[1]>=rect[1]*scale-tolerance
                and changed[2]<=rect[2]*scale+tolerance
                and changed[3]<=rect[3]*scale+tolerance,
                "Highlight pixels escaped authenticated original source bounds")
        filename=output/f"UNAPPROVED_source_slide4_candidate_{index:03d}.png"
        with filename.open("xb") as stream:
            preview.save(stream,format="PNG")
        frames.append({
            "original_utterance_id":item["utterance_id"],
            "original_spoken_sha256":item["original_spoken_sha256"],
            "review_target_id":item["review_target_id"],
            "visual_kind":item["candidate_kind"],
            "original_slide_bbox_pdf_pt":rect,
            "changed_pixel_bbox":list(changed),
            "preview_png_sha256":_sha(filename),
            "source_based_visual_emphasis_pixels_verified":True,
            "speech_or_academic_approval":False,
            "actual_speech_timestamp":None,
            "highlighted_video_frame_verified":False,
        })
    require(tuple(_sha(x) for x in sources)==shas,
            "Protected originals changed while rendering review-only previews")
    return {
        "status":"FIVE_ORIGINAL_SLIDE4_UNTIMED_HIGHLIGHT_PNG_PREVIEWS_ONLY",
        "source_sha256":shas[0],
        "slides_sha256":shas[1],
        "script_sha256":shas[2],
        "original_slide":4,
        "original_utterance_count":5,
        "source_based_png_preview_count":len(frames),
        "review_only_preview_frames":frames,
        "actual_speech_to_highlight_sync_verified":False,
        "original_Kore_audio_accepted":False,
        "independent_mathematics_review_approved":False,
        "approved_encoded_mp4_available":False,
        "student_publication_authorized":False,
        "new_model_requests_sent":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    a=parser.parse_args(argv)
    print(json.dumps(render_five_untimed_original_slide4_previews(
        folder=a.folder,output_dir=a.output_dir),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
