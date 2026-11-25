"""Advance original G3 STATIC MP4 rebuild to immutable source-only element worklists.

Reuses *existing* element_plan_autodraft.propose and
element_plan_review_worklist.worklist. Source/slide/script SHA pinned to
original Serway §8.2 or §8.3. Materializes original publisher/narration
verbatim candidates outside source tree, while retaining ALL unverified
source-page/figure semantics and per-element spoken timing. No paid TTS,
model science egress, synthetic audio, rendering, academic acceptance,
historical Send replay or student publication.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .element_plan_autodraft import propose
from .element_plan_review_worklist import worklist
from .figure_source_identity import _sha,require
from .recovery_registry import lookup_mechanism

KIND="g3_static_source_element_draft"
SIGNATURE="G3_STATIC_ORIGINAL_VIDEO_REBUILD_NEEDS_TEXTBOOK_ELEMENT_WORKLIST"
MECHANISM="REUSE_ORIGINAL_ELEMENT_AUTODRAFT_STAGE_IMMUTABLE_UNAPPROVED_INPUT"
ROOT="g3_original_element_review_drafts_v1"


def _json(data:dict)->bytes:
    return (json.dumps(data,indent=2,ensure_ascii=False,
                       sort_keys=True)+"\n").encode("utf8")


def materialize(*,source_folder:Path,state_root:Path,section:str,
                original_source_hashes:dict,
                draft_producer=None,worklist_producer=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "G3 automatic source-element drafting not registered")
    require(section in ("Serway_8_2","Serway_8_3"),
            "Only original G3 source-pinned subsections may be staged")
    src=Path(source_folder).absolute()
    state=Path(state_root).absolute()
    require(src.is_dir() and state.is_dir()
            and not src.is_symlink() and not state.is_symlink()
            and not src.is_relative_to(state)
            and not state.is_relative_to(src),
            "G3 element draft must live outside original publisher source")
    names=("source.pdf","slides.pdf","script.txt")
    paths={name:src/name for name in names}
    require(type(original_source_hashes) is dict
            and set(original_source_hashes)==set(names)
            and all(path.is_file() and not path.is_symlink()
                    and _sha(path)==original_source_hashes[name]
                    for name,path in paths.items()),
            "Only exact original G3 source/slides/narration may be drafted")
    producer=draft_producer or propose
    draft=producer(source_pdf=paths["source.pdf"],
                   slides_pdf=paths["slides.pdf"],
                   script_txt=paths["script.txt"])
    require(type(draft) is dict
            and draft["status"]=="REVIEW_REQUIRED_NOT_TTS_READY"
            and draft["can_stage_or_synthesize_audio"] is False
            and draft["cannot_be_used_as_authored_element_plan"] is True
            and draft["source_meaning_reviewed"] is False
            and draft["manual_mapping_reviewed"] is False
            and draft["academic_approval"] is False
            and draft["automatic_author_approval"] is False
            and draft["student_publication"] is False
            and draft["all_audio_generated"] is False
            and all(draft[name.split(".")[0]+"_sha256"]==
                    original_source_hashes[name] for name in names),
            "G3 source-only draft must never act as accepted model meaning or TTS")
    slides=draft["slides"]
    require(type(slides) is list
            and len(slides)==draft["slide_count"]
            and 2<=len(slides)<=40
            and draft["utterance_count"]==sum(
                len(row["proposed_utterances"]) for row in slides)
            and draft["candidate_target_count"]==sum(
                len(row["auto_candidate_targets"]) for row in slides)
            and draft["ambiguous_utterance_count"]==sum(
                bool(unit["mapping_ambiguous"]) for row in slides
                for unit in row["proposed_utterances"])
            and 0<=draft["ambiguous_utterance_count"]<=
                draft["utterance_count"]
            and all(
                row["slide_number"]==n
                and row["source_page_approved"] is False
                and row["source_quote_approved"] is False
                and row["approved_for_stage"] is False
                and all(
                    unit["approved_for_tts"] is False
                    and unit["spoken_word_fidelity_verified"] is False
                    for unit in row["proposed_utterances"])
                for n,row in enumerate(slides,1)),
            "Original draft element or narration coverage is misleading")
    md=(worklist_producer or worklist)(draft)
    require(type(md) is str and len(md)<350_000
            and "REVIEW-ONLY" in md
            and "not authorized for TTS" in md,
            "Mandatory human/independent source meaning review omitted")
    require(all(_sha(paths[name])==original_source_hashes[name]
                for name in names),
            "Original textbook source changed during draft")
    packet=_json(draft)
    require(0<len(packet)<2_000_000,
            "Original source element proposal exceeds allowed size")
    token=hashlib.sha256(packet).hexdigest()
    home=state/ROOT/section
    require(not home.is_symlink()
            and not home.is_relative_to(src),
            "G3 review-only proposal folder redirected")
    home.mkdir(parents=True,exist_ok=True)
    outputs=[
        (home/(token+".json"),packet),
        (home/(token+".md"),md.encode("utf8"))]
    for path,body in outputs:
        require(not path.is_symlink(),
                "G3 original element draft output linked outside checkpoint")
        if path.exists():
            require(path.is_file() and path.read_bytes()==body,
                    "Previously saved original element proposal mutated")
        else:
            with path.open("xb") as stream:
                stream.write(body);stream.flush();os.fsync(stream.fileno())
    return {
        "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
        "section":section,
        "source_sha256":original_source_hashes["source.pdf"],
        "slides_sha256":original_source_hashes["slides.pdf"],
        "script_sha256":original_source_hashes["script.txt"],
        "draft_receipt":str(outputs[0][0]),
        "draft_receipt_sha256":_sha(outputs[0][0]),
        "mandatory_review_worklist":str(outputs[1][0]),
        "mandatory_review_worklist_sha256":_sha(outputs[1][0]),
        "original_slides":draft["slide_count"],
        "verbatim_narration_units":draft["utterance_count"],
        "unapproved_visual_candidates":draft["candidate_target_count"],
        "ambiguous_narration_to_visual_targets":
            draft["ambiguous_utterance_count"],
        "independent_scientific_source_review_complete":False,
        "per_element_TTS_ready":False,
        "independent_within_slide_highlight_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,
        "new_paid_gemini_API_calls":0,
    }
