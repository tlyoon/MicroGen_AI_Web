"""Recover exact legacy Beamer slide-counter clipping in normal production.

Only recognizes the historical MicroGen prompt's original headline preamble.
A physical slide counter must be inset and its correct total frame count
proven in a twice-compiled actual PDF before producer acceptance. This never
relabels physics, rewrites narration, touches original QA sources, or grants
academic / cost / publication authority.
"""
from __future__ import annotations
import re
from pathlib import Path

LEGACY_HEADLINE = re.compile(
    r"\\setbeamertemplate\{headline\}\{%\s*"
    r"\\hfill%\s*"
    r"\\insertframenumber\{\}\s*/\s*\\inserttotalframenumber%\s*"
    r"\\par%\s*\}", re.M)
SAFE_VARIANT = re.compile(
    r"\\setbeamertemplate\{headline\}\{%\s*"
    r"\\vskip7pt%\s*\\leavevmode%\s*"
    r"\\hbox to \\paperwidth\{%\s*"
    r"\\hfill\\scriptsize\\insertframenumber\{\}\s*/\s*"
    r"\\inserttotalframenumber\\hspace\*\{9pt\}%\s*"
    r"\}%\s*\\vskip5pt%\s*\}", re.M)
SAFE_HEADLINE = (
    "\\setbeamertemplate{headline}{%\n"
    "  \\vskip7pt%\n"
    "  \\leavevmode%\n"
    "  \\hbox to \\paperwidth{%\n"
    "    \\hfill\\scriptsize\\insertframenumber{} / \\inserttotalframenumber"
    "\\hspace*{9pt}%\n"
    "  }%\n"
    "  \\vskip5pt%\n"
    "}"
)

def normalize_legacy_headline(tex: str) -> tuple[str,str]:
    """Change only exact known beamer metadata preamble; never frame content."""
    if not isinstance(tex, str) or not tex.strip():
        raise ValueError("Missing original generated Beamer source")
    safe_matches=list(SAFE_VARIANT.finditer(tex))
    if safe_matches:
        if len(safe_matches)!=1 or LEGACY_HEADLINE.search(tex):
            raise ValueError("Ambiguous or repeated Beamer metadata headline")
        match=safe_matches[0]
        canonical=tex[:match.start()]+SAFE_HEADLINE+tex[match.end():]
        return canonical,("ALREADY_SAFE_HEADLINE" if canonical==tex else
                          "SAFE_HEADLINE_CANONICALIZED")
    matches=list(LEGACY_HEADLINE.finditer(tex))
    if len(matches)!=1:
        if len(matches)>1:
            raise ValueError("Multiple legacy metadata headline definitions")
        # Unknown / no headline: do not guess and modify content.
        return tex,"NO_RECOGNIZED_LEGACY_HEADLINE"
    from .recovery_registry import lookup_mechanism
    try:
        registered=lookup_mechanism(
            "slide_layout_repair","LEGACY_BEAMER_TOP_EDGE_SLIDE_COUNTER")
    except (ValueError,OSError) as exc:
        raise ValueError("Known Beamer repair registry is invalid") from exc
    if registered!="INSET_BEAMER_COUNTER_TWO_PASS_PHYSICAL_PROOF":
        raise ValueError("Known Beamer repair not registered or retired")
    start,end=matches[0].span()
    updated=tex[:start]+SAFE_HEADLINE+tex[end:]
    if updated.replace(SAFE_HEADLINE,tex[start:end],1)!=tex:
        raise ValueError("Beamer repair changed anything beyond headline")
    return updated,"KNOWN_LEGACY_HEADLINE_RECOVERED"

def verify_slide_counter_pdf(pdf_file: Path,*,min_top_inset_pt=1.0,
                             min_right_inset_pt=5.0) -> dict:
    """Independently inspect every compiled counter's physical PDF text box."""
    import pymupdf
    pdf_file=Path(pdf_file)
    if not pdf_file.is_file() or pdf_file.is_symlink():
        raise ValueError("Actual unlinked Beamer PDF needed")
    evidence=[]
    with pymupdf.open(pdf_file) as doc:
        if not 1<=len(doc)<=250:
            raise ValueError("Invalid generated presentation page count")
        total=len(doc)
        for index,page in enumerate(doc,1):
            expected=f"{index} / {total}"
            hits=[]
            for block in page.get_text("dict").get("blocks",[]):
                if block.get("type")!=0:
                    continue
                for line in block.get("lines",[]):
                    for span in line.get("spans",[]):
                        if re.fullmatch(r"\d+\s*/\s*\d+",span.get("text","").strip()):
                            hits.append(span)
            if len(hits)!=1 or " ".join(hits[0]["text"].split())!=expected:
                raise ValueError(f"PDF slide {index}: unique correct {expected} counter missing")
            x0,y0,x1,y1=map(float,hits[0]["bbox"])
            if not (x0>=0 and y0>=min_top_inset_pt
                    and x1<=page.rect.width-min_right_inset_pt
                    and y1<max(28.0,.14*page.rect.height)):
                raise ValueError(
                    f"PDF slide {index}: page counter touches/crosses top or right edge")
            evidence.append({"slide":index,"counter":expected,
                             "bbox_pt":[round(v,3) for v in (x0,y0,x1,y1)]})
    return {"status":"REAL_BEAMER_PAGE_COUNTERS_PHYSICALLY_VERIFIED",
            "slide_count":len(evidence),
            "counter_geometry":evidence,
            "mathematics_approved":False,
            "scientific_review_approved":False,
            "paid_tts_authorized":False,
            "student_publication_authorized":False}
