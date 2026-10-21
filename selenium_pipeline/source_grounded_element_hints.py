"""Recompute original-PDF lexical evidence for every genuine narration/slide candidate.

Lexical source overlap is NOT semantic evidence or a reviewer attestation.
Exact visible block PDF identity and immutable source hashes are mandatory.
"""
from __future__ import annotations
import re
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .incremental_element_candidate_map import candidate_map

def _tokens(s:str)->list[str]:
    return re.findall(r"[a-z0-9]+",s.casefold())

def source_evidence_worklist(*,folder:Path,candidates:dict|None=None)->dict:
    folder=Path(folder).absolute()
    before={k:_sha(folder/name) for k,name in (
        ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
        ("script_sha256","script.txt"))}
    hints=candidates if candidates is not None else candidate_map(folder=folder)
    require(type(hints) is dict
            and hints.get("status")=="PER_UTTERANCE_SLIDE_ELEMENT_CANDIDATES_REVIEW_REQUIRED"
            and all(hints.get(k)==v for k,v in before.items())
            and hints.get("slide_count")==len(hints.get("slides",[])),
            "Source-grounded original candidate list is stale")
    pages=[];rows=[];seen=set()
    with pymupdf.open(folder/"source.pdf") as source,pymupdf.open(folder/"slides.pdf") as deck:
        pages=[" ".join(_tokens(pg.get_text())) for pg in source]
        require(len(deck)==len(hints["slides"]),"Slide PDF pages changed")
        for slide in hints["slides"]:
            n=slide["slide"]
            require(type(n) is int and 1<=n<=len(deck),"Invalid original slide number")
            raw=deck[n-1].get_text("blocks")
            ids={}
            for elem in slide["candidate_visual_targets"]:
                index=elem["anchor"]["index"]
                require(type(index) is int and 0<=index<len(raw)
                        and raw[index][4].strip()==elem["visible_text"]
                        and all(abs(float(a)-float(b))<=.002
                                for a,b in zip(raw[index][:4],elem["bbox_pdf_pt"])),
                        "Candidate element no longer matches actual visible PDF block")
                ids[elem["draft_element_id"]]=elem
            for unit in slide["original_utterance_candidates"]:
                uid=unit["utterance_id"]
                require(uid not in seen and type(uid) is str
                        and unit["original_text_sha256"] and
                        type(unit["candidate_visual_targets"]) is list,
                        "Duplicate or invalid original narrated element identity")
                seen.add(uid)
                options=[]
                for target in unit["candidate_visual_targets"]:
                    elem=ids.get(target["target_id"])
                    require(elem is not None
                            and elem["bbox_pdf_pt"]==target["original_visible_bbox_pdf_pt"]
                            and elem["visible_text"]==target["visible_pdf_text"],
                            "Ranked narration target has altered source geometry")
                    words=_tokens(elem["visible_text"])
                    phrases=[words[i:i+5] for i in range(max(0,len(words)-4))]
                    phrases=[" ".join(words[:min(5,len(words))])] if not phrases and len(words)>=3 else [" ".join(v) for v in phrases]
                    matches=[]
                    for page_index,content in enumerate(pages,1):
                        if any(len(x)>=12 and x in content for x in phrases):
                            matches.append(page_index)
                    options.append({"target_id":target["target_id"],
                                    "actual_visible_pdf_bbox_pt":elem["bbox_pdf_pt"],
                                    "source_pages_with_lexical_overlap":matches[:20],
                                    "source_page_hits_truncated":len(matches)>20,
                                    "lexical_overlap_is_semantic_proof":False,
                                    "requires_human_math_review":True})
                rows.append({"utterance_id":uid,
                             "spoken_text_sha256":unit["original_text_sha256"],
                             "candidate_source_hints":options,
                             "selected_target_id":None,
                             "reviewed":False,
                             "audio_generation_authorized":False})
    require(len(rows)==hints["utterance_count"]
            and all(_sha(folder/name)==before[k] for k,name in (
                ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
                ("script_sha256","script.txt"))),
            "Original narration coverage or source changed while extracting evidence")
    return {"status":"ORIGINAL_PDF_LEXICAL_ELEMENT_REVIEW_WORKLIST_ONLY",
            **before,"utterance_count":len(rows),
            "source_page_count":len(pages),"entries":rows,
            "human_reviewed_count":0,
            "semantic_element_approval":False,
            "tts_authorized":False,"publication_authorized":False}
