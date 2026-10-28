"""Independent, conservative mathematical-term conflict report on exact PDF blocks.

Provides stronger evidence of *disagreement*; cannot prove agreement,
author mathematics acceptance, speaker fidelity or student release.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .element_plan_autodraft import file_hash
from .original_thomas84_pdf_math_risk import require
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences

TRIG_PATTERN = {
    "sine": r"\b(?:sine|sin)\b",
    "cosine": r"\b(?:cosine|cos)\b",
    "tangent": r"\b(?:tangent|tan)\b",
    "secant": r"\b(?:secant|sec)\b",
}
DOMAINS = {
    "strict_positive": r"\b(?:strictly positive|greater than zero|positive)\b",
    "nonnegative": r"\b(?:nonnegative|non-negative|at least zero)\b",
    "strict_negative": r"\b(?:strictly negative|less than zero)\b",
    "nonpositive": r"\b(?:nonpositive|non-positive|at most zero)\b",
}

def features(text: str) -> dict:
    lower = text.casefold()
    return {
        "trig": sorted(k for k,v in TRIG_PATTERN.items()
                       if re.search(v,lower)),
        "domain": sorted(k for k,v in DOMAINS.items()
                         if re.search(v,lower)),
        "explicit_numerals": sorted(set(re.findall(r"\b\d+(?:\.\d+)?\b",lower))),
        "visible_inequality": bool(re.search(r"[<≤≥>]",lower)),
    }

def compare_math_claims(spoken: str, visible: str) -> dict:
    a,b=features(spoken),features(visible)
    conflicts=[]
    uncertainties=[]
    # Only one trigonometric function on each side is unambiguous enough
    # to rule out a distinctly named visual object. Mixed formulas are
    # not automatically rejected.
    if len(a["trig"])==len(b["trig"])==1 and a["trig"]!=b["trig"]:
        conflicts.append("SINGLE_TRIG_FUNCTION_CONFLICT")
    if a["domain"] and b["domain"]:
        a_strength=set(a["domain"]); b_strength=set(b["domain"])
        if ("strict_positive" in a_strength and "nonpositive" in b_strength or
            "strict_negative" in a_strength and "nonnegative" in b_strength or
            "nonpositive" in a_strength and "strict_positive" in b_strength or
            "nonnegative" in a_strength and "strict_negative" in b_strength):
            conflicts.append("EXPLICIT_POLARITY_CONTRADICTION")
        elif a_strength!=b_strength:
            uncertainties.append("DOMAIN_STRICTNESS_OR_SCOPE_DIFFERS")
    if a["explicit_numerals"] and b["explicit_numerals"]:
        if not (set(a["explicit_numerals"]) & set(b["explicit_numerals"])):
            uncertainties.append("NUMERICAL_ANCHOR_NOT_SHARED")
    if b["visible_inequality"] and not a["domain"]:
        uncertainties.append("INEQUALITY_VISUAL_NOT_SPOKEN_EXPLICITLY")
    return {
        "spoken_features":a,"visible_features":b,
        "provable_local_term_conflicts":conflicts,
        "insufficient_evidence_flags":uncertainties,
        "whole_source_math_verified":False,
        "safe_for_release":False,
    }

def crosscheck(*,original:Path,risk_receipt:Path,output:Path)->dict:
    root=Path(original).resolve(); source=Path(risk_receipt).resolve()
    dest=Path(output).absolute()
    require(root.is_dir() and source.is_file() and dest.parent.is_dir()
            and not dest.exists() and not dest.is_relative_to(root.parent),
            "No overwrite/missing original risk receipt")
    report=json.loads(source.read_text(encoding="utf8"))
    require(report.get("status")==
            "PHYSICALLY_REVERIFIED_PDF_TARGETS_SEMANTICALLY_UNAPPROVED"
            and report.get("actual_pdf_blocks_verified")==29
            and report.get("mathematical_semantics_approved") is False
            and report.get("student_publication_authorized") is False,
            "Untrusted PR336 physical verification receipt")
    from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and report["source_pdf_sha256"]==EXPECTED_SOURCE_SHA,
            "Original textbook SHA changed")
    tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    summary=[]
    for item in report["candidates"]:
        slide=item["slide"]; sentence=item["sentence_index"]
        units,_=tokenize_reference_sentences(tts["slides"][slide-1]["tts_text"])
        require(1<=sentence<=len(units)
                and item["physical_pdf_geometry_and_text_verified"] is True
                and item["semantic_math_approved"] is False,
                "Source text or approval state incompatible with PR336")
        # Inspect exact source text block, rather than trusting a new model
        # to explain geometry or guess which mathematical term it represents.
        # Geometry content supplied by PR335 source-derived PDF layout is
        # re-grounded through the source/slide PDF below by exact rectangle.
        import pymupdf
        with pymupdf.open(root/"slides.pdf") as doc:
            page=doc[slide-1]
            candidates=[b for b in page.get_text("blocks") if len(b)>4
                        and all(abs(b[k]-item["pdf_rect_pt"][k])<=.15
                                for k in range(4))]
            require(len(candidates)==1,"Original PDF block geometry drift")
            visible=str(candidates[0][4])
        result=compare_math_claims(units[sentence-1]["narration_fragment"],visible)
        summary.append({"slide":slide,"sentence_index":sentence,
                        "original_pdf_element_id":item["element_id"],
                        "original_pdf_source_text_sha256":
                            __import__("hashlib").sha256(visible.encode("utf8")).hexdigest(),
                        **result})
    require(len(summary)==29,"Some real PDF candidate missing")
    output_record={
        "schema_version":1,
        "status":"ORIGINAL_SOURCE_DOMAIN_TRIG_CONFLICT_SCAN_UNAPPROVED",
        "source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "pr336_physical_receipt_sha256":file_hash(source),
        "source_pdf_targets_crosschecked":len(summary),
        "local_term_contradictions":sum(bool(x["provable_local_term_conflicts"])
                                        for x in summary),
        "review_uncertainties":sum(bool(x["insufficient_evidence_flags"])
                                   for x in summary),
        "full_mathematical_source_approval":False,
        "complete_spoken_element_highlight_approval":False,
        "student_publication_authorized":False,
        "candidates":summary,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(output_record,f,ensure_ascii=False,indent=2)
        f.write("\n")
    return output_record

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--original",required=True,type=Path)
    arg.add_argument("--risk-receipt",required=True,type=Path)
    arg.add_argument("--out",required=True,type=Path)
    a=arg.parse_args()
    r=crosscheck(original=a.original,risk_receipt=a.risk_receipt,output=a.out)
    print(json.dumps({k:v for k,v in r.items() if k!="candidates"},indent=2))
if __name__=="__main__":
    main()
