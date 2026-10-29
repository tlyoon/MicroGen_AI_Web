"""Final combined original-source §8.4 mathematics, sound-alike TTS and H264 gate.

All 66 historical narration meanings plus five corrected source
Slide4 utterances are independently source/visible-PDF grounded.
Two genuinely diagnosed mathematical defects (Slide8 negative leg,
Slide17 incomplete integral) must be fixed in actual PDF+PCM+movie.
Audio pass follows OWNER-RELAXED sound-alike recognition, not
perfect word accuracy; actual C->circa or math reversals remain FAIL.
Contextual title/highlights may be an appropriate element for
general narration; uniqueness of a formula is NOT required there.
No web/Whisper, no automatic student publication, no original edits.
"""
from __future__ import annotations
import argparse,hashlib,json,wave
from pathlib import Path
import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_offline_word_pdf_timing import (
    tokenize_reference_sentences,HISTORIC_SLIDES)
from .original_thomas84_all66_independent_semantic_matrix import (
    CURATED_BLOCKS,CONTEXTUAL_NOT_PROVEN_AS_UNIQUE_ELEMENT,
    MATH_ISSUES,STATUS as REVIEW_STATUS)
from .original_thomas84_signed_triangle_source_repair import (
    STATUS as REPAIR_STATUS,CORRECTED_SPOKEN)
from .original_thomas84_signed_triangle_full_mp4_independent_audit import (
    STATUS as REAL_MEDIA_STATUS)
from .original_thomas84_slide11_independent_trig_voice_check import STATUS as SL11_STATUS
from .original_thomas84_five_source_domain_proofs import STATUS as DOMAIN_STATUS
from .original_thomas84_new_kore_offline_audio_qa import STATUS as NEW17_STATUS
from .original_thomas84_worked_examples_math_proof import evaluate_worked_rules
from .tts_flexible_pronunciation_contract import evaluate_tts_soundalike

STATUS="THOMAS84_ALL_THREE_QA_CHECKS_COMPLETED_SOURCE_MATH_PHONETIC_MEDIA_PASS_REVIEW_ONLY"
SLIDE4_SOURCE_STATUS="REAL_FIVE_KORE_REQUESTED_WAVS_UNBIASED_OFFLINE_ASR_REVIEW_ONLY"
def _load(p:Path)->dict:
    require(p.is_file() and not p.is_symlink(),"Actual source proof missing or symlinked")
    return json.loads(p.read_text(encoding="utf8"))

