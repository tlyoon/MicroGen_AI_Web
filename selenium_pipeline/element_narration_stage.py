"""Strict source-grounded element-level staging for reviewed (not approved) MP4 previews.

Input is an explicit author-authored scene plan with one narration WAV per
precise rendered element. This module neither invents a mapping nor claims
that a WAV's audible words match its associated transcript. No TTS/cloud IO.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import wave
from pathlib import Path

import pymupdf

from .pdf_element_geometry import URI_PREFIX


class ElementStageError(ValueError):
    pass


def need(condition: bool, message: str):
    if not condition:
        raise ElementStageError(message)


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def save(path: Path, value: dict):
    with path.open("x",encoding="utf-8") as file:
        json.dump(value,file,indent=2,ensure_ascii=False)
        file.write("\n")


def canonical(data) -> str:
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,
            separators=(",",":"),allow_nan=False).encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"\s+"," ",text).casefold().strip()


def rectangle(page, anchor: dict):
    need(isinstance(anchor,dict),"Element anchor must be an object")
    if anchor.get("type")=="text_block":
        index=anchor.get("index")
        blocks=page.get_text("blocks")
        need(type(index) is int and 0<=index<len(blocks),"Invalid rendered text block index")
        block=blocks[index]
        need(len(block)>4 and isinstance(block[4],str)
             and normalize(anchor.get("text_evidence","")) in normalize(block[4])
             and len(normalize(anchor.get("text_evidence","")))>=7,
             "Text evidence not present at anchored rendered block")
        rect=pymupdf.Rect(block[:4])
        category="text"
    elif anchor.get("type")=="image_panel":
        index=anchor.get("index")
        panels=anchor.get("panels")
        ordinal=anchor.get("panel")
        images=page.get_images(full=True)
        need(type(index) is int and 0<=index<len(images),"Missing image in slide")
        need(type(panels) is int and 2<=panels<=6 and
             type(ordinal) is int and 1<=ordinal<=panels,
             "Invalid composite panel index")
        locations=page.get_image_rects(images[index][0])
        need(len(locations)==1,"Composite image placement ambiguous")
        image=locations[0]
        need(image.width>200 and image.width/image.height>2.5,
             "Figure is not a legible horizontal multi-panel image")
        width=image.width/panels
        rect=pymupdf.Rect(image.x0+(ordinal-1)*width,image.y0,
                           image.x0+ordinal*width,image.y1)
        category="figure_panel"
    else:
        raise ElementStageError("Unsupported anchor type (no automatic guessing)")
    need(not rect.is_empty and rect.get_area()>=25
         and page.rect.contains(rect)
         and rect.y0>=30 and rect.y1<page.rect.height-17,
         "Anchored region empty, clipped, or in slide footer/title")
    need(rect.get_area()<.85*page.rect.get_area(),
         "Oversized highlight target")
    return rect,category


def prepare(*, source_pdf:Path, slides_pdf:Path, authored_json:Path,
            recorded_audio:Path, destination:Path)->dict:
    source=Path(source_pdf).resolve()
    slides=Path(slides_pdf).resolve()
    author_file=Path(authored_json).resolve()
    audio=Path(recorded_audio).resolve()
    dest=Path(destination).resolve()
    need(all(p.is_file() and not p.is_symlink() for p in (source,slides,author_file)),
         "Source, slides and author plan required")
    need(audio.is_dir() and not audio.is_symlink(),"Recorded WAV directory required")
    need(not dest.exists() and dest.parent.is_dir(),"Destination must be new")
    need(not dest.is_relative_to(source.parent)
         and not dest.is_relative_to(slides.parent)
         and not dest.is_relative_to(audio)
         and not author_file.is_relative_to(dest),
         "Cannot stage inside source, plan, or audio tree")
    plan=json.loads(author_file.read_text(encoding="utf-8"))
    need(plan.get("schema_version")==1
         and plan.get("status")=="author_specified_unapproved_element_narration",
         "Not an explicit author-specified review plan")
    need(plan.get("source_sha256")==digest(source)
         and plan.get("slides_sha256")==digest(slides),
         "Stale source or slide SHA")
    voice=plan.get("voice_id")
    need(isinstance(voice,str) and len(voice)>5 and
         "unknown" not in voice.lower(), "Explicit synthesized voice identity required")
    parts=plan.get("parts")
    need(isinstance(parts,list) and 1<=len(parts)<=40
         and [x.get("part_id") for x in parts]==[
             f"part_{i:02d}" for i in range(1,len(parts)+1)],
         "Invalid/misordered part plan")
    output=[]
    collected=[]
    source_text=[]
    with pymupdf.open(source) as original, pymupdf.open(slides) as deck:
        need(original.page_count>0 and deck.page_count>0,"Empty PDF")
        source_text=[normalize(p.get_text()) for p in original]
        last_slide=0
        all_audio=set()
        for part in parts:
            records=part.get("slides")
            need(isinstance(records,list) and records,"Empty part slides")
            part_slides=[]
            board={"schema_version":1,"part_id":part["part_id"],
                   "plan_sha256":canonical(plan),
                   "slides":[],"narration_segments":[]}
            chunks=[]
            seconds=0.
            for j,record in enumerate(records,1):
                slide_index=record.get("slide")
                page_index=record.get("source_page")
                quote=record.get("source_evidence")
                need(type(slide_index) is int and last_slide<slide_index<=len(deck),
                     "Slides must be unique, strictly increasing, and in PDF")
                need(type(page_index) is int and 1<=page_index<=len(original)
                     and isinstance(quote,str) and len(normalize(quote))>=12
                     and normalize(quote) in source_text[page_index-1],
                     "Verbatim evidence absent from specified textbook source page")
                last_slide=slide_index
                pg=deck[slide_index-1]
                sid=f"{part['part_id']}.s{j:03d}"
                elements=record.get("elements")
                need(isinstance(elements,list) and elements,
                     "Every slide needs narrated anchored elements")
                regions=[]
                declared=[]
                for k,item in enumerate(elements,1):
                    eid=f"{sid}.e{k:02d}"
                    rect,category=rectangle(pg,item.get("anchor",{}))
                    for prior in regions:
                        overlap=(rect & prior).get_area()/min(rect.get_area(),prior.get_area())
                        need(overlap<.90,"Two element anchors are duplicated or nearly identical")
                    regions.append(rect)
                    chunk=item.get("wav")
                    spoken=item.get("spoken_text")
                    need(isinstance(chunk,str) and
                         re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav",chunk) is not None
                         and chunk not in all_audio,"Missing, repeated or unsafe WAV name")
                    all_audio.add(chunk)
                    path=audio/chunk
                    need(path.is_file() and not path.is_symlink(),"Missing source narration WAV")
                    with wave.open(str(path),"rb") as wav:
                        fmt=(wav.getnchannels(),wav.getsampwidth(),
                             wav.getframerate(),wav.getcomptype())
                        time=wav.getnframes()/wav.getframerate()
                    need(0.2<=time<=120 and fmt[3]=="NONE",
                         "Invalid, excessively long or encoded PCM segment WAV")
                    need(isinstance(spoken,str) and len(spoken.split())>=4
                         and len(spoken)<2000,
                         "Narration segment must be nonempty and bounded")
                    seconds+=time
                    seg_id=f"n{len(chunks)+1}"
                    chunks.append({"segment_id":seg_id,
                         "filename":f"n{len(chunks)+1}.wav",
                         "speech_sha256":hashlib.sha256(spoken.encode("utf-8")).hexdigest(),
                         "voice_id":voice,"pause_after_ms":0})
                    board["narration_segments"].append({
                        "segment_id":seg_id,"slide_id":sid,"element_ids":[eid],
                        "spoken_text":spoken,"estimated_duration_s":round(time,3)})
                    declared.append({"element_id":eid,"kind":category,
                        "source_concept_ids":["manual_source_verified_review_candidate"],
                        "source_page":page_index})
                    part_slides.append({"eid":eid,"rect":rect,"source_wav":path,
                        "part_wav":f"n{len(chunks)}.wav", "slide":slide_index})
                board["slides"].append({"slide_id":sid,
                    "title":record.get("title") or f"Original slide {slide_index}",
                    "elements":declared})
            need(0<seconds<590,"Part spoken WAV duration not safely below 600s")
            output.append((part["part_id"],board,chunks,part_slides,seconds))
            collected.extend(x["slide"] for x in part_slides)
        need(len(all_audio)==sum(len(x[2]) for x in output),
             "Duplicated audio chunk assignment")
        dest.mkdir()
        try:
            save(dest/"series_inputs.json",{"schema_version":1,
                "status":"review_only_source_bound_inputs",
                "source_sha256":digest(source),
                "plan_sha256":canonical(plan),
                "parts":[item[0] for item in output]})
            for name,board,chunks,geo,duration in output:
                folder=dest/name
                folder.mkdir()
                (folder/"wav").mkdir()
                stage_pdf=pymupdf.open()
                by_slide={}
                for g in geo:by_slide.setdefault(g["slide"],[]).append(g)
                for slide_num,regions in by_slide.items():
                    original_page=deck[slide_num-1]
                    page=stage_pdf.new_page(width=original_page.rect.width,
                                            height=original_page.rect.height)
                    page.show_pdf_page(page.rect,deck,slide_num-1)
                    for region in regions:
                        page.insert_link({"kind":pymupdf.LINK_URI,
                            "from":region["rect"],
                            "uri":URI_PREFIX+region["eid"]})
                stage_pdf.save(folder/"instrumented.pdf",garbage=4,deflate=True)
                stage_pdf.close()
                for row in geo:
                    copied=folder/"wav"/row["part_wav"]
                    shutil.copy2(row["source_wav"],copied)
                    need(digest(copied)==digest(row["source_wav"]),
                         "Segment WAV changed during copy")
                save(folder/"storyboard.json",board)
                save(folder/"tts_chunks.json",{
                    "schema_version":1,"part_id":name,"segments":chunks})
            save(dest/"element_stage_receipt.json",{
                "status":"review_only_source_grounded_audio_words_not_verified",
                "source_sha256":digest(source),
                "slides_sha256":digest(slides),
                "plan_sha256":canonical(plan),
                "voice_id":voice,
                "total_source_slides":len(deck),
                "staged_source_slides":[p["slide"] for part in parts
                                               for p in part["slides"]],
                "complete_lecture_coverage":False if
                   [p["slide"] for part in parts for p in part["slides"]]!=list(
                   range(1,len(deck)+1)) else True,
                "audio_text_fidelity_verified":False,
                "mathematical_approval":False,
                "source_page_quote_presence_verified":True,
                "part_seconds":[round(item[4],3) for item in output],
                "no_production_completion":True})
        except BaseException:
            shutil.rmtree(dest,ignore_errors=True)
            raise
    return {"staged":str(dest),"part_seconds":[round(x[4],3) for x in output],
            "voice":voice,"status":"review_only"}
