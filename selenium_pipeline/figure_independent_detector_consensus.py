"""Orthogonal AKAZE validation of ORB/RANSAC candidate transformations.

No detector consensus is scientific proof of author-complete figure panels.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

import pymupdf

from .figure_local_feature_correspondence import audit_local_feature_correspondence
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_source_identity import require, _sha


def detector_consensus(orb: dict, second: dict) -> dict:
    require(type(orb) is dict and type(second) is dict
            and len(orb.get("arbitrary_four_width_bins", [])) == 4
            and len(second.get("akaze_bins", [])) == 4,
            "Must have independent four-bin feature observations")
    out = []
    for i,(a,b) in enumerate(zip(orb["arbitrary_four_width_bins"],
                                second["akaze_bins"])):
        require(a.get("scan_bin") == b.get("scan_bin") == i,
                "Mismatched scan bin numbering")
        ma, mb = a.get("affine_source_render_to_slide_px"),b.get("affine_source_render_to_slide_px")
        ok=False
        if a.get("geometrically_coherent_candidate") and b.get("inlier_count",0)>=5 and mb is not None:
            require(type(ma) is list and type(mb) is list
                    and len(ma)==len(mb)==2
                    and all(len(row)==3 for row in ma+mb)
                    and all(type(v) in (float,int) and math.isfinite(v)
                            for row in ma+mb for v in row),
                    "Nonfinite or malformed fit cannot be considered consensus")
            linear=max(abs(ma[x][y]-mb[x][y]) for x in range(2) for y in range(2))
            translation=math.hypot(ma[0][2]-mb[0][2],ma[1][2]-mb[1][2])
            ok=linear<=.035 and translation<=12
        out.append({
            "scan_bin":i,
            "orb_ransac_inliers":a.get("ransac_inlier_count",0),
            "akaze_ransac_inliers":b.get("inlier_count",0),
            "secondary_detector_transform_consistent":ok,
            "author_intended_panel_certified":False,
        })
    return {
        "schema_version":1,
        "status":"ORTHOGONAL_DETECTOR_GEOMETRY_REVIEW_REQUIRED",
        "independent_matching_detector":"AKAZE",
        "consistent_scan_bin_count":sum(x["secondary_detector_transform_consistent"] for x in out),
        "scan_bin_crosschecks":out,
        "complete_original_figure_verified":False,
        "original_panel_count_and_labels_verified":False,
        "source_to_slide_full_coverage_verified":False,
        "narrated_highlights_verified":False,
        "publication_authorized":False,
    }


def audit_secondary_detector(*,source:Path,slides:Path,source_page:int,
                             slide_page:int,figure_id:str) -> dict:
    first=audit_local_feature_correspondence(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    inventory=inventory_pre_caption_vectors(
        source=source,page_number=source_page,figure_id=figure_id)
    require(first["source_sha256"]==inventory["source_sha256"]
            and first["video_or_publication_authorized"] is False,
            "Inconsistent source audit or unauthorized figure claim")
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"schema_version":1,
                "status":"SECONDARY_DETECTOR_UNAVAILABLE_REVIEW_REQUIRED",
                "complete_original_figure_verified":False,
                "publication_authorized":False}
    srcpath,deckpath=Path(source).absolute(),Path(slides).absolute()
    rect=pymupdf.Rect(inventory["candidate_scan_corridor"])
    with pymupdf.open(srcpath) as book,pymupdf.open(deckpath) as deck:
        pix=book[source_page-1].get_pixmap(
            matrix=pymupdf.Matrix(3,3),clip=rect,
            colorspace=pymupdf.csGRAY,alpha=False)
        source_im=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)
        slide=deck[slide_page-1]
        images=[i for i in slide.get_image_info(xrefs=True)
                if int(i["width"])>=48 and int(i["height"])>=48
                and pymupdf.Rect(i["bbox"]).width>=50
                and pymupdf.Rect(i["bbox"]).height>=25]
        require(len(images)==1 and type(images[0].get("xref")) is int
                and images[0]["xref"]>0,"Require one actual material bitmap")
        raw=deck.extract_image(images[0]["xref"])["image"]
        target=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_GRAYSCALE)
        require(target is not None and target.size<=4_000_000
                and source_im.size<=1_500_000,
                "Unbounded source-slide comparison")
    detector=cv2.AKAZE_create()
    a,da=detector.detectAndCompute(source_im,None)
    b,db=detector.detectAndCompute(target,None)
    matches=[]
    if da is not None and db is not None:
        knn=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(db,da,k=2)
        matches=[m for pair in knn if len(pair)==2
                 for m,n in [pair] if m.distance<.8*n.distance]
    bins=[]
    for i in range(4):
        group=[m for m in matches if i*target.shape[1]/4
               <=b[m.queryIdx].pt[0]<(i+1)*target.shape[1]/4]
        found={"scan_bin":i,"ratio_matches":len(group),
               "inlier_count":0,"affine_source_render_to_slide_px":None}
        if len(group)>=6:
            sp=np.float32([a[m.trainIdx].pt for m in group])
            tp=np.float32([b[m.queryIdx].pt for m in group])
            matrix,mask=cv2.estimateAffinePartial2D(
                sp,tp,method=cv2.RANSAC,ransacReprojThreshold=3,
                maxIters=500,confidence=.99)
            if matrix is not None and mask is not None:
                found["inlier_count"]=int(mask.sum())
                found["affine_source_render_to_slide_px"]=[
                    [round(float(v),5) for v in row] for row in matrix]
        bins.append(found)
    result=detector_consensus(first,{"akaze_bins":bins})
    require(_sha(srcpath)==first["source_sha256"]
            and _sha(deckpath)==first["slides_sha256"],
            "Original source/slide changed during independent detector audit")
    return {**result,"source_sha256":first["source_sha256"],
            "slides_sha256":first["slides_sha256"],
            "source_page":source_page,"slide_page":slide_page,"figure_id":figure_id,
            "independent_akaze_match_count":len(matches),
            "akaze_scan_bin_data":bins}


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    x=p.parse_args(argv)
    print(json.dumps(audit_secondary_detector(
        source=x.source,slides=x.slides,
        source_page=x.source_page,slide_page=x.slide_page,
        figure_id=x.figure_id),indent=2,sort_keys=True))
    return 2


if __name__=="__main__":
    raise SystemExit(main())