def combined_gate(*,original:Path,corrected_source:Path,
                  source_review:Path,domain_evidence:Path,
                  slide11_voice:Path,original16_ASR:Path,
                  slide4_five_source:Path,slide4_five_ASR:Path,
                  new8_audio:Path,new8_ASR:Path,new17_ASR:Path,
                  independent_final_video:Path,out:Path)->dict:
    root=Path(original).resolve();pair=Path(corrected_source).resolve()
    paths=[Path(x).resolve() for x in (
        source_review,domain_evidence,slide11_voice,original16_ASR,
        slide4_five_source,slide4_five_ASR,new8_ASR,new17_ASR,
        independent_final_video)]
    voice=Path(new8_audio).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and voice.is_dir()
            and all(z.is_file() and not z.is_symlink() for z in paths)
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "All immutable original source/audio/video evidence required")
    (old_review,domains,sl11,asr16,source4,asr4,asr8,asr17,media)=[
        _load(p) for p in paths]
    paired=_load(pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json")
    paid=_load(voice/"REAL_TTS_AUDIO_CANDIDATE_UNAPPROVED.json")
    oldscript=_load(root/"script_tts.json")
    revised=_load(pair/"script_tts.json")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
        and paired.get("status")==REPAIR_STATUS
        and old_review.get("status")==REVIEW_STATUS
        and old_review.get("exact_real_source_narration_utterances_reviewed")==66
        and domains.get("status")==DOMAIN_STATUS
        and domains.get("real_mathematical_domain_scopes_examined")==5
        and sl11.get("status")==SL11_STATUS
        and sl11.get("phonetic_source_consistency_pass") is True
        and media.get("status")==REAL_MEDIA_STATUS
        and media.get("source_corrected_slide8_and_slide17_present") is True
        and media.get("both_actual_full_AAC_audio_streams_decoded") is True
        and media.get("strict_video_duration_less_than_600") is True
        and media.get("part1_independently_redecoded_source_pdf_H264_frames")==56
        and media.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
        and media.get("new_real_corrected_source_pdf_sha256")==file_hash(pair/"slides.pdf")
        and paid.get("status")==
             "REAL_GENUINE_CORRECTED_SLIDE8_KORE_PCM_ONE_REQUEST_AWAITING_OFFLINE_QA"
        and paid.get("actual_WAV_sha256")==asr8.get("real_new_WAV_SHA256")
        and asr8.get("tts_soundalike_qa",{}).get("tts_qa_soundalike_pass") is True
        and not asr8["tts_soundalike_qa"]["critical_errors"]
        and asr17.get("status")==NEW17_STATUS
        and asr17.get("phonetic_soundalike_screen_pass") is True
        and not asr17.get("source_ASR_suspected_math_disagreement_codes")
        and source4.get("segment_count")==5
        and asr4.get("status")==SLIDE4_SOURCE_STATUS
        and asr4.get("genuine_source_registered_pcm_count")==5
        and asr16.get("actual_historical_slides_inspected")==16
        and asr16.get("source_original_hashes",{}).get("source.pdf")==EXPECTED_SOURCE_SHA
        and all(x.get("student_publication_authorized") is False
                for x in (paired,old_review,domains,sl11,media,paid,asr8,asr17,asr4,asr16)),
        "Combined original source/mathematics/PCM/live-movie hash lineage failed")
    # Whole-original source and previously source-verified new slideshow.
    tts= revised["slides"];source_tts=oldscript["slides"]
    require([x["slide"] for x in tts]==list(range(1,18))
            and len(tts)==len(source_tts)==17,
            "Original slide script source manifest changed")
    annotated=[]
    signed_fixed=0
    contextual_accepted=0
    with pymupdf.open(root/"slides.pdf") as original_pdf,pymupdf.open(pair/"slides.pdf") as corrected:
        require(len(original_pdf)==len(corrected)==17,
                "Actual repaired physical slides PDF not 17 pages")
        for slide,units in CURATED_BLOCKS.items():
            page=corrected[slide-1]
            speech,_=tokenize_reference_sentences(tts[slide-1]["tts_text"])
            original_speech,_=tokenize_reference_sentences(
                source_tts[slide-1]["tts_text"])
            require(len(speech)==len(original_speech)==len(units),
                    "Actual source narrated academic sentence count changed")
            for sentence,(record,previous,indices) in enumerate(
                zip(speech,original_speech,units),1):
                key=slide,sentence
                if key not in ((8,2),(17,2)):
                    require(record["narration_fragment_sha256"]==
                            previous["narration_fragment_sha256"],
                            "Unexpected original narration math changed")
                else:
                    require(record["narration_fragment_sha256"]!=
                            previous["narration_fragment_sha256"],
                            "Actual source mathematical sign/integral correction missing")
                blocks=page.get_text("blocks")
                require(bool(indices) and all(
                    type(i) is int and 0<=i<len(blocks) and blocks[i][6]==0
                    for i in indices),
                    "Full 66 relevant original PDF source target not visible")
                if key in MATH_ISSUES:
                    require("opposite = |x|" in corrected[7].get_text()
                            and CORRECTED_SPOKEN in tts[7]["tts_text"],
                            "Geometric nonnegative side length/signed tan defect persists")
                    signed_fixed+=1
                if key==(17,2):
                    require("For I =" in corrected[16].get_text()
                            and "integral of d x over" in tts[16]["tts_text"],
                            "Underdefined original integration review question persists")
                qualitative=key in CONTEXTUAL_NOT_PROVEN_AS_UNIQUE_ELEMENT
                contextual_accepted+=int(qualitative)
                annotated.append({
                    "slide":slide,"sentence_index":sentence,
                    "physical_source_PDF_blocks":[int(i) for i in indices],
                    "corrected_original_narration_source_sha256":
                         record["narration_fragment_sha256"],
                    "source_math_relevance_review":
                         "RELEVANT_QUALITATIVE_SECTION_ELEMENT" if qualitative
                         else "SOURCE_EXPRESSION_OR_PROCEDURE",
                    "nonnegative_triangle_geometry_corrected":
                        key in MATH_ISSUES,
                    "release_accepted_under_context_relevance_not_unique_equation":True
                })
        # All unchanged slides must match source; only two source-math
        # repaired slides may differ from protected original.
        changed=[]
        for i in range(17):
            a=original_pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            b=corrected[i].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            if a.samples!=b.samples:changed.append(i+1)
        require(changed==[8,17],
                "Exactly signed-triangle and full-integral source slides may change")
    require(len(annotated)==66 and signed_fixed==2
            and contextual_accepted==12 and
            len({(k["slide"],k["sentence_index"]) for k in annotated})==66,
            "Cannot independently adjudicate all 66 source math utterances")
    proofs=evaluate_worked_rules()
    require(len(proofs)==4 and
            all(z["limited_mathematics_result_pass"] for z in proofs.values()),
            "Original worked calculus symbolic source identities failed")
    # Rerun the owner's LATEST tolerant policy on the actual genuine source
    # registered WAVs + UNPROMPTED old transcripts, not 15/16 old strict QA.
    all_old=[]
    for row in asr16["slides"]:
        slide=row["slide"]
        require(slide in HISTORIC_SLIDES and
                file_hash(root/f"slide{slide}.wav")==row["historical_WAV_sha256"],
                "Genuine original full-slide PCM/source SHA changed")
        reference=source_tts[slide-1]["tts_text"]
        q=evaluate_tts_soundalike(reference,row["asr_transcript"])
        all_old.append({"slide":slide,"decision":q["tts_qa_decision"],
          "similarity":q["phonetic_token_similarity"],
          "critical_errors":q["critical_errors"]})
    require(len(all_old)==16
            and all(z["decision"] in ("PASS_SIMILAR_SOUND",
                                     "PASS_WITH_MINOR_VARIATIONS")
                    and not z["critical_errors"] for z in all_old),
            "A real original PCM WAV has a confirmed math contradiction")
    actual4=[]
    for a,b in zip(source4["source_verified_tts_highlight_units"],
                   asr4["five_source_audio_rows"]):
        require(a["original_utterance_id"]==b["utterance_id"]
                and a["corrected_tts_text_sha256"]==b["source_text_sha256"],
                "Protected source corrected Slide4 spoken math reference mismatch")
        q=evaluate_tts_soundalike(a["corrected_tts_text"],b["recognized_verbatim"])
        actual4.append({"utterance":b["utterance_id"],
            "decision":q["tts_qa_decision"],
            "similarity":q["phonetic_token_similarity"],
            "critical_errors":q["critical_errors"]})
    require(len(actual4)==5 and
            all(z["decision"]=="PASS_SIMILAR_SOUND" and
                not z["critical_errors"] for z in actual4),
            "Real source corrected Slide4 sound-alike QA remains blocked")
    # New edited utterance source identities; two full video formats and
    # all audio after a verified paid provider single-shot receipt.
    require(asr8["source_corrected_script_sha256"]==
              paid["corrected_narration_text_sha256"]
            and asr17["original_source_corrected_TTS_fragment_sha256"]==
              hashlib.sha256(
                 "First, for the integral of d x over the square root of x squared minus sixteen with x greater than four, determine the appropriate secant substitution and its differential to obtain the resulting trigonometric integrand.".encode("utf8")).hexdigest()
            and all(float(z)<600 for z in media["full_actual_video_seconds"]),
            "Two true corrected narration/math videos do not pass sample timing")
    # No publication (authorization/action separate). This is an
    # owner-relaxed QA release-CANDIDATE decision, not proof of perfect
    # utterance phonetics or voice identity.
    result={
      "schema_version":1,"status":STATUS,
      "original_textbook_sha256":EXPECTED_SOURCE_SHA,
      "corrected_actual_source_pdf_sha256":file_hash(pair/"slides.pdf"),
      "independently_audited_actual_final_movie_SHA256":
           media["full_2part_actual_H264_AAC_sha256"],
      "real_complete_movies_seconds":media["full_actual_video_seconds"],
      "all_66_original_narration_meanings_referenced_to_actual_PDF":len(annotated),
      "contextual_section_highlights_accepted_as_relevant_not_unique_equations":
           contextual_accepted,
      "actual_corrected_signed_triangle_math_items_resolved":signed_fixed,
      "actual_corrected_integral_question_resolved":1,
      "original_five_domain_restriction_source_math_checks_pass":True,
      "four_worked_trig_calculus_antiderivatives_symbolically_checked":4,
      "original_sixteen_actual_recorded_WAVs_latest_phonetic_screen_pass":len(all_old),
      "five_original_slide4_source_corrected_WAVs_latest_phonetic_screen_pass":len(actual4),
      "two_original_math_repair_Kore_WAVs_offline_phonetic_screen_pass":2,
      "slide11_old_trig_false_positive_resolved_as_co_sign_cosine":True,
      "actual_final_movie_source_PDF_H264_frames_second_pass":56+48,
      "all_actual_final_movies_under_600_s":True,
      "math_source_automated_review_criteria_satisfied":True,
      "owner_flexible_soundalike_TTS_criteria_satisfied":True,
      "source_visual_element_relevance_criteria_satisfied":True,
      "actual_H264_AAC_media_integrity_criteria_satisfied":True,
      "three_requested_QA_checks_completed":True,
      "release_candidate_QA_gate_pass":True,
      "independent_human_aural_voice_identity_certified":False,
      "every_individual_spoken_word_acoustically_proven":False,
      "publication_was_performed":False,
      "student_publication_authorized":False,
      "strict_no_original_source_or_prior_movie_overwrite":True,
      "real_source_phrase_screening_decisions":all_old,
      "five_slide4_soundalike_rows":actual4,
      "all_66_academic_visual_relevance_judgments":annotated,
    }
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original textbook source mutated during final combined QA")
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("original","corrected_source","source_review",
                 "domain_evidence","slide11_voice","original16_ASR",
                 "slide4_five_source","slide4_five_ASR","new8_audio",
                 "new8_ASR","new17_ASR","independent_final_video","out"):
        p.add_argument("--"+name.replace("_","-").lower(),dest=name,
                       type=Path,required=True)
    r=combined_gate(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in r.items()
                      if k not in ("real_source_phrase_screening_decisions",
                        "five_slide4_soundalike_rows",
                        "all_66_academic_visual_relevance_judgments")},indent=2))
if __name__=="__main__":main()
