"""Independent source/textbook cross-review of 66 §8.4 source cue units.

Fail closed: mechanical source provenance and correct spot formulas are NOT
equivalent to comprehensive academic semantics or audio pronunciation.
Prove the generated slide17 exercise is underdetermined by constructing
two different integrands sharing the exact same stated square-root form.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf
import sympy as S
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_66_source_cue_pcm_plan import STATUS as PLAN_STATUS
from .original_thomas84_composite_source_semantic_corrections import (
    STATUS as REPAIR_STATUS,actual_source_composite)
from .original_thomas84_historic_audio_soundalike_audit import (
    STATUS as AUDIO_STATUS)
from .original_thomas84_worked_examples_math_proof import (
    evaluate_worked_rules)
from .original_thomas84_offline_word_pdf_timing import (
    tokenize_reference_sentences)
from .automatic_math_semantic_qa import inspect_math_semantics

STATUS="ALL66_SOURCE_PDF_NARRATION_MATH_RISK_AUDIT_ONE_UNDERSPECIFIED_EXERCISE_NO_RELEASE"

def underdetermined_integral_proof()->dict:
    """Same radical sqrt(x²−16), different numerator => different u integrand."""
    u=S.symbols("u",positive=True,real=True)
    x=S.Integer(4)*S.sec(u)
    dx=S.diff(x,u)
    # On 0<u<pi/2 the principal positive root is 4tan(u).
    root=S.Integer(4)*S.tan(u)
    integrand1=S.trigsimp(dx/root)
    integrand2=S.trigsimp(x*dx/root)
    require(S.trigsimp(integrand1-S.sec(u))==0
            and S.trigsimp(integrand2-4*S.sec(u)**2)==0
            and S.trigsimp(x*x-16-root*root)==0
            and S.simplify((integrand1-integrand2).subs(u,S.pi/4))!=0,
            "Underdetermined mathematical counterexample proof did not hold")
    return {
        "domain":"x>4, 0<u<pi/2",
        "same_given_radicand":"sqrt(x^2-16)",
        "substitution":"x=4sec(u), dx=4sec(u)tan(u)du",
        "case_a_original_integral":"integral dx/sqrt(x^2-16)",
        "case_a_transformed_integrand":"sec(u)",
        "case_b_original_integral":"integral x dx/sqrt(x^2-16)",
        "case_b_transformed_integrand":"4sec(u)^2",
        "two_distinct_valid_resulting_integrands_symbolically_proved":True,
        "therefore_no_unique_integrand_from_a_radicand_alone":True,
    }

def source_block_present(page,physical:dict)->bool:
    label=" ".join(physical["physical_source_pdf_text"].split())
    rect=physical["physical_original_pdf_rect_pt"]
    return any(b[6]==0 and " ".join(str(b[4]).split())==label
               and all(abs(float(b[i])-rect[i])<.12 for i in range(4))
               for b in page.get_text("blocks"))

def review_real_math(*,original:Path,source_plan:Path,
                     corrections:Path,spoken_audio:Path,
                     final_real_media_audit:Path,out:Path)->dict:
    root=Path(original).resolve()
    names=[Path(z).resolve() for z in
           (source_plan,corrections,spoken_audio,final_real_media_audit)]
    output=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in names) and output.parent.is_dir()
            and not output.exists()
            and not output.is_relative_to(root.parent),
            "Requires protected original source and new external evidence")
    plan,repairs,voice,media=[
        json.loads(p.read_text(encoding="utf8")) for p in names]
    require(plan.get("status")==PLAN_STATUS
            and repairs.get("status")==REPAIR_STATUS
            and voice.get("status")==AUDIO_STATUS
            and media.get("status")==
              "TWO_ACTUAL_CORRECTED_ORIGINAL_8_4_MP4S_INDEPENDENT_PHYSICAL_AUDIT_RELEASE_BLOCKED"
            and plan.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and repairs.get("protected_original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and voice.get("source_textbook_SHA256")==EXPECTED_SOURCE_SHA
            and media.get("source_original_pdf_sha256")==EXPECTED_SOURCE_SHA
            and repairs.get("original_66_source_cue_plan_sha256")==file_hash(names[0])
            and voice.get("independent_real_media_audit_sha256")==file_hash(names[3])
            and plan.get("actual_original_historic_narration_sentences")==66
            and plan.get("physical_source_pdf_cues_verified")==66
            and repairs.get("incomplete_or_wrong_context_original_cues_corrected")==10
            and voice.get("real_original_historic_WAVs_screened")==16
            and voice.get("targeted_voice_math_pronunciation_review_required")==1
            and media.get("original_pdf_frames_independently_decoded")==106
            and all(x.get("student_publication_authorized") is False
                    for x in (plan,repairs,voice,media))
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Source provenance/math/audio/media history not valid")
    proven=evaluate_worked_rules()
    require(len(proven)==4 and all(x["limited_mathematics_result_pass"]
                                  for x in proven.values()),
            "Source example antiderivative proof failed")
    signed_corrections={(q["slide"],q["sentence_index"]):q
                        for q in repairs["corrected_original_pdf_composite_focuses"]}
    require(len(signed_corrections)==10,"Ten original source math fixes not present")
    sentences=json.loads((root/"script_tts.json").read_text(encoding="utf8"))["slides"]
    items=[]
    scope_flags=[]
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==17,"Actual generated slide pages missing")
        for hist in plan["source_historical_slides"]:
            slide=hist["slide"]
            script,_=tokenize_reference_sentences(
                sentences[slide-1]["tts_text"])
            original=hist["physical_original_pdf_source_targets"]
            require(len(script)==len(original),"Source sentence or PDF elements missing")
            for recorded,cue in zip(script,original):
                key=(slide,recorded["sentence_index"])
                require(recorded["narration_fragment_sha256"]==
                            cue["narration_source_sha256"]
                        and recorded["sentence_index"]==cue["sentence_index"],
                        "Original human-readable source sentence SHA mismatch")
                fixed=signed_corrections.get(key)
                if fixed:
                    assert fixed["original_narration_fragment_sha256"]==recorded["narration_fragment_sha256"]
                    actual_source_composite(pdf[slide-1],tuple(
                        (b["original_pdf_block_index"],b["original_pdf_text"])
                        for b in fixed["original_pdf_source_blocks"]))
                    status="CORRECTED_REAL_MULTI_BLOCK_SOURCE_CUE_NOT_SEMANTICALLY_CERTIFIED"
                else:
                    require(source_block_present(pdf[slide-1],cue),
                            "Historical source mathematical cue no longer physically visible")
                    status="PHYSICAL_ORIGINAL_PDF_SINGLE_BLOCK_CUE_NOT_SEMANTICALLY_CERTIFIED"
                flag_list=cue["source_term_audit_flags"]
                if flag_list:
                    scope_flags.append({"slide":slide,
                        "sentence_index":recorded["sentence_index"],
                        "math_text_uncertainty_codes":flag_list})
                items.append({
                    "slide":slide,"sentence_index":recorded["sentence_index"],
                    "narration_sha256":cue["narration_source_sha256"],
                    "source_text_block_physically_reverified":True,
                    "source_composite_corrected":bool(fixed),
                    "provisional_math_semantic_status":status,
                    "source_term_uncertainties":flag_list,
                    "full_spoken_math_semantic_truth_certified":False,
                    "student_release_eligible":False,
                })
        page=pdf[16]
        question=" ".join(" ".join(str(b[4]).split())
                   for b in page.get_text("blocks")
                   if b[6]==0 and
                       (("For an integral containing" in b[4]) or
                        ("x2 −16 with x > 4" in b[4])))
        require("For an integral containing" in question
                and "resulting trigonometric integrand" in question
                and "x2 −16" in question,
                "Specific physically visible generated final-review question changed")
        slide17=sentences[16]["tts_text"]
        lint=inspect_math_semantics(
            "**Slide 1 [60 sec]:\n"+slide17,
            source_sha256=EXPECTED_SOURCE_SHA)
        require(any(x["rule"]==
                    "incomplete_integral_does_not_define_transformed_integrand"
                    for x in lint["findings"]),
                "Reusable pre-TTS semantic guard failed to catch real ambiguous question")
    require(len(items)==66 and
            len({(x["slide"],x["sentence_index"]) for x in items})==66
            and len(scope_flags)==5
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "66-source academic math risk inventory incomplete/drift")
    proof=underdetermined_integral_proof()
    issue={
        "slide":17,"narration_sentence_index":2,
        "source_pdf_visible_ambiguity":question,
        "mathematical_counterexample":proof,
        "severity":"BLOCKING_UNDERSPECIFIED_EXERCISE",
        "precise_source_grounded_candidate_revision":
            "Evaluate the integral of dx over sqrt(x squared minus sixteen), for x greater than four. Set x equal to four secant u, with zero less than u less than pi over two. Find dx and show the transformed integrand is secant u.",
        "requires_regenerated_slide_script_and_source_corrected_audio":True,
        "original_source_files_must_not_be_overwritten":True,
        "repair_applied_to_student_video":False
    }
    result={
        "schema_version":1,"status":STATUS,
        "original_textbook_sha256":EXPECTED_SOURCE_SHA,
        "physical_source_pdf_sha256":file_hash(root/"slides.pdf"),
        "original_PDF_source_utterances_audited":len(items),
        "selected_worked_math_families_verified_limited":len(proven),
        "old_mathematical_context_fixes_physically_rechecked":10,
        "source_inequality_scope_textual_review_flags":len(scope_flags),
        "confirmed_source_question_underdefinition_issues":1,
        "targeted_asr_only_math_voice_suspicions":1,
        "independently_audited_two_corrected_complete_MP4s":2,
        "source_underdefined_question_counterexample":issue,
        "five_domain_scope_uncertainties":scope_flags,
        "full_mathematics_academic_semantics_approved":False,
        "all_66_narration_visual_math_matches_approved":False,
        "student_publication_authorized":False,
        "student_release_accepted_videos":0,
        "source_provisional_66_sentence_decisions":items,
        "source_plan_receipt_sha256":file_hash(names[0]),
        "voice_receipt_sha256":file_hash(names[2]),
        "media_receipt_sha256":file_hash(names[3])
    }
    with output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","source_plan","corrections","spoken_audio",
                "final_real_media_audit","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    report=review_real_math(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in report.items()
                       if k not in ("source_underdefined_question_counterexample",
                                    "source_provisional_66_sentence_decisions",
                                    "five_domain_scope_uncertainties")},
                     indent=2))
if __name__=="__main__":main()
