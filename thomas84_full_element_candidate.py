"""Explicit full Thomas 8.4 academic-review candidate for existing source slides.

The 17-slide mapping is authored for this textbook section, NOT generated
automatically from arbitrary new user PDFs. The underlying element staging
algorithm is generic and independently source- and geometry-bound.

No new statements are certified scientifically or narratively. The candidate
is REVIEW ONLY, and full coverage is not academic approval.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from selenium_pipeline.element_narration_stage import rectangle


def H(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()


def T(index,evidence,narration):
    return ({"type":"text_block","index":index,"text_evidence":evidence},narration)


def I(narration):
    return ({"type":"image_whole","index":0},narration)


def P(index,of,narration):
    return ({"type":"image_panel","index":0,"panels":of,"panel":index},narration)


# Original PDF page (1-based), verbatim source-PDF evidence,
# selected visual anchors and corresponding explicitly authored speech.
CONTENT = {
1:(1,"Trigonometric Substitutions",[
 T(1,"8.4 Trigonometric Substitutions",
   "Section eight point four: trigonometric substitutions. We will transform integrals involving square roots of quadratic expressions by using trigonometric identities.")]),
2:(1,"The most common substitutions are x = a tan u",[
 T(2,"Core Question:",
   "Our central problem is turning radicals containing quadratic expressions into integrable trigonometric functions by selecting the appropriate substitution."),
 T(7,"Reversibility and Procedure:",
   "We must also choose an invertible interval for the substituted angle, and use the four-step procedure to return to the original variable.")]),
3:(1,"The most common substitutions are x = a tan u",[
 T(5,"a2 + x2, set x = a tan u",
   "For a square root of a squared plus x squared, use x equals a tangent u. The Pythagorean identity transforms the sum into a squared secant squared u."),
 T(9,"a2 −x2, set x = a sin u",
   "For a square root of a squared minus x squared, use x equals a sine u. The radical is then related to a cosine squared term."),
 T(13,"x2 −a2, set x = a sec u",
   "For a square root of x squared minus a squared, use x equals a secant u. The corresponding identity gives a squared tangent squared u.")]),
4:(1,"reference right triangles in Figure 8.2",[
 P(1,3,"In the first reference triangle, x equals a times tangent u. The adjacent side is a, the opposite side is x, and the hypotenuse is the square root of a squared plus x squared."),
 P(2,3,"The middle reference triangle corresponds to the sine substitution. Here x is opposite the angle, a is the hypotenuse, and the remaining side is the square root of a squared minus x squared."),
 P(3,3,"The third reference triangle represents the secant substitution. Its hypotenuse is x, the adjacent side is a, and the opposite side is the square root of x squared minus a squared.")]),
7:(2,"We set x = 2 tan u",[
 T(7,"Let x = 2 tan u",
   "Example one: to integrate one over the square root of four plus x squared, let x equal two tangent u. Then d x equals two secant squared u d u."),
 T(12,"4 + 4 tan2 u",
   "The square root of four plus x squared becomes two times the absolute value of secant u. On the chosen open interval, secant is positive, so the absolute value can be removed."),
 T(18,"sec u du = ln",
   "After substituting and cancelling factors, we integrate secant u. Its antiderivative is the natural logarithm of the absolute value of secant u plus tangent u, plus a constant.")]),
8:(3,"We drew a reference triangle for the original substitution",[
 I("The reference right triangle for tangent u equals x over two has opposite side x, adjacent side two, and hypotenuse square root of four plus x squared."),
 T(7,"Read the trigonometric ratio",
   "Read secant u from this triangle as the square root of four plus x squared divided by two."),
 T(10,"Back-substitute into the antiderivative",
   "Substitute secant and tangent in the logarithmic antiderivative. The result is the natural logarithm of the absolute value of square root of four plus x squared over two, plus x over two, followed by the integration constant.")]),
9:(3,"inverse hyperbolic sine function in terms of the natural logarithm",[
 T(2,"Following the same substitution",
   "Example two generalizes the tangent substitution to a positive constant a. It produces a logarithmic antiderivative involving square root of a squared plus x squared."),
 T(11,"Since sinh",
   "The inverse hyperbolic sine of x divided by a is another antiderivative of the same integrand. The two expressions therefore differ only by a constant."),
 T(24,"Evaluating both sides at x = 0",
   "Set x equal to zero. The inverse hyperbolic sine and the logarithm both become zero, showing that the difference constant is zero.")]),
10:(3,"We set x = 3 sin u",[
 T(7,"Let x = 3 sin u",
   "Example three has square root of nine minus x squared in the denominator. Set x equal to three sine u, so the differential is three cosine u d u."),
 T(11,"9 −x2 = 3 cos u",
   "On the selected interval, cosine u is positive. Thus the square root of nine minus x squared is three cosine u, and the cosine factor cancels in the transformed integral."),
 T(17,"Apply the half-angle formula",
   "What remains is nine times the integral of sine squared u. Use the half-angle identity, sine squared u equals one minus cosine two u, divided by two, and integrate term by term.")]),
11:(4,"sin 2u = 2 sin u cos u",[
 T(2,"Rewrite sin 2u",
   "To reverse the substitution in example three, use the double-angle identity sine two u equals two sine u cosine u. This converts the result into single-angle trigonometric functions."),
 I("The reference triangle shows sine u equals x over three, and cosine u equals the square root of nine minus x squared over three."),
 T(15,"9 −x2 + C",
   "Substituting those ratios gives nine halves times inverse sine of x over three, minus x halves times the square root of nine minus x squared, plus a constant.")]),
12:(4,"We first rewrite the radical as",[
 T(6,"25x2 −4 for x",
   "Example four evaluates the integral of one over the square root of twenty-five x squared minus four, for x greater than two fifths."),
 T(10,"25x2 −4 = 5",
   "Factor the leading coefficient inside the radical. The square root of twenty-five x squared minus four becomes five times the square root of x squared minus four twenty-fifths."),
 T(13,"sec u tan u",
   "Choose x equals two fifths secant u on the positive first-quadrant branch. The differential brings in secant u tangent u, and the simplified radical contains tangent u without an absolute value.")]),
13:(4,"With these substitutions, we have",[
 T(7,"ln | sec u + tan u",
   "Substitution cancels the tangent factors, leaving one fifth of the integral of secant u. This integrates to one fifth the natural logarithm of the absolute value of secant u plus tangent u."),
 I("The reference triangle expresses secant u as five x over two and tangent u as the square root of twenty-five x squared minus four over two."),
 T(12,"25x2 −4 = 1",
   "Replace both trigonometric ratios with the algebraic expressions from the triangle. The antiderivative is one fifth times their logarithmic sum, plus the integration constant.")]),
14:(2,"For reversibility, x = a tan u requires",[
 T(2,"Why is the domain of u strictly restricted",
   "Concept check. Why must the angle be restricted to the open interval between negative and positive pi over two when x equals a tangent u?"),
 T(8,"To make the substitution invertible",
   "Consider whether a restriction must provide a unique inverse tangent and keep secant positive, so that square roots simplify without an absolute-value ambiguity.")]),
15:(2,"For reversibility, x = a tan u requires",[
 T(2,"Correct Answer: (B)",
   "The correct answer to the concept check is B. The interval is chosen for two mathematical reasons."),
 T(7,"unique inverse",
   "First, the tangent function is one to one on this interval. Therefore the inverse tangent maps back uniquely from x to u."),
 T(11,"a2 sec2 u",
   "Second, cosine and secant are positive throughout this interval. Consequently the square root of a squared secant squared u equals a secant u for positive a, without a piecewise absolute value.")]),
16:(1,"These substitutions are effective in transforming integrals",[
 T(2,"Identity Alignment",
   "To summarize, match a squared plus x squared with tangent substitution, a squared minus x squared with sine substitution, and x squared minus a squared with secant substitution."),
 T(3,"Restricted Domains",
   "Every substitution requires an appropriate inverse-function domain. Such restrictions also control whether absolute value signs can be removed."),
 T(4,"Reference Triangles",
   "Use a reference right triangle to convert the final expression back from angle u to the original variable x. When needed, first factor coefficients to reveal the standard quadratic form.")]),
17:(4,"sin 2u = 2 sin u cos u",[
 T(3,"carry out Step 1 and Step 2",
   "For your first review question, consider the square root of x squared minus sixteen, with x greater than four. Choose a secant substitution, compute the differential, and simplify the resulting integrand."),
 T(4,"double-angle identities",
   "For the second question, explain why a double-angle identity should be applied before reading a reference triangle. Remember that the triangle directly supplies ratios for u, rather than for two u.")]),
}

PAGE5_QUOTE="We want any substitution we use in an integration to be reversible"


def create(*,source,slides,prior_plan,output):
    if output.exists():
        raise FileExistsError(output)
    original=json.loads(prior_plan.read_text(encoding="utf8"))
    frozen={record["slide"]:record for p in original["parts"]
            for record in p["slides"]}
    if sorted(frozen)!=[5,6]:
        raise ValueError("Pilot source must contain precisely slides five and six")
    if original["source_sha256"]!=H(source) or original["slides_sha256"]!=H(slides):
        raise ValueError("Corrected source slides changed since two-slide pilot")
    enriched=[]
    for i in range(1,18):
        if i in frozen:
            record=json.loads(json.dumps(frozen[i]))
            record["source_page"]=2
            record["source_evidence"]=PAGE5_QUOTE
            enriched.append(record)
            continue
        page,evidence,items=CONTENT[i]
        elements=[]
        for k,(anchor,text) in enumerate(items,1):
            elements.append({"anchor":anchor,"spoken_text":text,
                "wav":f"s{i:02d}_e{k:02d}.wav"})
        enriched.append({"slide":i,"source_page":page,
            "source_evidence":evidence,"title":f"Thomas 8.4, slide {i}",
            "elements":elements})
    part1=[p for p in enriched if p["slide"]<=8]
    part2=[p for p in enriched if p["slide"]>=9]
    total=sum(len(p["elements"]) for p in enriched)
    assert len(enriched)==17 and total>=40
    obj={"schema_version":1,
         "status":"author_specified_unapproved_element_narration",
         "source_sha256":H(source),"slides_sha256":H(slides),
         "voice_id":"gemini_gemini-3.8-flash-lite-tts_Kore_REVIEW_ONLY",
         "authoring_basis":"Thomas_8_4_explicit_source_pdf_and_verified_rendered_slide_review_candidate",
         "parts":[{"part_id":"part_01","slides":part1},
                  {"part_id":"part_02","slides":part2}]}
    output.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({"output":str(output),
          "slides":len(enriched),"narration_elements":total,
          "part_counts":[sum(len(p["elements"]) for p in part1),
                         sum(len(p["elements"]) for p in part2)]},indent=2))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--slides",type=Path,required=True)
    ap.add_argument("--two-slide-plan",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    create(source=args.source,slides=args.slides,prior_plan=args.two_slide_plan,
           output=args.output)


if __name__=="__main__":main()
