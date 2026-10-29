> **YOUTUBE PUBLICATION ADDENDUM — 18 October 2026:** The owner explicitly authorizes automatic publication of fully technically verified lecture videos to their **YouTube channel**, not Moodle. No human academic approval is required for this authorized YouTube publishing workflow. A pinned exact YouTube channel, one designated publisher machine, source/figure/audio/<600-second/highlight QA and resumable SHA-256 evidence remain mandatory. The uploader is implemented in a draft adapter, but no live upload has been performed. See [YouTube course publisher](YOUTUBE_COURSE_PUBLISH_ADAPTER_20261018.md). Earlier generic student-publication wording is superseded only for this specific approved YouTube mode; it never grants Moodle access.

# MicroGen_AI_Web — Owner Amendment: Automatic Internal Stage Progression

**Effective 18 October 2026. Latest explicit instruction by the project owner.**

**Authoritative change:** **No human approval is required to proceed from one internal generation/development stage to the next** after the current stage satisfies its required machine-verifiable technical contract. The system must advance automatically, without asking the owner to approve mathematics, figures, narration, voice, or highlighting at each handoff. Human academic and listening review is OPTIONAL for internal work and may be recorded separately without blocking the pipeline.

This is an explicit supersession of the **mandatory-human-stage-gate portions** of
`EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md`,
`GEMINI_UI_MODEL_AND_LECTURE_RELEASE_GATES_20261018.md`,
and `EVIDENCE_LOCKED_CANDIDATE_HANDOFF_20261018.md`.
The historical text of those records remains intact or visibly annotated.

## Stage advancement policy

1. **Default: automatic progress.** Figures → slides → narration → script QA → TTS → TTS QA → verified synchronized multipart video → immutable technical candidate package can all proceed automatically, so long as the required technical preflight, stage integrity and downstream checks pass. No per-stage human academic approval or independent listening signature is required.
2. **Technical failures still block.** Missing or cropped multipanel figures, broken source/caption mapping, missing slide references, malformed narration, inconsistent effective TTS model/voice, incomplete fallback evidence, invalid WAV/PCM, QA defects, damaged source hashes, missing synchronized highlights, stale pixel evidence, durations **not strictly less than 600 seconds**, or unsourced element mappings must fail closed. Do not weaken these checks or claim an unsuccessful stage passed.
3. **No invented human approvals.** If a stage advances on technical checks alone, label it `technical_only`, `human_review_record_verified: false`, and `student_published: false`. A green automated QA run is **not** proof that a lecturer reviewed the mathematics or listened to the lecture. Human review can still be performed later for independent quality assurance but is not a dependency for the next internal stage.
4. **Audio and video handoffs.** The existing isolated TTS repaired-audio export and source-bound highlighted-video candidate handoff have **technical-only, no-signature routes**. Both recheck the original source, effective voice/provenance, retry journal where relevant, measured PCM or MP4 duration, encoded highlighted pixels, and frozen hashes. Both use new, isolated destinations and never overwrite originals.
5. **Separate external publication.** Automatic internal continuation is **not** authorization to upload a video to Moodle, make it student-facing, overwrite historical student media, or distribute files externally. That distinct action retains its explicit publication authorization and source-bound safety checks. An approved production-generation *internal artifact* must not be mislabeled as `student_published`.
6. **No replacement or resource-policy changes.** Original source PDFs, slide decks, script/WAV/MP4 files, review evidence and dirty three-PC production checkouts remain protected. HP, Dell-115 and Yoga6 only; no Zenbook, no GCS leasing, no unauthorized reassignment. Gemini Flash-Lite/Kore primary, Flash/Kore secondary, conditional Cloud Chirp 3 HD/Corey after independently witnessed retries; no mixed voices; no Whisper.
7. **No false delivery claims.** A draft PR or synthetic FFmpeg test does not make the full production generator ready or mean a real lesson has been generated. The three-PC legacy static-video path remains disabled until it can produce true element-synchronized multipart MP4s.

## Binding code changes

- `runner.valid("video")`, `three_pc_worker.stage_recorded("video")` and `process_job` use actual `production_video_contract.verify_series`, not `verify_academic_lecture`, for internal stage progression. The historical static-video encoder remains blocked; a verified multipart lesson may be marked technically complete without a human signature.
- `microgen_batch.process_one` resumes previously verified technically compliant lectures without asking for human approval. It must not run the old static encoder when the technical contract is absent.
- `tts_qa_promotion.export_verified` can export repaired audio after full machine QA, voice/PCM/fallback evidence and immutable-hash validation. The separate `export_reviewed` still requires genuine human attestation if a **human-reviewed** label is requested.
- `review_candidate_handoff.stage_technically_verified_candidate` can create an independently re-auditable isolated candidate without a reviewer signature. The separate `stage_human_reviewed_candidate` retains its authentic optional signed path.
- The independent academic review and student-publication validators remain available. The former is optional for internal progression. The latter is **only** for an actual external publication authorization.

## Test policy

Regression tests must explicitly verify a clean technical lesson/audio/candidate advances **without** any human approval file, and still reject technical corruption, altered files, 600+ second videos, inconsistent voices, fabricated approval labels, overwrite attempts and unauthorized external publication.

**No production or student-release authority is conveyed by this amendment.**
