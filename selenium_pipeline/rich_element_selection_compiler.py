"""Compile independently verified Gemini/ChatGPT rich-element mappings into the
existing production element-review format, without inventing math approval.

When ALL narration is physically source-backed *nonmathematical text*, the
technical-only selection can be prepared for the project's existing separate
billable Gemini-TTS authorization flow. No model content may declare academic
approval. Math/figure/ambiguous clauses remain explicit, localized review gaps.
The source/author/script and raw model response bytes are revalidated AGAIN
when the existing production review bridge consumes a machine selection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .element_plan_review_bridge import template, file_hash
from .rich_element_model_alignment import (
    RichMappingError, require, load_accepted_checkpoint,
    assess_response, request_for_slide, parse_response,
)


MODE = "machine_source_and_author_quote_verified_text_only"


def _load_responses(directory:Path, expected:int) -> tuple[dict,dict]:
    directory=Path(directory).absolute()
    require(directory.is_dir() and not directory.is_symlink(),
            "Actual independently captured model responses folder required")
    found={}
    digests={}
    for slide in range(1,expected+1):
        file=directory / f"slide_{slide:03d}.json"
        if not file.exists():
            continue
        require(file.is_file() and not file.is_symlink(),
                "Untrusted model response file or symlink")
        try:
            raw=file.read_text("utf8")
        except OSError as exc:
            raise RichMappingError("Model response cannot be read") from exc
        found[slide]=parse_response(raw)
        digests[file.name]=file_hash(file)
    require(not any(p.is_symlink() or p.name not in digests
                    for p in directory.glob("slide_*.json")),
            "Unknown or unsafe model response file; avoid phantom coverage")
    return found, digests


def compile_selection(*, source_folder:Path, checkpoint:Path,
                      responses:Path, tts_model:str, tts_voice:str)->dict:
    from .element_plan_autodraft import file_hash as hash_file
    source_folder=Path(source_folder).absolute()
    checkpoint=Path(checkpoint).absolute()
    responses=Path(responses).absolute()
    require(responses!=checkpoint and not responses.is_relative_to(source_folder),
            "Model outputs cannot be placed within original author files")
    meta,draft=load_accepted_checkpoint(folder=source_folder,checkpoint=checkpoint)
    require(isinstance(tts_model,str) and tts_model in
            {"gemini-3.8-flash-lite-tts","gemini-3.8-flash-tts"}
            and isinstance(tts_voice,str) and 3<=len(tts_voice)<=30
            and tts_voice.replace("_","").isalnum(),
            "Unsupported or unreviewed TTS provider identity")
    supplied,digests=_load_responses(responses,draft["slide_count"])
    selection=template(draft)
    selection["draft_sha256"]=file_hash(
        checkpoint/"element_mapping_candidates.json")
    selection["voice_id"]=(
        f"gemini_{tts_model}_{tts_voice}_REVIEW_ONLY")
    selection["tts_model"]=tts_model
    selection["tts_voice"]=tts_voice
    selection["machine_source_evidence_mode"]=MODE
    selection["source_inputs_sha256"]=meta["source_inputs_sha256"]
    selection["evidence_checkpoint_folder"]=str(checkpoint)
    selection["model_response_folder"]=str(responses)
    selection["model_response_sha256"]=digests
    selection["model_processed_utterances"]=0
    selection["source_anchored_technical_text_utterances"]=0
    selection["remaining_technical_review_items"]=[]
    selection["student_publication"]=False
    selection["academic_approval"]=False
    review=[]
    for slide_row,source_row in zip(selection["slides"],draft["slides"]):
        slide=source_row["slide_number"]
        if slide not in supplied:
            review.append({"slide":slide,"reason":"missing_entire_model_response"})
            continue
        response=supplied[slide]
        audit=assess_response(source_folder=source_folder,
            checkpoint=checkpoint,slide_number=slide,
            proposed=response)
        selection["model_processed_utterances"]+=audit["utterances_total"]
        selection["source_anchored_technical_text_utterances"]+=(
            audit["text_source_and_author_anchors_passed"])
        invalid=[
            {"slide":slide,"utterance_id":entry["utterance_id"],
             "reasons":entry["remaining_independent_scientific_review_reasons"]}
            for entry in audit["entries"]
            if entry["remaining_independent_scientific_review_reasons"]]
        review.extend(invalid)
        if invalid:
            # Leave the entire slide incomplete. A partial, interpolated
            # narrator-to-figure plan must never be promoted as complete.
            continue
        entries=audit["entries"]
        pages={entry["publisher_source_page"] for entry in entries}
        if len(pages)!=1 or None in pages:
            review.append({"slide":slide,
                           "reason":"slide_spans_multiple_or_unknown_textbook_pages"})
            continue
        authored={row["draft_element_id"]:row
                  for row in source_row["auto_candidate_targets"]}
        groups=[]
        for entry in entries:
            target_id=entry["selected_visible_target_id"]
            if groups and groups[-1]["target_id"]==target_id:
                groups[-1]["utterance_ids"].append(entry["utterance_id"])
            else:
                groups.append({"target_id":target_id,
                    "utterance_ids":[entry["utterance_id"]]})
        ids=[g["target_id"] for g in groups]
        if len(ids)!=len(set(ids)):
            review.append({"slide":slide,
                           "reason":"nonadjacent_reuse_of_one_visual_target"})
            continue
        fragments={r["proposal_id"]:r["verbatim_script_fragment"]
                   for r in source_row["proposed_utterances"]}
        for group in groups:
            phrase="".join(fragments[x] for x in group["utterance_ids"]).strip()
            if len(phrase.split())<4 or len(phrase)>1999:
                review.append({"slide":slide,
                    "reason":"spoken_visual_group_must_have_four_words_and_be_bounded"})
        if any(x["slide"]==slide for x in review):
            continue
        slide_row["source_page"]=pages.pop()
        slide_row["source_evidence"]=entries[0]["exact_source_page_quote"]
        slide_row["review_note"]=(
            "Machine-only technical mapping: original publisher quote and "
            "actual author PDF text block independently matched; this is "
            "NOT a human academic review or student publication approval.")
        slide_row["elements"]=[]
        for position,group in enumerate(groups,1):
            target=authored[group["target_id"]]
            require(target["kind"] in {"text_block","text_group"}
                    and target.get("source_evidence_verified") is False,
                    "Only verified physical source PDF text may auto process")
            slide_row["elements"].append({
                "draft_element_id":group["target_id"],
                "utterance_ids":group["utterance_ids"],
                "wav":f"s{slide:03d}_e{position:02d}.wav",
                "element_review_note":
                    "Source-verifier checked exact original textbook quote, "
                    "unchanged slide PDF block and spoken-language overlap; "
                    "math and figure semantics are not claimed.",
                "figure_review_acknowledged":False,
            })
    selection["remaining_technical_review_items"]=review
    # Part boundaries derive ONLY from actual already authored words and
    # are conservative estimates; full WAV and real MP4 <600s gates remain.
    elapsed=0.
    boundaries=[]
    for slide,source_row in enumerate(draft["slides"],1):
        duration=sum(len(u["verbatim_script_fragment"].split()) for u
                     in source_row["proposed_utterances"])*60/70
        if elapsed>0 and elapsed+duration>=420:
            boundaries.append(slide-1)
            elapsed=0.
        elapsed+=duration
        if duration>=420:
            review.append({"slide":slide,
                           "reason":"one_slide_exceeds_safe_audio_part_budget"})
    selection["part_boundaries_after_slides"]=sorted(set(boundaries))
    ready=not review and len(supplied)==draft["slide_count"] and all(
        row.get("elements") for row in selection["slides"])
    selection["status"]=("REVIEWED_SELECTION_FOR_PROCESSING"
                         if ready else "REVIEW_SELECTION_INCOMPLETE")
    selection["machine_technical_processing_ready"]=ready
    if ready:
        selection["reviewer_note"]=(
            "Independent machine source-PDF and authored text-only passage "
            "verification; no human academic assessment or student release "
            "is claimed, and billed synthesis needs separate authorization.")
    selection["academic_approval"]=False
    selection["student_publication"]=False
    selection["source_and_model_receipts_immutable_and_reusable"]=True
    return selection


def verify_machine_selection(*, source:Path,slides:Path,script:Path,
                             draft:Path,selection:dict)->None:
    """Runs inside the paid-TTS promotion entrypoint: REBUILD all AI proofs."""
    root=Path(source).absolute().parent
    require(Path(slides).absolute()==root/"slides.pdf"
            and Path(script).absolute()==root/"script.txt"
            and Path(source).absolute()==root/"source.pdf"
            and selection.get("machine_source_evidence_mode")==MODE,
            "Machine model selection does not bind canonical publisher assets")
    folder=selection.get("evidence_checkpoint_folder")
    response_folder=selection.get("model_response_folder")
    require(type(folder) is str and type(response_folder) is str,
            "Machine mapping source-evidence paths unavailable")
    expected=compile_selection(
        source_folder=root,checkpoint=Path(folder),
        responses=Path(response_folder),
        tts_model=selection["tts_model"],tts_voice=selection["tts_voice"])
    require(expected.get("status")=="REVIEWED_SELECTION_FOR_PROCESSING"
            and expected==selection
            and expected["draft_sha256"]==file_hash(Path(draft)),
            "Machine source/model/textbook/author mapping changed since review")
    require(not expected["remaining_technical_review_items"]
            and expected["academic_approval"] is False
            and expected["student_publication"] is False,
            "Unresolved rich semantic mapping cannot authorize element TTS")


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-folder",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--responses",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--tts-model",default="gemini-3.8-flash-lite-tts")
    p.add_argument("--tts-voice",default="Kore")
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.source_folder.absolute()),
            "Write a NEW original-source-external selection receipt only")
    selection=compile_selection(
        source_folder=a.source_folder,checkpoint=a.checkpoint,
        responses=a.responses,tts_model=a.tts_model,tts_voice=a.tts_voice)
    with a.out.open("x",encoding="utf8") as stream:
        json.dump(selection,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status":selection["status"],
          "text_proof_utterances":
             selection["source_anchored_technical_text_utterances"],
          "unresolved":len(selection["remaining_technical_review_items"]),
          "technical_processing_ready":
             selection["machine_technical_processing_ready"],
          "paid_tts_authorized":False,"student_publication_authorized":False}))
if __name__=="__main__":
    main()
