"""Publisher-original visual feature registration for Thomas Figures 8.2 AND 8.3.

Fixes the earlier raw whole-page correlation/graph-run false nonidentification
without weakening graph-label and speech acceptance. SIFT feature matching
is constrained to original physical source-caption page corridors, checks
actual inlier spatial coverage across all three visual panel bands, bounded
similarity transform, and source/slide image hashes. It never edits assets.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .figure_source_identity import require,_sha
from .original_thomas84_figure_asset_trace import SOURCE_SHA
from .original_five_figure_evidence_reconciliation import STATUS as CAPTION_STATUS

STATUS="ORIGINAL_FIGURE82_83_ALL_THREE_PANELS_TEXTBOOK_SOURCE_FEATURE_PROVEN_LABELS_PENDING"
# PDF x2 raster [x0,y0,x1,y1], based on genuine source/author physical layout.
PUBLISHER_IMAGE_CORRIDOR={
    "8.2":{"original_publisher_page":1,"author_slide":4,
           "source_raster_crop_2x":[500,960,1110,1240]},
    "8.3":{"original_publisher_page":2,"author_slide":6,
           "source_raster_crop_2x":[0,0,600,1000]},
}

def classify_feature_evidence(*,figure_id:str,data:dict)->dict:
    require(figure_id in PUBLISHER_IMAGE_CORRIDOR,
            "Only original bounded Figures8.2/8.3 are supported")
    expected=PUBLISHER_IMAGE_CORRIDOR[figure_id]
    require(data["publisher_page"]==expected["original_publisher_page"]
            and data["original_author_slide"]==expected["author_slide"]
            and data["corridor_2x"]==expected["source_raster_crop_2x"],
            "Figure source page, author slide or pinned crop changed")
    matched=data["ratio_test_matching_keypoints"]
    inliers=data["geometric_RANSAC_inliers"]
    bands=data["author_image_thirds_inlier_counts"]
    matrix=data["estimated_source_image_similarity_transform"]
    require(isinstance(bands,list) and len(bands)==3
            and all(type(x) is int and x>=7 for x in bands)
            and sum(bands)==inliers
            and isinstance(matched,int) and matched>=35
            and isinstance(inliers,int) and inliers>=35
            and inliers/matched>=.60,
            "Source graphics/panel glyph spatial correspondence insufficient")
    require(len(matrix)==3 and all(len(row)==3 for row in matrix)
            and all(isinstance(v,(int,float)) for row in matrix for v in row),
            "Invalid source-to-author homography estimate")
    xscale,yscale,skewxy,skewyx,px,py=(
        matrix[0][0],matrix[1][1],matrix[0][1],matrix[1][0],
        matrix[2][0],matrix[2][1])
    require(1.25<xscale<1.42 and 1.25<yscale<1.42
            and abs(xscale-yscale)<.06 and abs(skewxy)<.08
            and abs(skewyx)<.08 and abs(px)<.00015 and abs(py)<.00015,
            "Source figure feature correspondence is distorted or wrong scale")
    return {
        **data,
        "author_bitmap_to_publisher_original_three_panel_geometry_correspondence_verified":True,
        "per_panel_matched_source_feature_inliers":bands,
        "all_three_source_image_panel_artwork_correspondence_proven":True,
        "publisher_caption_math_labels_and_axis_semantics_full_proven":False,
        "genuine_WAV_each_panel_label_word_synced":False,
    }

def physical_match(*,root:Path,figure_id:str,book)->dict:
    try:
        import cv2,numpy as np,pymupdf
    except ImportError as exc:
        require(False,f"Native Windows feature matcher unavailable: {exc}")
    expected=PUBLISHER_IMAGE_CORRIDOR[figure_id]
    author=root/f"Figure {figure_id}.png"
    require(author.is_file() and not author.is_symlink(),
            "Frozen original named figure bitmap missing")
    arr=cv2.imread(str(author),cv2.IMREAD_GRAYSCALE)
    require(arr is not None and 100<=arr.shape[0]<=600
            and 100<=arr.shape[1]<=600,
            "Unrecognized original figure raster size")
    pix=book[expected["original_publisher_page"]-1].get_pixmap(
        matrix=pymupdf.Matrix(2,2),alpha=False)
    src=cv2.cvtColor(np.frombuffer(pix.samples,np.uint8).reshape(
        pix.height,pix.width,3),cv2.COLOR_RGB2GRAY)
    x0,y0,x1,y1=expected["source_raster_crop_2x"]
    require(0<=x0<x1<=src.shape[1] and 0<=y0<y1<=src.shape[0],
            "Original source corridor escapes true textbook page")
    area=src[y0:y1,x0:x1]
    sift=cv2.SIFT_create(nfeatures=2800)
    original_keys,original_values=sift.detectAndCompute(arr,None)
    page_keys,page_values=sift.detectAndCompute(area,None)
    require(original_values is not None and page_values is not None
            and len(original_keys)>=50 and len(page_keys)>=100,
            "Not enough genuine source/publisher figure features")
    pairs=cv2.BFMatcher(cv2.NORM_L2).knnMatch(
        original_values,page_values,k=2)
    good=[a for a,b in pairs if a.distance<.7*b.distance]
    require(len(good)>=35,"No unique original source-panel descriptors")
    srcpoints=np.float32([original_keys[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    dstpoints=np.float32([page_keys[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    H,mask=cv2.findHomography(srcpoints,dstpoints,cv2.RANSAC,4.0)
    require(H is not None and mask is not None,
            "Genuine original textbook figure homography unavailable")
    matched=[p for p,yes in zip(good,mask.ravel()) if int(yes)]
    counts=[0,0,0]
    for p in matched:
        band=min(2,int(original_keys[p.queryIdx].pt[1]*3/arr.shape[0]))
        counts[band]+=1
    result={
        "publisher_page":expected["original_publisher_page"],
        "original_author_slide":expected["author_slide"],
        "corridor_2x":expected["source_raster_crop_2x"],
        "ratio_test_matching_keypoints":len(good),
        "geometric_RANSAC_inliers":len(matched),
        "author_image_thirds_inlier_counts":counts,
        "estimated_source_image_similarity_transform":[
            [float(v) for v in row] for row in H.tolist()],
        "original_author_png_sha256":_sha(author),
    }
    return classify_feature_evidence(figure_id=figure_id,data=result)

def audit_original(*,root:Path,caption_report:dict)->dict:
    import pymupdf
    root=Path(root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and _sha(root/"source.pdf")==SOURCE_SHA
            and caption_report.get("status")==CAPTION_STATUS
            and caption_report.get("student_publication_authorized") is False,
            "Wrong original publisher source or missing authoritative caption proof")
    rows={p["figure"]:p for p in caption_report[
        "five_exact_original_caption_author_embedded_figure_identity_proofs"]}
    before={str(p):_sha(p) for p in
            [root/"source.pdf",root/"slides.pdf",root/"slides.tex",
             root/"Figure 8.2.png",root/"Figure 8.3.png"]}
    matched={}
    with pymupdf.open(root/"source.pdf") as pdf:
        require(len(pdf)==6,"Wrong pinned publisher section page count")
        for fig in ("8.2","8.3"):
            expected=PUBLISHER_IMAGE_CORRIDOR[fig]
            source=rows[fig]
            require(source["original_slide_id"]==
                    f"8.4_slide{expected['author_slide']}"
                    and source["original_author_image_sha256"]==
                        _sha(root/f"Figure {fig}.png")
                    and source["publisher_caption_number_source_verified"]
                    and source["original_author_png_identical_to_rendered_slide_bitmap"],
                    "Publisher source identity and old author bitmap equality disagree")
            matched[fig]=physical_match(root=root,figure_id=fig,book=pdf)
    require(before=={p:_sha(Path(p)) for p in before},
            "Original publisher/source Beamer figure asset modified")
    return {
        "status":STATUS,
        "publisher_source_sha256":SOURCE_SHA,
        "two_exact_source_figure_panel_image_matches":matched,
        "original_figures_publisher_panel_visual_match_count":2,
        "all_three_panel_image_spatial_correspondence_for_each":True,
        "prior_legacy_three_graph_color_run_reflow_algorithm_accepted":False,
        "whole_panels_axis_labels_symbol_meaning_certified":False,
        "all_original_WAV_word_times_to_each_graph_symbol_certified":False,
        "full_production_release":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--caption-receipt",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    require(a.caption_receipt.is_file() and not a.caption_receipt.is_symlink()
            and a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.root.absolute()),
            "Require physically original input and exclusive fresh source QA output")
    sha=_sha(a.caption_receipt)
    item=audit_original(root=a.root,caption_report=json.loads(
        a.caption_receipt.read_text("utf8")))
    require(sha==_sha(a.caption_receipt),"Original specialized source evidence mutated")
    with a.out.open("x",encoding="utf8") as stream:
        json.dump(item,stream,indent=2,ensure_ascii=False);stream.write("\n")
    print(json.dumps({
        "status":STATUS,
        "original_figures_with_three_panel_source_visual_match":2,
        "feature_inliers":{
            fig:x["geometric_RANSAC_inliers"]
            for fig,x in item["two_exact_source_figure_panel_image_matches"].items()},
        "full_figure_math_semantic_acceptance":False,
        "student_publication_authorized":False,
    }))
if __name__=="__main__":
    main()
