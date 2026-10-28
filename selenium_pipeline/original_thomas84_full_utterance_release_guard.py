"""Original-text utterance coverage and fail-closed lecture release guard.

No transcript words or visual coordinates are invented. A pixel-verified
MP4 cannot become student-ready without independent math source semantics
and full original-narration-to-element coverage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA, require
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences

ALLOWED_AUDIT_STATUS=(
 "TWO_REAL_FULL_8_4_MP4S_29_CANDIDATES_INDEPENDENTLY_REAUDITED_NO_RELEASE")
CANDIDATE_STATUS="REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
PCM_STATUS="REVIEW_ONLY_REAL_SOURCE_16_WAV_29_PDF_CANDIDATE_SAMPLE_PLAN"

def release_eligible(summary:dict)->bool:
    """Minimal *necessary* eligibility gate, never sufficient for publication."""
    return (
        summary.get("actual_independently_audited_complete_videos")==2
        and summary.get("historical_utterances_with_no_element_mapping")==0
        and summary.get("historical_utterances_not_semantically_approved")==0
        and summary.get("corrected_slide4_source_math_accepted") is True
        and summary.get("all_source_audio_video_consistency_accepted") is True
        and summary.get("full_mathematics_independent_source_accepted") is True
        and summary.get("all_utterance_element_synchronization_accepted") is True
        and summary.get("actual_each_video_under_600s") is True
    )

def classify_utterance(segment:dict)->dict:
    timed=segment.get("actual_recorded_word_start_second") is not None and (
        segment.get("actual_recorded_word_end_second") is not None)
    mapped=segment.get("unique_target_review_priority") is True
    require(segment.get("eligible_for_final_student_highlight") is False
            and segment.get("speech_to_visible_math_semantics_approved") is False
            and (not mapped or (timed and bool(segment.get("candidate_targets")))),
            "Cannot silently promote provisional PDF geometry to academic approval")
    if not timed:
        reason="NO_INDEPENDENT_ACOUSTIC_WORD_TIMING"
    elif not mapped:
        reason="NO_UNAMBIGUOUS_VISIBLE_ORIGINAL_PDF_TARGET"
    else:
        reason="PDF_TARGET_CANDIDATE_NOT_MATH_SEMANTICALLY_APPROVED"
    return {"sentence_index":segment["sentence_index"],
            "original_narration_fragment_sha256":
                segment["spoken_original_fragment_sha256"],
            "actual_audio_word_timing_present":bool(timed),
            "provisional_original_pdf_target":
                segment["candidate_targets"][0]["original_pdf_element_id"]
                if mapped else None,
            "release_blocker_reason":reason,
            "source_math_semantics_approved":False,
            "student_release_eligible":False}

def build_coverage(*,original:Path,candidates:Path,plan:Path,
                   independent_audit:Path,out:Path)->dict:
    root=Path(original).resolve()
    c=Path(candidates).resolve()
    p=Path(plan).resolve()
    a=Path(independent_audit).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(x.is_file() and not x.is_symlink()
            for x in (c,p,a)) and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Read-only original evidence or external receipt missing")
    records=json.loads(c.read_text(encoding="utf8"))
    timeline=json.loads(p.read_text(encoding="utf8"))
    actual=json.loads(a.read_text(encoding="utf8"))
    require(records.get("status")==CANDIDATE_STATUS
            and timeline.get("status")==PCM_STATUS
            and actual.get("status")==ALLOWED_AUDIT_STATUS
            and records.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and timeline.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and actual.get("original_source_sha256")==EXPECTED_SOURCE_SHA
            and actual.get("student_publication_authorized") is False
            and actual.get("student_release_accepted_videos")==0
            and actual.get("real_provisional_original_pdf_highlights_reverified")==29
            and timeline.get("source_candidate_receipt_sha256")==file_hash(c)
            and actual.get("all_16_original_PCM_WAVs_byte_verified") is True,
            "Missing direct verified original narration and real encoded media evidence")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Not the protected textbook original")
    tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    require([s.get("slide") for s in tts["slides"]]==list(range(1,18)),
            "Protected original 17 slide narration ordering changed")
    historical=[]
    missing=[]
    mapped=[]
    for slide in records["slides"]:
        index=slide["slide"]
        sentences,_=tokenize_reference_sentences(tts["slides"][index-1]["tts_text"])
        entries=slide["candidate_segments"]
        require(len(sentences)==len(entries),"Saved source sentence count drift")
        proof=[]
        for unit,source in zip(entries,sentences):
            require(unit["sentence_index"]==source["sentence_index"]
                    and unit["spoken_original_fragment_sha256"]==
                    source["narration_fragment_sha256"],
                    "Actual original narration hash mismatch")
            info=classify_utterance(unit)
            if info["provisional_original_pdf_target"] is None:
                missing.append({"slide":index,**info})
            else:
                mapped.append({"slide":index,**info})
            proof.append(info)
        historical.append({"slide":index,"source_utterances":len(proof),
                           "provisional_target_count":sum(
                               bool(x["provisional_original_pdf_target"]) for x in proof),
                           "utterances":proof,
                           "complete_math_semantic_approval":False})
    require(len(historical)==16
            and sum(x["source_utterances"] for x in historical)==66
            and len(mapped)==29 and len(missing)==37,
            "Real §8.4 history drift or complete coverage incorrectly claimed")
    late_no_times=sum(not m["actual_audio_word_timing_present"] for m in missing)
    status={
        "schema_version":1,
        "status":"TWO_REAL_FULL_8_4_VIDEOS_66_HISTORIC_SENTENCES_37_UNMAPPED_RELEASE_BLOCKED",
        "actual_independently_audited_complete_videos":2,
        "historical_original_PCM_WAVs":16,
        "historical_original_narration_utterances":66,
        "historical_utterances_with_provisional_pdf_mapping":len(mapped),
        "historical_utterances_with_no_element_mapping":len(missing),
        "historical_unmapped_sentences_without_acoustic_timestamps":late_no_times,
        "historical_utterances_not_semantically_approved":66,
        "corrected_slide4_source_math_accepted":False,
        "all_source_audio_video_consistency_accepted":True,
        "full_mathematics_independent_source_accepted":False,
        "all_utterance_element_synchronization_accepted":False,
        "actual_each_video_under_600s":all(
            0<x["duration_s"]<600 for x in actual["verified_original_mp4_parts"]),
        "student_publication_authorized":False,
        "actual_completely_verified_source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "independent_real_media_audit_sha256":file_hash(a),
        "original_16_pcm_plan_sha256":file_hash(p),
        "historical_source_utterances":historical,
        "original_unmapped_spoken_utterances":missing,
    }
    require(release_eligible(status) is False,
            "Partial technical approval cannot be release")
    status["release_eligible"]=False
    for name in ("source.pdf","slides.pdf","script_tts.json"):
        require((root/name).is_file(),
                "Missing original source coverage document")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original textbook altered during coverage audit")
    with dest.open("x",encoding="utf8") as output:
        json.dump(status,output,indent=2,ensure_ascii=False);output.write("\n")
    return status

def main():
    p=argparse.ArgumentParser()
    for key in ("original","candidates","plan","independent_audit","out"):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    result=build_coverage(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("historical_source_utterances",
                                   "original_unmapped_spoken_utterances")},
                     indent=2))
if __name__=="__main__":main()
