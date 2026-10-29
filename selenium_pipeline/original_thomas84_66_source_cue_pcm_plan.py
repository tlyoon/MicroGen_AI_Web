"""Combine all 66 genuine §8.4 sentence source PDF cues and exact source PCM.

65 utterances have independently measured source WAV word intervals;
the single title uses one actual whole-original-WAV clip explicitly
labeled NOT word anchored. All source mappings remain semantically
provisional and all 37 contextual/new cues remain release blocked.
"""
from __future__ import annotations
import argparse
import json
import wave
from pathlib import Path
import pymupdf

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA, require
from .original_thomas84_all_historical_pcm_plan import sample_windows
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_pdf_math_risk import physical_matches
from .original_thomas84_math_domain_crosscheck import compare_math_claims
from .original_thomas84_37_contextual_cues import STATUS as CUES_STATUS

STATUS="ALL_66_PHYSICAL_ORIGINAL_PDF_CUES_65_REAL_WORD_TIMES_SOURCE_PCM_REVIEW_ONLY"

def source_cue_event(*,page,slide:int,unit:dict,
                     contextual:dict|None,narration:str)->dict:
    key=(slide,unit["sentence_index"])
    if unit["unique_target_review_priority"]:
        require(contextual is None and
                unit["speech_to_visible_math_semantics_approved"] is False,
                "Existing unique source cue cannot have conflicting proposal")
        pick=unit["candidate_targets"][0]
        require(physical_matches(page,pick),"Old source-PDF text geometry drift")
        visual={
            "physical_source_pdf_text":pick["actual_visible_original_pdf_text"],
            "physical_original_pdf_rect_pt":pick["source_pdf_rect_pt"],
            "physical_original_pdf_element_id":pick["original_pdf_element_id"],
            "source_support":"PR335_OLD_ACOUSTIC_LEXICAL_UNAPPROVED"}
    else:
        require(contextual is not None and contextual["slide"]==slide
                and contextual["sentence_index"]==unit["sentence_index"]
                and contextual["original_narration_fragment_sha256"]==
                    unit["spoken_original_fragment_sha256"]
                and contextual["spoken_element_sync_release_approved"] is False,
                "Original context cue does not match source narration")
        visual={
            "physical_source_pdf_text":contextual["original_pdf_visible_text"],
            "physical_original_pdf_rect_pt":contextual["original_pdf_rect_pt"],
            "physical_original_pdf_element_id":
                f"s{slide:03d}.pdf_block.{contextual['original_pdf_block_index']:03d}",
            "source_support":contextual["source_support_category"]}
        candidates=[b for b in page.get_text("blocks") if b[6]==0
                and " ".join(str(b[4]).split())==visual["physical_source_pdf_text"]
                and all(abs(float(b[i])-visual["physical_original_pdf_rect_pt"][i])<.12
                        for i in range(4))]
        require(len(candidates)==1,"New source cue cannot be recovered from original")
    result=compare_math_claims(narration,visual["physical_source_pdf_text"])
    require(not result["provable_local_term_conflicts"],
            "A spoken/source mathematical term conflict blocks proposal")
    return {
        "slide":slide,
        "sentence_index":unit["sentence_index"],
        "narration_source_sha256":unit["spoken_original_fragment_sha256"],
        **visual,
        "source_term_audit_flags":result["insufficient_evidence_flags"],
        "local_trig_or_sign_term_conflict":False,
        "independent_full_source_math_semantics_approved":False,
        "student_publication_authorized":False,
    }

