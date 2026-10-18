> **SUPERSEDED MANDATORY-HUMAN STAGE GATE (18 October 2026):** The owner now explicitly authorizes **unattended internal stage progression on verified technical QA**. This document's human approval requirements are optional for internal generation and review handoffs; they do **not** control whether the next internal stage starts. External student publication remains a separate authorized action. See [latest owner amendment](OWNER_AMENDMENT_AUTOMATIC_INTERNAL_STAGE_PROGRESS_20261018.md). The original narrative below is historical.

# MicroGen_AI_Web — Evidence-Locked Human-Reviewed Candidate Handoff

**Effective development date: 18 October 2026. Status: DRAFT / NOT PRODUCTION-RELEASE AUTHORIZATION.**

This additional stage preserves the effective contract in
[EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md](EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md)
and the prior
[SOURCEBOUND_HIGHLIGHT_WINDOW_PAUSE_QA_20261018.md](SOURCEBOUND_HIGHLIGHT_WINDOW_PAUSE_QA_20261018.md).

## Purpose and state transitions

The reviewed-element pipeline already produces isolated, source-bound, **review-only**
multipart MP4s with encoded-pixel checks. The new module
`selenium_pipeline.review_candidate_handoff` adds a **controlled, nonpublishing**
handoff from a verified frozen review bundle to an independently human-reviewed
candidate package. It **does not** create a production `lecture_completion.json`,
`part_receipt.json` with accepted status, or anything for Moodle.

The three distinct states are:

1. **TECHNICALLY_VERIFIED_CANDIDATE_AWAITING_HUMAN_REVIEW**: a read-only fresh
   inspection checks actual encoded MP4s (strictly below 600 seconds), all
   source-linked narrated-element WAVs, hashes, slide geometry, audio timeline,
   beginning/middle/end highlight samples, unhighlighted pauses, and the
   original review report. It outputs a stable SHA-256 candidate fingerprint
   without writing any approval or publication file.
2. **EXPLICIT_HUMAN_REVIEW_RECORDED_CANDIDATE_ONLY**: an *independently authored*
   human review record, residing **outside** source, frozen audio and review
   trees, must name the fingerprint and exact source/slides hash. All five
   independent review flags must be true. A JSON claim is traceability, not
   a cryptographic guarantee that an identifiable person actually listened.
3. **HUMAN_REVIEWED_TECHNICAL_CANDIDATE_NOT_PUBLISHED**: only after successful
   review matching, the module copies the full source-bound review evidence
   (source PDF, slide deck, authored element plan, original element WAVs,
   storyboard, staged WAVs, original review MP4s, combined audio, decoded pixel
   QA, clean slide PDFs, and reference images) into an **entirely new isolated
   directory**. It validates every copied hash and independently reruns the
   encoded-pixel review from inside the copied package. The candidate manifest
   explicitly records production and student publication as **false**.

No model, TTS, ASR, cloud API or browser call is performed by this handoff.

## Read-only candidate fingerprint

Run from the repository with the existing approved environment:

```powershell
python -m selenium_pipeline.review_candidate_handoff `
  --source "PATH\TO\subchapter\source.pdf" `
  --slides "PATH\TO\subchapter\slides.pdf" `
  --authored "PATH\TO\author_element_plan.json" `
  --audio "PATH\TO\frozen_original_element_wavs" `
  --review-root "PATH\TO\previous_isolated_review"
```

The output provides a content fingerprint and a per-file SHA-256 inventory.
It cannot generate an academic approval. Files may be in different directory
locations on different PCs, but **the same bytes** produce the same fingerprint
because absolute paths are not included.

## Human attestation — illustrative FIELD SCHEMA ONLY

After **actual independent review**, the lecturer may create a separate JSON
file outside all three input trees with the following fields. This example is
**not an approval** and intentionally contains false flags:

```json
{
  "schema_version": 1,
  "status": "PENDING_INDEPENDENT_HUMAN_REVIEW",
  "human_authored_explicit_approval": false,
  "reviewed_by": "",
  "approved_at_utc": "",
  "candidate_sha256": "",
  "source_sha256": "",
  "slides_sha256": "",
  "mathematics_and_source_approved": false,
  "complete_figures_and_panels_approved": false,
  "all_original_element_wavs_listened_and_approved": false,
  "semantic_spoken_highlight_mapping_approved": false,
  "uniform_tts_voice_listening_approved": false,
  "student_publication_permitted": false
}
```

The status may be set to `human_candidate_review_approved` and the flags
set to true **only by the independent human reviewer after performing those
checks**. A green CI/test suite does not substitute for the actual review.

The review artifact must record the exact candidate, source and slide hashes,
the reviewer's identity and a real UTC time. Each of the following checks is
separate: mathematical accuracy and source adherence; complete readable
multipanel figures; listening to **every original element WAV**; semantic
correctness of spoken-element highlighting; and uniform actually heard voice.

## Independently reviewed candidate packaging

Only after a genuine approved JSON exists, a separate command may use the same
five `--source/--slides/--authored/--audio/--review-root` arguments plus:

```powershell
  --approval "PATH\TO\independent_human_review.json" `
  --destination "PATH\TO\NEW_isolated_candidate_directory"
```

The destination must **not exist** and must be outside the original source,
audio, review and human-approval trees. Existing lecture files are never
overwritten or deleted. The destination can be independently rechecked using
`selenium_pipeline.element_highlight_workflow.verify_rendered(..., output=None)`.
It contains the original review part filenames and source files for audit,
but **no accepted production receipt**, no Moodle publication and no student
release permission. It never automatically copies to the source-adjacent
student-facing delivery directory.

## Non-negotiable limitations

- The current browser selector proves Flash *family*, not exact backend Gemini
  3.8 version. The element scene `voice_id` is a declared model/voice ID, not
  cryptographic proof of the actual TTS service: the handoff explicitly records
  `voice_origin_independently_verified: false`. It is NOT a replacement for
  the agreed Gemini Flash-Lite/Kore, Flash/Kore and conditional Cloud
  Chirp/Corey authorization and audio-provenance gates.
- Window/pause pixel QA is sampled, not a full phoneme-level alignment or
  independent semantic correctness proof.
- TTS output cannot be converted from an entire slide WAV into multiple
  spoken elements without separately sourced element WAVs and independent
  human listening.
- **All original production assets and dirty Google Drive checkouts remain
  protected**. Allowed PCs for this course are HP, Dell-115 and Yoga6 only,
  not Zenbook. No Whisper, GCS leasing or unauthorized publication.
- Draft PRs must retain their dependency ordering. Thomas Calculus 8.4's
  original audio and 8.5/8.6 element mapping remain subject to their
  independent human acceptance gates.

The next development milestone is a separately reviewed, full
production-contract-compliant multipart publisher that consumes an accepted
handoff **without** inventing or silently upgrading any approvals.
