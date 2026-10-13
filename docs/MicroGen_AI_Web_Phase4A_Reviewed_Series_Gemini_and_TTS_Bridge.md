# MicroGen_AI_Web — Phase 4A: reviewed multipart Gemini/Selenium and TTS bridge

**Date:** 13 October 2026
**Status:** Isolated, opt-in integration into the existing Gemini web UI and TTS *interfaces*. **The new series is not enabled in legacy runner.py.** No real Thomas lesson has passed science/figure/video acceptance.

## What was built

1. `selenium_pipeline/series_bridge.py` prepares each approved planned video part in a **new local staging directory outside the textbook source tree**, copying a hash-checked, read-only reference `source.pdf` and writing a Part i/N source-grounded joint storyboard brief. It refuses unreviewed concept outlines, mismatched source hashes, domain mismatches and existing destinations. It does **not** claim that a draft page inventory is conceptually approved.
2. `selenium_pipeline/series_gemini.py` provides an explicitly invoked *real Gemini web UI* storyboard-candidate adapter reusing the existing vendor Selenium client, persistent authenticated Chrome, UI Flash mode and local browser exclusion lock. Model output must be one complete, duplicate-key-free JSON object that passes the Phase 3A slide/narration/source-concept structural gate. Candidate output **always requires independent subject-scientific review** and is never automatically promoted to an approved lecture.
3. `stage_tts_job` requires a separate explicit `tts_review_receipt.json` with `status=approved`, reviewer identity, meaningful note and the **exact storyboard SHA-256**. It converts semantic narration segments into the existing `**Slide N [duration]:` grammar, storing the mapping in `storyboard.json`. A TTS "Slide N" refers to a **narration segment**, not necessarily a distinct Beamer slide.
4. `invoke_existing_tts` can explicitly run the maintained `selenium_pipeline.tts` engine (Gemini 3.8 Flash Lite or Chirp3 if configured) using the existing per-user AppData/Microvid credential loader, queue/circuit-breaker/retry infrastructure and voice-continuity fallback. The series bridge does not duplicate vendor TTS logic.
5. `accept_legacy_tts_batch` rechecks numbered WAV files and the existing `tts_input_manifest.json` against every approved spoken segment, and **rejects incomplete files, wrong text and mixed provider/model/voice output**. It generates the exact ordered per-segment WAV manifest accepted by Phase 3B `speech_segment_timing.build_segment_timeline`.
6. `selenium_pipeline/series_cli.py` exposes separated local `prepare`, `candidate`, `stage-tts`, `run-tts`, and `accept-wavs` commands. Live browser/TTS actions require explicit `--confirm-live`; ordinary commands cannot consume credits. All output paths are no-overwrite and reside in staging, not next to `source.pdf`.

## Intended controlled workflow

Only after the approved Phase 2 `concept_outline.json` and matching `lesson_plan.json` exist for a source:

~~~powershell
$root = 'G:\My Drive\Projects\Thomas_calculus_13ed'
$pdf = "$root\2\2.2\source.pdf"
$review = 'C:\MicroGen_Phase4Review'
$part = "$review\part_01"

# Reviewed outline/plan must exist at explicitly named files first.
python -m selenium_pipeline.series_cli prepare --source-root $root --source-pdf $pdf --outline "$review\concept_outline_APPROVED.json" --plan "$review\lesson_plan.json" --domain mathematics --part part_01 --output $part

# Only after review-gate preflight; this action actually uses the Gemini UI.
python -m selenium_pipeline.series_cli candidate --source-root $root --source-pdf $pdf --outline "$review\concept_outline_APPROVED.json" --plan "$review\lesson_plan.json" --domain mathematics --part part_01 --authoring-folder $part --output "$review\storyboard_CANDIDATE.json" --confirm-live

# A person/domain QA must review scientific meaning, the completeness
# of equations, and figure/caption/provenance BEFORE creating approval.json.
python -m selenium_pipeline.series_cli stage-tts --source-root $root --source-pdf $pdf --outline "$review\concept_outline_APPROVED.json" --plan "$review\lesson_plan.json" --domain mathematics --part part_01 --storyboard "$review\storyboard_REVIEWED.json" --review-receipt "$review\storyboard_APPROVAL.json" --output "$review\tts_stage_01"

# Only explicitly approved content goes to real TTS, using AppData secrets.
python -m selenium_pipeline.series_cli run-tts --tts-folder "$review\tts_stage_01" --provider gemini --model gemini-3.8-flash-lite-tts --voice Kore --confirm-live --output "$review\wav_segments.json"
~~~

This TTS manifest may then enter Phase 3B/3C timing/video stages **only after real speech-content QA, Beamer slide/source-fidelity review, measured geometry, duration and multipart continuity verification**.

## Tests and release boundary

15 targeted offline tests cover: source immutable local staging, unapproved source rejection, domain mismatch, exact script conversion, review SHA invalidation, tampering, no overwrites, duplicate/truncated Gemini JSON, incomplete/mixed/wrong TTS output, candidate-only status, CLI actions and accidental live-call guards. Gemini transport is tested via injection, **not an actual authenticated model response**. WAV files used in tests are PCM fixtures. GitHub CI includes both Linux and Windows historical suites.

**Remaining before real textbook pilot:** domain-authorized conversion of the *11-page, presently unreviewed* Thomas 2.2 source draft into a genuine mathematical concept catalog; a corresponding approved lesson plan; model-authored joint slides.tex and compiled geometry anchors (not just JSON); independent narration-acoustic and visual source-fidelity QA; strict <630-second final MP4 and Part i/N release receipts; and distributed multi-PC publication locks. These must not be bypassed by setting a Boolean environment variable or fabricating review metadata.

The canonical test root is `G:\My Drive\Projects\Thomas_calculus_13ed`. Never overwrite the separate shared `G:\My Drive\Projects\MicroGen_AI_Web` repository, which still has older uncommitted local edits. Zenbook remains excluded.
