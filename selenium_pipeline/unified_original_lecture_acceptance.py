"""Read-only full original-source lecture readiness: maths, PCM, pixels, TTS, QA.

Unverified, partial or absent evidence is a RELEASE BLOCKER, not a reason
to synthesize academic consent. No rendering, paid provider or publishing.
"""
from pathlib import Path
from .original_math_audio_release_ledger import summarize_original_review_readiness
from .sourcebound_production_video import verify_production_candidate
from .lecture_release_gate import verify_academic_lecture,verify_student_publication
from .figure_source_identity import _sha

def inspect_original_multimedia_acceptance(*,original_folder:Path,queue_root:Path,
                                            candidate:Path|None=None)->dict:
    f=Path(original_folder).absolute()
    q=Path(queue_root).absolute()
    review=summarize_original_review_readiness(queue_root=q,folder=f)
    original_sha=review["source_coverage_sha256"]
    blockers=[]
    if review["source_math_pending_or_disputed"]:
        blockers.append("INDEPENDENT_SOURCE_MATH_REVIEW")
    technical=False;human=False;publication=False;voice=False
    part_count=0
    if candidate is None:
        blockers.append("NO_VERIFIED_ORIGINAL_MULTIPART_ELEMENT_VIDEO")
    else:
        c=Path(candidate).absolute()
        if (not c.is_dir() or c.is_symlink() or
            c.is_relative_to(f) or f.is_relative_to(c) or
            not (c/"source.pdf").is_file() or
            (c/"source.pdf").is_symlink() or
            _sha(c/"source.pdf")!=original_sha):
            blockers.append("CANDIDATE_ORIGINAL_SOURCE_IDENTITY_MISMATCH")
        else:
            # Fresh decoding rechecks all encoded element target pixels,
            # exact WAV-vs-MP4 soundtrack and actual strict <600s parts.
            try:
                video=verify_production_candidate(c)
            except (ValueError,OSError,RuntimeError):
                blockers.append("UNVERIFIED_MP4_AUDIO_PIXEL_OR_DURATION")
            else:
                technical=True;part_count=len(video["parts"])
                # A technical MP4 is NOT proof of actual Kore provider/voice.
                if (not (c/"tts_input_manifest.json").is_file()
                    or not (c/"script.txt").is_file()):
                    blockers.append("MISSING_EFFECTIVE_TTS_VOICE_AND_SCRIPT_EVIDENCE")
                else:
                    try:
                        from .tts_effective_identity import verify_effective_identity
                        from .runner import blocks
                        import json
                        manifest=json.loads((c/"tts_input_manifest.json").read_text())
                        spoken=blocks((c/"script.txt").read_text(encoding="utf8"))
                        verify_effective_identity(manifest,spoken)
                    except (ValueError,OSError,RuntimeError):
                        blockers.append("UNVERIFIED_HOMOGENEOUS_SPOKEN_VOICE")
                    else:
                        voice=True
                # Do not even consider attested human release until actual
                # independent source math and effective TTS are established.
                if not review["source_math_pending_or_disputed"] and voice:
                    try:
                        verify_academic_lecture(c)
                    except (ValueError,OSError,RuntimeError):
                        blockers.append("MISSING_EXPLICIT_HUMAN_ACADEMIC_LISTENING_QA")
                    else:
                        human=True
                        try:
                            verify_student_publication(c)
                        except (ValueError,OSError,RuntimeError):
                            blockers.append("MISSING_SEPARATE_STUDENT_PUBLICATION_AUTHORIZATION")
                        else:
                            publication=True
    if technical and not voice:
        # Clear explicit voice evidence required; a waveform alone not TTS.
        pass
    elif technical and not human and review["source_math_pending_or_disputed"]:
        blockers.append("MISSING_HUMAN_ACADEMIC_AND_LISTENING_QA")
    return {
        "status":"ORIGINAL_LECTURE_READY" if publication and not blockers
                 else "ORIGINAL_LECTURE_RELEASE_BLOCKED",
        "original_utterances":review["original_utterances"],
        "independent_math_agreements":review["source_validated_ai_math_agreements"],
        "math_pending_or_disputed":review["source_math_pending_or_disputed"],
        "original_source_sha256":original_sha,
        "source_bound_decoded_audio_pixels_and_duration_verified":technical,
        "verified_mp4_parts":part_count,
        "homogeneous_voice_manifest_verified":voice,
        "explicit_human_academic_and_listening_approval_verified":human,
        "explicit_student_publication_record_verified":publication,
        "blocking_stages":sorted(set(blockers)),
        "student_publication_authorized":publication and not blockers,
        "actual_publication_performed":False}
