"""Reconcile ALL five original §8.4 figure assets with existing source/slide evidence.

This checks actual original textbook caption identity and exact author PNG/pixel
identity for every figure. Source-panel completeness, labels, axes, sign/domain
science and spoken element timing are NOT certified by a matching caption.
Never replace source files or claim student production acceptance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .figure_source_identity import require, _sha
from .original_thomas84_figure_asset_trace import (
    SOURCE_SHA, EXPECTED, audit as figure_audit,
)
from .original_all41_38_source_academic_gap_reconciler import STATUS as GAP_STATUS

STATUS="ORIGINAL_FIVE_FIGURE_PNG_SLIDE_CAPTION_IDENTITY_RECONCILED_SCIENCE_REVIEW_PENDING"

def reconcile(*,source_folder:Path,prior_scholarly:dict)->dict:
    source_folder=Path(source_folder)
    require(source_folder.is_dir() and not source_folder.is_symlink()
            and _sha(source_folder/"source.pdf")==SOURCE_SHA,
            "Wrong publisher-original Thomas §8.4 source; never use regenerated lecture")
    require(prior_scholarly.get("status")==GAP_STATUS
            and prior_scholarly.get("student_publication_authorized") is False
            and prior_scholarly.get("full_original_production_gate_passed") is False
            and prior_scholarly.get("original_source_slides")==41,
            "Only current known nonproduction 41-original slide inventory supported")
    historic=prior_scholarly["figure_identity_and_full_panel_label_worklist_for_this_register"]
    require(len(historic)==5,
            "Do not silently add or omit any of five original unresolved figure mappings")
    evidence=figure_audit(source=source_folder/"source.pdf",
                          slides=source_folder/"slides.pdf",
                          latex=source_folder/"slides.tex",
                          figure_directory=source_folder)
    require(evidence["status"]=="FIVE_ORIGINAL_FIGURE_ASSETS_BITMAP_IDENTICAL_SOURCE_CAPTIONS_FOUND"
            and evidence["figure_asset_to_embedded_bitmap_identity_count"]==5
            and evidence["original_source_pdf_sha256"]==SOURCE_SHA
            and evidence["full_figures_source_pdf_equivalence_accepted"] is False
            and evidence["student_publication_authorized"] is False,
            "Existing source panel/caption/author-bitmap evidence untrustworthy")
    expected_keys={f"8.4_slide{slide}":f"Figure {label}.png"
                   for (label,slide) in EXPECTED}
    require({row["slide"]:row["author_source_figure"] for row in historic}
            ==expected_keys,"Academic image registry disagrees with actual authored source")
    by_key={f"8.4_slide{x['original_slide_number']}":x
            for x in evidence["figures"]}
    require(set(by_key)==set(expected_keys),"Original figure source audit missing slides")
    original=prior_scholarly["detailed_original_slide_acceptance_deficits"]
    output=[]
    for item in historic:
        key=item["slide"]
        fig=by_key[key]
        row=original[key]
        expected_png=expected_keys[key]
        require(item["author_source_figure"]==expected_png
                and item["author_figure_sha256"]==fig["original_asset_sha256"]
                and fig["original_named_figure_file"]==expected_png
                and fig["decoded_asset_pixels_identical_to_embedded_slide_bitmap"] is True
                and fig["mathematical_figure_labels_verified"] is False
                and fig["source_figure_semantics_approved"] is False
                and row["actual_original_source_source_spoken_focus_scene_present"] is True,
                "Caption and author PNG identity must not certify an incorrect image or semantics")
        output.append({
            "original_slide_id":key,"figure":fig["figure_id"],
            "original_publisher_caption_page":fig["source_textbook_caption_page"],
            "original_author_image_sha256":fig["original_asset_sha256"],
            "original_actual_embedded_figure_pdf_rect_pt":
                fig["actual_embedded_slide_rect_pt"],
            "publisher_caption_number_source_verified":True,
            "original_author_png_identical_to_rendered_slide_bitmap":True,
            "publisher_figure_full_panel_source_crop_verified":False,
            "publisher_figure_all_math_symbols_and_axis_labels_verified":False,
            "publisher_figure_all_spoken_label_timing_verified":False,
            "source_figure_scholarship_final_accepted":False,
            "earlier_specialized_source_figure_reviews_may_reduce_remaining_work":True,
            "next_check":"Compare original textbook figure source-body panels and every "
                "label, domain and axis tick with the rendered author image; "
                "cross-reference existing source-verified specialized receipts "
                "before creating any new repaired figure.",
        })
    require(len(output)==5,"Original textbook image sample count altered")
    return {
        "status":STATUS,"original_source_pdf_sha256":SOURCE_SHA,
        "original_author_slide_pdf_sha256":evidence["original_slides_pdf_sha256"],
        "original_41_slide_38_spoken_qa_independently_retained":True,
        "five_exact_original_caption_author_embedded_figure_identity_proofs":output,
        "figure_assets_with_confirmed_source_caption_and_author_render_identity":5,
        "figure_assets_with_full_source_panel_math_axis_spoken_completeness_approved":0,
        "figure_semantics_still_pending_count":5,
        "scholarly_figure_full_acceptance":False,
        "full_41_slide_academic_production_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-folder",type=Path,required=True)
    parser.add_argument("--academic-inventory",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(argv)
    require(args.academic_inventory.is_file() and not args.academic_inventory.is_symlink()
            and args.out.parent.is_dir() and not args.out.exists()
            and not args.out.is_relative_to(args.source_folder.absolute()),
            "Exclusive versioned evidence output outside publisher originals required")
    before=_sha(args.academic_inventory)
    academic=json.loads(args.academic_inventory.read_text(encoding="utf8"))
    result=reconcile(source_folder=args.source_folder,prior_scholarly=academic)
    require(_sha(args.academic_inventory)==before,"Existing scholarly inventory altered")
    with args.out.open("x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status":result["status"],"caption_bitmap_matched":5,
                      "full_semantic_figure_acceptance":False,
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
