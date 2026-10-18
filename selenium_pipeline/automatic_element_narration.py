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

def _spoken_paragraphs(text: str, slide_number: int) -> list[str]:
    """Only explicit paragraph boundaries; never infer word/audio alignment."""
    paragraphs=[part.strip() for part in re.split(r"\n[ \t]*\n+",text.strip())]
    need(1 <= len(paragraphs) <= 12
         and all(4 <= len(part.split()) and len(part) < 2000
                 for part in paragraphs),
         f"Slide {slide_number}: needs 1-12 bounded, explicit spoken paragraphs")
    need(normalize(" ".join(paragraphs))==normalize(text),
         f"Slide {slide_number}: paragraphs do not exactly cover the narration")
    return paragraphs


def inspect_text_only(*,source:Path,slides:Path,script:Path)->dict:
    """Read-only, exact ordered paragraph -> *distinct* visible text blocks.

    Supports multi-element mathematical prose ONLY when the original PDF
    exposes those expressions as independently exact, accessible text.
    Never guesses semantic figure identity, OCR, panel crops or equations
    with missing PDF text.
    """
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
            # PDF figure graphics may be encoded as regular images, inline
            # image blocks, or vector paths (which get_images() misses).
            # A strict text-only source mapper must reject all three forms.
            need(not page.get_images(full=True)
                 and not page.get_drawings()
                 and not any(block.get("type")==1
                             for block in page.get_text("dict").get("blocks",[])),
                 f"Slide {number}: includes a figure/vector/inline image; "
                 "automatic text-only mapping prohibited")
            paragraphs=_spoken_paragraphs(text,number)
            evidence=normalize(text)
            need(len(evidence)>=12,"Narration lacks source evidence")
            # Demand *whole slide narration* appears sequentially and
            # verbatim on exactly ONE original textbook page.
            source_pages=[i+1 for i,page_text in enumerate(pages)
                          if evidence in page_text]
            need(len(source_pages)==1,
                 f"Slide {number}: narration does not match one unique textbook page")
            candidates=page.get_text("blocks")
            elements=[]
            positions=[]
            used=set()
            for ordinal,paragraph in enumerate(paragraphs,1):
                exact=normalize(paragraph)
                options=[]
                for index,block in enumerate(candidates):
                    if (len(block)>=5 and isinstance(block[4],str)
                            and normalize(block[4])==exact):
                        anchor={"type":"text_block","index":index,
                                "text_evidence":block[4].strip()}
                        try:
                            rect,_=rectangle(page,anchor)
                        except ValueError:
                            continue
                        options.append((anchor,rect))
                need(len(options)==1,
                     f"Slide {number}, element {ordinal}: ambiguous or nonverbatim rendered text")
                anchor,rect=options[0]
                need(anchor["index"] not in used,
                     f"Slide {number}: a visible text block cannot be narrated twice")
                used.add(anchor["index"])
                # Require explicit reading order and distinct geometric regions.
                # Never infer focus order from unanchored narration.
                for earlier in positions:
                    overlap=(rect & earlier).get_area()
                    need(overlap < .05*min(rect.get_area(),earlier.get_area()),
                         f"Slide {number}: overlapping narrated elements")
                if positions:
                    need(rect.y0 >= positions[-1].y1-2,
                         f"Slide {number}: narrated text order conflicts with visual order")
                positions.append(rect)
                elements.append({
                    "anchor":anchor,
                    "wav":f"s{number:03d}_e{ordinal:02d}.wav",
                    "spoken_text":paragraph
                })
            selections.append({
                "slide":number,"source_page":source_pages[0],
                "source_evidence":text.strip(),
                "title":f"Textbook slide {number}",
                "elements":elements
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
    count=sum(len(slide["elements"]) for slide in slides)
    need(len(seconds)==count,
         "Original element PCM duration count differs from anchored elements")
    chunks=[]
    current=[]
    duration=0.
    cursor=0
    for slide in slides:
        parts=seconds[cursor:cursor+len(slide["elements"])]
        cursor+=len(parts)
        need(all(type(sec) in (float,int) and .2<=sec<=120 for sec in parts),
             "Invalid original element-WAV duration")
        slide_seconds=sum(parts)
        need(slide_seconds<540,
             "A single slide exceeds safe multipart duration; requires a genuine split")
        if current and duration+slide_seconds>=540:
            chunks.append(current)
            current=[]
            duration=0.
        current.append(slide)
        duration+=slide_seconds
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
