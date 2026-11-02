"""Original Figure8.3 five previously unchecked source-printed angle glyphs.

Previous full artwork and 10 function/number glyph proofs are SHA-reused;
this verifies only actual source font-rendered printed boundary marks in the
original author bitmap, not the truth of every curve or narrated phoneme.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .evidence_reuse_contract import file_sha256,EvidenceReuseBlocked
from .original_fig83_six_printed_glyph_pixel_proof import (
    registered_patch,PRIOR_STATUS as SOURCE_GEOMETRY_STATUS,
)
from .original_fig83_four_nonzero_tick_pixel_proof import STATUS as TEN_STATUS
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_FIG83_FIVE_REAL_ANGULAR_BOUNDARY_GLYPH_GROUPS_AUTHOR_PIXEL_PASS_NONPRODUCTION"
# Real Thomas §8.4 publisher p/2 font maps source vector math π/2.
# These are original-page *glyphs*, not new claims about curve truth.
GROUPS=(
  ("arctangent_positive_pi_half",1,(96,106,89,109),("p","2")),
  ("arctangent_negative_pi_half",1,(89,105,149,170),("-","p","2")),
  ("arcsine_positive_pi_half",2,(96,106,198,219),("p","2")),
  ("arcsine_negative_pi_half",2,(89,105,274,295),("-","p","2")),
  ("arcsecant_positive_pi",3,(96,106,331,344),("p",)),
)

def require(ok,why):
    if not ok:raise EvidenceReuseBlocked(why)

def group_vector_bbox(words,region,expected):
    x0,x1,y0,y1=region
    candidates=[w for w in words if
                x0<=w[0]<=x1 and y0<=w[1]<=y1 and
                w[4].replace(chr(0x2212),"-") in expected]
    observed=sorted(w[4].replace(chr(0x2212),"-") for w in candidates)
    require(observed==sorted(expected),
            "Original publisher angle boundary missing/duplicated π or denominator glyph")
    return [float(min(w[0] for w in candidates)),
            float(min(w[1] for w in candidates)),
            float(max(w[2] for w in candidates)),
            float(max(w[3] for w in candidates))]

def audit(*,original:Path,prior_ten:Path,registration:Path):
    import cv2,numpy as np,pymupdf
    original=Path(original).absolute()
    prior_ten=Path(prior_ten).absolute()
    registration=Path(registration).absolute()
    paths=[original/"source.pdf",original/"slides.pdf",
           original/"Figure 8.3.png",prior_ten,registration]
    require(all(p.is_file() and not p.is_symlink() for p in paths),
            "Only immutable existing author source/previous accepted glyph receipts")
    checks={str(p):file_sha256(p) for p in paths}
    book_hash,slide_hash=ORIGINAL_PINS["8.4"]
    require(checks[str(original/"source.pdf")]==book_hash
            and checks[str(original/"slides.pdf")]==slide_hash,
            "Wrong publisher source or original author slide version")
    previous=json.loads(prior_ten.read_text("utf8"))
    require(previous.get("status")==TEN_STATUS
            and previous.get("publisher_source_sha256")==book_hash
            and previous.get("author_original_slides_sha256")==slide_hash
            and previous.get("original_previous_glyphs_accepted_without_reanalysis")==6
            and len(previous.get("newly_source_anchored_nonzero_ticks",{}))==4
            and previous.get("student_publication_authorized") is False,
            "Previous ten original printed pixel patches not accepted")
    geometry=json.loads(registration.read_text("utf8"))
    require(geometry.get("status")==SOURCE_GEOMETRY_STATUS
            and geometry.get("publisher_source_sha256")==book_hash
            and geometry.get("student_publication_authorized") is False,
            "Previously accepted three-panel source geometry unavailable")
    record=geometry["two_exact_source_figure_panel_image_matches"]["8.3"]
    require(record.get("all_three_source_image_panel_artwork_correspondence_proven") is True
            and record.get("publisher_page")==2
            and record.get("original_author_slide")==6
            and record.get("original_author_png_sha256")==checks[
                str(original/"Figure 8.3.png")],
            "Old Figure8.3 source identity must be reused, not recreated")
    require(previous.get("reused_existing_registration_receipt_sha256")==
            checks[str(registration)],"Prior pixel proof homography changed")
    homography=np.asarray(record["estimated_source_image_similarity_transform"],float)
    require(homography.shape==(3,3) and np.isfinite(homography).all()
            and abs(np.linalg.det(homography))>1e-5,
            "Previously verified original image coordinates corrupt")
    author=cv2.imread(str(original/"Figure 8.3.png"),cv2.IMREAD_GRAYSCALE)
    require(author is not None and author.shape==(480,232),
            "Not the original source-locked author figure")
    with pymupdf.open(original/"source.pdf") as original_pdf:
        page=original_pdf[1]
        text=page.get_text()
        require("FIGURE 8.3" in text and "tan-1" in text
                and "sin-1" in text and "sec-1" in text,
                "Not the actual original printed inverse graph mathematics")
        words=page.get_text("words")
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        raw=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        source=cv2.cvtColor(raw,cv2.COLOR_RGB2GRAY)[:1000,:600]
        transformed=cv2.warpPerspective(source,homography,
                     (author.shape[1],author.shape[0]),
                     flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderValue=255)
        results={}
        for label,panel,area,glyphs in GROUPS:
            bbox=group_vector_bbox(words,area,glyphs)
            results[label]={
                **registered_patch(author=author,source_warp=transformed,
                  homography=homography,box=bbox,min_correlation=.88),
                "source_publisher_panel_index":panel,
                "source_font_vector_tokens_as_extracted":list(glyphs),
                "actual_source_math_angle_boundary_visual_patch_verified":True,
            }
    require(len(results)==5 and all(v[
                "actual_source_math_angle_boundary_visual_patch_verified"]
                for v in results.values()),"Source angular label patch coverage not five")
    require(checks=={str(p):file_sha256(p) for p in paths},
            "Prior source or image glyph receipts changed")
    return {
        "status":STATUS,
        "original_source_sha256":book_hash,
        "original_author_slides_sha256":slide_hash,
        "original_author_figure_png_sha256":checks[str(original/"Figure 8.3.png")],
        "reused_previous_ten_glyphs_source_receipt_sha256":checks[str(prior_ten)],
        "reused_existing_source_image_registration_sha256":checks[str(registration)],
        "previous_frozen_source_glyphs_reused_unchanged":10,
        "five_new_angular_source_font_glyph_group_pixels":results,
        "complete_graph_curve_mathematical_geometry_certified":False,
        "each_spoken_angular_word_audibly_certified":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--previous-ten",type=Path,required=True)
    p.add_argument("--previous-registration",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.original.absolute()),
            "Never overwrite previous author source or earlier academic proof")
    result=audit(original=a.original,prior_ten=a.previous_ten,
                 registration=a.previous_registration)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"new_angular_glyph_groups":
                      len(result["five_new_angular_source_font_glyph_group_pixels"]),
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
