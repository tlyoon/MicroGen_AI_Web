"""Retain earlier PR362 technically accepted CORRECTED Thomas §8.4 revision.

Its publisher source SHA matches the frozen 17-slide original, but its
corrected author PDF SHA does NOT. Never rerun or discard old successful
math/TTS/video source science; never transplant its acceptance onto the
different uncorrected author PDF or authorize student/Moodle publication.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS
from .evidence_reuse_contract import AcceptedClaim,ProposedCheck,preflight

STATUS="THOMAS84_CORRECTED_PR362_ACCEPTANCE_REUSED_DISTINCT_ORIGINAL_AUTHOR_LINEAGE_NONPRODUCTION"
REPORT="20261029_PR362_COMPLETE_66_SOURCE_MATH_TTS_VIDEO_COMBINED_QA.json"
AUTHOR="20261029_PR361_SIGNED_TRIANGLE_SOURCE_PDF_SCRIPT_CORRECTED_NO_AUDIO/slides.pdf"
MOVIES=(
    "20261029_PR361D_SLIDE8_SLIDE17_BOTH_SOURCE_MATH_CORRECTED_FULL_REAL_MP4S/"
    "part_01/Thomas_8_4_part01_SIGNED_TRIANGLE_SOURCE_KORE_CORRECTED_REVIEW_ONLY.mp4",
    "20261029_PR361D_SLIDE8_SLIDE17_BOTH_SOURCE_MATH_CORRECTED_FULL_REAL_MP4S/"
    "part_02_OriginalSource_Slide17_MATH_CORRECTED_REVIEW_ONLY.mp4",
)
SCOPE="corrected_17_slide_66_cue_automated_math_TTS_video_candidate"
STANDARD="original_Thomas84_pr362_owner_flexible_review_only"

def reconcile(*,original:Path,checkpoint:Path)->dict:
    original=Path(original).absolute()
    checkpoint=Path(checkpoint).absolute()
    publisher,original_author=ORIGINAL_PINS["8.4"]
    paths={
        "original_textbook":original/"source.pdf",
        "uncorrected_author":original/"slides.pdf",
        "corrected_author":checkpoint/AUTHOR,
        "historic_receipt":checkpoint/REPORT,
        "movie_1":checkpoint/MOVIES[0],
        "movie_2":checkpoint/MOVIES[1],
    }
    require(all(p.is_file() and not p.is_symlink() for p in paths.values()),
            "Prior physically verified source/movies or original professor author source missing")
    hashes={key:_sha(path) for key,path in paths.items()}
    require(hashes["original_textbook"]==publisher
            and hashes["uncorrected_author"]==original_author,
            "Frozen original source version has changed")
    prev=json.loads(paths["historic_receipt"].read_text("utf8"))
    require(prev.get("status")==
            "THOMAS84_ALL_THREE_QA_CHECKS_COMPLETED_SOURCE_MATH_PHONETIC_MEDIA_PASS_REVIEW_ONLY"
            and prev.get("original_textbook_sha256")==publisher
            and prev.get("corrected_actual_source_pdf_sha256")==hashes["corrected_author"]
            and hashes["corrected_author"]!=hashes["uncorrected_author"]
            and prev.get("independently_audited_actual_final_movie_SHA256")==[
                hashes["movie_1"],hashes["movie_2"]]
            and len(prev.get("real_complete_movies_seconds",[]))==2
            and all(0<float(s)<600 for s in prev["real_complete_movies_seconds"])
            and all(prev.get(key) is True for key in (
                "math_source_automated_review_criteria_satisfied",
                "owner_flexible_soundalike_TTS_criteria_satisfied",
                "source_visual_element_relevance_criteria_satisfied",
                "actual_H264_AAC_media_integrity_criteria_satisfied",
                "release_candidate_QA_gate_pass",
            ))
            and prev.get("student_publication_authorized") is False
            and prev.get("publication_was_performed") is False
            and prev.get("independent_human_aural_voice_identity_certified") is False
            and prev.get("every_individual_spoken_word_acoustically_proven") is False,
            "Do not silently promote old §8.4 candidate or incorrectly equate author versions")
    # The prior source-grounded accepted claim is reused by the generic
    # immutable receipt/scope verifier, WITHOUT modifying any historical file.
    old=AcceptedClaim(
        component_id="Thomas §8.4 corrected authored revision",
        scope=SCOPE,standard=STANDARD,
        source_sha256=publisher,
        author_sha256=hashes["corrected_author"],
        artifact_sha256=hashes["movie_1"],
        receipt_path=paths["historic_receipt"],
        receipt_sha256=hashes["historic_receipt"],
        evidence_claim_path=("release_candidate_QA_gate_pass",),
        previous_pr="#362")
    proposed=ProposedCheck(
        component_id=old.component_id,scope=SCOPE,standard=STANDARD,
        source_sha256=publisher,author_sha256=hashes["corrected_author"],
        artifact_sha256=hashes["movie_1"])
    decision=preflight(proposed,[old])
    require(decision.decision=="REUSE_VERIFIED"
            and decision.new_production_release_granted is False,
            "Previously successful corrected author review cannot be silently repeated or published")
    original_revision=preflight(ProposedCheck(
        component_id=old.component_id,scope=SCOPE,standard=STANDARD,
        source_sha256=publisher,author_sha256=original_author,
        artifact_sha256=hashes["movie_1"]),[old])
    require(original_revision.decision=="TARGETED_REVALIDATION",
            "Different uncorrected professor-authored deck cannot inherit corrected version acceptance")
    require(hashes=={key:_sha(path) for key,path in paths.items()},
            "Original/protected prior acceptance sources changed during lineage reconciliation")
    return {
        "status":STATUS,
        "original_publisher_textbook_sha256":publisher,
        "frozen_uncorrected_original_author_pdf_sha256":original_author,
        "prior_corrected_author_pdf_sha256":hashes["corrected_author"],
        "prior_corrected_full_review_movies_sha256":[hashes["movie_1"],hashes["movie_2"]],
        "prior_original_corrected_66_source_cue_automated_review_accepted":True,
        "prior_review_scope_fully_reused_without_reencoding_or_retts":True,
        "prior_scope_decision":decision.decision,
        "separate_original_author_version_decision":original_revision.decision,
        "prior_receipt_sha256":hashes["historic_receipt"],
        "original_author_and_corrected_author_same_bytes":False,
        "previous_version_manual_phonetic_completeness_certified":False,
        "student_publication_authorized":False,
        "next_unverified_scope":"Do not redo PR362 corrected source acceptance; "
            "only pursue genuinely new per-element claims or altered authored versions.",
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    require(args.out.parent.is_dir() and not args.out.exists()
            and not args.out.is_relative_to(args.original.absolute()),
            "Only fresh external author-lineage evidence receipt permitted")
    result=reconcile(original=args.original,checkpoint=args.checkpoint)
    with args.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
                      "corrected_author":result["prior_scope_decision"],
                      "different_uncorrected_author":result["separate_original_author_version_decision"],
                      "student_publication_authorized":False}))
if __name__=="__main__":
    main()
