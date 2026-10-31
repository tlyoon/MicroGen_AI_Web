"""Original Thomas 8.4 equation-source witnesses beyond verbatim paragraph matching.

This auditor independently reopens original publisher source.pdf and rendered
slides.pdf, requiring entire exact algebraic equality chains or BOTH endpoints
of a single longer source equality chain (only θ→u dummy-angle rename).
It does not prove every statement in the deck, examine raster figures, or
approve audio/video. A source-head/tail match is narrower than general
mathematical semantic equivalence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import pymupdf
from .figure_source_identity import require, _sha

_SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
# Number of independently witnessed equations expected from the original
# source per slide. An accidental omission is a hard failure, not a pass.
_EXPECTED={3:3,4:3,5:2,9:1,12:1}

def canonical(value:str)->str:
    value=unicodedata.normalize("NFKC",value)
    value=(value.replace("θ","u").replace("Θ","u")
            .replace("−","-").replace("–","-").replace("\u00a0"," "))
    return re.sub(r"\s+","",value).casefold().rstrip(".")

def find_slide_target(lines:list[tuple[str,list[float]]],slide:int)->list[tuple[str,list[float]]]:
    targets=[]
    for raw,box in lines:
        if slide==3 and canonical(raw) in ("x=atanu","x=asinu","x=asecu"):
            targets.append((raw,box))
        elif slide==4 and "we have" in raw and "=" in raw:
            targets.append((raw.split("we have ",1)[1],box))
        elif slide in (5,9) and raw.count("=")>=3 and ("tan2" in raw or "sin2" in raw):
            targets.append((raw,box))
        elif slide==12 and "radical becomes" in raw and "=" in raw:
            targets.append((raw.split("radical becomes ",1)[1],box))
    return targets

def match_line(math_expression:str,source_lines:list[list[str]],
               *,slide:int)->list[dict]:
    target=canonical(math_expression)
    candidates=[]
    for page_index,page_lines in enumerate(source_lines,1):
        for line in page_lines:
            src=canonical(line)
            if slide==3:
                if target and target in src:
                    kind="literal_source_substitution"
                else:
                    continue
            elif math_expression.count("=")>=3:
                if target==src:
                    kind="complete_textbook_algebraic_chain"
                else:
                    continue
            else:
                lhs,rhs=target.split("=",1)
                parts=src.split("=")
                if len(parts)>=3 and lhs==parts[0] and rhs==parts[-1]:
                    kind="source_chain_first_last_equality"
                else:
                    continue
            candidates.append({"textbook_page":page_index,
                               "original_source_line":line,
                               "source_match_kind":kind})
    return candidates

def _lines(page)->list[tuple[str,list[float]]]:
    result=[]
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines",[]):
            text="".join(span["text"] for span in line["spans"])
            if text:
                result.append((text,[round(float(x),3) for x in line["bbox"]]))
    return result

def audit(*,source:Path,slides:Path)->dict:
    source,slides=Path(source).absolute(),Path(slides).absolute()
    require(source.is_file() and slides.is_file()
            and not source.is_symlink() and not slides.is_symlink(),
            "Original publisher source and original slide PDF required")
    before=(_sha(source),_sha(slides))
    require(before[0]==_SOURCE_SHA,"Not original publisher Thomas §8.4 source PDF")
    evidence=[]
    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(len(deck)==17 and len(book)>=4,
                "Original 17-slide §8.4 deck or publisher PDF missing")
        publisher=[[line for line in pg.get_text().splitlines() if "=" in line]
                   for pg in book]
        # Publisher body header must be the expected section.
        require("8.4 Trigonometric Substitutions" in book[0].get_text(),
                "Source section identity changed")
        for slide_number,expected_count in _EXPECTED.items():
            page=deck[slide_number-1]
            target_lines=find_slide_target(_lines(page),slide_number)
            require(len(target_lines)==expected_count,
                    f"Missing/reflowed mathematical equality on slide {slide_number}: "
                    f"found {len(target_lines)}, require {expected_count}")
            for expression,bbox in target_lines:
                hits=match_line(expression,publisher,slide=slide_number)
                # An identical equation on multiple publisher pages should not
                # masquerade as a uniquely grounded figure or equation.
                unique_pages={hit["textbook_page"] for hit in hits}
                require(bool(unique_pages),
                        f"No original source equation chain for slide {slide_number}: "
                        f"{expression!r}")
                require(0<=bbox[0]<bbox[2]<=page.rect.width+1
                        and 0<=bbox[1]<bbox[3]<=page.rect.height+1,
                        f"Original mathematical source target outside slide {slide_number}")
                evidence.append({"slide_number":slide_number,
                                 "rendered_slide_math_equation":expression,
                                 "rendered_slide_rect_pt":bbox,
                                 "original_textbook_page_candidates":sorted(unique_pages),
                                 "single_original_page_candidate":(
                                     next(iter(unique_pages)) if len(unique_pages)==1
                                     else None),
                                 "source_equality_chain_witnesses":hits,
                                 "whole_equation_source_pattern_verified":True,
                                 "source_semantics_beyond_equation_pattern_approved":False})
    require((_sha(source),_sha(slides))==before,"Original publisher PDFs changed")
    require(len(evidence)==sum(_EXPECTED.values()),"Source equation count drift")
    return {"schema_version":1,
            "status":"ORIGINAL_TEXTBOOK_EQUATION_CHAINS_PATTERN_WITNESSED",
            "source_pdf_sha256":before[0],"slide_pdf_sha256":before[1],
            "slide_count":17,
            "equation_pattern_witness_count":len(evidence),
            "slides_with_pattern_witnesses":list(_EXPECTED),
            "remaining_slide_equations_and_figures_approved":False,
            "all_academic_semantics_verified":False,
            "encoded_video_accepted":False,
            "student_publication_authorized":False,
            "equations":evidence}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--slides",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    out=a.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(a.source.absolute().parent),
            "Exclusive external source-bound report destination required")
    report=audit(source=a.source,slides=a.slides)
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status":report["status"],
                      "witnesses":report["equation_pattern_witness_count"],
                      "slides":report["slides_with_pattern_witnesses"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
