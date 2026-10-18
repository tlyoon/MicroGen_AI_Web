# MicroGen_AI_Web effective contract and supersession index

**Effective from 18 October 2026.** This document records the latest explicit course-owner decisions and supersedes *conflicting prescriptive statements* in the older October blueprints, trial reports and troubleshooting notes. Historical documents remain intact as evidence of prior designs, not as an alternative production authorization.

**Additional binding development guard:** [Gemini UI model provenance and explicit
academic/student release gates](GEMINI_UI_MODEL_AND_LECTURE_RELEASE_GATES_20261018.md).
An authenticated Flash model picker is not independent evidence of the exact
deployed Gemini 3.8 model; technically verified MP4s are not automatically
human-approved or student-publishable.

**Applies to:** `tlyoon/MicroGen_AI_Web` only. This document does **not** authorize merging drafts, a new lecture generation campaign, paid experiments, production replacement or student publication. The saved checkpoint is `microgen-checkpoint-2026-10-18`.

## Non-negotiable production acceptance

1. **Strict video limit:** Every completed MP4 part must have actual encoded duration **strictly less than 600 seconds**. Exactly 600 seconds, 620 seconds or any historical 600–630-second "exception" fails. Planned narration parts should target 8–9 minutes to leave margin. Long subtopics require meaningful **upstream** splitting into coherent parts with continuity, not arbitrary chopping of finished MP4.
2. **True synchronized element highlighting:** Every spoken equation, phrase, diagram and complete multi-panel figure must align with the correct visible slide region in measured narration time. Static full-slide video and slideshow-only timing are never valid substitutes. Source, graphics, figure captions, script, slides, recorded PCM WAV segments, timing and encoded video must have verifiable linked identities. Matching hashes/pixels cannot prove audible mathematical correctness.
3. **Source completeness and approvals:** Preserve the exact textbook content, mathematical meaning, multipanel figures, source/caption associations and figure legibility. Regeneration of a changed slide arrangement requires invalidation and rechecking of dependent narration/TTS/video. Automatic approval is prohibited; independent human listening, scientific/figure review and explicit release decision remain separate gates.
4. **Model configuration:** Gemini 3.8 Flash is the selected **text-generation target** for slides, narration and figure abstraction across development and production unless explicitly changed for a benchmark. A browser menu confirming the Flash *family* is not, by itself, proof of exact deployed version; reports must identify the strength of each verification.
5. **Approved TTS order:** Gemini Flash-Lite TTS (Kore) primary, after **at least three genuine transient-failure attempts per unresolved slide**; whole-batch Gemini Flash TTS (Kore) next, also requiring the specified completed retry queues; **conditional** Cloud Chirp 3 HD (Corey) last only after independent observed Lite and Flash exhaustion. The real effective model/voice is recorded. Do not mix Kore/Corey or different TTS models within one accepted lecture. Never escalate for malformed inputs, auth/permissions, missing evidence or disk faults.
6. **TTS billing:** Ordinary metered Gemini Flash-Lite/Flash TTS for routine approved course production has the owner's standing permission; do not require repetitive paid-usage confirmation for each normal lesson. Experimental API trial/Interactions routes require their own explicit consent flags, and directly selected Cloud Chirp requires its explicit authorization. Automatic Cloud is allowed **only with the independently observed prerequisite fallback chain and billing safeguards**. There is no unlimited authorization for speculative testing.
7. **Speech ASR:** No Whisper, faster-whisper, openai-whisper or CTranslate2 Whisper dependency/use. Do not treat a TTS call as independent ASR. Gemini-backed independent transcription, when actually supported and authorized, remains the intended tool; disagreements are reviewed by a human, never automatically waived.
8. **Three-PC campaign:** HP, Dell-115 and Yoga6 only; **Zenbook excluded** until the owner explicitly authorizes it. Use Drive-native coordination, exclusive job ownership, immutable source/checksum receipts, bounded retries and FIFO. Do not introduce Google Cloud Storage leasing, silent reassignment, shared-Drive atomic-lock assumptions or unapproved simultaneous browser-profile access.
9. **Preservation:** Original source PDFs, slide decks, editable TeX, audio, MP4s, review artifacts, prior historical files, and dirty production working trees are protected. Code checkout and source root remain separate. Ordinary validated lecture outputs belong next to each subchapter's `source.pdf`; unreviewed/experimental artifacts must be in fresh, isolated folders. Do not silently overwrite existing artifacts or change the original three-PC Google Drive repository.
10. **Truthful release status:** Mock and synthetic tests, CI, generated video metadata, pixel checks or model-picker labels are technical evidence only. They do not certify real mathematical/figure/audio quality, lecturer listening approval, student publication or release to Moodle.

