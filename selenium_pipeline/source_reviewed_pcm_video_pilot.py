"""Genuine WAV-backed, source-reviewed element highlight REVIEW MP4 handoff.

This is NOT a student-production acceptance gate. Each accepted visual marker
is tied to an explicitly source-quoted reviewer decision and separately
supplied externally staged PCM audio (not an existing whole-slide WAV).
A decoded before/after transition check verifies encoded pixels, but acoustic
script fidelity and mathematical listening QA remain independently unproven.
"""
from __future__ import annotations
from pathlib import Path
from .figure_source_identity import require,_sha
from .reviewed_unpaid_tts_handoff import stage_reviewed_unpaid_audio_jobs
from .sourcebound_element_pcm_receipts import inspect_supplied_element_wavs
from .incremental_element_review_encoder import encode_segment_highlight_review
from .independent_encoded_transition_audit import verify_encoded_boundaries

def stage_source_reviewed_pcm_video_pilot(*,folder:Path,packet:dict,
                                         wav_receipts:list[dict],
                                         destination:Path)->dict:
    folder,destination=Path(folder).absolute(),Path(destination).absolute()
    require(destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(folder),
            "Only a new isolated review-video destination is allowed")
    review=stage_reviewed_unpaid_audio_jobs(folder=folder,packet=packet)
    jobs=review["candidate_tts_jobs"]
    require(2<=jobs["job_count"]<=40
            and review["attested_utterances"]==jobs["job_count"]
            and jobs["paid_tts_execution_authorized"] is False,
            "Two or more genuine separately reviewed original utterances required")
    checked=inspect_supplied_element_wavs(folder=folder,jobs=jobs,
                                           receipts=wav_receipts)
    original=_sha(folder/"slides.pdf")
    require(checked["audio_clip_count"]==jobs["job_count"]
            and checked["slides_sha256"]==original,
            "Not all reviewed original element WAVs independently supplied")
    technical=encode_segment_highlight_review(
        slides=folder/"slides.pdf",jobs=jobs,
        clips=checked["encoder_clip_inputs"],destination=destination)
    mp4=destination/"element_highlight_review.mp4"
    transitions=verify_encoded_boundaries(
        slides=folder/"slides.pdf",mp4=mp4,receipt=technical)
    require(transitions["transition_count"]==jobs["job_count"]-1
            and _sha(mp4)==transitions["encoded_mp4_sha256"]
            and _sha(folder/"slides.pdf")==original
            and technical["actual_encoded_duration_s"]<600,
            "Encoded original WAV boundary or visible PDF element failed review")
    return {"status":"REAL_PCM_SOURCE_REVIEWED_HIGHLIGHT_MP4_TECHNICAL_PILOT_ONLY",
            "original_slide_sha256":original,
            "encoded_mp4_sha256":_sha(mp4),
            "actual_encoded_mp4_duration_s":technical["actual_encoded_duration_s"],
            "independent_boundary_transition_checks":transitions["transition_count"],
            "reviewed_original_utterances":review["attested_utterances"],
            "unreviewed_original_utterances":review["unresolved_utterances"],
            "physical_element_pcm_chunk_count":checked["audio_clip_count"],
            "spoken_text_audio_fidelity_verified":False,
            "claimed_tts_voice_acoustically_verified":False,
            "all_original_lecture_elements_reviewed":review["unresolved_utterances"]==0,
            "academic_math_and_listening_qa_completed":False,
            "production_video_accepted":False,
            "student_publication_authorized":False}
