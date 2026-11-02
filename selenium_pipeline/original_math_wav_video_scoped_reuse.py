"""Evidence-first bounded mathematical/WAV/encoded-pixel QA reuse on original Thomas.

Reuses previously independently proved *narrow* scopes from PR443/444/449.
Does NOT suppress complete lecture generation, all-symbol math, every WAV word,
image-label science, full production acceptance, or release. Evidence receipts
and sources are SHA checked on each replay; never regenerate source materials.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence_reuse_contract import (
    AcceptedClaim, EvidenceReuseBlocked, ProposedCheck, file_sha256, preflight,
)
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_86_THREE_BOUNDED_SCIENCE_WAV_PIXEL_SCOPES_REUSED_NO_REGENERATION"
MATH_FILE=("20261102_PR449_THREE_EXACT_MATH_SOURCE_EXAMPLES/"
           "ORIGINAL_86_SLIDES5_7_8_SOURCE_TABLE_REDUCTION_SYMPY.json")
SPEECH_FILE=("20261102_PR443_THREE_SOURCE_SPOKEN_AUDIO_PIXELS/"
             "ORIGINAL_86_THREE_GENUINE_SPOKEN_SOURCE_FOCUS_QA.json")
PIXEL_FILE=("20261102_PR444_ALL41_38_REAL_FOCUS_JOINED_V2/"
            "ALL41_38_SOURCE_SPOKEN_JOINED_INDEPENDENT_QA.json")

def _ensure(ok:bool,reason:str)->None:
    if not ok:
        raise EvidenceReuseBlocked(reason)

def _load(p:Path)->dict:
    _ensure(p.is_file() and not p.is_symlink(),"Immutable specialized source receipt missing")
    return json.loads(p.read_text("utf8"))

def check_existing(original:Path,checkpoint:Path)->dict:
    """Verify independent per-scope receipts and real physical inputs without TTS/API."""
    source=Path(original).absolute()
    checkpoint=Path(checkpoint).absolute()
    source_hash,author_hash=ORIGINAL_PINS["8.6"]
    pdf=source/"source.pdf"
    slides=source/"slides.pdf"
    tex=source/"slides.tex"
    wav=source/"slide6.wav"
    inputs=(pdf,slides,tex,wav)
    _ensure(all(p.is_file() and not p.is_symlink() for p in inputs)
            and file_sha256(pdf)==source_hash
            and file_sha256(slides)==author_hash,
            "Wrong publisher/author original §8.6 source version")
    before={str(p):file_sha256(p) for p in inputs}
    paths={"math":checkpoint/MATH_FILE,"speech":checkpoint/SPEECH_FILE,
           "pixel":checkpoint/PIXEL_FILE}
    proof={k:_load(v) for k,v in paths.items()}
    science=proof["math"]
    _ensure(science.get("status")==
            "ORIGINAL_THOMAS86_THREE_SOURCE_TABLE_REDUCTION_EXAMPLES_EXACT_MATH_NONPRODUCTION"
            and science.get("original_publisher_sha256")==source_hash
            and science.get("original_author_slides_pdf_sha256")==author_hash
            and science.get("symbolic_proofs",{}).get(
                "slide8_example4_two_independent_primitives_and_composed_chain") is True
            and science.get("student_publication_authorized") is False,
            "Old original scoped exact math proof absent or unsupported")
    speech=proof["speech"]
    _ensure(speech.get("status")==
            "ORIGINAL_THOMAS86_THREE_SOURCE_REAL_PCM_SPOKEN_12_FOCUS_PILOTS_NONPRODUCTION"
            and speech.get("student_publication_authorized") is False
            and speech.get("total_real_spoken_source_highlight_events")==12,
            "Original genuine WAV word-focus pilot source evidence missing")
    speech_slide=speech["pilot_original_86_spoken_video_evidence"]["6"]
    _ensure(speech_slide["original_publisher_sha256"]==source_hash
            and speech_slide["original_author_slide_sha256"]==author_hash
            and speech_slide["original_wav_sha256"]==file_sha256(wav)
            and len(speech_slide["publisher_audio_visual_events"])==4
            and len(speech_slide["real_encoded_independent_pixel_samples"])==5
            and speech_slide["all_individual_math_figure_label_narration_complete"] is False,
            "WAV/source/decoded-frame limited proof incompatible with original source")
    # Exactly one actual off frame and four independently checked ON frames.
    events=speech_slide["publisher_audio_visual_events"]
    samples=speech_slide["real_encoded_independent_pixel_samples"]
    _ensure(samples[0]["active_math_figure_element"] is None
            and all(v==0 for v in samples[0][
                "independent_real_encoded_frame_border_counts"].values()),
            "Original unhighlighted audio video start incorrectly emphasized")
    seen=set()
    for sample in samples[1:]:
        label=sample["active_math_figure_element"]
        _ensure(label in events and label not in seen,
                "Four distinct authentic WAV-word timestamp target scenes required")
        seen.add(label)
        bounds=events[label]
        _ensure(bounds["source_publisher_mathematical_visual_identity_verified"] is True
                and 0 <= bounds["actual_start_s"] < bounds["actual_end_s"] <
                    speech_slide["original_PCM_duration_s"]
                and sample["independent_real_encoded_frame_border_counts"][label] >= 6
                and all(v==0 for k,v in sample[
                    "independent_real_encoded_frame_border_counts"].items() if k!=label),
                "One real source-spoken highlight is unsynchronized or mistaken for another")
    _ensure(seen==set(events),"Original 4 WAV source-graphic events incomplete")
    pilot=paths["speech"].parent/"thomas86_original_slide06_realword_h264.mp4"
    _ensure(pilot.is_file() and not pilot.is_symlink()
            and file_sha256(pilot)==speech_slide["encoded_original_video_sha256"],
            "Physical genuine original spoken pilot H264 altered")
    movie=proof["pixel"]
    parts=movie.get("source_8_6_actual_joined_H264_parts",[])
    _ensure(movie.get("status")==
            "ORIGINAL_THOMAS_ALL41_38_SOURCE_SPOKEN_SLIDES_47_REAL_FOCUS_EVENT_SAMPLES_NONPRODUCTION"
            and movie.get("student_publication_authorized") is False
            and movie.get("full_41_slide_academic_equation_figure_label_word_timing_accepted") is False
            and movie.get("new_actual_8_6_joined_original_slide_samples")==13
            and movie.get("new_actual_8_6_joined_spoken_element_samples")==21
            and len(movie.get("actual_source_slide_pixel_qa",[]))==13
            and len(movie.get("actual_original_spoken_highlight_pixel_qa",[]))==21
            and len(parts)==2,
            "Previous actual decoded original §8.6 joined video proof missing")
    joined=[]
    for part in parts:
        p=paths["pixel"].parent/f"THOMAS_8.6_38_FOCUS_SOURCE_QA_part{part['part']:02d}.mp4"
        _ensure(p.is_file() and not p.is_symlink()
                and part["mp4_sha256"]==file_sha256(p)
                and 0<part["real_encoded_seconds"]<600,
                "Previously independently accepted actual H264 media altered")
        joined.append({"part":part["part"],"sha256":file_sha256(p)})
    _ensure(all(x["independent_decoded_yellow_border_count"]>=6 for x in
                movie["actual_original_spoken_highlight_pixel_qa"]),
            "Full joined source-spoken actual pixel evidence omitted")
    _ensure(before=={str(p):file_sha256(p) for p in inputs},
            "Publisher original/author/PCM changed during reuse preflight")
    return {
        "status":STATUS,
        "original_publisher_source_sha256":source_hash,
        "original_author_slides_sha256":author_hash,
        "accepted_scopes":{
            "selected_exact_reduction_math":{
                "previous_pr":"#449","verification_scope":
                    "slide8_example4_tan5_two_step_exact_math",
                "artifact_sha256":file_sha256(tex),
                "physical_previous_receipt_sha256":file_sha256(paths["math"]),
                "reused_existing_pass_not_newly_recalculated":True,
                "all_other_equation_science_accepted":False},
            "sampled_original_WAV_word_to_visual":{
                "previous_pr":"#443","verification_scope":
                    "slide6_four_real_source_spoken_focus_events",
                "artifact_sha256":file_sha256(wav),
                "physical_previous_receipt_sha256":file_sha256(paths["speech"]),
                "original_encoded_pilot_sha256":file_sha256(pilot),
                "reused_existing_pass_not_newly_recalculated":True,
                "all_spoken_phonemes_approved":False},
            "actual_joined_mp4_decoded_source_pixels":{
                "previous_pr":"#444","verification_scope":
                    "section86_thirteen_slides_twentyone_focus_samples",
                "artifact_sha256":joined[0]["sha256"],
                "physical_previous_receipt_sha256":file_sha256(paths["pixel"]),
                "both_original_joined_parts":joined,
                "reused_existing_pass_not_newly_recalculated":True,
                "full_all_element_encoded_media_approved":False},
        },
        "all_math_WAV_and_encoded_pixels_completely_certified":False,
        "student_publication_authorized":False,
    }

def decision_for_domain(*,ledger:Path,original:Path,checkpoint:Path,
                        domain:str,requested_scope:str|None=None):
    """Use a verified, immutable domain receipt to suppress only duplicate QA.

    Fresh input hashes and previous receipt SHA are checked on every call.
    Publication remains false even if all three narrow scopes can be reused.
    """
    scopes={
        "math":("selected_exact_reduction_math",
                "slide8_example4_tan5_two_step_exact_math",
                "original_scoped_symbolic_v1"),
        "audio":("sampled_original_WAV_word_to_visual",
                 "slide6_four_real_source_spoken_focus_events",
                 "original_scoped_audio_word_timing_v1"),
        "video":("actual_joined_mp4_decoded_source_pixels",
                 "section86_thirteen_slides_twentyone_focus_samples",
                 "original_scoped_encoded_pixel_v1"),
    }
    _ensure(domain in scopes,"Unsupported source-specific QA reuse domain")
    field,accepted_scope,standard=scopes[domain]
    original=Path(original).absolute()
    checkpoint=Path(checkpoint).absolute()
    ledger=Path(ledger).absolute()
    existing=_load(ledger)
    _ensure(existing.get("status")==STATUS
            and existing.get("student_publication_authorized") is False
            and existing.get("all_math_WAV_and_encoded_pixels_completely_certified") is False,
            "Missing or falsely promoted bounded original-source reuse evidence")
    source_hash,author_hash=ORIGINAL_PINS["8.6"]
    _ensure(file_sha256(original/"source.pdf")==source_hash
            and file_sha256(original/"slides.pdf")==author_hash,
            "Previously accepted source/author changed")
    saved=existing["accepted_scopes"][field]
    if domain=="math": artifact=original/"slides.tex"
    elif domain=="audio": artifact=original/"slide6.wav"
    else:
        artifact=(checkpoint/"20261102_PR444_ALL41_38_REAL_FOCUS_JOINED_V2"/
                  "THOMAS_8.6_38_FOCUS_SOURCE_QA_part01.mp4")
    _ensure(artifact.is_file() and not artifact.is_symlink()
            and saved["artifact_sha256"]==file_sha256(artifact),
            "Frozen independently verified mathematical/WAV/video artifact changed")
    history=[AcceptedClaim(
        component_id="Thomas original §8.6 domain-scoped "+domain,
        scope=accepted_scope, standard=standard,
        source_sha256=source_hash, author_sha256=author_hash,
        artifact_sha256=file_sha256(artifact),
        receipt_path=ledger, receipt_sha256=file_sha256(ledger),
        evidence_claim_path=("accepted_scopes",field,
                             "reused_existing_pass_not_newly_recalculated"),
        previous_pr=saved["previous_pr"])]
    return preflight(ProposedCheck(
        component_id=history[0].component_id,
        scope=requested_scope or accepted_scope,standard=standard,
        source_sha256=source_hash,author_sha256=author_hash,
        artifact_sha256=file_sha256(artifact)),history)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    _ensure(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.original.absolute()),
            "Prior source cannot be changed or overwrite previous review receipts")
    result=check_existing(a.original,a.checkpoint)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":result["status"],
                      "reused_domains":list(result["accepted_scopes"]),
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