## Prescriptive precedence and known supersession

The latest explicit owner-approved rule controls when earlier proposals conflict. Preserve earlier documents so that the deviation and correction history remains independently auditable.

| Historical document / policy | Superseded assertion | Effective rule |
| --- | --- | --- |
| `README.md` original opening, `MicroGen_AI_Web_Integrated_Architecture_and_Implementation_Blueprint_v1.md`, `MicroGen_Integrated_Multidisciplinary_Multipart_Sync_Blueprint_v2_20261013.md` | 630-second hard cap; reviewable 600–630-second exception | **Every part strictly <600 s without exception** |
| `MicroGen_AI_Web_Phase1_Domain_Profile_and_Series_Schemas.md`, `MicroGen_AI_Web_Phase2_Source_Aware_Top_Down_Lesson_Planner.md`, `MicroGen_AI_Web_Phase3A_Joint_Storyboard_and_Anchor_Contract.md`, `MicroGen_AI_Web_Phase3C_Synchronized_Highlight_FFmpeg_Preview.md`, `MicroGen_Offline_TTS_Duration_Preflight.md` | Older planning/preview allowance up to 630 seconds | **600-s upper bound for planning and encoded output** |
| `BROWSER_TTS_CONTRACT_ACCEPTANCE_20261017.md` and `TTS_PAID_ENTRYPOINT_AUTHORIZATION_CONTRACT_20261017.md` | Per-command routine Gemini cost consent and blanket no automatic Cloud fallback | **`TTS_RESTORED_OWNER_APPROVED_FALLBACK_POLICY_20261017.md`** with source-bound retry-journal guards |
| Earlier experimental Whisper design / withdrawn PR #104 | Whisper-based offline transcription | **`NO_WHISPER_ASR_DESIGN_CONTRACT.md`**, no Whisper |
| Old static-video FFmpeg scripts and early lecture completion receipts | A single static `slides.mp4` can indicate completion | **`production_video_contract.py`** plus independent academic/release gates |

Old measurements, evidence screenshots, logs, and reports of previously observed lecture durations are *historical facts* and should not be erased or rewritten as though those old events never occurred. A historical document's original wording is preserved but must be marked **SUPERSEDED FOR NORMATIVE USE**.

## Current code-development boundaries

- The routine `runner`, `three_pc_worker` and `microgen_batch` deliberately block noncompliant legacy video production; this is correct behavior, not a production-completeness claim.
- All historical static video scripts (root PDF/PNG versions and vendored MoviePy variant) must not delete/publish a legacy `slides.mp4`. `selenium_pipeline/video_ffmpeg.py` may only be exercised via synthetic, explicitly marked isolated review-test paths; no student-facing output.
- Full production operation remains blocked pending implementation/review of the missing compliant end-to-end academic/figure/audio verification and final release permissions.
- Git checkpoint `microgen-checkpoint-2026-10-18`, latest draft PR #129 and the separate archived legacy three-PC edits must remain unchanged by corrective development. Proceed on a separate isolated feature branch; do not merge the stacked drafts out of order.

## Regression expectations

CI should cover schema and policy documents, direct script and CLI entrypoints, no-overwrite adversarial tests, boundary cases 599.9/600/620/629.9 seconds, TTS fallback voice/payment rules, no-Whisper contract, and encoded-highlight acceptance. Never infer production success solely from these tests.
