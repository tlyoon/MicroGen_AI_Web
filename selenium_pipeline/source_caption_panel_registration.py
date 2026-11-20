"""Automatic, source-witnessed captioned multi-panel figure registration.

This recycles original source-caption/panel-letter geometric provenance
checks and ORB/AKAZE cross-detector registration. Only original PDF panel
marks inside genuine decorative anchor boxes and an exact printed "(a)/(b)"
figure caption can supply panel labels/meanings. Both independent detectors
must agree on source->slide transformation, with per-panel RGB pixel coverage
of the actual slide bitmap. No arbitrary equal-width strips, OCR, Gemini
guesses, source rewriting or academic/TTS/release authorization.

This method works for supported caption layouts; missing markers, an
unregistered bitmap, nonmatching images or detector uncertainty fail closed.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import re

import pymupdf

from .figure_source_identity import require, _sha
from .verified_slide_visual_candidates import registered_raster_targets


def caption_parts(page, figure_id: str) -> tuple[str, pymupdf.Rect, list[tuple[str,str]]]:
    require(type(figure_id) is str and
            re.fullmatch(r"\d{1,2}\.\d{1,3}",figure_id),
            "Expected physical numbered textbook figure")
    pattern=re.compile(rf"(?i)^\s*figure\s+{re.escape(figure_id)}\b")
    caps=[b for b in page.get_text("blocks")
          if len(b)>4 and isinstance(b[4],str)
          and pattern.match(" ".join(b[4].split()))]
    require(len(caps)==1,"Unique original printed Figure caption required")
    cap=caps[0]
    text=" ".join(cap[4].split())
    matches=list(re.finditer(r"\(([a-f])\)\s+",text,re.I))
    ids=[m[1].lower() for m in matches]
    require(2<=len(ids)<=5 and
            ids==list("abcde"[:len(ids)]),
            "Original caption must name all consecutively labelled panels")
    parts=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        part=text[m.end():end].strip()
        require(len(part)>=12,
                "Original printed caption lacks substantive panel meaning")
        parts.append((ids[i],part))
    return text,pymupdf.Rect(cap[:4]),parts


def physical_label_rules(page, caption: pymupdf.Rect,
                         parts: list[tuple[str,str]]) -> list[dict]:
    """Each printed letter must have an actual filled marker and underline."""
    drawings=page.get_drawings()
    fills=[(pymupdf.Rect(x["rect"]),x)
           for x in drawings if x.get("fill") is not None
           and 5 <= pymupdf.Rect(x["rect"]).width <= 20
           and 5 <= pymupdf.Rect(x["rect"]).height <= 20]
    rules=[pymupdf.Rect(x["rect"]) for x in drawings
           if x.get("type") in ("s","fs")
           and 18 <= pymupdf.Rect(x["rect"]).width <= 240
           and pymupdf.Rect(x["rect"]).height <= 1.5]
    labels=[]
    for letter,_meaning in parts:
        matches=[]
        for word in page.get_text("words"):
            if str(word[4]).strip().casefold()!=letter:
                continue
            rect=pymupdf.Rect(word[:4])
            center=pymupdf.Point((rect.x0+rect.x1)/2,
                                 (rect.y0+rect.y1)/2)
            if not (20<=center.x<caption.x0-15
                    and caption.y0-130<=center.y<=caption.y1+25):
                continue
            anchors=[fill for fill,detail in fills
                     if fill.contains(center)
                     and fill.x0>=rect.x0-4 and fill.x1<=rect.x1+4]
            if len(anchors)!=1:
                continue
            attached=[r for r in rules
                       if r.x0<=center.x<=r.x1
                       and abs(r.y0-anchors[0].y0-4)<=5]
            if len(attached)!=1:
                continue
            matches.append((rect,anchors[0],attached[0]))
        require(len(matches)==1,
                f"Printed original panel {letter} lacks unique vector box and underline")
        rect,fill,underline=matches[0]
        labels.append({
            "panel":letter,
            "word_rect":[round(float(v),3) for v in rect],
            "marker_rect":[round(float(v),3) for v in fill],
            "underline_rect":[round(float(v),3) for v in underline],
        })
    centers=[(x["marker_rect"][0]+x["marker_rect"][2])/2 for x in labels]
    baselines=[x["underline_rect"][1] for x in labels]
    require(centers==sorted(set(centers))
            and max(baselines)-min(baselines)<=4
            and all(a["underline_rect"][2]+4<b["underline_rect"][0]
                    for a,b in zip(labels,labels[1:])),
            "Panel printed rules overlap or are not aligned and ordered")
    return labels


def _fit_feature(source_gray, target_gray, name: str) -> dict:
    try:
        import cv2
        import numpy as np
    except ImportError:
        require(False,"ORB and AKAZE scientific image matching dependencies missing")
    if name=="ORB":
        detector=cv2.ORB_create(nfeatures=2300)
        minimum=65
    else:
        detector=cv2.AKAZE_create()
        minimum=32
    origin,descriptors=detector.detectAndCompute(source_gray,None)
    dest,destination=detector.detectAndCompute(target_gray,None)
    require(descriptors is not None and destination is not None,
            f"{name}: original/slide image features missing")
    pairs=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        descriptors,destination,k=2)
    matched=[m for pair in pairs if len(pair)==2
             for m,n in [pair] if m.distance<.75*n.distance]
    require(len(matched)>=minimum,
            f"{name}: too few genuinely matching original image descriptors")
    src=np.float32([origin[m.queryIdx].pt for m in matched])
    dst=np.float32([dest[m.trainIdx].pt for m in matched])
    matrix,mask=cv2.estimateAffinePartial2D(
        src,dst,method=cv2.RANSAC,ransacReprojThreshold=3.5,
        maxIters=3000,confidence=.99)
    require(matrix is not None and mask is not None
            and int(mask.sum())>=minimum,
            f"{name}: original source-to-slide transform is not robust")
    a,b=matrix[0,0],matrix[1,0]
    scale=math.hypot(a,b)
    require(.15<scale<3.0 and abs(b)/scale < .02
            and abs(matrix[0,1]+b)<.025,
            f"{name}: source-to-slide source raster is distorted or rotated")
    return {"name":name,"matrix":matrix,"src":src,"dst":dst,
            "inlier_mask":mask.ravel().astype(bool),
            "inliers":int(mask.sum()),"matches":len(matched)}


def inspect_panel_correspondence(*,source: Path, slides: Path,
                                 source_page: int,slide_page: int,
                                 figure_id: str)->dict:
    """Genuine PDF caption meanings + independently registered image panels."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        require(False,"Existing OpenCV image provenance dependency unavailable")
    source,slides=Path(source).absolute(),Path(slides).absolute()
    require(source.is_file() and slides.is_file()
            and not source.is_symlink() and not slides.is_symlink(),
            "Missing/unsafe original textbook or lesson PDF")
    hashes={"source_sha256":_sha(source),"slides_sha256":_sha(slides)}
    with pymupdf.open(source) as textbook,pymupdf.open(slides) as deck:
        require(type(source_page) is int and 1<=source_page<=len(textbook)
                and type(slide_page) is int and 1<=slide_page<=len(deck),
                "Source/slide physical page not found")
        page=textbook[source_page-1]
        slide=deck[slide_page-1]
        caption,caprect,parts=caption_parts(page,figure_id)
        labels=physical_label_rules(page,caprect,parts)
        original_image=registered_raster_targets(slide,slide_page)
        require(len(original_image)==1,
                "One unique physical material raster expected for figure slide")
        target=original_image[0]
        anchor=target["anchor"]
        img=deck.extract_image(anchor["xref"])
        require(type(img) is dict and isinstance(img.get("image"),bytes)
                and len(img["image"])<=16_000_000,
                "Unbounded or missing actual embedded slide figure bitmap")
        # Reuse the historical rendered-raster equivalence guard: an
        # embedded bitmap may exist while a later shape/annotation overlays
        # or clips it. Verify what the learner will actually SEE, pixel-for-
        # pixel, against an independent image-only slide reference.
        slide_rect=pymupdf.Rect(target["bbox_pdf_pt"])
        with pymupdf.open() as blank_doc:
            blank=blank_doc.new_page(width=slide.rect.width,
                                     height=slide.rect.height)
            blank.insert_image(slide_rect,stream=img["image"],
                               keep_proportion=False)
            matrix=pymupdf.Matrix(2,2)
            actual=slide.get_pixmap(matrix=matrix,clip=slide_rect,
                    colorspace=pymupdf.csRGB,alpha=False,annots=True)
            reference=blank.get_pixmap(matrix=matrix,clip=slide_rect,
                    colorspace=pymupdf.csRGB,alpha=False,annots=False)
            require(actual.width==reference.width
                    and actual.height==reference.height
                    and bytes(actual.samples)==bytes(reference.samples),
                    "Actual learner-visible panel has occlusion/clip/overlay")
        dst=cv2.imdecode(np.frombuffer(img["image"],np.uint8),
                         cv2.IMREAD_COLOR)
        require(dst is not None and dst.ndim==3 and dst.shape[2]==3
                and 100<=dst.shape[0]<=1400 and 140<=dst.shape[1]<=2500,
                "Source-locked slide image has unsupported pixel geometry")
        first=min(x["marker_rect"][0] for x in labels)
        last=max(x["underline_rect"][2] for x in labels)
        bounds=pymupdf.Rect(
            max(0,math.floor(first-35)),
            max(0,math.floor(labels[0]["marker_rect"][1]-215)),
            min(page.rect.width,math.ceil(max(last+125,caprect.x0-3))),
            min(page.rect.height,math.ceil(max(
                caprect.y1+30,labels[0]["marker_rect"][3]+65))))
        require(page.rect.contains(bounds)
                and 30_000<=bounds.get_area()<=200_000,
                "Captioned figure source search must be spatially bounded")
        scale=2
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=bounds,
                           colorspace=pymupdf.csRGB,alpha=False,annots=True)
        src_rgb=np.frombuffer(pix.samples,np.uint8).reshape(
            pix.height,pix.width,3)
        src=cv2.cvtColor(src_rgb,cv2.COLOR_RGB2BGR)
        srcgray=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)
        gray=cv2.cvtColor(dst,cv2.COLOR_BGR2GRAY)
        orb=_fit_feature(srcgray,gray,"ORB")
        akaze=_fit_feature(srcgray,gray,"AKAZE")
        probe=np.float32([[0,0],[pix.width,0],[0,pix.height],
                          [pix.width,pix.height]]).reshape(-1,1,2)
        a=cv2.transform(probe,orb["matrix"]).reshape(-1,2)
        b=cv2.transform(probe,akaze["matrix"]).reshape(-1,2)
        require(float(np.linalg.norm(a-b,axis=1).max())<=4.0,
                "Independent ORB and AKAZE source image registrations disagree")
        # Author's original printed panel RULES, not arbitrary equal-width
        # bins, define panel separators. Project to native slide bitmap.
        edges=[]
        for left,right in zip(labels,labels[1:]):
            x=(left["underline_rect"][2]+right["underline_rect"][0])/2
            origin=np.float32([[(x-bounds.x0)*scale,
                                (labels[0]["marker_rect"][1]-bounds.y0)*scale]])
            mapped=origin@orb["matrix"][:,:2].T+orb["matrix"][:,2]
            edges.append(float(mapped[0,0]))
        pixels=[0]+[round(x) for x in edges]+[dst.shape[1]]
        require(all(0<=x<y<=dst.shape[1] and y-x>=35
                    for x,y in zip(pixels,pixels[1:])),
                "Physical source panel rules fail to partition slide image")
        for model in (orb,akaze):
            groups=[]
            for x0,x1 in zip(pixels,pixels[1:]):
                observed=model["dst"][model["inlier_mask"]]
                count=int(((observed[:,0]>=x0)&(observed[:,0]<x1)).sum())
                groups.append(count)
            require(all(x>=6 for x in groups),
                    "Each panel must independently contain matched image features")
            model["panel_inliers"]=groups
        reconstructed=cv2.warpAffine(
            src,orb["matrix"],(dst.shape[1],dst.shape[0]),
            flags=cv2.INTER_LINEAR,borderValue=(255,255,255))
        disagreement=np.abs(reconstructed.astype(np.int16)-
                            dst.astype(np.int16)).mean(axis=2)
        agree=(disagreement<=12)
        overall=float(agree.mean())
        per_panel=[float(agree[:,a:b].mean())
                   for a,b in zip(pixels,pixels[1:])]
        mae=float(disagreement.mean())
        require(overall>=.93 and mae<=5
                and all(x>=.91 for x in per_panel),
                "Slide imagery does not reproduce complete source captioned panels")
        rect=pymupdf.Rect(target["bbox_pdf_pt"])
        panels=[]
        for i,((letter,meaning),marker) in enumerate(zip(parts,labels)):
            native=[pixels[i],0,pixels[i+1],dst.shape[0]]
            pdf=[rect.x0+rect.width*native[0]/dst.shape[1],
                 rect.y0,rect.x0+rect.width*native[2]/dst.shape[1],
                 rect.y1]
            panels.append({
                "panel":letter,"caption_meaning":meaning,
                "printed_marker_source":marker,
                "slide_native_pixel_bbox":native,
                "slide_page_bbox_pdf_pt":[round(float(v),3) for v in pdf],
                "reproduced_RGB_tolerance12_fraction":
                    round(per_panel[i],5),
                "orb_inlier_feature_count":orb["panel_inliers"][i],
                "akaze_inlier_feature_count":akaze["panel_inliers"][i],
                "panel_caption_meaning_source_witnessed":True,
                "panel_visible_source_to_slide_pixel_provenance_verified":True,
                "panel_mathematics_independently_verified":False,
                "panel_narration_audio_verified":False,
            })
    require(_sha(source)==hashes["source_sha256"]
            and _sha(slides)==hashes["slides_sha256"],
            "Original textbook or slides mutated during independent figure registration")
    return {
        "schema_version":1,
        "status":"SOURCE_CAPTION_AND_BOTH_DETECTORS_PANEL_CORRESPONDENCE_VERIFIED",
        **hashes,
        "figure_id":figure_id,"source_page":source_page,
        "slide_page":slide_page,
        "caption_text":caption,
        "caption_sha256":hashlib.sha256(caption.encode("utf8")).hexdigest(),
        "whole_slide_figure_id":target["draft_element_id"],
        "embedded_figure_decoded_md5":anchor["decoded_image_md5"],
        "image_dimensions":list(anchor["native_dimensions_px"]),
        "panel_count":len(panels),"panels":panels,
        "original_source_search_region_pdf_pt":
            [round(float(x),3) for x in bounds],
        "orb_ransac_inlier_count":orb["inliers"],
        "akaze_ransac_inlier_count":akaze["inliers"],
        "panel_RGB_12_tolerance_fraction":round(overall,5),
        "source_to_slide_mean_RGB_abs_error":round(mae,5),
        "printed_caption_panel_meanings_verified":True,
        "source_slide_panels_physically_registered":True,
        "independent_mathematical_semantics_verified":False,
        "per_utterance_acoustic_alignment_verified":False,
        "G2_approved":False,"student_publication_authorized":False,
    }
