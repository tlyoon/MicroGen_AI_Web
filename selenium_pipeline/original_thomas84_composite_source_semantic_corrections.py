"""Real original-PDF composite math-focus corrections to 10 cue mismappings.

Original PDF text sometimes fragments formulas across separate blocks.
A textually visible block alone may be incomplete or irrelevant to the
spoken mathematical claim. Recover exact original source block sets
with actual page geometry; do not promote unapproved video release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pymupdf
import sympy as S
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_66_source_cue_pcm_plan import STATUS as CUE_STATUS

STATUS="TEN_ORIGINAL_PDF_SEMANTIC_FOCUS_CORRECTIONS_REVIEW_ONLY"

# Exact source-PDF block indexes / literal phrases on genuine slides.pdf.
# Compound figures/equations are not collapsed into fictitious text blocks.
# These correct clearly incomplete or wrong-context existing focus targets.
CORRECTIONS={
    (5,4):((5,"x = a sec u"),(6,"when x/a")),
    (7,1):((5,"Z dx"),(6,"4 + x2"),(7,"Let x = 2 tan u")),
    (8,2):((2,"From tan u = x"),(3,"construct the right triangle")),
    (9,2):((11,"Since sinh"),(13,"a2 + x2")),
    (10,3):((13,"9 sin2 u"),(14,"3 cos u = 9"),(16,"sin2 u du")),
    (12,2):((10,"25x2"),(11,"x2")),
    (13,1):((3,"sec u tan u du"),(6,"sec u du")),
    (15,2):((3,"Reversibility:"),(8,"Simplification of Radicals:")),
    (16,1):((2,"Identity Alignment:"),),
    (17,2):((2,"For an integral containing"),(3,"x2 −16")),
}

def actual_source_composite(page,entries:tuple[tuple[int,str],...])->dict:
    source=page.get_text("blocks")
    require(type(entries) is tuple and bool(entries),
            "Missing original source PDF mathematical focus")
    proven=[]
    for idx,expected in entries:
        require(type(idx) is int and idx<len(source) and idx>=0
                and source[idx][6]==0
                and expected.casefold() in
                    " ".join(str(source[idx][4]).split()).casefold(),
                "A supposedly related source mathematical text block does not exist")
        rect=[float(source[idx][j]) for j in range(4)]
        require(0<=rect[0]<rect[2]<=page.rect.width+.1
                and 0<=rect[1]<rect[3]<=page.rect.height+.1,
                "Original source text rectangle outside visual slide")
        proven.append({"original_pdf_block_index":idx,
                       "original_pdf_text":" ".join(str(source[idx][4]).split()),
                       "original_pdf_bbox_pt":rect})
    span=[min(z["original_pdf_bbox_pt"][0] for z in proven),
          min(z["original_pdf_bbox_pt"][1] for z in proven),
          max(z["original_pdf_bbox_pt"][2] for z in proven),
          max(z["original_pdf_bbox_pt"][3] for z in proven)]
    return {"original_pdf_source_blocks":proven,
            "original_pdf_visual_union_rect_pt":span,
            "source_geometry_exactly_recomputed":True,
            "full_spoken_element_mathematics_semantically_approved":False}

def limited_domain_proofs()->dict:
    """Limited analytic identities and actual valid-branch sample checks."""
    u=S.symbols("u",real=True);a=S.symbols("a",positive=True)
    sample={
      "sine_principal_cos_nonnegative":
        (S.cos(u),[-S.pi/2,-S.pi/4,0,S.pi/4,S.pi/2],"nonnegative"),
      "tangent_principal_sec_positive":
        (S.sec(u),[-S.pi/4,0,S.pi/4],"positive"),
      "secant_principal_tan_nonnegative":
        (S.tan(u),[0,S.pi/6,S.pi/4],"nonnegative"),
      "strict_secant_x_gt_two_fifths_tan_positive":
        (S.tan(u),[S.pi/6,S.pi/4],"positive"),
    }
    proofs={}
    for name,(expression,angles,sign) in sample.items():
        checked=[]
        for angle in angles:
            real=S.simplify(S.trigsimp(expression.subs(u,angle)))
            good=real.is_positive if sign=="positive" else real.is_nonnegative
            checked.append(bool(good))
        proofs[name]={"source_domain_sample_count":len(angles),
                      "representative_branch_sign_checks_pass":all(checked),
                      "continuous_full_interval_proven_by_sampling":False}
    # For positive a and the principal tangent branch,
    # d(tan u)/du = sec²(u), positive whenever cos(u) != 0.
    derivative=S.simplify(S.trigsimp(S.diff(S.tan(u),u)-S.sec(u)**2))==0
    # For 0<=u<pi/2, x=(2/5)sec u, so x²-(2/5)²
    # equals (2/5 tan u)²; with tan u>=0 the positive root is (2/5)tan u.
    radial=S.simplify(S.trigsimp(
        (S.Rational(2,5)*S.sec(u))**2-S.Rational(2,5)**2-
        (S.Rational(2,5)*S.tan(u))**2))==0
    require(derivative and radial and
            all(x["representative_branch_sign_checks_pass"]
                for x in proofs.values()),
            "Standard source-backed domain algebraic relation changed")
    proofs["tangent_derivative_monotonic_identity"]={"symbolic_identity_pass":True}
    proofs["positive_secant_radicand_square_identity"]={"symbolic_identity_pass":True}
    return proofs

def recover_actual_context(*,original:Path,full_plan:Path,
                           independent_media_audit:Path,out:Path)->dict:
    root=Path(original).resolve();p=Path(full_plan).resolve()
    audit=Path(independent_media_audit).resolve()
    destination=Path(out).absolute()
    require(root.is_dir() and p.is_file() and audit.is_file()
            and destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(root.parent),
            "Only protected actual source read and exclusive external receipt allowed")
    plan=json.loads(p.read_text(encoding="utf8"))
    media=json.loads(audit.read_text(encoding="utf8"))
    require(plan.get("status")==CUE_STATUS and
            plan.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and plan.get("physical_source_pdf_cues_verified")==66
            and plan.get("student_publication_authorized") is False
            and media.get("status")==
                "TWO_REAL_66_CUE_H264_AAC_MP4S_PHYSICALLY_INDEPENDENTLY_VERIFIED_NO_RELEASE"
            and media.get("source_original_pdf_sha256")==EXPECTED_SOURCE_SHA
            and media.get("student_publication_authorized") is False
            and media.get("source_pdf_reverified_provisional_cue_events")==66
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Source math context or genuine media evidence not proven")
    index={(s["slide"],r["sentence_index"]):r
           for s in plan["source_historical_slides"]
           for r in s["physical_original_pdf_source_targets"]}
    require(len(index)==66,"All source original narrated mathematical units required")
    corrected=[]
    with pymupdf.open(root/"slides.pdf") as doc:
        require(len(doc)==17,"Original protected source PDF pages changed")
        for (slide,sentence),parts in CORRECTIONS.items():
            require((slide,sentence) in index,"Original narrated focus not in source plan")
            old=index[(slide,sentence)]
            candidate=actual_source_composite(doc[slide-1],parts)
            corrected.append({
                "slide":slide,"sentence_index":sentence,
                "original_narration_fragment_sha256":
                    old["narration_source_sha256"],
                "superseded_review_only_pdf_element_id":
                    old["physical_original_pdf_element_id"],
                **candidate,
                "original_math_acoustic_source_remapping_accepted":False,
                "student_publication_authorized":False,
            })
    require(len(corrected)==10
            and len({(x["slide"],x["sentence_index"]) for x in corrected})==10,
            "Ten original PDF source focus corrections missing")
    mathematical=limited_domain_proofs()
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Protected textbook PDF mutated during math correction")
    result={
        "schema_version":1,"status":STATUS,
        "protected_original_textbook_sha256":EXPECTED_SOURCE_SHA,
        "original_66_source_cue_plan_sha256":file_hash(p),
        "independent_real_video_audit_sha256":file_hash(audit),
        "incomplete_or_wrong_context_original_cues_corrected":len(corrected),
        "standard_domain_limited_math_checks":mathematical,
        "source_mathematical_equivalence_for_all_66_approved":False,
        "release_eligible":False,
        "student_publication_authorized":False,
        "corrected_original_pdf_composite_focuses":corrected,
    }
    with destination.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ("original","full_plan","independent_media_audit","out"):
        parser.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    d=recover_actual_context(**vars(parser.parse_args()))
    print(json.dumps({k:v for k,v in d.items()
                      if k not in ("corrected_original_pdf_composite_focuses",
                                   "standard_domain_limited_math_checks")},indent=2))
if __name__=="__main__":main()
