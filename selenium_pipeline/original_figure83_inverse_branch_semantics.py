"""Source-locked inverse trig branch/domain science for original Figure8.3.

The full graph image is publisher-origin proven separately; here verifies
selected *mathematical* inverse branches and secant principal-root sign
against actual textbook source page2 and original authored slides6/7.
Does not certify pixel glyphs, all graph ticks/axes or real audio timing.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from .figure_source_identity import require,_sha
from .original_figure82_83_actual_publisher_feature_registration import STATUS as FIG_STATUS
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_84_INVERSE_TRIG_PRINCIPAL_BRANCH_AND_SECANT_ROOT_EXACT_NONPRODUCTION"
CLAUSES={
    6:(r"\tan^{-1}\left(\frac{x}{a}\right)",
       r"-\frac{\pi}{2} < \theta < \frac{\pi}{2}",
       "Figure 8.3.png"),
    7:(r"\sin^{-1}\left(\frac{x}{a}\right)",
       r"\sec^{-1}\left(\frac{x}{a}\right)",
       r"\frac{x}{a} \ge 1",r"\frac{x}{a} \le -1",
       r"\sqrt{x^{2}-a^2} = a \tan \theta"),
}

def branch_science()->dict:
    try: import sympy as s
    except ImportError as exc:
        require(False,f"Independent exact math library unavailable: {exc}")
    positive=(s.Integer(0),s.pi/6,s.pi/4)
    negative=(-s.pi/4,-s.pi/6)
    for theta in positive+negative:
        require(s.trigsimp(s.atan(s.tan(theta))-theta)==0,
                "Publisher arctangent inverse branch (-pi/2,pi/2) false")
        require(s.trigsimp(s.asin(s.sin(theta))-theta)==0,
                "Publisher arcsine inverse branch [-pi/2,pi/2] false")
    for theta in (s.Integer(0),s.pi/6,s.pi/4,2*s.pi/3,3*s.pi/4,s.pi):
        require(s.trigsimp(s.asec(s.sec(theta))-theta)==0,
                "Publisher arcsecant inverse branch [0,pi/2)∪(pi/2,pi] false")
    a=s.Integer(3)
    for theta in (s.Integer(0),s.pi/6,s.pi/4):
        x=a*s.sec(theta)
        require(s.simplify(
            s.sqrt(x*x-a*a)-a*s.tan(theta))==0,
            "Positive-domain secant substitution principal-root simplification false")
    wrong=s.Integer(-1)*s.pi/6
    # Without the original positive-theta restriction, the same radical
    # cannot be replaced by a*tan(theta); it changes sign.
    require(s.simplify(s.sqrt(a*a*s.sec(wrong)**2-a*a)
            -a*s.tan(wrong))!=0,
            "Negated-theta secant principal-root sign incorrectly generalized")
    return {
        "original_graph_arctangent_inverse_principal_domain_sampled_exact":True,
        "original_graph_arcsine_inverse_principal_domain_sampled_exact":True,
        "original_graph_arcsecant_two_branch_principal_domains_sampled_exact":True,
        "original_secant_root_positive_restricted_angle_exact":True,
        "negative_angle_principal_root_incorrect_promotion_rejected":True,
        "all_source_curves_and_math_label_pixels_fully_approved":False,
        "spoken_figure_element_word_sync_fully_approved":False,
    }

def audit_original(*,folder:Path,visual_receipt:dict)->dict:
    import pymupdf
    root=Path(folder).absolute()
    publisher,author=ORIGINAL_PINS["8.4"]
    require(root.is_dir() and not root.is_symlink()
            and _sha(root/"source.pdf")==publisher
            and _sha(root/"slides.pdf")==author,
            "Not source-locked original Thomas §8.4 publisher/author corpus")
    require(visual_receipt.get("status")==FIG_STATUS
            and visual_receipt.get("student_publication_authorized") is False
            and visual_receipt.get("original_figures_publisher_panel_visual_match_count")==2
            and visual_receipt["two_exact_source_figure_panel_image_matches"]["8.3"][
                "all_three_source_image_panel_artwork_correspondence_proven"] is True,
            "Original publisher image Figure8.3 identity not independently proven")
    paths=[root/name for name in (
        "source.pdf","slides.pdf","slides.tex","Figure 8.3.png",
        "script.txt","slide6.wav","slide7.wav")]
    before={str(p):_sha(p) for p in paths}
    tex=(root/"slides.tex").read_text(encoding="utf8")
    slides=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",tex,re.S)
    require(len(slides)==17
            and all(part in slides[5] for part in CLAUSES[6])
            and all(part in slides[6] for part in CLAUSES[7]),
            "Original authored inverse Figure8.3 domains changed or misplaced")
    with pymupdf.open(root/"source.pdf") as source:
        require(len(source)==6,"Wrong publisher source section")
        text=" ".join(source[1].get_text().split())
        require(all(term in text for term in (
            "For reversibility","x = a tan u","tan-1","x = a sin u",
            "sin-1","x = a sec u","sec-1","FIGURE 8.3")),
            "Publisher printed original inverse-function labels or domain source missing")
    result=branch_science()
    require({str(p):_sha(p) for p in paths}==before,
            "Original publisher/author figures or PCM mutated during exact science verification")
    return {
        "status":STATUS,
        "original_publisher_source_sha256":publisher,
        "original_authored_slide_sha256":author,
        "actual_publisher_inverse_graph_page":2,
        "actual_authored_inverse_figure_and_domains_slide_numbers":[6,7],
        "original_source_selected_mathematical_clauses_checked":
            sum(len(x) for x in CLAUSES.values()),
        "branch_science":result,
        "source_textbook_visual_identity_verified":True,
        "source_all_pixels_scientific_axis_tick_identity_verified":False,
        "every_original_spoken_label_time_approved":False,
        "full_production_academic_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--figure-receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.figure_receipt.is_file() and not a.figure_receipt.is_symlink()
            and a.out.parent.is_dir() and not a.out.exists(),
            "Versioned non-overwriting publisher graph proof receipt required")
    prior=_sha(a.figure_receipt)
    result=audit_original(folder=a.original,visual_receipt=json.loads(
        a.figure_receipt.read_text("utf8")))
    require(prior==_sha(a.figure_receipt),"Original publisher figure evidence mutated")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({
        "status":STATUS,"source_math_clauses":
            result["original_source_selected_mathematical_clauses_checked"],
        "original_fig83_graph_branch_science_sampled_exact":True,
        "student_publication_authorized":False,
    }))
if __name__=="__main__":
    main()
