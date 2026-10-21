"""Incremental slide-level narration recovery across existing real lecture assets.

A recovered figure layout is NOT a whole-lecture veto. Independently queue
each slide's original narration, source/slide geometry and measured audio;
NEVER infer per-word timing from silence or a whole-slide WAV. The queue is
for a verified follow-on element mapper and element TTS, not for publishing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .runner import blocks
from .element_plan_autodraft import utterances


def _review_classification(page) -> tuple[str, int, int]:
    """Bounded visual-complexity triage, not a judgment of math correctness."""
    material_images=[x for x in page.get_image_info()
                     if x.get("width",0)>=48 and x.get("height",0)>=48]
    drawings=page.get_drawings()
    visible_blocks=[x for x in page.get_text("blocks")
                    if len(x)>=5 and isinstance(x[4],str) and x[4].strip()]
    if material_images:
        return "SOURCE_MATH_OR_FIGURE_ELEMENT_MAPPING_NEEDED",len(material_images),len(visible_blocks)
    if drawings:
        return "SOURCE_MATH_OR_VECTOR_ELEMENT_MAPPING_NEEDED",0,len(visible_blocks)
    return "SOURCE_TEXT_ELEMENT_MAPPING_NEEDED",0,len(visible_blocks)


def inspect_folder(folder:Path) -> dict:
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink(),
            "Subchapter source folder unavailable")
    source, slides, script=(folder/x for x in ("source.pdf","slides.pdf","script.txt"))
    require(all(x.is_file() and not x.is_symlink() for x in (source,slides,script)),
            "Immutable source, slides and narration required")
    original=[_sha(x) for x in (source,slides,script)]
    plan=inspect_original_slide_wav_plan(folder)
    require(plan["source_sha256"]==original[0]
            and plan["slides_sha256"]==original[1],
            "Untrusted source-bound WAV multipart evidence")
    raw=script.read_text(encoding="utf-8-sig")
    spoken=blocks(raw)
    require(len(spoken)==plan["original_wav_count"],
            "Original slide WAVs, PDF and script must have identical numbering")
    entries=[]
    with pymupdf.open(slides) as pdf:
        require(len(pdf)==len(spoken),
                "Slide PDF page count drifted from original narration")
        for (number,text),page,wav in zip(spoken,pdf,plan["wav_evidence"]):
            require(type(number) is int and number==len(entries)+1
                    and wav["slide_index"]==number
                    and type(text) is str and bool(text.strip()),
                    "Broken original slide order or empty narration")
            spoken_units=utterances(text)
            visual,images,blocks_count=_review_classification(page)
            part=[p["part_id"] for p in plan["proposed_parts"]
                  if p["slide_start"]<=number<=p["slide_end"]]
            require(len(part)==1,"Missing contiguous multipart work assignment")
            entries.append({
                "slide":number,"candidate_part_id":part[0],
                "slide_original_wav_sha256":wav["sha256"],
                "original_slide_audio_s":wav["duration_s"],
                "original_slide_narration_sha256":
                    hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "original_verbatim_utterances":[{
                    "utterance_id":f"s{number:03d}.utterance.{i:03d}",
                    "original_text":piece,
                    "original_text_sha256":hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                    "source_to_exact_visible_element_verified":False,
                    "spoken_text_audio_verified":False,
                    "highlight_start_end_from_this_wav_verified":False,
                } for i,piece in enumerate(spoken_units,1)],
                "visible_pdf_text_blocks":blocks_count,
                "material_figure_image_count":images,
                "element_mapping_next_action":visual,
                "source_figure_layout_issue_blocks_unrelated_slides":False,
                "technical_spoken_highlight_alignment_verified":False,
                "ready_for_billed_element_tts":False,
                "student_publication_authorized":False,
            })
    require([_sha(x) for x in (source,slides,script)]==original
            and all(_sha(folder/x["relative_name"])==x["sha256"]
                    for x in plan["wav_evidence"]),
            "Original teaching assets altered during independent worklist")
    return {
        "status":"INCREMENTAL_NARRATION_ELEMENT_EXECUTION_QUEUE_REVIEW_ONLY",
        "source_sha256":original[0],"slides_sha256":original[1],
        "script_sha256":original[2],
        "source_folder":str(folder),
        "slide_count":len(entries),
        "original_wav_count":plan["original_wav_count"],
        "original_slide_wav_total_s":plan["total_original_wav_duration_s"],
        "audio_only_part_count":plan["proposed_part_count"],
        "candidate_parts":plan["proposed_parts"],
        "slides":entries,
        "finished_lecture_production_authorized":False,
        "actual_element_wav_jobs_verified":0,
        "all_original_assets_preserved":True,
        "student_publication_authorized":False,
    }


def inspect_batch(*,root:Path,subchapters:tuple[str,...]) -> dict:
    root=Path(root).absolute()
    require(root.is_dir() and 1<=len(subchapters)<=40
            and len(set(subchapters))==len(subchapters)
            and all(isinstance(n,str)
                    and bool(re.fullmatch(r"[1-9][0-9]*\.[1-9][0-9]*",n))
                    for n in subchapters),
            "Select explicit, unique original numeric subchapters")
    records=[]
    for name in subchapters:
        try:
            entry=inspect_folder(root/name)
        except (OSError,ValueError,RuntimeError) as exc:
            # A missing/invalid subchapter stays BLOCKED, but does not
            # prevent independently complete adjacent subchapters advancing.
            # Never promote an exception to claimed source verification.
            entry={
                "status":"SOURCE_SUBCHAPTER_BLOCKED_INDEPENDENT_RECOVERY",
                "source_folder":str(root/name),
                "error_type":type(exc).__name__,
                "slides":[],"original_wav_count":0,"slide_count":0,
                "actual_element_wav_jobs_verified":0,
                "finished_lecture_production_authorized":False,
                "all_original_assets_preserved":False,
                "student_publication_authorized":False,
            }
        records.append(entry)
    return {
        "status":"NARRATION_ELEMENT_RECOVERY_QUEUE_NOT_PRODUCTION_RELEASE",
        "subchapter_names":list(subchapters),
        "independently_readable_subchapters":sum(
            r["status"]=="INCREMENTAL_NARRATION_ELEMENT_EXECUTION_QUEUE_REVIEW_ONLY"
            for r in records),
        "blocked_subchapters":sum(
            r["status"]!="INCREMENTAL_NARRATION_ELEMENT_EXECUTION_QUEUE_REVIEW_ONLY"
            for r in records),
        "subchapters":[{
            "name":name, **record
        } for name,record in zip(subchapters,records)],
        "all_subchapters_ready_for_production":False,
        "figure83_layout_reopen_required":False,
        "math_content_and_axis_qa_remains_separate":True,
        "spoken_to_element_timing_verified":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--subchapters",required=True,nargs="+")
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    result=inspect_batch(root=args.root,subchapters=tuple(args.subchapters))
    output=args.out.absolute()
    require(output.parent.is_dir() and not output.exists()
            and not output.is_relative_to(args.root.absolute()),
            "Write new queue JSON only outside original teaching directory")
    with output.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2,sort_keys=True,ensure_ascii=True)
        out.write("\n")
    print(json.dumps({
        "status":result["status"],
        "slides_per_subchapter":{p["name"]:p["slide_count"] for p in result["subchapters"]},
        "audio_parts_per_subchapter":{p["name"]:p["audio_only_part_count"]
                                      for p in result["subchapters"]},
        "no_automatic_paid_tts":not result["paid_tts_authorized"],
    },indent=2))
    # Creating a correctly marked REVIEW-ONLY execution queue is a successful
    # bounded task. A nonzero exit made unattended schedulers misclassify
    # this safe result as an execution stall, despite zero production authority.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
