"""Build immutable verbatim utterance-to-original target REVIEW manifest.

Produces an exhaustive source-bound worklist, NOT billable or production
TTS input. Reconstructs everything from original PDFs and script.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from .element_plan_autodraft import propose
from .strict_source_element_mapping import classify
from .figure_source_identity import require,_sha

def build(*,source:Path,slides:Path,script:Path)->dict:
    source,slides,script=(Path(x).absolute() for x in (source,slides,script))
    evidence=classify(source=source,slides=slides,script=script)
    draft=propose(source_pdf=source,slides_pdf=slides,script_txt=script)
    hashes=[_sha(x) for x in (source,slides,script)]
    require(hashes==[draft["source_sha256"],draft["slides_sha256"],draft["script_sha256"]]
        ==[evidence["source_sha256"],evidence["slides_sha256"],evidence["script_sha256"]],
        "Source scripts or original visuals have changed")
    records=[]
    for s,t in zip(draft["slides"],evidence["slides"]):
        require(s["slide_number"]==t["slide"] and
                len(s["proposed_utterances"])==len(t["utterances"]),
                "Narration worklist missing slide")
        utterances=[]
        for a,b in zip(s["proposed_utterances"],t["utterances"]):
            require(a["proposal_id"]==b["utterance_id"] and
                    a["verbatim_script_fragment"]==b["exact_verbatim_script_fragment"],
                    "Narration source words were altered")
            phrase=a["verbatim_script_fragment"]
            utterances.append({
                "utterance_id":a["proposal_id"],
                "verbatim_script_fragment":phrase,
                "verbatim_utf8_sha256":hashlib.sha256(phrase.encode("utf8")).hexdigest(),
                "candidate_visible_target_id":b["candidate_visual_id"],
                "source_page_evidence":b["unique_source_pdf_page"],
                "source_word_appearance_verified":b["text_appearance_supported"],
                "selected_element_id":None,
                "reviewed_source_quote":None,
                "reviewer_mapping_rationale":None,
                "verified_original_figure_panel":False,
                "tts_clip_filename":f"s{s['slide_number']:03d}_u{len(utterances)+1:03d}.wav",
                "element_mapping_approved":False,
                "tts_authorized":False,
                "speech_timing_sample_verified":False,
            })
        require("".join(x["verbatim_script_fragment"] for x in utterances)
                ==s["verbatim_slide_narration"],
                "Original narration not covered exactly once")
        records.append({"slide":s["slide_number"],
                        "slide_original_script_sha256":s["original_script_block_sha256"],
                        "figure_review_required":s["figure_panel_review_required"],
                        "utterances":utterances})
    require([_sha(x) for x in (source,slides,script)]==hashes,
            "An original PDF or WAV script changed during manifest creation")
    return {"schema_version":1,
        "status":"VERBATIM_ELEMENT_NARRATION_MANIFEST_REVIEW_REQUIRED",
        "source_sha256":hashes[0],"slides_sha256":hashes[1],"script_sha256":hashes[2],
        "original_slide_count":len(records),
        "original_utterance_count":draft["utterance_count"],
        "unresolved_utterance_count":sum(len(x["utterances"]) for x in records),
        "original_academic_approval_granted":False,
        "verbatim_narration_unchanged":True,
        "parts":[],"slides":records,
        "complete_mapping_accepted":False,"element_tts_batch_allowed":False,
        "production_video_accepted":False,"student_publication_authorized":False}
def validate(*,source:Path,slides:Path,script:Path,receipt:dict)->dict:
    regenerated=build(source=source,slides=slides,script=script)
    require(type(receipt) is dict and regenerated==receipt,
            "Modified/approved/forged source narration manifest")
    return regenerated

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("source","slides","script"):
        p.add_argument("--"+field,required=True,type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    out=a.out.absolute()
    require(not out.exists() and out.parent.is_dir()
            and not out.is_relative_to(a.source.absolute().parent)
            and not out.is_relative_to(a.slides.absolute().parent),
            "New out-of-original staging manifest required")
    receipt=build(source=a.source,slides=a.slides,script=a.script)
    with out.open("x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2,ensure_ascii=True,sort_keys=True)
    print(json.dumps({k:receipt[k] for k in (
        "status","original_slide_count","original_utterance_count",
        "unresolved_utterance_count","element_tts_batch_allowed")},indent=2))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
