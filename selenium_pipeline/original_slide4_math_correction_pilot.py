"""Genuine-original Thomas 8.4 Slide-4 mathematics correction pilot.

Source-grounded, exact symbolic witness and a revised FIVE-utterance TTS script.
This module NEVER reviews its own mathematics independently, uses Gemini, or
approves audio. Corrected text must be synthesized anew and independently QA'd.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .ai_academic_web_review import build_review_job
from .original_slide4_exact_source_evidence import build_five_original_source_evidence
from .source_locked_academic_review import assert_original_slide4_source_packet
from .original_principal_root_interval_qa import audit_exact_principal_root_domains

_ORIGINAL_SOURCE_SHA = "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
_ORIGINAL_SPEECH_SHAS = (
    "8132bd0c3eef29710020a6be2683baaaba4e020578068d357ae8bf6c2f5225a4",
    "3f463c584fd4cf5175891fc3e1c20c7d1980eeca88ca6419732ea3316df5529d",
    "f5306f146099ead1fdec8e954302facf490747c38059da2925b6540f9e4b4408",
    "08c5022f048adc63f239a68ab2242df4f4280cb118bc915b4fbadaa81095ea2e",
    "9e97fb9c5384787ee7ad811d1e44e63023e5519ec4ba5287f6428611b6a51a67",
)
_REVISED_NARRATION = (
    "The three trigonometric substitutions can be visualized with reference right triangles. Their geometric side lengths are non-negative. When the substitution angle is negative, the diagram uses a positive reference angle, not the signed angle itself.",
    "Assume a is positive. For x equals a tangent u, the adjacent leg is a, and the opposite leg has length the absolute value of x. The hypotenuse is the square root of a squared plus x squared. On the interval between negative pi over two and pi over two, secant u is positive.",
    "For x equals a sine u, with u between negative pi over two and pi over two inclusive, a is the hypotenuse and the opposite side has length the absolute value of x. The other leg is the square root of a squared minus x squared. Cosine u is non-negative on this interval.",
    "For x equals a secant u, restrict to x at least a, and u between zero inclusive and pi over two exclusive. The hypotenuse has length x and the adjacent leg is a. The opposite leg is the square root of x squared minus a squared, and tangent u is non-negative.",
    "For positive a, the principal square root is non-negative. The three radicals simplify to a times the absolute value of secant u, a times the absolute value of cosine u, and a times the absolute value of tangent u, respectively. On the specified restricted domains these absolute values reduce to secant u, cosine u and tangent u.",
)
def exact_math_counterexamples() -> dict:
    """Two exact signed-length counterexamples + positive branch theorems."""
    try:
        import sympy as s
    except ImportError:
        raise ValueError("SymPy required to prove exact math, cannot approve")
    a=s.Integer(2)
    neg=-s.pi/4
    x_tan=s.simplify(a*s.tan(neg))
    x_sine=s.simplify(a*s.sin(-s.pi/6))
    require(x_tan==-2 and x_sine==-1 and bool(neg < 0),
            "Exact negative-angle and negative-length counterexample failed")
    theorem=audit_exact_principal_root_domains()
    require(theorem["conditional_principal_root_branches_proven"] is True
            and theorem["conditional_principal_root_branch_count"]==3
            and theorem["independent_source_math_review_approved"] is False,
            "Conditional mathematical theorem missing or falsely approved")
    # Direct, exact rational/algebraic checks supplement the domain-range theorem.
    root_plus=s.sqrt(a*a+x_tan*x_tan)
    cos_neg=s.cos(neg)
    require(s.simplify(root_plus-a/s.cos(neg))==0
            and s.simplify(s.sqrt(a*a-x_sine*x_sine)-a*s.cos(-s.pi/6))==0,
            "Exact nonnegative radical branch witness failed")
    return {
        "status":"ORIGINAL_TANGENT_AND_SINE_SIGNED_TRIANGLE_DEFECTS_PROVED",
        "exact_counterexamples":[
            {"form":"x=a*tan(u)","a":"2","u":"-pi/4","x":str(x_tan),
             "defect":"u negative, x cannot be a positive triangle side length"},
            {"form":"x=a*sin(u)","a":"2","u":"-pi/6","x":str(x_sine),
             "defect":"signed opposite-leg x is negative; side length must be abs(x)"},
        ],
        "positive_parameter_condition":"a>0",
        "conditional_principal_root_forms_verified":3,
        "source_pdf_glyph_independently_approved":False,
        "narration_claim_all_angles_acute_refuted":True,
        "mathematical_derivation_exact":True,
        "independent_academic_model_consensus_approved":False,
        "student_release_authorized":False,
    }

def prepare_corrected_original_slide4(*,folder:Path) -> dict:
    folder=Path(folder).absolute()
    before=tuple(_sha(folder/f) for f in ("source.pdf","slides.pdf","script.txt"))
    require(before[0]==_ORIGINAL_SOURCE_SHA,
            "Only immutable original Thomas 8.4 source eligible")
    job=build_review_job(folder=folder,slide_numbers=[4])
    packet=build_five_original_source_evidence(folder=folder)
    original=assert_original_slide4_source_packet(job=job,packet=packet)
    utterances=job["slides"][0]["utterances"]
    require(len(utterances)==len(original)==len(_REVISED_NARRATION)==5
            and tuple(u["spoken_sha256"] for u in utterances)==_ORIGINAL_SPEECH_SHAS
            and "acute angle u" in utterances[0]["spoken_text"]
            and "x and a represent the opposite and adjacent legs" in utterances[1]["spoken_text"]
            and "x is the opposite leg" in utterances[2]["spoken_text"],
            "Original defective mathematical narration is not unchanged")
    proof=exact_math_counterexamples()
    fixed=[]
    for i,(u,ev,corrected) in enumerate(zip(utterances,original,_REVISED_NARRATION)):
        digest=hashlib.sha256(corrected.encode("utf-8")).hexdigest()
        fixed.append({
            "original_utterance_id":u["id"],
            "original_spoken_sha256":u["spoken_sha256"],
            "original_source_verified_target_id":ev["review_target_id"],
            "old_narration":u["spoken_text"],
            "revised_narration":corrected,
            "revised_text_sha256":digest,
            "new_same_voice_tts_request_candidate":{
                "utterance_id":u["id"],
                "tts_text":corrected,
                "tts_text_sha256":digest,
                "preferred_provider":"Gemini web Flash-Lite TTS",
                "preferred_voice":"Kore",
                "maximum_primary_attempts":3,
                "fallback_only_after_three_failed_primary_attempts":True,
                "same_voice_across_all_segments_required":True,
                "no_request_submitted":True,
            },
            "mathematics_text_revision_required":True,
            "old_WAV_must_not_be_labeled_corrected_text":True,
            "new_same_voice_TTS_wav_received":False,
            "spoken_content_checked_against_revised_text":False,
            "synchronized_highlight_media_accepted":False,
        })
    require(tuple(_sha(folder/f) for f in ("source.pdf","slides.pdf","script.txt"))==before,
            "Protected originals changed during math repair preparation")
    return {
        "status":"REAL_SOURCE_SLIDE4_CORRECTED_NARRATION_STAGED_QA_REQUIRED",
        "source_sha256":before[0],
        "slides_sha256":before[1],
        "script_sha256":before[2],
        "original_slide":4,
        "original_utterances":5,
        "exact_original_source_quote_count":10,
        "proved_math_defects":proof,
        "corrected_utterances":fixed,
        "new_audio_required":True,
        "audio_provider_request_sent":False,
        "corrected_mathematics_independently_ai_approved":False,
        "genuine_corrected_audio_received":False,
        "actual_speech_to_highlight_verified":False,
        "final_encoded_under_600s_mp4_approved":False,
        "student_publication_authorized":False,
        "original_files_modified":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args(argv)
    original=args.folder.absolute()
    out=args.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(original),
            "New exclusive external review receipt required, not original folder")
    result=prepare_corrected_original_slide4(folder=original)
    with out.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status":result["status"],
                      "original_units":result["original_utterances"],
                      "corrected_tts_jobs_staged":len(result["corrected_utterances"]),
                      "source_sha256":result["source_sha256"],
                      "academic_release_approved":False,
                      "output":str(out)},ensure_ascii=True))
if __name__=="__main__":
    main()
