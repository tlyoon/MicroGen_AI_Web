"""Fail-closed release bridge: original-acoustic-pause MP4s NEVER certify speech sync.

Promotion requires per-element source-verified WAVs, their trusted plan and
existing rendered/pixel acceptance. No original PDF/WAV/MP4 is overwritten.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .verbatim_element_manifest import build
from .figure_source_identity import require,_sha
from .element_highlight_workflow import source_bound_plan
from .figure_narration_promotion import check_production_anchor_provenance
from .sourcebound_production_video import accept_candidate

def inspect(*,source:Path,slides:Path,script:Path,
            authored:Path|None=None,audio:Path|None=None,
            review:Path|None=None,destination:Path|None=None)->dict:
    source,slides,script=[Path(p).absolute() for p in (source,slides,script)]
    source_manifest=build(source=source,slides=slides,script=script)
    paths=(authored,audio,review,destination)
    if any(p is not None for p in paths):
        require(all(p is not None for p in paths),
                "A complete plan, source-bound element WAVs, review and new target are required together")
    base={"schema_version":1,"source_sha256":source_manifest["source_sha256"],
        "slides_sha256":source_manifest["slides_sha256"],
        "original_script_sha256":source_manifest["script_sha256"],
        "utterances":source_manifest["original_utterance_count"],
        "provisional_slide_wav_timing_is_element_alignment":False,
        "require_independent_real_element_wav_sample_timings":True,
        "require_original_figure_semantic_review":True,
        "source_or_video_overwrite_allowed":False,
        "student_publication_authorized":False}
    if all(p is None for p in paths):
        return {**base,"status":"ELEMENT_SYNC_RELEASE_BLOCKED_NO_SOURCE_BOUND_AUDIO",
            "actual_element_wav_provenance_verified":False,
            "encoded_production_candidate_exists":False}
    authored,audio,review,destination=(Path(p).absolute() for p in paths)
    require(not destination.exists() and destination.parent.is_dir()
            and not destination.is_relative_to(source.parent)
            and not destination.is_relative_to(audio)
            and not destination.is_relative_to(review),
            "New source-separated production candidate required")
    require(authored.is_file() and not authored.is_symlink()
            and audio.is_dir() and not audio.is_symlink()
            and review.is_dir() and not review.is_symlink(),
            "Missing non-symlink audio, plan or reviewed video")
    before=(_sha(source),_sha(slides),_sha(script),_sha(authored))
    plan=json.loads(authored.read_text(encoding="utf8"))
    require(plan.get("status") in {
            "machine_verified_exact_text_element_narration",
            "author_specified_unapproved_element_narration"},
            "Original acoustic-pause pilot manifest is NOT per-element audio")
    require(plan.get("source_sha256")==before[0]
            and plan.get("slides_sha256")==before[1],
            "Source-bound plan does not match textbook/slide originals")
    # All source/figure and WAV identities are reverified by existing gates
    # before the first output byte is written.
    check_production_anchor_provenance(plan)
    source_bound_plan(source=source,slides=slides,plan=authored,audio=audio)
    require([_sha(p) for p in (source,slides,script,authored)]==list(before),
            "Source or reviewed audio plan changed during preflight")
    result=accept_candidate(source=source,slides=slides,authored=authored,
                            audio=audio,review_root=review,candidate=destination)
    require(destination.is_dir(),"Existing production bridge did not create candidate")
    return {**base,"status":"ELEMENT_SOURCE_BOUND_TECHNICAL_CANDIDATE_STAGED",
        "actual_element_wav_provenance_verified":True,
        "encoded_production_candidate_exists":True,
        "production_bridge_receipt":result,
        "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for f in ("source","slides","script"):
        p.add_argument("--"+f,type=Path,required=True)
    for f in ("authored","audio","review","destination"):
        p.add_argument("--"+f,type=Path)
    a=p.parse_args(argv)
    print(json.dumps(inspect(source=a.source,slides=a.slides,script=a.script,
            authored=a.authored,audio=a.audio,review=a.review,
            destination=a.destination),indent=2,default=str))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
