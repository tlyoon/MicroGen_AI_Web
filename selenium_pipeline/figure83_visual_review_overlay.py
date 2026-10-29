"""Render non-production Figure 8.3 review overlays without changing lecture PDFs."""
from __future__ import annotations
import hashlib,io,json,math
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha

def validated_review_boxes(packet:dict,*,page_width:float,page_height:float)->list[dict]:
    require(type(packet) is dict and packet.get("status")=="ORIGINAL_FIGURE83_REVIEW_ONLY"
            and packet.get("student_publication_authorized") is False
            and packet.get("paid_tts_authorized") is False
            and type(packet.get("review_utterances")) is list
            and 0<len(packet["review_utterances"])<=100,
            "Source-bound review-only packet required")
    boxes=[]
    for e in packet["review_utterances"]:
        rect=e.get("candidate_full_expression_pdf_bbox_pt")
        if rect is None:continue
        require(type(rect) is list and len(rect)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in rect)
                and 0<=rect[0]<rect[2]<=page_width and
                0<=rect[1]<rect[3]<=page_height,
                "Review rectangle outside actual PDF page")
        boxes.append({"utterance_id":e["utterance_id"],"bbox":rect})
    return boxes

def render_review_preview(*,slides:Path,packet:dict,output:Path)->dict:
    slides,output=Path(slides).absolute(),Path(output).absolute()
    before=_sha(slides)
    require(before==packet.get("slides_sha256")
            and packet.get("slide_page")==5 and output.suffix.lower()==".png"
            and slides.parent not in output.parents and output!=slides
            and output.parent.is_dir(),
            "Require exact original slide fingerprint and independent PNG staging")
    with pymupdf.open(slides) as deck:
        require(len(deck)>=5,"Missing genuine slide 5")
        page=deck[4]
        boxes=validated_review_boxes(packet,page_width=page.rect.width,page_height=page.rect.height)
        for a in boxes:
            page.draw_rect(pymupdf.Rect(a["bbox"]),color=(1,.35,0),width=1.2,
                           overlay=True)
        data=page.get_pixmap(matrix=pymupdf.Matrix(2,2),
                             colorspace=pymupdf.csRGB,alpha=False).tobytes("png")
    require(_sha(slides)==before,"Lecture PDF mutated during review rendering")
    with output.open("xb") as handle:
        handle.write(data)
    return {"status":"REVIEW_PNG_ONLY_NEVER_PRODUCTION",
            "original_slides_sha256":before,
            "review_overlay_count":len(boxes),
            "review_png_sha256":hashlib.sha256(data).hexdigest(),
            "mathematical_accuracy_verified":False,
            "narrated_element_timing_verified":False,
            "student_publication_authorized":False}