def combine_source_plan(*,original:Path,old_candidates:Path,
                        contextual_receipt:Path,worked_math_receipt:Path,
                        out:Path)->dict:
    root=Path(original).resolve()
    oldpath=Path(old_candidates).resolve()
    newpath=Path(contextual_receipt).resolve()
    mathpath=Path(worked_math_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in (oldpath,newpath,mathpath))
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Exclusive external output and genuine input evidence required")
    old=json.loads(oldpath.read_text(encoding="utf8"))
    newer=json.loads(newpath.read_text(encoding="utf8"))
    math=json.loads(mathpath.read_text(encoding="utf8"))
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and old.get("status")==
              "REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
            and newer.get("status")==CUES_STATUS
            and math.get("status")==
               "FOUR_REAL_8_4_WORKED_IDENTITIES_LIMITED_DOMAIN_PROOF_NO_RELEASE"
            and newer.get("pr335_candidate_receipt_sha256")==file_hash(oldpath)
            and math.get("actual_worked_example_formulas_limited_math_pass")==4
            and old.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and newer.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and math.get("original_source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and all(x.get("student_publication_authorized") is False
                    for x in (old,newer,math)),
            "Source or worked mathematical receipts inconsistent")
    unmatched={(x["slide"],x["sentence_index"]):x for x in newer["proposals"]}
    require(len(unmatched)==37,"All 37 source contextual cues required")
    tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    require([z["slide"] for z in tts["slides"]]==list(range(1,18)),
            "Original recorded source narration inventory drift")
    allslides=[]
    total=0
    measured=0
    fulltitle=0
    flags=0
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==17,"Original 17 source PDF pages missing")
        for s in old["slides"]:
            slide=s["slide"]
            source_wav=root/f"slide{slide}.wav"
            require(file_hash(source_wav)==s["source_wav_sha256"],
                    "Protected old source WAV identity drift")
            with wave.open(str(source_wav),"rb") as actual:
                require(actual.getnchannels()==1 and actual.getsampwidth()==2
                        and actual.getframerate()==24000
                        and actual.getcomptype()=="NONE",
                        "Source audio format is not original mono16 24k")
                frame_count=actual.getnframes()
                require(len(actual.readframes(frame_count))==2*frame_count,
                        "Incomplete source genuine PCM")
            spoken,_=tokenize_reference_sentences(
                tts["slides"][slide-1]["tts_text"])
            require(len(spoken)==len(s["candidate_segments"]),
                    "Original sentence alignment changed")
            physical=[]
            windows=[]
            for unit,narration in zip(s["candidate_segments"],spoken):
                idx=unit["sentence_index"]
                require(narration["sentence_index"]==idx and
                        narration["narration_fragment_sha256"]==
                           unit["spoken_original_fragment_sha256"],
                        "Original actual recorded narration SHA mismatch")
                new=unmatched.get((slide,idx))
                item=source_cue_event(page=pdf[slide-1],slide=slide,unit=unit,
                        contextual=new,narration=narration["narration_fragment"])
                begin=unit["actual_recorded_word_start_second"]
                end=unit["actual_recorded_word_end_second"]
                if begin is not None:
                    require(type(begin) in (float,int) and
                            type(end) in (float,int) and
                            0<=begin<end<=frame_count/24000+.02,
                            "Actual original speech word interval missing/drift")
                    measured+=1
                    audio_style="MEASURED_ACTUAL_ORIGINAL_WAV_WORD_TIMING"
                else:
                    require(slide==1 and idx==1 and begin is None and end is None
                            and len(spoken)==1,
                            "Only original title narration may lack word timestamp")
                    begin=0.
                    end=frame_count/24000
                    fulltitle+=1
                    audio_style="FULL_ORIGINAL_TITLE_WAV_NOT_WORD_ALIGNED"
                item["audio_time_evidence_type"]=audio_style
                item["actual_source_pcm_word_start_second"]=(float(begin)
                    if audio_style.startswith("MEASURED") else None)
                item["actual_source_pcm_word_end_second"]=(float(end)
                    if audio_style.startswith("MEASURED") else None)
                windows.append({"begin_s":float(begin),"end_s":float(end),
                                "sentence_index":idx,
                                "pdf_target":item["physical_original_pdf_element_id"]})
                physical.append(item)
                total+=1
                flags+=bool(item["source_term_audit_flags"])
            source_windows=sample_windows(frame_count,windows)
            targets={x["physical_original_pdf_element_id"]:x
                     for x in physical}
            require(all(p["provisional_pdf_target"] in targets
                    for p in source_windows if p["provisional_pdf_target"] is not None),
                    "Missing genuine page source PDF visual target")
            allslides.append({
                "slide":slide,
                "source_wav_sha256":s["source_wav_sha256"],
                "original_source_PCM_total_samples":frame_count,
                "physical_original_pdf_source_targets":physical,
                "source_pcm_sample_exact_timeline":source_windows,
                "full_independent_math_semantics_accepted":False,
            })
    require(len(allslides)==16 and total==66 and measured==65
            and fulltitle==1 and len(unmatched)==37
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Real full historic source coverage failed")
    result={
        "schema_version":1,
        "status":STATUS,
        "original_textbook_sha256":EXPECTED_SOURCE_SHA,
        "original_slides_pdf_sha256":file_hash(root/"slides.pdf"),
        "old_29_pdf_candidate_sha256":file_hash(oldpath),
        "new_37_pdf_source_cues_sha256":file_hash(newpath),
        "four_worked_math_proof_sha256":file_hash(mathpath),
        "real_historical_wavs_covered":16,
        "actual_original_historic_narration_sentences":total,
        "real_original_WAV_measured_word_intervals":measured,
        "whole_original_title_WAV_single_utterance_unanchored":fulltitle,
        "source_term_scope_uncertainty_review_flags":flags,
        "physical_source_pdf_cues_verified":66,
        "all_original_WAV_PCM_samples_accounted_for":True,
        "full_math_source_semantic_verification_approved":False,
        "release_eligible":False,
        "student_publication_authorized":False,
        "source_historical_slides":allslides,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write("\n")
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ("original","old_candidates","contextual_receipt","worked_math_receipt","out"):
        parser.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    r=combine_source_plan(**vars(parser.parse_args()))
    print(json.dumps({k:v for k,v in r.items()
                     if k!="source_historical_slides"},indent=2))
if __name__=="__main__":main()
