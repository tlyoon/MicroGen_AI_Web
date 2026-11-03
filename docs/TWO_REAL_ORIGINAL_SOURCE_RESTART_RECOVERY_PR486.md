# PR486 — Idempotent real original multisource campaign and fault recovery

## Engineering problem

In the long development campaign, resuming after failures could repeat the same source checks, browser requests, original lecture analyses and TTS. A single complete or blocked academic section should have a durable source-bound completion decision independent of the next original section.

## Implementation

New `selenium_pipeline.original_multisource_recovery_campaign` consumes a source/external-evidence manifest for 1–12 sections, pins exact physical source.pdf, slides.pdf, script.txt SHA-256 and the original PR475/481/482/483 per-section immutable mapping worklist/fallback/queue and model response bytes. It checks a source-external immutable campaign contract on every invocation and creates **per-section canonical SHA-verified receipts** only after `original_source_e2e_acceptance` independently checks the original. Atomic rename on native Windows avoids half-published source proof; physical byte changes and stale evidence fail closed, with no silent replacement. The next invocation **reuses** already stored source decisions without rescanning original equation/figure contents or trying Gemini/TTS/FFmpeg again.

A crash after section A was durably written but before section B is complete is simulated by a test that throws directly after the first source receipt. The second run uses the previously written A receipt unchanged and processes ONLY section B. Changed publisher PDF, model response, or physical/canonical receipt bytes invalidate the old campaign and require a **new separately versioned** work area. A successful upstream dry-run never claims video completion, and a blocked source review cannot be marked ready for student publication.

Native Windows CLI:

`python -m selenium_pipeline.original_multisource_recovery_campaign --spec <source-section-evidence-manifest.json> --outdir <NEW-external-campaign-folder>`

The manifest's `sections` array contains distinct `section`, `lecture`, `checkpoint`, `fallback_dir`, `queue_dir` and optional `model_responses` paths. No model API, new PCM or output media is generated.

## Actual Dell-115 original §8.4+§8.5 acceptance

**First run:** two independently frozen original publisher+author+script sections inspected, each blocked for unresolved source-to-maths/figure narration with zero TTS/model calls, zero modified originals.

**Immediately repeated run:** exactly **two** genuine old source decisions reused, **zero** original sections re-inspected. A local patch forced the original inspector to throw if called, proving the no-rescan property. Durable original-source and second-run receipt:

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261103_PR486_TWO_REAL_ORIGINAL_SOURCE_IDEMPOTENT_RESTART_V1\REAL_ORIGINAL_TWO_SOURCE_CLEAN_RESUME_RESULT.json`

Synthetic real-PDF fault injection tests also cover crash after first accepted section, changed original source, changed prior model response, tampered/read/write receipt and two-source distinct source-bound identity. Neither a true new H264 lecture nor full student release was claimed, because §§8.4/8.5 remain blocked by the 155 general source-to-element semantic mapping gaps across the original 41-slide corpus.

No HP/Yoga/Ubuntu/local LLM, no repeated Figure8.3 science audits, no paid Gemini API/Cloud TTS.
