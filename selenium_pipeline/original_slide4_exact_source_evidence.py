"""Immutable Thomas8.4 Slide4 five-utterance SOURCE QUOTE review packet.

This packet cannot approve math, figures, narration, voice, or publication.
Each quote is tested against spatially coherent EXACT original PDF tokens.
A formula string here is an extracted TEXT witness, not a parsed radical.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .ai_academic_web_review import build_review_job
from .original_slide4_five_visual_candidates import inspect_original_slide4_five_visual_candidates
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .figure_source_identity import _sha,require

# Manual transcription from the original 6-page source PDF followed by actual
# EXACT token and original PDF spatial-continuity proof on Dell-115.
# Do not auto-combine columns or silently 'repair' malformed radical symbols.
_SOURCE_PASSAGES=(
  ((1,"Reference triangles for the three basic substitutions"),
   (1,"identifying the sides labeled x and a for each substitution.")),
  ((1,"The most common substitutions are x = a tan u, x = a sin u, and x = a sec u."),
   (1,"a2 + x2 = a2 + a2 tan2 u = a2(1 + tan2 u) = a2 sec2 u.")),
  ((1,"The most common substitutions are x = a tan u, x = a sin u, and x = a sec u."),
   (1,"a2 - x2 = a2 - a2 sin2 u = a2(1 - sin2 u) = a2 cos2 u.")),
  ((1,"The most common substitutions are x = a tan u, x = a sin u, and x = a sec u."),
   (2,"x2 - a2 = a2 sec2 u - a2 = a2(sec2 u - 1) = a2 tan2 u.")),
  ((1,"Reference triangles for the three basic substitutions"),
   (2,"To simplify calculations with the substitution x = a sec u, we will restrict its use to")),
)
_KINDS=("INTRO_REFERENCE_TRIANGLES","TANGENT_SQUARED_IDENTITY",
        "SINE_SQUARED_IDENTITY","SECANT_SQUARED_IDENTITY",
        "ROOT_ABSOLUTE_VALUES_CONTEXT_ONLY")
def build_five_original_source_evidence(*,folder:Path,passages=None)->dict:
    root=Path(folder).absolute()
    hashes=tuple(_sha(root/x) for x in ("source.pdf","slides.pdf","script.txt"))
    job=build_review_job(folder=root,slide_numbers=[4])
    visual=inspect_original_slide4_five_visual_candidates(folder=root)
    require(job["utterance_count"]==visual["utterance_candidate_count"]==5
       and (job["source_sha256"],job["slides_sha256"],job["script_sha256"])==hashes
       and (visual["source_sha256"],visual["slides_sha256"],visual["script_sha256"])==hashes
       and visual["source_mathematical_review_approved"] is False,
       "Original source-slide/narrator evidence or review state drift")
    provided=_SOURCE_PASSAGES if passages is None else tuple(passages)
    require(len(provided)==5 and all(p==q for p,q in zip(provided,_SOURCE_PASSAGES)),
       "Five original source passages were changed or reordered")
    rows=[]
    for i,(u,target,quotes) in enumerate(zip(job["slides"][0]["utterances"],
                                             visual["utterance_candidates"],provided)):
        require(u["id"]==target["utterance_id"]
                and u["spoken_sha256"]==target["original_spoken_sha256"]
                and type(u["spoken_text"]) is str
                and target["candidate_highlight_bbox_pdf_pt"],
                "Narrator or visible target not source-bound")
        evidence=[]
        for page,quote in quotes:
            witness=prove_source_quote_occurrence(source_pdf=root/"source.pdf",
                expected_sha256=hashes[0],page_number=page,verbatim_quote=quote)
            require(witness["status"]=="EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT"
                    and witness["quote_occurrences"]==1,
                    "Not a unique coherent source passage")
            evidence.append({"source_physical_page":page,
                "exact_extracted_pdf_quote":quote,
                "source_quote_sha256":witness["quote_sha256"],
                "original_pdf_spatial_coherence_verified":True})
        rows.append({"original_utterance_id":u["id"],
            "spoken_sha256":u["spoken_sha256"],
            "exact_original_spoken_text":u["spoken_text"],
            "review_target_id":target["review_target_id"],
            "review_target_bbox_pdf_pt":target["candidate_highlight_bbox_pdf_pt"],
            "evidence_kind":_KINDS[i],
            "source_evidence":evidence,
            "exact_source_quote_count":len(evidence),
            "evidence_is_semantic_math_approval":False,
            "original_radical_glyph_reliably_decoded":False,
            "review_disposition":"AWAIT_INDEPENDENT_SOURCE_MATH_REVIEW",
            "original_audio_approved":False})
    require(tuple(_sha(root/x) for x in ("source.pdf","slides.pdf","script.txt"))==hashes,
        "Original source changed while building independent evidence")
    return {"status":"FIVE_ORIGINAL_SLIDE4_SOURCE_QUOTE_PACKET_REVIEW_ONLY",
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_slide":4,
        "original_utterance_count":5,
        "verified_exact_pdf_source_excerpt_count":sum(r["exact_source_quote_count"] for r in rows),
        "source_math_semantically_approved_utterances":0,
        "source_text_quotations_prove_narration_correct":False,
        "source_radical_operator_academically_verified":False,
        "independent_two_pass_review_approved":False,
        "original_utterance_evidence":rows,
        "gemini_provider_request_sent":False,
        "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(build_five_original_source_evidence(folder=a.folder),indent=2,ensure_ascii=True))
if __name__=="__main__":main()
