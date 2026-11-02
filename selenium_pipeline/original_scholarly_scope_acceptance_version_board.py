"""Read-only source-hash/author-version scholarly acceptance and gap board.

Reuse previously verified independent physical receipts. Never infer that a
sampled equation/WAV/graph glyph means exhaustive lecture approval. Newer
regenerated 20/17-slide versions are separate, not present in this immutable
original-corpus acceptance board and must be registered independently.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .evidence_reuse_contract import file_sha256,EvidenceReuseBlocked
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_THOMAS_VERSIONED_SCIENCE_ACCEPTANCE_REUSE_AND_OPEN_SCOPE_LEDGER_NONPRODUCTION"
RECEIPTS={
    "original_41_gap":"20261102_PR445_CURRENT_41_SOURCE_ACADEMIC_DEFICITS/"
       "ORIGINAL_41_SOURCE_38_WAV_PIXEL_FOCUS_REMAINING_ACADEMIC_DEFICITS.json",
    "all_six_figure_art":"20261102_PR454_ALL_SIX_FIGURE_SCIENCE_WORKLIST/"
       "ORIGINAL_ALL_SIX_PUBLISHER_ARTWORK_SOURCE_RECONCILIATION.json",
    "original_86_math_wav_video":"20261102_PR457_MATH_WAV_VIDEO_REUSE_VERIFIED/"
       "THREE_ORIGINAL_SCIENCE_AUDIO_VIDEO_EVIDENCE_REUSED.json",
    "prior_corrected_84":"20261102_PR458_CORRECTED_AUTHOR_ACCEPTANCE_LINEAGE/"
       "PR362_CORRECTED_ACCEPTANCE_NOT_FROZEN_AUTHOR.json",
    "original_83_first_six_labels":
       "20261102_PR465_FIG83_PRINTED_FUNCTION_AND_AXIS_TICK_PIXEL_AUDIT/"
       "THOMAS84_FIG83_SIX_VECTOR_PRINTED_GLYPH_PATCH_PIXELS.json",
    "original_83_four_endpoints":
       "20261102_PR467_FIG83_NONZERO_ENDPOINT_SOURCE_TICK_PIXELS/"
       "FOUR_ORIGINAL_INVERSE_SINE_SECANT_NEGATIVE_POSITIVE_ONE_TICKS.json",
}
EXPECTED_SLIDES={"8.4":17,"8.5":11,"8.6":13}

def _require(ok,reason):
    if not ok: raise EvidenceReuseBlocked(reason)

def _read(cp:Path,key:str):
    path=cp/RECEIPTS[key]
    _require(path.is_file() and not path.is_symlink(),
             "Missing prior accepted source version evidence: "+key)
    return json.loads(path.read_text("utf8")),file_sha256(path)

def board(*,checkpoint:Path,original:Path)->dict:
    import pymupdf
    checkpoint=Path(checkpoint).absolute()
    original=Path(original).absolute()
    _require(original.is_dir() and not original.is_symlink()
             and checkpoint.is_dir(),"Original/accepted evidence must be real physical files")
    evidence={key:_read(checkpoint,key) for key in RECEIPTS}
    old=evidence["original_41_gap"][0]
    art=evidence["all_six_figure_art"][0]
    wav=evidence["original_86_math_wav_video"][0]
    prior=evidence["prior_corrected_84"][0]
    six=evidence["original_83_first_six_labels"][0]
    four=evidence["original_83_four_endpoints"][0]
    _require(old.get("original_source_slides")==41
             and old.get("original_source_pixel_and_audio_math_focus_slides")==38
             and old.get("true_original_spoken_element_samples_total")==47
             and old.get("student_publication_authorized") is False
             and old.get("full_original_production_gate_passed") is False,
             "Historical original source WAV/pixel academic gap must stay open")
    _require(art.get("original_frozen_41_source_slides")==41
             and art.get("all_six_original_author_figure_source_artwork_matched") is True
             and art.get("source_figure_identity_missing_count")==0
             and art.get("student_publication_authorized") is False,
             "Cannot claim missing original figure source identity resolved without source proof")
    _require(wav.get("student_publication_authorized") is False
             and wav.get("all_math_WAV_and_encoded_pixels_completely_certified") is False
             and set(wav.get("accepted_scopes",{}))=={
                "selected_exact_reduction_math",
                "sampled_original_WAV_word_to_visual",
                "actual_joined_mp4_decoded_source_pixels"},
             "Existing original selected math/audio/video evidence conflated with full scope")
    _require(prior.get("prior_scope_decision")=="REUSE_VERIFIED"
             and prior.get("separate_original_author_version_decision")=="TARGETED_REVALIDATION"
             and prior.get("prior_original_corrected_66_source_cue_automated_review_accepted") is True
             and prior.get("student_publication_authorized") is False,
             "Previously accepted corrected original lecture is a distinct author version")
    pub84,author84=ORIGINAL_PINS["8.4"]
    _require(six.get("publisher_source_pdf_sha256")==pub84
             and six.get("original_author_slides_pdf_sha256")==author84
             and six.get("three_inverse_function_labels_pixel_matched")==3
             and six.get("three_graph_axis_zero_tick_labels_pixel_matched")==3
             and six.get("student_publication_authorized") is False,
             "Original source 6 labels do not match frozen author version")
    _require(four.get("publisher_source_sha256")==pub84
             and four.get("author_original_slides_sha256")==author84
             and four.get("reused_existing_six_source_label_glyph_receipt_sha256")==
                   evidence["original_83_first_six_labels"][1]
             and four.get("original_previous_glyphs_accepted_without_reanalysis")==6
             and len(four.get("newly_source_anchored_nonzero_ticks",{}))==4
             and four.get("student_publication_authorized") is False,
             "Four new printed endpoints cannot silently revalidate prior labels")
    sections={}
    for section,n in EXPECTED_SLIDES.items():
        pub,author=ORIGINAL_PINS[section]
        folder=original/section
        files=(folder/"source.pdf",folder/"slides.pdf",folder/"slides.tex")
        _require(all(p.is_file() and not p.is_symlink() for p in files),
                 "Original published/author mathematical source missing")
        _require(file_sha256(files[0])==pub and file_sha256(files[1])==author,
                 "Changed original author version; do not inherit old lecturer-science approval")
        with pymupdf.open(files[1]) as deck:
            _require(len(deck)==n,"Original author slide count changed")
        rows=old["original_sections"][section]
        focused=rows["at_least_one_verified_source_focus_slide_count"]
        _require(type(focused)==int and 0<=focused<=n,
                 "Original sampled focus count invalid")
        sections[section]={
            "original_publisher_source_sha256":pub,
            "frozen_original_author_slides_pdf_sha256":author,
            "original_author_slides_count":n,
            "source_original_substantive_slides_with_one_or_more_spoken_focus_samples":focused,
            "full_per_symbol_source_equation_semantics_accepted":False,
            "all_actual_source_graph_labels_axes_and_curves_certified":False,
            "every_original_WAV_word_phonetically_certified":False,
            "full_every_element_decoded_MP4_source_highlight_sync_accepted":False,
            "student_publication_authorized":False,
        }
    _require(sum(x["source_original_substantive_slides_with_one_or_more_spoken_focus_samples"]
                 for x in sections.values())==38
             and sum(x["original_author_slides_count"] for x in sections.values())==41,
             "Prior source original full-slide counts silently changed")
    _require(prior.get("frozen_uncorrected_original_author_pdf_sha256")==author84
             and prior.get("prior_corrected_author_pdf_sha256")!=author84,
             "Old corrected and original academic release versions must never collapse")
    # A prior review candidate may be reused as a candidate; no release.
    return {
        "status":STATUS,
        "accepted_evidence_reused_without_computation_or_paid_regeneration":True,
        "prior_immutable_receipt_sha256":{
            k:sha for k,(value,sha) in evidence.items()},
        "frozen_original_section_author_version_receipts":sections,
        "frozen_original_total_41_slides":41,
        "original_38_sampled_spoken_focus_slides_only":38,
        "original_47_spoken_focus_samples_not_every_utterance":47,
        "original_six_figure_publisher_artwork_identities_already_accepted":6,
        "original_83_specific_vector_printed_author_bitmap_glyphs_accepted":10,
        "corrected_prior_author_84":{
            "author_pdf_sha256":prior["prior_corrected_author_pdf_sha256"],
            "same_textbook_as_frozen_original_84":True,
            "same_author_pdf_as_frozen_original_84":False,
            "previous_66_cue_automated_technical_review_candidate_reused":True,
            "all_original_WAV_phonemes_independently_certified":False,
            "student_publication_authorized":False,
        },
        "distinct_live_regenerated_85_20_slide_lecture":
             "SEPARATE_AUTHOR_VERSION_NOT_ONBOARDED_TO_THIS_FROZEN_ORIGINAL_LEDGER",
        "distinct_live_regenerated_86_17_slide_lecture":
             "SEPARATE_AUTHOR_VERSION_NOT_ONBOARDED_TO_THIS_FROZEN_ORIGINAL_LEDGER",
        "remaining_priorities":[
            "Complete actual author equation-to-publisher each-intermediate-symbol scholarly comparison by original version, reusing already accepted exact examples",
            "Verify source graph remaining angular labels, tick values and mathematical curve correctness without redoing accepted source artwork identity",
            "Verify every original source WAV phonetic concept and visual element timing, retaining sound-alike tolerance but rejecting obvious errors such as c read as circa",
            "Onboard regenerated 20/17 author slide versions using their own real SHA-bounded independent academic/media acceptance",
            "Full decoded H264-AAC complete lecture source scholarly acceptance before any authorized student release",
        ],
        "full_41_original_scholar_scientific_release_pass":False,
        "full_41_original_audio_and_media_release_pass":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint",type=Path,required=True)
    ap.add_argument("--original",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args(argv)
    _require(a.out.parent.is_dir() and not a.out.exists()
             and not a.out.is_relative_to(a.original.absolute()),
             "New versioned output only; never modify originals or prior receipts")
    result=board(checkpoint=a.checkpoint,original=a.original)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
                      "original_slides":41,
                      "source_focus_slides":38,
                      "source_figure_images_already_matched":6,
                      "Fig83_label_pixels":10,
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
