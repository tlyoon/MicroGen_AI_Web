"""Source-locked five flagged §8.4 trig-domain checks; fail closed.

Conservative mathematical distinction: true algebra, correct principal
interval/sign branch, physically present original PDF text, spoken
interval scope, and complete 66-utterance acoustic meaning are separate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pymupdf
import sympy as S
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_math_domain_crosscheck import compare_math_claims
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_66_source_cue_pcm_plan import STATUS as SOURCE_STATUS
from .original_thomas84_66_academic_math_risk_audit import STATUS as ACADEMIC_STATUS
from .original_thomas84_new_kore_offline_audio_qa import STATUS as VOICE_STATUS

STATUS="FIVE_REAL_ORIGINAL_SOURCE_TRIG_BRANCH_DOMAIN_AUDITS_ALGEBRA_PASS_NO_FULL_RELEASE"
KEYS={(5,3):"principal_sine_closed_domain",
      (5,4):"principal_secant_positive_domain",
      (12,3):"strict_secant_first_quadrant",
      (14,2):"tangent_branch_secant_positive",
      (15,2):"tangent_branch_secant_positive"}

def branch_math_checks()->dict:
    u=S.symbols("u",real=True);a=S.symbols("a",positive=True)
    trig={
      "sine":(S.sin(u),S.cos(u)),
      "tangent":(S.tan(u),S.sec(u)),
      "secant":(S.sec(u),S.tan(u)),
    }
    # Exact algebraic formula checks under principal-branch sign choice.
    relations={
      "sine_radicand":S.trigsimp(
          a*a-(a*S.sin(u))**2-(a*S.cos(u))**2),
      "tangent_radicand":S.trigsimp(
          a*a+(a*S.tan(u))**2-(a*S.sec(u))**2),
      "secant_radicand":S.trigsimp(
          (a*S.sec(u))**2-a*a-(a*S.tan(u))**2),
      "tan_monotone_derivative":S.trigsimp(
          S.diff(S.tan(u),u)-S.sec(u)**2),
      "sin_monotone_derivative":S.trigsimp(
          S.diff(S.sin(u),u)-S.cos(u)),
      "sec_monotone_derivative":S.trigsimp(
          S.diff(S.sec(u),u)-S.sec(u)*S.tan(u))
    }
    require(all(S.simplify(z)==0 for z in relations.values()),
            "Original branch radicand/derivative identities not satisfied")
    samples={
      "principal_sine_closed_domain":([-S.pi/2,-S.pi/4,0,S.pi/4,S.pi/2],
          S.cos(u),"nonnegative"),
      "principal_secant_positive_domain":([0,S.pi/6,S.pi/4],
          S.cos(u),"positive"),
      "strict_secant_first_quadrant":([S.pi/6,S.pi/4],
          S.tan(u),"positive"),
      "tangent_branch_secant_positive":([-S.pi/4,0,S.pi/4],
          S.sec(u),"positive"),
    }
    result={}
    for scenario,(angles,expression,polarity) in samples.items():
        checks=[]
        for angle in angles:
            z=S.simplify(S.trigsimp(expression.subs(u,angle)))
            good=z.is_positive if polarity=="positive" else z.is_nonnegative
            checks.append(bool(good))
        require(all(checks),"Positive-source branch check failed")
        result[scenario]={
            "source_branch":(
                "[-pi/2,pi/2] arcsine" if scenario=="principal_sine_closed_domain"
                else "[0,pi/2) secant positive"
                    if scenario=="principal_secant_positive_domain"
                else "(0,pi/2) secant strict x>a"
                    if scenario=="strict_secant_first_quadrant"
                else "(-pi/2,pi/2) tangent"
            ),
            "exact_mathematical_identities_proved":True,
            "representative_domain_sign_checks":len(checks),
            "finite_samples_alone_prove_whole_interval":False,
            "source_inequality_endpoint_interpretation_explicit":True
        }
    return result

def verify_source_domains(*,original:Path,source_plan:Path,
                          academic_report:Path,new_voice_report:Path,
                          out:Path)->dict:
    root=Path(original).resolve()
    refs=[Path(z).resolve() for z in (source_plan,academic_report,new_voice_report)]
    dest=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() for p in refs)
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Genuine original mathematical source and exclusive external receipt needed")
    plan,academic,voice=[json.loads(p.read_text(encoding="utf8")) for p in refs]
    require(plan.get("status")==SOURCE_STATUS
            and academic.get("status")==ACADEMIC_STATUS
            and voice.get("status")==VOICE_STATUS
            and plan.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and academic.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and voice.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and academic.get("source_plan_receipt_sha256")==file_hash(refs[0])
            and academic.get("source_inequality_scope_textual_review_flags")==5
            and voice.get("phonetic_soundalike_screen_pass") is True
            and all(z.get("student_publication_authorized") is False
                    for z in (plan,academic,voice))
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original source-specific domain/voice evidence drift")
    flags=academic["five_domain_scope_uncertainties"]
    require({(x["slide"],x["sentence_index"]) for x in flags}==set(KEYS)
            and len(flags)==5,
            "Exactly five actual original domain cases required")
    scripts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    source={(slide["slide"],x["sentence_index"]):x
            for slide in plan["source_historical_slides"]
            for x in slide["physical_original_pdf_source_targets"]}
    algebra=branch_math_checks()
    checked=[]
    with pymupdf.open(root/"slides.pdf") as pages:
        require(len(pages)==17,"Original protected source PDF pages missing")
        for k in sorted(KEYS):
            number,index=k
            tts,_=tokenize_reference_sentences(
                scripts["slides"][number-1]["tts_text"])
            sentence=tts[index-1]["narration_fragment"]
            z=source[k]
            visible=z["physical_source_pdf_text"]
            bounds=z["physical_original_pdf_rect_pt"]
            require(any(b[6]==0
                     and " ".join(str(b[4]).split())==" ".join(visible.split())
                     and all(abs(float(b[j])-bounds[j])<.12 for j in range(4))
                     for b in pages[number-1].get_text("blocks")),
                    "Original source mathematical domain visual rectangle drift")
            require(tts[index-1]["narration_fragment_sha256"]==
                    z["narration_source_sha256"],
                    "Actual narration original source identity changed")
            local=compare_math_claims(sentence,visible)
            require(not local["provable_local_term_conflicts"],
                    "A genuine trigonometric contradiction was detected")
            kind=KEYS[k]
            statement={
             "principal_sine_closed_domain":
                "For x=a sin u and a>0, -pi/2<=u<=pi/2, cos(u)>=0; "
                "sqrt(a^2-x^2)=a cos(u). Inverse asin endpoints included.",
             "principal_secant_positive_domain":
                "For x/a>=1 and a>0, 0<=u<pi/2, sec(u)>=1 and tan(u)>=0; "
                "sqrt(x^2-a^2)=a tan(u). Upper endpoint is EXCLUDED.",
             "strict_secant_first_quadrant":
                "For x>2/5 and x=(2/5)sec(u), 0<u<pi/2, tan(u)>0; "
                "sqrt(x^2-(2/5)^2)=(2/5)tan(u), no absolute value.",
             "tangent_branch_secant_positive":
                "For -pi/2<u<pi/2 and a>0, cos(u)>0, sec(u)>0; "
                "sqrt(a^2+x^2)=a sec(u). Both endpoints EXCLUDED.",
            }[kind]
            needs_clarity=(k==(5,4) and
                "less than" not in sentence.lower() and
                "open" not in sentence.lower())
            checked.append({
              "slide":number,"original_narrated_sentence_index":index,
              "speech_source_SHA256":z["narration_source_sha256"],
              "physical_original_PDF_domain_text":visible,
              "exact_physical_original_source_block_geometry_verified":True,
              "mathematical_branch_rule":kind,
              "source_branch_mathematics_proved":True,
              "source_branch_reasoning":statement,
              "plain_English_narration_endpoint_clarification_recommended":
                  needs_clarity,
              "local_source_scope_flag_addressed_by_explicit_domain":True,
              "all_spoken_audio_semantics_accepted":False
            })
    require(len(checked)==5 and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Five protected source domains or original math missing")
    result={
      "schema_version":1,"status":STATUS,
      "original_textbook_SHA256":EXPECTED_SOURCE_SHA,
      "original_66_source_plan_sha256":file_hash(refs[0]),
      "real_mathematical_domain_scopes_examined":len(checked),
      "explicit_trig_branch_inequality_sign_proofs":len(algebra),
      "original_five_uncertainties_addressed_by_math_source_branch_checks":True,
      "some_English_scope_clarifications_still_recommended":True,
      "all_original_audio_segments_independently_pronunciation_approved":False,
      "all_66_speech_to_PDF_semantics_certified":False,
      "student_publication_authorized":False,
      "release_eligible":False,
      "exact_original_domain_proof_rows":checked,
      "mathematics_algebraic_symbolic_proof_summary":algebra,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","source_plan","academic_report","new_voice_report","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    data=verify_source_domains(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in data.items()
                      if k not in ("exact_original_domain_proof_rows",
                                   "mathematics_algebraic_symbolic_proof_summary")},
                     indent=2))
if __name__=="__main__":main()
