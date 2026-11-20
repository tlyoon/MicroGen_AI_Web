# Retroactive image repair for completed MicroGen lecture packages

## Purpose

This reusable command inspects and rebuilds previously published lectures after
a source-grounded figure correction. It is not a one-off Chapter 8 script.

Three distinct steps:
1. Audit source PDF figure mentions, existing figure files, LaTeX references,
   rendered PDF pages, and likely source omissions without writing to lecture folders.
2. Stage an independently reviewed and source-grounded image and LaTeX patch;
   compile PDFs, verify unchanged accepted script and WAV tracks, regenerate
   synchronization evidence, encode new videos and slide-boundary video parts,
   and compare decoded MP4 frames against corrected PDF renderings.
3. Publish only after staging checks pass, backed up under .history and with
   checksums, completion-receipt updates, readback and rollback support.

## Invocation on authorized computer

Run from the repository root:

    python -m selenium_pipeline.retrofit_image_repair --audit-chapter "G:\My Drive\Serway\Serway_8_14\8" --report "C:\MicroGen\chapter8_image_audit.json"

The LLM must visually verify the source PDF, identify confirmed defects and
prepare a vetted patch folder containing a corrected slides.tex and required
image assets. A filename or source-caption match alone does not prove mapping.

    python -m selenium_pipeline.retrofit_image_repair --stage "G:\My Drive\Serway\Serway_8_14\8\8.1" --patch-dir "C:\MicroGen\fixes\8.1" --work-dir "C:\MicroGen\stage\8.1"

Review the staging artifacts and retrofit_state.json; then execute:

    python -m selenium_pipeline.retrofit_image_repair --publish "G:\My Drive\Serway\Serway_8_14\8\8.1" --work-dir "C:\MicroGen\stage\8.1"

Chapter 9 and later chapters use identical commands with different directory
parameters. Do not execute two writers on the same package concurrently.

## Fail-closed constraints

- source.pdf is immutable; original and staged SHA-256 checks are mandatory.
- The repair does not fabricate images or infer unverified crop coordinates.
- Missing source figures when no slide graphics are referenced require review.
- Retained unused original figure assets are informational: they may be
  intentional after splitting a composite into readable subpanels.
- Changed narration or slide count requires a separate full script/TTS/acoustic
  QA pipeline run; the safe retrofit path refuses stale WAV reuse.
- Valid existing scripts, WAVs and TTS acceptance can be reused when unchanged.
- Active MP4 parts are under 600 seconds and split at verified slide boundaries.
  Full-length slides.mp4 is archival if it exceeds 600 seconds.
- New independent acoustic QA, utterance-level highlight acceptance and
  scientific source-mapping verification must not be claimed without their
  actual corresponding tests.
- No YouTube, Moodle or external document links are changed automatically.
- Old published outputs remain intact until new outputs pass acceptance.
- Publication writes completion receipts last and backs up prior outputs.
- Do not treat a clean automated audit as a replacement for source/slide visual QA.
- An existing nonempty stage is never overwritten without explicit reconciliation.

## Tests

    python -m pytest -q tests/test_retrofit_image_repair.py
    python -m pytest -q tests/test_zca101_figure_source_recovery.py tests/test_figure_audit.py tests/test_slide_narration_sync.py tests/test_video_ffmpeg_assembly.py

The real existing-lecture smoke test must be done against an isolated staging
directory, without altering the published materials.


## V3 complete source evidence patches for difficult textbook layouts

When automatic source-caption crop geometry is ambiguous or touches the figure
boundary, inspect the original source PDF and prepare separately verified
full-resolution source renderings. A patch can contain:

- slides.tex: the corrected complete slide deck
- exact source-derived Figure X.Y.png files
- source_figure_chain_v1.json, binding source SHA-256, PDF page, crop geometry,
  every printed caption and exact PNG hashes
- optionally source_split_figure_chain_v1.json, figure_repair_provenance.json,
  and source-bound upper/lower panel PNGs displayed on multiple slides

The retrofit does not trust a ledger merely because it is present:
verify_figure_crops rerenders from the immutable source and checks hashes;
verify_split_figure_chain proves pixel identity, letter witnesses, and complete
source vector/raster/annotation union coverage; verify_latex_figure_chain
establishes that all printed captions are represented in active slide graphics.
Rendered PDF visibility is also mandatory.

A historical exact-source split may have provenance but no split ledger.
In that case the pipeline can reconstruct the ledger after strict proof,
without silently substituting one for another.

Vector-only two-panel composites may be divided at a proven seam: the union
must cover the complete original source, with significant vector elements
and distinct physical source panel letters in separate split images. Missing
panels or unsupported images still fail closed.

Deterministic source-provenance proof is not by itself an independent
scientific, acoustic or student-publication approval.
