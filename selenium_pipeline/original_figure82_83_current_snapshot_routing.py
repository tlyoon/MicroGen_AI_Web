"""Version-specific Figure 8.2/8.3 QA dispatch and blocker diagnosis.

The immutable 41-slide original §8.4 uses Figure 8.2 on *slide 4*
and Figure 8.3 on *slide 6*. Earlier specialists default to slide 5
or assume a reflow arrangement not present in this authored snapshot.
An internally inconsistent specialist must never promote figure release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .original_thomas84_figure_asset_trace import SOURCE_SHA, audit as five_assets
from .original_five_figure_evidence_reconciliation import STATUS as CAPTION_STATUS
from .original_figure82_symbolic_branch_qa import exact_squared_identities
from .figure_three_graph_color_reflow import audit_real_three_graph_reflow

STATUS="ORIGINAL_84_FIG82_83_REAL_SOURCE_ROUTING_AND_TOPOLOGY_GAP_IDENTIFIED_NONPRODUCTION"

def triage_layout(*,figure_id:str,author_slide:int,graph_evidence:dict)->dict:
    require(figure_id=="8.3" and author_slide==6,
            "Figure8.3 is original authored slide6; reject old slide5 default")
    require(graph_evidence["source_page"]==2
            and graph_evidence["slide_page"]==6
            and graph_evidence["detected_graph_count"]==3
            and graph_evidence["original_vertical_graph_run_count"]==3,
            "Figure8.3 actual source three-panel geometry changed")
    source_bands=graph_evidence["graph_correspondence_evidence"]
    require(isinstance(source_bands,list)
            and len(source_bands)==graph_evidence["slide_horizontal_graph_run_count"],
            "Actual candidate source/slide panel alignments inconsistent")
    real_count=graph_evidence["slide_horizontal_graph_run_count"]
    complete=(real_count==3
              and graph_evidence["three_graph_curve_shape_sequence_coherent"] is True
              and graph_evidence["three_graph_black_ink_geometry_plausible"] is True)
    return {
        "actual_original_source_page":2,"actual_authored_slide":6,
        "publisher_source_three_graph_regions_verified":True,
        "slide_colored_graph_run_count_observed":real_count,
        "old_three_separate_horizontal_bands_assumption_valid":real_count==3,
        "source_and_slide_complete_panel_geometry_approved":complete,
        "reflow_reconstruction_or_individual_panel_ink_review_required":not complete,
        "release_blocker_if_unmatched":"REVIEW_SOURCE_TO_SLIDE_GRAPH_PANEL_SEGMENTATION",
    }

def audit(*,folder:Path,caption_receipt:dict)->dict:
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink()
            and _sha(root/"source.pdf")==SOURCE_SHA
            and caption_receipt.get("status")==CAPTION_STATUS
            and caption_receipt.get("student_publication_authorized") is False,
            "Wrong frozen publisher section or insufficient figure evidence")
    all_five=five_assets(source=root/"source.pdf",slides=root/"slides.pdf",
                        latex=root/"slides.tex",figure_directory=root)
    require(all_five["figure_asset_to_embedded_bitmap_identity_count"]==5
            and all_five["full_figures_source_pdf_equivalence_accepted"] is False,
            "Actual five original author PNGs must remain source-checked")
    before={p:_sha(root/p) for p in ("source.pdf","slides.pdf","script.txt",
                                    "Figure 8.2.png","Figure 8.3.png")}
    expected={r["figure"]:r for r in
              caption_receipt["five_exact_original_caption_author_embedded_figure_identity_proofs"]}
    for num,slide in (("8.2",4),("8.3",6)):
        require(expected[num]["original_slide_id"]==f"8.4_slide{slide}"
                and expected[num]["original_author_image_sha256"]==
                    _sha(root/f"Figure {num}.png"),
                "Original audited figure image/author slide identity changed")
    # Algebraic squares are exact science checks, not source text/glyph/branch
    # approval. Do not assume earlier narration phrase anchor is still present.
    squared=exact_squared_identities()
    require(squared["exact_symbolic_squared_identities_verified"]
            and squared["squared_identity_count"]==3
            and squared["principal_root_sign_conditions_academically_approved"] is False,
            "Original trig substitution principal-root signs not approved")
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck)==17
                and len(deck[3].get_image_info(xrefs=True))>=1
                and len(deck[5].get_image_info(xrefs=True))>=1,
                "Original authored Figure8.2/8.3 visual slides absent")
    raw=audit_real_three_graph_reflow(
        source=root/"source.pdf",slides=root/"slides.pdf",
        source_page=2,slide_page=6,figure_id="8.3")
    graph=triage_layout(figure_id="8.3",author_slide=6,graph_evidence=raw)
    require(before=={p:_sha(root/p) for p in before},
            "Original author/publisher PCM script and figure mutated")
    return {
        "status":STATUS,
        "publisher_original_source_sha256":SOURCE_SHA,
        "original_figure82_actual_author_slide":4,
        "original_figure83_actual_author_slide":6,
        "specialized_prior_figure83_slide5_default_is_wrong_for_this_snapshot":True,
        "figure82_three_exact_squared_trig_algebra_identities":3,
        "figure82_principal_root_sign_branch_domain_full_source_approval":False,
        "figure82_source_triangle_panel_label_all_pixels_approved":False,
        "figure83_source_layout_diagnostic":graph,
        "figure83_source_graphs_assumed_separately_preserved":False,
        "figure83_scientific_panel_axis_and_label_completeness_approved":False,
        "new_editorial_render_or_original_wav_tts_generated":False,
        "full_original_academic_release_approved":False,
        "student_publication_authorized":False,
        "next_auto_repair":(
            "Build an original-§8.4 source page2 → author slide6 panel-sensitive "
            "registration; distinguish real source three vertical graph regions "
            "from candidate authored horizontal-run segmentation. Validate "
            "each original inverse-function glyph, axes, curves, signs and "
            "real source-spoken PCM alignment independently before promotion."),
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--caption-receipt",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    require(a.caption_receipt.is_file() and not a.caption_receipt.is_symlink()
            and a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.folder.absolute()),
            "Require immutable publisher/author source and fresh external review receipt")
    previous=_sha(a.caption_receipt)
    result=audit(folder=a.folder,caption_receipt=json.loads(
        a.caption_receipt.read_text("utf8")))
    require(_sha(a.caption_receipt)==previous,"Old figure science receipt modified")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
                      "correct_author_figure83_slide":6,
                      "source_panel_count":3,
                      "math_symbols_exact_squares":3,
                      "figure_release":False}))
if __name__=="__main__":
    main()
