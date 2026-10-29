# Source-bound spoken-window and pause pixel verification

**18 October 2026 — Draft development hardening, not a production release.**

This document supplements the effective MicroGen_AI_Web contract and PR #131.
The critical requirements remain **every MP4 part strictly below 600 seconds**, genuine
audio-aligned highlighting of the **spoken slide element**, source-accurate
full figures and multipanel crops, consistent TTS model/voice, independent human
math/figure/listening review and separate student-publication authorization.

## Problem corrected

The historic decoded-pixel QA checked each narrated element primarily at its
midpoint. A video with the correct element highlighted only around the
midpoint could pass even if the wrong element or no emphasis appeared earlier
or later in the same WAV segment. Likewise, a highlight erroneously
continuing into a silent audio pause did not face an independent pause check.

Passing a midpoint sample is **not equivalent to continuously synchronized
spoken-element highlighting**.

## Mandatory additional technical checks

The offline MP4 inspector now:

- Decodes the actual VFR MP4 frame timestamps (not estimated TTS word timing).
- Samples each spoken source-bound element at **10%, 50% and 90%** of its
  measured WAV chunk time, and requires the encoded pixels to be demonstrably
  closer to the correct highlighted element than to the unhighlighted source.
- Checks every audio pause **80 ms or longer** against the correct unhighlighted
  slide and demands it differ appropriately from the prior active emphasis.
- Performs all needed indexed-frame extractions in **one batched FFmpeg
  invocation per part** even when many sample times refer to the same
  encoded VFR frame; does not introduce expensive repeated frame decoding.
- Writes counts and SHA-bound evidence for start/end highlight samples and
  for pauses. The review-series renderer and independent review verifier now
  **require** these new fields instead of treating midpoint-only evidence as
  sufficient.
- Rejects manipulated videos: a correct midpoint with an incorrect early
  highlight; a persistent highlight during audio silence; and historical
  receipts missing complete evidence even when an attacker updates that
  receipt's internal QA hash.
- Preserves the original source files and prior videos. Tests generate new
  disposable synthetic review MP4s only.

## What this does not establish

These checks are sampled observations at finite timepoints; they are **not**
full-frame or phoneme-by-phoneme proof of continuous semantic correctness.
A long event with several image changes between sampled timepoints may
still need exhaustive all-frame auditing. The code deliberately keeps all
outputs **REVIEW_ONLY** and does not produce a production completion
receipt or sign any academic approvals.

The original author must still independently confirm the mathematics,
figure-panel completeness, spoken words, phrase boundaries and semantic
target selection. Model-picker Flash family selection cannot prove
exact server model identity. The approved Gemini Flash-Lite/Kore →
Flash/Kore → conditional Cloud Chirp/Corey fallback policy remains unchanged;
no Whisper is introduced.

## Next implementation gate

After code review and multi-OS regressions, integrate these strict timing
checks into an independently approved end-to-end candidate workflow, and
complete independent human listening/figure review before any lecture
release. The existing Thomas Calculus 8.4/8.5/8.6 source assets and draft
PR dependency stack must remain intact; neither this patch nor a green CI
authorizes publishing any student materials.
