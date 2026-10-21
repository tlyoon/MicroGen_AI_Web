"""Original Figure 8.3 utterance-to-PDF review packet, never a release manifest."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from .figure_source_identity import require,_sha
from .figure83_slide_page_coordinates import actual_slide_figure_placement,transform_review_boxes
from .math_aware_slide5_figure_candidates import audit as source_review
from .figure83_source_math_acceptance_gate import evaluate_candidate_release

def assemble_review_packet(*,review:dict,placement:dict)->dict:
    disposition=evaluate_candidate_release(review)
    require(placement.get("original_slides_sha256")==review["slides_sha256"],
            "The source-bound original slide PDF fingerprint differs")
    conversion=transform_review_boxes(placement=placement,boxes=review["utterances"])
    indexed={entry["utterance_id"]:entry for entry in review["utterances"]}
    items=[]
    for anchor in conversion["review_anchors"]:
        original=indexed[anchor["utterance_id"]]
        items.append({"utterance_id":anchor["utterance_id"],
                      "original_narration":original["original_narration"],
                      "hypothesized_graph_panel":original["candidate_ordered_graph_panel"],
                      "candidate_full_expression_pdf_bbox_pt":
                          anchor["candidate_equation_pdf_points"],
                      "source_math_approved":False,
                      "actual_spoken_timing_approved":False})
    result={"schema_version":1,"status":"ORIGINAL_FIGURE83_REVIEW_ONLY",
            "source_sha256":review["source_sha256"],
            "slides_sha256":review["slides_sha256"],
            "script_sha256":review["script_sha256"],
            "slide_page":placement["slide_page"],
            "figure_placement":placement["figure_placement_pdf_pt"],
            "review_utterances":items,
            "review_dispositions":disposition["utterance_dispositions"],
            "release_blockers":disposition["release_blockers"],
            "student_publication_authorized":False,"paid_tts_authorized":False,
            "encoded_narrated_video_approved":False}
    canonical=json.dumps(result,sort_keys=True,ensure_ascii=True,separators=(",",":"))
    result["packet_content_sha256"]=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result

def audit_original_files(*,source:Path,slides:Path,script:Path)->dict:
    files=[Path(f).absolute() for f in (source,slides,script)]
    before=[_sha(f) for f in files]
    mapping=source_review(source=files[0],slides=files[1],script=files[2])
    placement=actual_slide_figure_placement(slides=files[1])
    packet=assemble_review_packet(review=mapping,placement=placement)
    require([_sha(f) for f in files]==before,"Original lecture files changed during review")
    return packet

def export_review_packet(packet:dict,*,output:Path,originals:list[Path])->Path:
    output=Path(output).absolute()
    require(output.suffix==".json" and len(originals)==3
            and all(isinstance(f,Path) for f in originals)
            and packet.get("status")=="ORIGINAL_FIGURE83_REVIEW_ONLY"
            and packet.get("student_publication_authorized") is False,
            "Only bounded review-only JSON may be exported")
    for original in originals:
        source_folder=original.absolute().parent
        require(output!=original.absolute()
                and source_folder not in output.parents,
                "Review outputs cannot enter or overwrite original teaching folder")
    require(output.parent.is_dir(),"Review staging folder must already exist")
    data=json.dumps(packet,indent=2,sort_keys=True,ensure_ascii=True)
    with output.open("x",encoding="utf-8",newline="\n") as f:
        f.write(data+"\n")
    return output

