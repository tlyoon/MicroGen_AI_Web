# MicroGen_AI_Web — Legacy completion receipt reconciliation

**Date:** 12 October 2026  
**Repository:** tlyoon/MicroGen_AI_Web (**not** tlyoon/MicroGen_AI).

## Why the repair exists

The Stage 5 PDF-to-video pilots identified a historical defect: the structural slide/script/WAV synchronization record could be deleted with the staging folder even after a receipt marked the lecture complete. PR #41 ensures that *new* runs publish that proof; this opt-in tool repairs **existing, already-published** receipts without regenerating slides, narration, WAVs or MP4s.

## Safe use

Run from the correctly identified MicroGen_AI_Web checkout with a Python environment containing PyMuPDF and imageio-ffmpeg, and use the **local path containing source.pdf** (not a GitHub path):

    python -m selenium_pipeline.reconcile_structural_sync --source-folder "C:\path\to\chapter\subchapter"

Without `--apply`, the tool is entirely read-only. It checks:
- Existing source and final-artifact hashes against the current completion receipt.
- Exact slide page count vs. numbered narration blocks and every numbered WAV.
- Passing **per-slide** TTS QA with no reviews or blocking errors and minimum fidelity at least the recorded threshold.
- No blocking narration-risk findings.
- A usable final MP4 with video and audio streams and duration consistent with the WAVs.
- Any pre-existing synchronization proof is valid; an invalid existing proof is never rewritten.

Only after a clean dry run, explicitly enable the change:

    python -m selenium_pipeline.reconcile_structural_sync --source-folder "C:\path\to\chapter\subchapter" --apply

The tool makes a timestamped backup of the old completion receipt in `.history/`, writes and verifies `slide_narration_sync.json` if absent, then atomically binds its SHA-256 to the completion receipt. All source PDFs, slides, scripts, WAVs and MP4s retain their original hashes. Existing valid bound receipts are left unchanged. Invalid/missing QA, edited files, missing source/receipt or unplayable videos fail closed.

## What this is *not*

The utility does **not** certify scientific correctness, figure selection, slide legibility, or the actual meaning of spoken symbols. It provides *structural and available audio-fidelity evidence* for previously generated lecture materials. Human or independent scientific-content review is still necessary.

Never use it to mark an uncompleted or actively encoding lecture as complete. It cannot create an MP4 or approve a failed generation.
