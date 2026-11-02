"""Reconcile six original source figures across independent specialized QA receipts.

Only source artwork provenance is resolved. Mathematical glyph-by-glyph,
axis/legend, figure-panel semantics and all genuine spoken-WAV timing
remain distinct mandatory blockers.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .figure_source_identity import require,_sha
from .original_five_figure_evidence_reconciliation import STATUS as FIVE
from .original_three_figure_source_body_visual_provenance import STATUS as THREE
from .original_figure82_83_actual_publisher_feature_registration import STATUS as TWO
from .original_all41_38_source_academic_gap_reconciler import STATUS as GAP
from .original_thomas86_tank_ex62_source_provenance import EXPECTED_TANK_PNG_SHA

STATUS="ALL_SIX_ORIGINAL_AUTHOR_IMAGES_PUBLISHER_VISUAL_PROVEN_FULL_SCIENCE_STILL_PENDING"

def aggregate(*,five:dict,three:dict,two:dict,tank:dict,academic:dict)->dict:
    require(five.get("status")==FIVE and three.get("status")==THREE
            and two.get("status")==TWO and academic.get("status")==GAP
            and tank.get("status")==
                "ORIGINAL_THOMAS86_EXERCISE62_SOURCE_FIGURE_MATH_VERIFIED_NONPRODUCTION"
            and all(v.get("student_publication_authorized") is False
                    for v in (five,three,two,tank,academic)),
            "Missing independently sourced original no-release figure audit")
    require(academic.get("original_source_slides")==41
            and academic.get("original_source_pixel_and_audio_math_focus_slides")==38
            and academic.get("source_images_inventory_total")==6
            and five.get("figure_assets_with_confirmed_source_caption_and_author_render_identity")==5
            and three.get("three_unique_correct_textbook_page_visual_matches")==3
            and two.get("original_figures_publisher_panel_visual_match_count")==2,
            "Original count/source version or independently verified figure scopes disagree")
    original=five["original_source_pdf_sha256"]
    require(three["original_source_sha256"]==original
            and two["publisher_source_sha256"]==original,
            "Original publisher/source physical fingerprint differs across specialized figure proofs")
    asset={x["figure"]:x for x in
           five["five_exact_original_caption_author_embedded_figure_identity_proofs"]}
    expected={f"8.{n}" for n in range(2,7)}
    require(set(asset)==expected,"Figure labels 8.2–8.6 incomplete")
    source_matches={}
    for figure in expected:
        row=asset[figure]
        if figure in ("8.2","8.3"):
            specific=two["two_exact_source_figure_panel_image_matches"][figure]
            require(specific["original_author_png_sha256"]==
                    row["original_author_image_sha256"]
                    and specific["all_three_source_image_panel_artwork_correspondence_proven"]
                    and specific["geometric_RANSAC_inliers"]>=35
                    and min(specific["per_panel_matched_source_feature_inliers"])>=7,
                    "Weak/missing actual original figure82/83 panel source evidence")
            method="PINNED_SOURCE_SIFT_RANSAC_THREE_PANEL_GEOMETRY"
            score=specific["geometric_RANSAC_inliers"]
        else:
            specific=three["source_body_three_independent_figure_visual_witnesses"][figure]
            require(specific["author_original_png_sha256"]==
                    row["original_author_image_sha256"]
                    and specific["original_author_png_to_textbook_source_body_visual_pattern_match"]
                    and specific["source_visual_normalized_correlation"]>=.78
                    and specific["source_visual_page_margin"]>=.20,
                    "Publisher original figure8.4-8.6 correct-page source image evidence invalid")
            method="PINNED_SOURCE_CORRECT_PAGE_RASTER_TEMPLATE"
            score=specific["source_visual_normalized_correlation"]
        require(row["publisher_caption_number_source_verified"]
                and row["original_author_png_identical_to_rendered_slide_bitmap"],
                "Original source caption/author bitmap proof missing")
        source_matches[figure]={
            "original_source_figure":figure,
            "author_slide":row["original_slide_id"],
            "author_png_sha256":row["original_author_image_sha256"],
            "source_artwork_correspondence_proven":True,
            "source_match_evidence_kind":method,
            "source_match_evidence_score":score,
            "every_visible_label_axis_symbol_and_spoken_word_verified":False,
        }
    require(tank["author_exercise_62_png_sha256"]==EXPECTED_TANK_PNG_SHA
            and tank["author_source_image_same_publisher_visual_verified"] is True
            and tank["symbolic_volume_derivative_equals_2L_sqrt_2rd_minus_d_squared"] is True
            and tank["all_original_figure_panel_labels_word_timed"] is False,
            "Tank original publisher PNG/formula evidence missing or falsely released")
    source_matches["Exercise 62"]={
        "original_source_figure":"Exercise 62",
        "author_slide":"8.6_slide11",
        "author_png_sha256":EXPECTED_TANK_PNG_SHA,
        "source_artwork_correspondence_proven":True,
        "source_match_evidence_kind":"PUBLISHER_EMBEDDED_JPEG_AUTHOR_IMAGE_PLUS_VOLUME_MATH",
        "source_match_evidence_score":tank["normalized_matching_correlation"],
        "every_visible_label_axis_symbol_and_spoken_word_verified":False,
    }
    require(len(source_matches)==6,
            "All six actual original author figures must be individually identified")
    return {
        "status":STATUS,
        "original_frozen_41_source_slides":41,
        "original_source_spoken_sample_focus_slides":38,
        "all_six_original_author_figure_source_artwork_matched":True,
        "six_independently_version_bound_figure_identity_receipts":source_matches,
        "source_figure_identity_missing_count":0,
        "source_figure_full_symbol_axes_label_and_spoken_semantic_approval_count":0,
        "original_academic_intermediate_math_full_completion_approved":False,
        "full_lecture_scientific_publication_gate_passed":False,
        "student_publication_authorized":False,
        "next_priority":"Reconcile each original source curve/axis/label with author pixels "
            "and original WAV word anchors; complete all residual mathematical "
            "expression and pronunciation gates independently.",
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("five","three","two","tank","academic","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args(argv)
    names=("five","three","two","tank","academic")
    inputs={n:getattr(a,n) for n in names}
    require(all(path.is_file() and not path.is_symlink()
                for path in inputs.values())
            and a.out.parent.is_dir() and not a.out.exists(),
            "No old evidence overwrite, missing or symlinked review receipts")
    before={k:_sha(path) for k,path in inputs.items()}
    result=aggregate(**{k:json.loads(path.read_text("utf8"))
                        for k,path in inputs.items()})
    require(before=={k:_sha(path) for k,path in inputs.items()},
            "Immutable publisher/source scientific evidence changed")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"publisher_source_figure_artworks":6,
                      "full_scientific_semantics_approved":False,
                      "student_publication_authorized":False}))

if __name__=="__main__":
    main()
