"""Four newly checked original Figure8.3 ±1 inverse sine/secant endpoint glyphs.

Prior six labels and full image geometry are accepted under exactly fixed
source+author PNG hashes. Reuse PR452 homography and PR465 6-glyph witness.
No previous artwork similarity rerun, no inference of curve truth, no TTS.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .evidence_reuse_contract import file_sha256,EvidenceReuseBlocked
from .original_fig83_six_printed_glyph_pixel_proof import (
    registered_patch, STATUS as PRIOR_STATUS,
    PRIOR_STATUS as GEOMETRY_STATUS,
)
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_THOMAS84_FIG83_FOUR_PRINTED_ENDPOINT_TICK_GLYPHS_PASS_NONPRODUCTION"
TICKS=(
    ("2_arcsine_negative_one","-1",(69,90,241,258),2),
    ("2_arcsine_positive_one","1",(124,136,241,258),2),
    ("3_arcsecant_negative_one","-1",(79,99,378,394),3),
    ("3_arcsecant_positive_one","1",(114,127,378,394),3),
)

def _require(x,reason):
    if not x:raise EvidenceReuseBlocked(reason)

def pick_tick(words,token,area):
    x0,x1,y0,y1=area
    _require(token in ("1","-1"),"Unreviewed graph tick identity")
    matches=[w for w in words if x0<=w[0]<=x1 and y0<=w[1]<=y1 and
             w[4].replace(chr(0x2212),"-")==token]
    _require(len(matches)==1,"Missing/duplicated source vector ±1 tick")
    return [float(q) for q in matches[0][:4]]

def audit(*,original:Path,previous_six:Path,registration:Path):
    import cv2,numpy as np,pymupdf
    original=Path(original).absolute()
    previous_six=Path(previous_six).absolute()
    registration=Path(registration).absolute()
    expected_source,expected_deck=ORIGINAL_PINS["8.4"]
    inputs=[original/"source.pdf",original/"slides.pdf",
            original/"Figure 8.3.png",previous_six,registration]
    _require(all(p.is_file() and not p.is_symlink() for p in inputs),
             "Frozen full image and prior six-label acceptance required")
    hashes={str(p):file_sha256(p) for p in inputs}
    _require(hashes[str(original/"source.pdf")]==expected_source
             and hashes[str(original/"slides.pdf")]==expected_deck,
             "Different original textbook or authored slide revision")
    earlier=json.loads(previous_six.read_text("utf8"))
    _require(earlier.get("status")==PRIOR_STATUS
             and earlier.get("publisher_source_pdf_sha256")==expected_source
             and earlier.get("original_author_slides_pdf_sha256")==expected_deck
             and earlier.get("original_author_figure_png_sha256")==
                   hashes[str(original/"Figure 8.3.png")]
             and earlier.get("three_inverse_function_labels_pixel_matched")==3
             and earlier.get("three_graph_axis_zero_tick_labels_pixel_matched")==3
             and earlier.get("registration_reused_without_redoing_similarity") is True
             and earlier.get("reused_previous_three_panel_registration_receipt_sha256")==
                   hashes[str(registration)]
             and earlier.get("student_publication_authorized") is False,
             "Previously accepted six actual printed glyphs missing or altered")
    prior=json.loads(registration.read_text("utf8"))
    _require(prior.get("status")==GEOMETRY_STATUS and
             prior.get("student_publication_authorized") is False and
             prior.get("publisher_source_sha256")==expected_source,
             "Geometry has no previously source-grounded fixed registration")
    geom=prior["two_exact_source_figure_panel_image_matches"]["8.3"]
    _require(geom["all_three_source_image_panel_artwork_correspondence_proven"] is True
             and geom["original_author_png_sha256"]==
                 hashes[str(original/"Figure 8.3.png")] and
             geom["original_author_slide"]==6 and geom["publisher_page"]==2
             and geom["corridor_2x"]==[0,0,600,1000],
             "Previous published three-panel image science not verifiable")
    H=np.asarray(geom["estimated_source_image_similarity_transform"],
                 dtype=np.float64)
    _require(H.shape==(3,3) and np.isfinite(H).all()
             and abs(np.linalg.det(H))>.00001,"Previous geometry corrupted")
    authored=cv2.imread(str(original/"Figure 8.3.png"),cv2.IMREAD_GRAYSCALE)
    _require(authored is not None and authored.shape==(480,232),
             "Wrong original author artwork")
    with pymupdf.open(original/"source.pdf") as book:
        page=book[1]
        words=page.get_text("words")
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        image=np.frombuffer(pix.samples,np.uint8).reshape(
            pix.height,pix.width,3)
        source=cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)[:1000,:600]
        warp=cv2.warpPerspective(source,H,
            (authored.shape[1],authored.shape[0]),
            flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderValue=255)
        labels={}
        for name,tick,region,panel in TICKS:
            token=pick_tick(words,tick,region)
            labels[name]={
                **registered_patch(author=authored,source_warp=warp,
                      homography=H,box=token,min_correlation=.83),
                "publisher_original_printed_token":tick,
                "inverse_graph_panel":panel,
                "original_glyph_is_independent_source_PDF_vector_text":True,
            }
    _require(len(labels)==4 and all(v[
        "this_exact_source_printed_glyph_has_original_author_bitmap_pixel_evidence"]
        for v in labels.values()),"Incomplete printed nonzero tick acceptance")
    _require(hashes=={str(p):file_sha256(p) for p in inputs},
             "Original author pixels or previous accepted evidence modified")
    return {
        "status":STATUS,
        "publisher_source_sha256":expected_source,
        "author_original_slides_sha256":expected_deck,
        "author_figure_png_sha256":hashes[str(original/"Figure 8.3.png")],
        "reused_existing_six_source_label_glyph_receipt_sha256":
            hashes[str(previous_six)],
        "reused_existing_registration_receipt_sha256":
            hashes[str(registration)],
        "original_eight_minus_plus_one_source_panel_labels_scoped_count":4,
        "original_previous_glyphs_accepted_without_reanalysis":6,
        "newly_source_anchored_nonzero_ticks":labels,
        "complete_all_pi_half_curve_axes_and_spoken_times_certified":False,
        "all_original_audio_pronunciations_accepted":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original",type=Path,required=True)
    ap.add_argument("--previous-six",type=Path,required=True)
    ap.add_argument("--previous-registration",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(argv)
    _require(a.out.parent.is_dir() and not a.out.exists()
             and not a.out.is_relative_to(a.original.absolute()),
             "Never overwrite source or an immutable prior accepted receipt")
    result=audit(original=a.original,previous_six=a.previous_six,
                 registration=a.previous_registration)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
                      "new_original_printed_tick_matches":len(
                          result["newly_source_anchored_nonzero_ticks"]),
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
