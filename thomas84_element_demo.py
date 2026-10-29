"""Source-linked Thomas 8.4 two-slide element narration demo plan.

The written narration is an authored PILOT, not copied from existing whole-slide
WAVs. Source and slide hashes are computed from the original verified files.
Academic and pronunciation review is still required before production use.
"""
import argparse,hashlib,json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--slides",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source_quote="We want any substitution we use in an integration to be reversible"
    obj={
      "schema_version":1,"status":"author_specified_unapproved_element_narration",
      "source_sha256":sha(args.source),"slides_sha256":sha(args.slides),
      "voice_id":"windows_sapi_Microsoft_Zira_Desktop_REVIEW_ONLY",
      "parts":[{"part_id":"part_01","slides":[
        {"slide":5,"source_page":2,"source_evidence":source_quote,
         "title":"Reversibility and domain restrictions — precise element pilot",
         "elements":[
           {"anchor":{"type":"text_block","index":2,
                      "text_evidence":"To reverse the substitution"},
            "wav":"s05_e01.wav",
            "spoken_text":"We restrict the substitution angle to a principal branch, so that we can reverse the substitution and return from u to x after integration."},
           {"anchor":{"type":"image_panel","index":0,"panels":3,"panel":1},
            "wav":"s05_e02.wav",
            "spoken_text":"For the tangent substitution, x equals a times tangent u. Choose u strictly between negative pi over two and positive pi over two. The first graph illustrates the restricted branch."},
           {"anchor":{"type":"image_panel","index":0,"panels":3,"panel":2},
            "wav":"s05_e03.wav",
            "spoken_text":"For the sine substitution, x equals a times sine u. The inverse branch extends from negative pi over two to positive pi over two, including both endpoints. See the middle graph."},
           {"anchor":{"type":"image_panel","index":0,"panels":3,"panel":3},
            "wav":"s05_e04.wav",
            "spoken_text":"For the positive secant substitution, with x divided by a at least one, choose angles from zero to less than pi over two. The third graph shows the relevant branch."}
         ]},
        {"slide":6,"source_page":2,"source_evidence":source_quote,
         "title":"Four-step procedure — precise element pilot",
         "elements":[
           {"anchor":{"type":"text_block","index":3,"text_evidence":"Substitute:"},
            "wav":"s06_e01.wav",
            "spoken_text":"Step one. Substitute for x using the appropriate trigonometric function, calculate the differential d x, and state the allowed angular domain."},
           {"anchor":{"type":"text_block","index":4,"text_evidence":"Transform:"},
            "wav":"s06_e02.wav",
            "spoken_text":"Step two. Transform the integrand by substituting x and d x. Simplify the resulting expression using a trigonometric identity."},
           {"anchor":{"type":"text_block","index":5,"text_evidence":"Integrate:"},
            "wav":"s06_e03.wav",
            "spoken_text":"Step three. Integrate the resulting trigonometric expression with respect to u."},
           {"anchor":{"type":"text_block","index":6,"text_evidence":"Reverse:"},
            "wav":"s06_e04.wav",
            "spoken_text":"Step four. Reverse the substitution using the original relationship and a right reference triangle, expressing the final antiderivative in terms of x."}
         ]}
      ]}]
    }
    args.output.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("Authored explicit 8-element pilot",args.output)
if __name__=="__main__":
    main()
