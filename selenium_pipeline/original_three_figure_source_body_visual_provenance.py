"""Independent original-textbook source-body visual provenance for Figures 8.4–8.6.

Finds authentic author-embedded PNG artwork in source textbook PAGE raster;
requires unique correct caption page and large margin against every wrong page.
This is an image-pattern correspondence, not full axis/graph label science.
Figures 8.2/8.3 are deliberately NOT promoted: lower first-pass correlation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .figure_source_identity import require, _sha
from .original_thomas84_figure_asset_trace import SOURCE_SHA, audit as audit_five
from .original_five_figure_evidence_reconciliation import (
    STATUS as CAPTION_STATUS,
)

TARGETS={"8.4":(3,10),"8.5":(4,13),"8.6":(4,15)}
STATUS="ORIGINAL_THOMAS84_THREE_SOURCE_BODY_ARTWORK_MATCHES_NOT_FULL_SCIENCE"

def classify_source_body(*,figure_id:str,expected_page:int,scores:list[dict])->dict:
    require(len(scores)==6 and sorted(row["page"] for row in scores)==list(range(1,7)),
            "Actual original publisher six-page visual-search evidence incomplete")
    for row in scores:
        require(-1<=row["normalized_correlation"]<=1
                and len(row["top_left_xy_px"])==2
                and all(type(k) is int and k>=0 for k in row["top_left_xy_px"]),
                "Image source-body similarity score or location invalid")
    ordered=sorted(scores,key=lambda p:p["normalized_correlation"],reverse=True)
    first,second=ordered[:2]
    score=first["normalized_correlation"]
    margin=score-second["normalized_correlation"]
    require(first["page"]==expected_page and score>=.78 and margin>=.20,
            f"Source-body visual identity NOT proven for Figure {figure_id}: "
            f"top page={first['page']} score={score:.4f} margin={margin:.4f}")
    return {
        "original_textbook_figure":figure_id,
        "unique_source_textbook_page":expected_page,
        "source_visual_normalized_correlation":round(float(score),5),
        "best_other_textbook_page_correlation":round(
            float(second["normalized_correlation"]),5),
        "source_visual_page_margin":round(float(margin),5),
        "source_raster_2x_top_left_xy_px":first["top_left_xy_px"],
        "original_author_png_to_textbook_source_body_visual_pattern_match":True,
        "complete_original_source_panel_pixel_equivalence_verified":False,
        "publisher_axis_ticks_and_symbol_science_approved":False,
        "individual_word_synchronized_figure_panel_labels_approved":False,
    }

def locate_figure_page_scores(*,original_pdf,figure_png:Path)->list[dict]:
    try:
        import cv2,numpy as np
        import pymupdf
    except ImportError as exc:
        require(False,f"Native Windows PDF/OpenCV source-body verification unavailable: {exc}")
    image=cv2.imread(str(figure_png),cv2.IMREAD_COLOR)
    require(image is not None and image.shape[0]>50 and image.shape[1]>60,
            "Author source image missing physical figure")
    # At original publisher PDF x2 raster, a 1.35x slide PNG closely
    # represents the source artwork from this physically pinned edition.
    template=cv2.resize(image,None,fx=1.35,fy=1.35,
                        interpolation=cv2.INTER_LINEAR)
    scores=[]
    for index,page in enumerate(original_pdf):
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(
            pix.height,pix.width,3)
        bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
        require(template.shape[0]<bgr.shape[0]
                and template.shape[1]<bgr.shape[1],
                "Original authored figure scale exceeds textbook page")
        result=cv2.matchTemplate(bgr,template,cv2.TM_CCOEFF_NORMED)
        _,score,_,coord=cv2.minMaxLoc(result)
        scores.append({"page":index+1,
                       "normalized_correlation":round(float(score),6),
                       "top_left_xy_px":list(map(int,coord))})
    return scores

def source_body_audit(*,root:Path,prior_receipt:dict)->dict:
    import pymupdf
    root=Path(root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and _sha(root/"source.pdf")==SOURCE_SHA
            and prior_receipt.get("status")==CAPTION_STATUS
            and prior_receipt.get("student_publication_authorized") is False,
            "Only frozen publisher original and earlier five-figure proof permitted")
    prior=prior_receipt["five_exact_original_caption_author_embedded_figure_identity_proofs"]
    previous={item["figure"]:item for item in prior}
    require(set(previous)=={"8.2","8.3","8.4","8.5","8.6"},
            "Old five source-caption author slide bitmap proof incomplete")
    old=audit_five(source=root/"source.pdf",slides=root/"slides.pdf",
                   latex=root/"slides.tex",figure_directory=root)
    require(old["figure_asset_to_embedded_bitmap_identity_count"]==5
            and old["full_figures_source_pdf_equivalence_accepted"] is False,
            "Existing exact author embedded image equality missing")
    inputs=[root/name for name in ("source.pdf","slides.pdf","slides.tex")]
    inputs.extend(root/f"Figure {label}.png" for label in previous)
    before={str(path):_sha(path) for path in inputs}
    proved={}
    with pymupdf.open(root/"source.pdf") as publisher:
        require(len(publisher)==6,"Wrong original textbook page count")
        for label,(page,slide) in TARGETS.items():
            image=root/f"Figure {label}.png"
            require(_sha(image)==previous[label]["original_author_image_sha256"]
                    and previous[label]["publisher_caption_number_source_verified"]
                    and previous[label]["original_author_png_identical_to_rendered_slide_bitmap"],
                    "Original source figure ID and authored bitmap mismatch")
            scores=locate_figure_page_scores(original_pdf=publisher,figure_png=image)
            matched=classify_source_body(figure_id=label,
                                         expected_page=page,scores=scores)
            proved[label]={
                **matched,"author_original_slide_number":slide,
                "author_original_png_sha256":_sha(image),
                "independent_all_six_pages_similarity_evidence":scores,
            }
    require(before=={str(path):_sha(path) for path in inputs},
            "Original textbook/slide/figures mutated during science audit")
    return {
        "status":STATUS,
        "original_source_sha256":SOURCE_SHA,
        "source_body_three_independent_figure_visual_witnesses":proved,
        "three_unique_correct_textbook_page_visual_matches":3,
        "figures_82_83_full_publisher_panel_correspondence_still_unproven":True,
        "five_original_figure_caption_and_rendered_png_matches_preserved":True,
        "mathematical_graph_label_semantic_and_utterance_complete":False,
        "full_academic_production_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--caption-receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.caption_receipt.is_file()
            and a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.root.absolute()),
            "Source and prior receipt must be immutable; output is exclusive")
    prior=json.loads(a.caption_receipt.read_text("utf8"))
    old=_sha(a.caption_receipt)
    result=source_body_audit(root=a.root,prior_receipt=prior)
    require(_sha(a.caption_receipt)==old,
            "Prior original captions unexpectedly changed during source proof")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"publisher_page_visual_matches":3,
                      "full_math_and_axis_label_acceptance":False,
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
