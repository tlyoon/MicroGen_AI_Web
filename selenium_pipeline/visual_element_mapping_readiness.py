"""Exhaustive, no-cost source/PDF/utterance focus gap discovery.

Unlike inspect_text_only, does not stop at slide 1. Reports the actual
reasons each genuine slide requires mathematical/figure semantic mapping.
Never claims a visual cue is correct, permits TTS, or publishes a video.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import pymupdf
from .automatic_element_narration import normalize, _spoken_paragraphs
from .runner import blocks
from .source_numbered_example_coverage import audit_latex_example_coverage

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_all(*,source:Path,slides:Path,script:Path,latex:Path|None=None)->dict:
    paths=[Path(x).absolute() for x in (source,slides,script)]
    if (not all(p.is_file() and not p.is_symlink() for p in paths)
            or len({str(p.resolve()) for p in paths})!=3):
        raise ValueError("Three genuine distinct non-symlink original assets required")
    before=[sha(x) for x in paths]
    text=paths[2].read_text(encoding="utf-8-sig")
    utterances=blocks(text)
    rows=[]
    with pymupdf.open(paths[0]) as original,pymupdf.open(paths[1]) as deck:
        if not original or len(deck)!=len(utterances):
            raise ValueError("Real source / slides / narration counts inconsistent")
        source_text=[normalize(p.get_text()) for p in original]
        from .beamer_template_vector_separator import distinguish_template
        vector_classification=distinguish_template(list(deck))
        for (n,spoken),page in zip(utterances,deck):
            issues=[]
            imgs=page.get_images(full=True)
            blocks_raw=page.get_text("dict").get("blocks",[])
            image_blocks=[a for a in blocks_raw if a.get("type")==1]
            vectors=page.get_drawings()
            classified=vector_classification[n-1]
            if imgs or image_blocks or classified["non_template_vector_path_count"]:
                issues.append("VISUAL_GRAPHICS_SEMANTIC_PROVENANCE_REQUIRED")
            source_pages=[i+1 for i,v in enumerate(source_text)
                          if len(normalize(spoken))>=12 and normalize(spoken) in v]
            if len(source_pages)!=1:
                issues.append("NARRATION_NOT_VERBATIM_ON_ONE_UNIQUE_SOURCE_PAGE")
            # Count real visible block anchors. A likely text match alone
            # cannot prove mathematical equivalence or focus timing.
            visible=[normalize(b[4]) for b in page.get_text("blocks")
                     if len(b)>=5 and isinstance(b[4],str)]
            try:
                paragraphs=_spoken_paragraphs(spoken,n)
                structurally_ok=True
            except Exception:
                paragraphs=[]
                structurally_ok=False
                issues.append("NARRATION_PARAGRAPH_TIMING_NOT_EXPLICIT")
            matched=[]
            for p in paragraphs:
                count=visible.count(normalize(p))
                matched.append(count)
            if not matched or any(c!=1 for c in matched):
                issues.append("NARRATION_TO_VISIBLE_TEXT_ANCHOR_NOT_EXACT")
            if not issues:
                # This diagnostic is only a preflight; actual independent
                # geometry and source-bound production validation remain
                # mandatory even if all cheap checks appear satisfied.
                issues=["REQUIRES_FULL_GEOMETRY_AND_AUDIO_TIMELINE_VALIDATION"]
            rows.append({
                "slide":n,"graphic_image_count":len(imgs)+len(image_blocks),
                "vector_path_count":len(vectors),
                "beamer_repeated_template_vector_count":classified[
                    "verified_repeated_margin_template_vector_count"],
                "non_template_vector_path_count":classified["non_template_vector_path_count"],
                "visible_text_block_count":len(visible),
                "spoken_paragraph_count":len(paragraphs),
                "exact_visible_paragraph_matches":sum(c==1 for c in matched),
                "verbatim_source_page_candidates":source_pages,
                "reasons":issues,
                "element_focus_proven":False,
                "per_element_tts_authorized":False,
            })
    # Add strict source-header/visible-label geometry evidence for every
    # original slide. This does not waive math, figure-body or word-timing QA.
    from .source_label_geometry_evidence import inspect as inspect_labels
    label_geometry=inspect_labels(source=paths[0],slides=paths[1],script=paths[2])
    if len(label_geometry["slides"]) != len(rows):
        raise ValueError("Label geometry source/slide count drift")
    for row,loc in zip(rows,label_geometry["slides"]):
        if row["slide"] != loc["slide"]:
            raise ValueError("Original slide identity changed across geometry audits")
        row["source_grounded_label_geometry"]=loc["labels"]
        row["source_verified_label_count"]=loc["read_only_source_label_candidates"]
    coverage=None
    if latex is not None:
        l=Path(latex).absolute()
        if not l.is_file() or l.is_symlink():
            raise ValueError("Missing nonsymlinked original slide TeX")
        before_tex=sha(l)
        coverage=audit_latex_example_coverage(
            source_pdf=paths[0],slides_tex=l.read_text(encoding="utf-8"))
        if sha(l)!=before_tex:raise ValueError("LaTeX changed during coverage check")
        coverage={"coverage_pass":coverage["coverage_pass"],
                  "missing_promised_source_examples":coverage["missing_promised_source_examples"],
                  "slides_tex_sha256":before_tex}
    if [sha(x) for x in paths]!=before:
        raise ValueError("Original PDF/slides/narration changed during inspection")
    return {"schema_version":1,
        "status":"READ_ONLY_FULL_DECK_FIGURE_SOURCE_NARRATION_GAP_DIAGNOSTIC",
        **dict(zip(("source_sha256","slides_sha256","script_sha256"),before)),
        "slide_count":len(rows),
        "source_label_geometry_candidate_count":label_geometry[
            "uniquely_source_grounded_label_count"],
        "source_label_geometry_ambiguous_count":label_geometry["ambiguous_label_count"],
        "source_grounded_labels_explicitly_spoken_in_script":label_geometry[
            "source_anchored_labels_explicitly_spoken"],
        "labels_do_not_verify_figure_bodies_or_math":True,
        "slides_with_graphics":sum(bool(
            r["graphic_image_count"]+r["non_template_vector_path_count"]) for r in rows),
        "slides_with_only_repeated_decorative_vectors":sum(
            r["graphic_image_count"]==0 and
            r["non_template_vector_path_count"]==0 and
            r["beamer_repeated_template_vector_count"]>0 for r in rows),
        "slides_without_single_source_verbatim_match":sum(len(r["verbatim_source_page_candidates"])!=1 for r in rows),
        "slides_without_explicit_paragraph_anchor":sum(
            r["spoken_paragraph_count"]==0 or
            r["spoken_paragraph_count"]!=r["exact_visible_paragraph_matches"]
            for r in rows),
        "textbook_example_coverage":coverage,
        "rows":rows,
        "automatic_video_approved":False,
        "student_publication_authorized":False}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for label in ("source","slides","script"):
        p.add_argument("--"+label,type=Path,required=True)
    p.add_argument("--latex",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    output=args.output.absolute()
    if not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError("New isolated diagnostic output only; no file overwrite")
    report=inspect_all(source=args.source,slides=args.slides,script=args.script,latex=args.latex)
    with output.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    print(json.dumps({k:report[k] for k in (
        "slide_count","slides_with_graphics",
        "slides_without_single_source_verbatim_match",
        "slides_without_explicit_paragraph_anchor",
        "automatic_video_approved")}))
    return 0

if __name__=="__main__":raise SystemExit(main())
