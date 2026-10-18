"""Conservative *automatic* source/slide-element narration and TTS input builder.

This is a STRICT exact-text case, not a guessed math/figure mapper:
one already authored slide narration paragraph must match exactly one visible
body text block and verbatim textbook page. Any ambiguity or figures BLOCK.
Human academic approval is optional; technical ambiguity is never waived.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import pymupdf

from .runner import blocks
from .element_narration_stage import normalize, rectangle

class AutomaticElementAudioError(ValueError):
    pass

def need(ok, message):
    if not ok: raise AutomaticElementAudioError(message)

def sha(path):
    need(path.is_file() and not path.is_symlink(),f"Missing or symlinked source: {path}")
    h=hashlib.sha256()
    with path.open("rb") as inp:
        for b in iter(lambda: inp.read(1048576),b""): h.update(b)
    return h.hexdigest()

def inspect_text_only(*,source:Path,slides:Path,script:Path)->dict:
    """Read-only deterministic matching, never creates or overwrites files."""
    source,slides,script=(Path(x).resolve() for x in (source,slides,script))
    raw=script.read_text(encoding="utf-8-sig")
    spoken=blocks(raw)
    need(spoken and len(spoken)<=500,"Empty or oversized narration")
    selections=[]
    with pymupdf.open(source) as original,pymupdf.open(slides) as deck:
        need(len(deck)==len(spoken) and len(original)>0,
             "Slide/narration counts differ or source PDF empty")
        pages=[normalize(page.get_text()) for page in original]
        for (number,text),page in zip(spoken,deck):
            need(len(text.split())>=4 and len(text)<2000,
                 f"Slide {number}: narration too short/long")
            need(not page.get_images(full=True),
                 f"Slide {number}: includes a figure; automatic text-only mapping prohibited")
            evidence=normalize(text)
            need(len(evidence)>=12, "Narration lacks source evidence")
            # A whole narration paragraph must correspond to exactly one
            # rendered block; never implicitly assign it to an equation or
            # multipart image or spread it over several highlights.
            blocks_on_page=page.get_text("blocks")
            options=[]
            for index,block in enumerate(blocks_on_page):
                if len(block)>=5 and isinstance(block[4],str) and normalize(block[4])==evidence:
                    anchor={"type":"text_block","index":index,
                            "text_evidence":block[4].strip()}
                    try:
                        rectangle(page,anchor)
                    except ValueError:
                        continue
                    options.append(anchor)
            need(len(options)==1,
                 f"Slide {number}: rendered text is ambiguous or differs from exact spoken words")
            source_pages=[i+1 for i,x in enumerate(pages) if evidence in x]
            need(len(source_pages)==1,
                 f"Slide {number}: no unique verbatim textbook page for narration")
            quote=text.strip()
            need(normalize(quote) in pages[source_pages[0]-1],
                 "Exact original source quotation missing")
            selections.append({
                "slide":number,"source_page":source_pages[0],
                "source_evidence":quote,
                "title":f"Textbook slide {number}",
                "elements":[{
                    "anchor":options[0],
                    "wav":f"s{number:03d}_e01.wav",
                    "spoken_text":text
                }]
            })
    return {"schema_version":1,
        "status":"EXACT_TEXT_ONLY_ELEMENT_MATCH_TECHNICAL",
        "source_sha256":sha(source),"slides_sha256":sha(slides),
        "script_sha256":sha(script),
        "elements":selections,
        "human_review_required":False,
        "figure_semantic_mapping_assumed":False,
        "no_automatic_panel_approvals":True}

def plan_for_audio(selections:dict, seconds:list[float],
                   *, provider:str,model:str,voice:str) -> dict:
    slides=selections["elements"]
    need(len(seconds)==len(slides),"Audio count does not match mapped elements")
    chunks=[]
    current=[]
    duration=0.
    for slide,sec in zip(slides,seconds):
        need(type(sec) in (float,int) and .2<=sec<=120,
             "Invalid original element-WAV duration")
        if current and duration+sec>=540:
            chunks.append(current)
            current=[]
            duration=0.
        current.append(slide)
        duration+=sec
    if current:chunks.append(current)
    need(1<=len(chunks)<=40,"Lecture requires too many short video parts")
    return {"schema_version":1,
        "status":"machine_verified_exact_text_element_narration",
        "source_sha256":selections["source_sha256"],
        "slides_sha256":selections["slides_sha256"],
        "script_sha256":selections["script_sha256"],
        "voice_id":f"{provider}_{model}_{voice}_REVIEW_ONLY",
        "parts":[{"part_id":f"part_{n:02d}","slides":x}
                 for n,x in enumerate(chunks,1)],
        "human_approval_required":False,
        "technical_exact_text_mapping":True}


def verify_automatic_source_mapping(*,source:Path,slides:Path,plan:dict)->dict:
    """Recompute EVERY text/source/page/rectangle pairing without trusting
    a previously written planner receipt or claim of human authorship."""
    need(plan.get("status")=="machine_verified_exact_text_element_narration"
         and plan.get("technical_exact_text_mapping") is True
         and plan.get("human_approval_required") is False,
         "Missing explicit machine-only narration provenance")
    verified=inspect_text_only(
        source=source,slides=slides,script=Path(source).parent/"script.txt")
    expanded=[slide for part in plan["parts"] for slide in part["slides"]]
    need(expanded==verified["elements"]
         and plan.get("script_sha256")==verified["script_sha256"]
         and plan.get("source_sha256")==verified["source_sha256"]
         and plan.get("slides_sha256")==verified["slides_sha256"],
         "Machine-derived source-to-narration mapping altered after selection")
    return verified
