"""Join all verbatim narration with Figure 8.3 evidence in a review ledger.

Never auto-synthesize: proposed panel identities and exact source citations
still need independent math review.
"""
from pathlib import Path
import json, hashlib
from .figure_source_identity import require,_sha
from .verbatim_element_manifest import build as original_utterances
from .math_aware_slide5_figure_candidates import audit as figure_hints

def create(*,source:Path,slides:Path,script:Path)->dict:
    paths=[Path(x).absolute() for x in (source,slides,script)]
    before=[_sha(x) for x in paths]
    original=original_utterances(source=paths[0],slides=paths[1],script=paths[2])
    figure=figure_hints(source=paths[0],slides=paths[1],script=paths[2])
    require(original["original_slide_count"]>=5
            and original["original_utterance_count"]>=8
            and before==[original["source_sha256"],original["slides_sha256"],
                         original["script_sha256"]]
            ==[figure["source_sha256"],figure["slides_sha256"],figure["script_sha256"]],
            "Original figure evidence not bound to verbatim narration")
    source_utterances=original["slides"][4]["utterances"]
    hints=figure["utterances"]
    require(len(source_utterances)==len(hints)
            and all(a["utterance_id"]==b["utterance_id"]
                    and a["verbatim_script_fragment"]==b["original_narration"]
                    for a,b in zip(source_utterances,hints)),
            "Slide5 narration/figure candidate evidence misaligned")
    decisions=[]
    for slide in original["slides"]:
        utterances=[]
        for i,original_unit in enumerate(slide["utterances"]):
            clue=hints[i] if slide["slide"]==5 else None
            utterances.append({
                "utterance_id":original_unit["utterance_id"],
                "verbatim_utf8_sha256":original_unit["verbatim_utf8_sha256"],
                "candidate_graph_panel_unapproved":(
                    clue["candidate_ordered_graph_panel"] if clue else None),
                "spoken_function_family_hints_unapproved":(
                    clue["function_names_explicitly_spoken"] if clue else []),
                "requested_math_source_review":"VERIFY_SOURCE_EQUATION_PANEL_AND_VISUAL_TARGET",
                "independent_original_math_evidence_approved":False,
                "spoken_element_mapping_verified":False,
                "separate_segment_wav_available":False,
                "tts_authorized":False})
        decisions.append({"slide":slide["slide"],"entries":utterances})
    require([_sha(x) for x in paths]==before,"Original teaching source changed")
    return {"schema_version":1,
        "status":"FULL_SOURCE_NARRATION_ELEMENT_DECISION_LEDGER_REVIEW_REQUIRED",
        "source_sha256":before[0],"slides_sha256":before[1],"script_sha256":before[2],
        "original_slide_count":len(decisions),
        "original_utterance_count":original["original_utterance_count"],
        "figure83_single_family_candidate_count":figure["unique_single_function_hint_count"],
        "figure83_ambiguous_family_count":figure["unresolved_hint_count"],
        "verified_source_math_utterance_count":0,
        "narration_decisions":decisions,
        "batch_element_tts_permitted":False,
        "source_bound_audio_available":False,
        "student_publication_authorized":False}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    for x in ("source","slides","script","out"):p.add_argument("--"+x,type=Path,required=True)
    a=p.parse_args(argv)
    dest=a.out.absolute()
    require(not dest.exists() and dest.parent.is_dir()
            and not dest.is_relative_to(a.source.absolute().parent),
            "New isolated decision ledger required")
    receipt=create(source=a.source,slides=a.slides,script=a.script)
    with dest.open("x",encoding="utf8") as fh:json.dump(receipt,fh,indent=2,sort_keys=True)
    print(json.dumps({k:receipt[k] for k in (
        "status","original_utterance_count","figure83_single_family_candidate_count",
        "verified_source_math_utterance_count","batch_element_tts_permitted")},indent=2))
    return 2
if __name__=="__main__":raise SystemExit(main())
