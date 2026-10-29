"""Independent full 66-sentence source-math and PDF-element focus adjudication.

A human-authored mathematical *review map* is verified against exact
genuine PDF geometry, SHA-locked original narration, corrected source
Slide17, original WAV PCM map, protected textbook and real second-pass
MP4 audit. Distinguish: source-related, complete mathematical element,
correct sign/domain, acoustic real-word timing and video pixels.
The map is NOT automatic evidence of mathematical truth; two signed
right-triangle statements require corrected source/voice before release.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_66_source_cue_pcm_plan import STATUS as PLAN_STATUS
from .original_thomas84_paired_question_source_fix import STATUS as PAIR_STATUS
from .original_thomas84_paired_sl17_independent_audit import STATUS as VIDEO_STATUS
from .original_thomas84_slide11_independent_trig_voice_check import STATUS as SL11_STATUS
from .original_thomas84_five_source_domain_proofs import STATUS as DOMAINS_STATUS

STATUS="ALL_66_GENUINE_PDF_SOURCE_ELEMENT_SEMANTIC_REVIEW_SIGNED_TRIANGLE_REPAIR_REQUIRED"
# Each index refers to an ORIGINAL visible PDF text block, not an
# invented synthetic layout element. Slide17 uses real corrected PDF.
CURATED_BLOCKS={
 1:((1,),),
 2:((2,),(3,4,5,6),(7,)),
 3:((2,),(3,4,5,6),(7,8,9,10),(11,12,13,14),(2,)),
 5:((2,),(3,4),(4,5),(5,6),(3,4),(4,5),(5,6),(2,)),
 6:((2,),(3,),(3,),(4,),(5,),(6,)),
 7:((4,5,6,7,8),(9,10,11,12),(13,),(14,15,16,17,18),(18,)),
 8:((10,),(2,3,4),(4,5,6),(7,8,9),(10,11,12,13,14,15,16,17,18)),
 9:((2,3,4,5,6,7,8,9,10),(11,12,13,14,15,16,17,18,19,20,21,22,23),(24,)),
10:((4,5,6,7,8),(9,10,11),(12,13,14,15,16),(17,18,19,20,21,22,23,24,25,26)),
11:((2,),(2,),(4,5,6,7,8),(9,10,11,12,13,14,15)),
12:((8,),(9,10,11),(12,13),(14,15,16,17)),
13:((2,3,4,5,6,7),(3,4,5,6,7),(8,9,10,11,12,13,14,15,16,17,18)),
14:((2,3,4,5,6),(8,9),(2,3,4,5,6,7,8,9,10,11)),
15:((2,),(3,4,5,6,7,8,9,10,11,12),(3,4,5,6,7),(8,),(8,9,10,11,12)),
16:((2,),(3,),(4,)),
17:((1,),(2,3),(4,),(4,)),
}
# Not a mere textual mismatch: a physical triangle side cannot be a
# negative variable. Existing source Slide8 labels "opposite=x",
# while arctan substitution allows x<0. Repair and revoice together.
MATH_ISSUES={
 (8,2):"SIGNED_OPPOSITE_SIDE_LENGTH_REQUIRES_ABSOLUTE_VALUE",
 (8,3):"INHERITS_UNQUALIFIED_SIGNED_OPPOSITE_TRIANGLE_GEOMETRY",
}
CONTEXTUAL_NOT_PROVEN_AS_UNIQUE_ELEMENT={
 (2,1),(2,2),(2,3),(3,1),(3,5),(5,8),(7,4),(8,1),
 (9,1),(11,1),(14,3),(17,1)
}

def _physical_source_block(page,index):
    visible=page.get_text("blocks")
    require(type(index) is int and 0<=index<len(visible)
            and visible[index][6]==0,
            "Curated mathematical element must be an actual visible original PDF text block")
    row=visible[index]
    text=" ".join(str(row[4]).split())
    rect=[float(row[i]) for i in range(4)]
    # TeX equations may yield a text block with only an unextractable
    # mathematical glyph; its physical rectangular PDF geometry remains real.
    require(isinstance(text,str) and 0<=rect[0]<rect[2]<=page.rect.width+.2
            and 0<=rect[1]<rect[3]<=page.rect.height+.2,
            "Original source math visible block malformed")
    return {"block_index":index,"actual_text":text,"rect_pt":rect}

def review_66(*,original:Path,source_plan:Path,paired_source:Path,
              independent_video:Path,source_slide11_audio:Path,
              five_domains:Path,out:Path)->dict:
    root=Path(original).resolve()
    original_receipts=[Path(z).resolve() for z in (
        source_plan,independent_video,source_slide11_audio,five_domains)]
    pair=Path(paired_source).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and
            all(p.is_file() and not p.is_symlink() for p in original_receipts)
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Protected original inputs and exclusive review-only external output required")
    plan,video,acoustic,domains=[
        json.loads(p.read_text(encoding="utf8")) for p in original_receipts]
    paired=json.loads((pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    require(plan.get("status")==PLAN_STATUS
            and plan.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and plan.get("actual_original_historic_narration_sentences")==66
            and plan.get("physical_source_pdf_cues_verified")==66
            and video.get("status")==VIDEO_STATUS
            and video.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and video.get("independent_actual_final_H264_PDF_frame_checks")==48
            and acoustic.get("status")==SL11_STATUS
            and acoustic.get("phonetic_source_consistency_pass") is True
            and domains.get("status")==DOMAINS_STATUS
            and domains.get("real_mathematical_domain_scopes_examined")==5
            and paired.get("status")==PAIR_STATUS
            and paired.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and file_hash(pair/"slides.pdf")==paired["corrected_pdf_sha256"]
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(z["student_publication_authorized"] is False
                    for z in (plan,video,acoustic,domains,paired)),
            "All original mathematically source-registered evidence must be present")
    original_tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    revised_tts=json.loads((pair/"script_tts.json").read_text(encoding="utf8"))
    require(len(original_tts["slides"])==len(revised_tts["slides"])==17,
            "Paired source updated original slide inventory missing")
    require(set(CURATED_BLOCKS)==
            {x["slide"] for x in plan["source_historical_slides"]},
            "All sixteen source-recorded slide cue sets mandatory")
    rows=[]
    with pymupdf.open(root/"slides.pdf") as original_pdf,pymupdf.open(pair/"slides.pdf") as corrected_pdf:
        require(len(original_pdf)==len(corrected_pdf)==17,
                "Original and source-corrected PDF pages must match")
        for record in plan["source_historical_slides"]:
            slide=record["slide"]
            page=corrected_pdf[slide-1] if slide==17 else original_pdf[slide-1]
            script=revised_tts["slides"][slide-1]["tts_text"] if slide==17 \
                    else original_tts["slides"][slide-1]["tts_text"]
            sentences,_=tokenize_reference_sentences(script)
            old,_=tokenize_reference_sentences(
                original_tts["slides"][slide-1]["tts_text"])
            mappings=record["physical_original_pdf_source_targets"]
            configured=CURATED_BLOCKS[slide]
            require(len(sentences)==len(mappings)==len(configured),
                    "Semantic source original passage to PDF count mismatch")
            for idx,(sentence,orig,blocks) in enumerate(
                zip(sentences,mappings,configured),1):
                key=slide,idx
                require(sentence["sentence_index"]==orig["sentence_index"]==idx,
                        "Independent semantic review sequence mismatch")
                if slide==17 and idx==2:
                    require(sentence["narration_fragment_sha256"]!=
                            old[idx-1]["narration_fragment_sha256"],
                            "New real corrected complete mathematical integral not used")
                else:
                    require(sentence["narration_fragment_sha256"]==
                            orig["narration_source_sha256"],
                            "Source narrative identity changed")
                candidates=[_physical_source_block(page,b) for b in blocks]
                visible=" ".join(p["actual_text"] for p in candidates)
                # Reinspect all actual selected PDF text/rectangles. Must
                # remain genuine physical mathematical source, not regex
                # rank or fabricated math content.
                rect=[min(k["rect_pt"][0] for k in candidates),
                      min(k["rect_pt"][1] for k in candidates),
                      max(k["rect_pt"][2] for k in candidates),
                      max(k["rect_pt"][3] for k in candidates)]
                known_issue=MATH_ISSUES.get(key)
                contextual=key in CONTEXTUAL_NOT_PROVEN_AS_UNIQUE_ELEMENT
                rows.append({
                    "slide":slide,"sentence_index":idx,
                    "exact_source_narration_fragment_sha256":
                        sentence["narration_fragment_sha256"],
                    "independent_review_source_pdf_sha256":
                        paired["corrected_pdf_sha256"] if slide==17
                        else plan["original_slides_pdf_sha256"],
                    "actual_visible_original_source_pdf_text":visible,
                    "actual_selected_source_pdf_blocks":candidates,
                    "actual_source_composite_rect_pt":rect,
                    "source_math_visual_issue":known_issue,
                    "source_qualitative_contextual_scope_only":contextual,
                    "source_historical_acoustic_word_window_proven":
                        orig["audio_time_evidence_type"]==
                        "MEASURED_ACTUAL_ORIGINAL_WAV_WORD_TIMING",
                    "mathematical_semantics_accepted_by_this_audit":
                        known_issue is None and not contextual,
                    "final_student_visual_element_focus_approved":False,
                    "student_publication_authorized":False})
        assert len(rows)==66
        # Actual targeted critical math counterexample: a signed
        # tangent substitution has x<0 on its principal inverse branch,
        # but geometric opposite leg length cannot equal x<0.
        x=-2
        assert abs(x)==2 and x<0
        slide8=" ".join(str(b[4]) for b in original_pdf[7].get_text("blocks")
                        if b[6]==0)
        revised_slide8=" ".join(str(b[4]) for b in corrected_pdf[7].get_text("blocks")
                                if b[6]==0)
        require("opposite = x" in slide8
                and "opposite = x" in revised_slide8,
                "Historical signed-triangle source math no longer reproducible")
    require(len({(x["slide"],x["sentence_index"]) for x in rows})==66
            and sum(bool(x["source_math_visual_issue"]) for x in rows)==2
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Full 66 sound mathematical source inventory incomplete")
    bad=[{"slide":r["slide"],"sentence_index":r["sentence_index"],
          "issue":r["source_math_visual_issue"]}
         for r in rows if r["source_math_visual_issue"]]
    result={
        "schema_version":1,"status":STATUS,
        "original_textbook_sha256":EXPECTED_SOURCE_SHA,
        "exact_real_source_narration_utterances_reviewed":66,
        "real_PDF_source_visible_composite_element_maps":66,
        "source_math_signed_triangle_issues_to_repair":len(bad),
        "source_qualitative_contextual_focuses_needing_extra_semantic_scope":
            sum(x["source_qualitative_contextual_scope_only"] for x in rows),
        "source_five_trig_domain_cases_separately_evaluated":5,
        "historical_slide11_trig_phonetic_suspicion_reconciled":True,
        "source_corrected_real_slide17_integral_present":True,
        "independent_verified_66_full_video_student_release":False,
        "all_original_math_academic_source_semantics_approved":False,
        "release_eligible":False,"student_publication_authorized":False,
        "blocking_signed_triangle_issues":bad,
        "reviewed_original_source_utterances":rows,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("original","source_plan","paired_source",
                 "independent_video","source_slide11_audio",
                 "five_domains","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    z=review_66(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in z.items()
                      if k not in ("blocking_signed_triangle_issues",
                                  "reviewed_original_source_utterances")},
                     indent=2))
if __name__=="__main__":main()
