"""Strict source-grounded visual mapping triage without false semantic approval.

Exact visible words, one-ranked target, and original source quote consistency
are evidence for a provisional textual match, NOT permission to synthesize or
claim spoken-word correctness. All math/figure uncertainty fails closed.
"""
from __future__ import annotations
import hashlib, re, unicodedata
from pathlib import Path
import pymupdf
from .element_plan_autodraft import propose
from .figure_source_identity import require, _sha

def norm(s):
    return " ".join(unicodedata.normalize("NFKC",s).casefold().split())
def classify(*,source:Path,slides:Path,script:Path)->dict:
    paths=[Path(x).absolute() for x in (source,slides,script)]
    require(all(x.is_file() and not x.is_symlink() for x in paths),
            "Original source PDF, slides PDF, and script required")
    before=[_sha(x) for x in paths]
    draft=propose(source_pdf=paths[0],slides_pdf=paths[1],script_txt=paths[2])
    require([draft[x] for x in ("source_sha256","slides_sha256","script_sha256")]==before,
            "Stale or forged draft provenance")
    mapping=[]
    with pymupdf.open(paths[0]) as original,pymupdf.open(paths[1]) as deck:
        require(len(deck)==draft["slide_count"],"Slide count drift")
        for row in draft["slides"]:
            idx=row["slide_number"]
            targets={t["draft_element_id"]:t for t in row["auto_candidate_targets"]}
            page=deck[idx-1]
            entries=[]
            for speech in row["proposed_utterances"]:
                choices=speech["candidate_target_rankings_unverified"]
                matches=[]
                for choice in choices:
                    target=targets.get(choice["draft_element_id"])
                    if not target or target["kind"]!="text_block" or target["panel_identity_review_required"]:
                        continue
                    text=target["visible_text"] or ""
                    literal=norm(speech["verbatim_script_fragment"])
                    visible=norm(text)
                    # Full equality only; prefix overlap and math keyword
                    # similarity are NOT enough to certify meaning.
                    if literal!=visible or len(literal)<12:
                        continue
                    page_words=norm(page.get_text())
                    if literal not in page_words:continue
                    original_pages=[n+1 for n,p in enumerate(original)
                                    if literal in norm(p.get_text())]
                    if len(original_pages)!=1:continue
                    matches.append((choice["draft_element_id"],original_pages[0]))
                unique=len(matches)==1 and not row["figure_panel_review_required"]
                entries.append({
                    "utterance_id":speech["proposal_id"],
                    "exact_verbatim_script_fragment":speech["verbatim_script_fragment"],
                    "unique_verbatim_text_original_pdf_match":bool(unique),
                    "candidate_visual_id":matches[0][0] if unique else None,
                    "unique_source_pdf_page":matches[0][1] if unique else None,
                    "text_appearance_supported":bool(unique),
                    "mathematical_semantics_verified":False,
                    "narration_spoken_word_alignment_verified":False,
                    "element_tts_authorized":False,
                    "review_reason":("UNIQUE_LITERAL_TEXT_APPEARANCE_ONLY"
                         if unique else "SOURCE_OR_SEMANTIC_ELEMENT_REVIEW_REQUIRED"),
                })
            mapping.append({"slide":idx,
                            "all_utterances_literal_proven":
                                all(x["unique_verbatim_text_original_pdf_match"] for x in entries),
                            "utterances":entries})
    require([_sha(x) for x in paths]==before,"Originals changed during semantic triage")
    count=sum(x["unique_verbatim_text_original_pdf_match"]
              for row in mapping for x in row["utterances"])
    return {
        "schema_version":1,
        "status":"STRICT_SOURCE_LITERAL_ELEMENT_MAPPING_REVIEW_ONLY",
        "source_sha256":before[0],"slides_sha256":before[1],"script_sha256":before[2],
        "slide_count":len(mapping),"utterance_count":draft["utterance_count"],
        "original_ambiguous_utterance_count":draft["ambiguous_utterance_count"],
        "literal_source_text_evidence_count":count,
        "still_unapproved_count":draft["utterance_count"]-count,
        "slides":mapping,
        "per_element_tts_authorized":False,
        "complete_lecture_mapping_verified":False,
        "math_figure_semantics_verified":False,
        "student_publication_authorized":False,
    }
def main(argv=None):
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides","script"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args(argv)
    print(json.dumps(classify(source=a.source,slides=a.slides,script=a.script),
        indent=2,ensure_ascii=True,sort_keys=True))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
