# G2: owned-browser model failover, no-duplicate academic checkpoint and source-review microbatches

**Date:** 13 November 2026, Dell-115 only. **Branch:** `feature/pr528-autonomous-ai-lecture-acceptance` (draft PR #528). **Scope:** technical recovery and genuinely original Serway 6.4 source-review evidence. **G2 remains unapproved.**

## Repeated blocker and observed root cause

The existing academic-review contract requested authenticated Gemini Flash with Medium thinking. Real account-A Chrome 9222 and already-running account-B Chrome 9225 owned-tab preflights instead found currently offered Gemini models Flash-Lite, Hydrogen, Pro, Argon and Carbon; neither offered exactly Flash. The genuine old request window on 13 Nov correctly stopped with no source claim/Send. Repeating a missing menu choice is not a Selenium cure.

A scoped no-Send Pro/Medium capability probe **passed** in the original account-A tab and made zero source uploads, source claims or model requests. The first attempt on a genuine nine-unit source job then failed **before Send** with the known picker failure and was durably certified as `CERTIFIED_PRESEND_UNSENT`. The shared `series_gemini._browser_request` called a separate `ensure_mode(port,...)` twice after vendor had established an owned tab. This could read or refocus a different tab and used the package-wide Flash model-ID default even while the actual owned academic tab was Pro. Neither symptom is permission to weaken academic science.

## Structural fixes in the normal source-review path

- `academic_gemini_presend_preflight` verifies only the exact model and thinking level in the controlled authenticated tab. It can check an already-running alternate authorized account but does not open a new login. The separately selected Pro family is not called equivalent to Flash.
- `academic_review_model_failover` allows Pro **only for bounded source-academic review**, and only after witnessed missing Flash on the authorized accounts. It writes one external source-SHA-bound, immutable model-route receipt and reuses it across certified-unsent retries. It restores the process environment and never changes figure Flash-Lite or normal slides/narration Flash default. It uses the original academic campaign, its one-Send global original-utterance index, exact source hashes and strict PDF/source validator.
- `series_gemini._browser_request` now verifies the *same* vendor-owned tab and its model family directly before upload and again before the single Send; it never uses a separate parent-tab `ensure_mode` and it derives default requested-family model IDs from the selected mode. An explicitly contradictory model ID remains disallowed.
- The normal `source_review_autonomous_campaign` CLI routes through the same scoped recovery automatically, not via a separate one-off manual launcher.
- `academic_source_microbatch` checks every immutable original claim in the shared source-index, excludes already-attempted original units, rebuilds only still-unattempted source-hash-bound jobs with a maximum of two original utterances, preserves original text, target IDs and exact PDF quotation packets, and emits versioned **write-once** plans/checkpoint roots that share the original global claim index. It checks exact request-text SHA **again after persisted JSON reload**, closing a reproduced v1 sorted-key serialization regression. Source SHA drift, foreign claim, overlapping unit and changed plan stop before model Send.

## Real Serway 6.4 acceptance checks

Original source SHA-256: `64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd`. The original changed-source six-job plan held 41 eligible narration units. Source-global claims now mark **37** of these already attempted (some with valid unresolved replies, some without source-complete replies), leaving only **4** unclaimed original IDs: `s014.utterance.001`–`004`. The v2 short planner proposes two two-utterance jobs and preserves the original six-job manifest unchanged.

After the transport fix, the **same** previously certified-unsent nine-unit review window successfully verified Pro Medium, uploaded real `source.pdf` and `slides.pdf`, and registered exactly **one** Send. The model produced **only one** of nine required rows, an `UNRESOLVED` citation about a baseball/drag derivation. Its untrusted 931-character original reply was quarantined with SHA-256 `f946bce5ea814caf6837f538023c9fa12d0d68c7572bbe04a182de0468190f37`. The original request is now `SUBMITTED_OR_UNCERTAIN`, can_auto_retry=false. No model row or academic approval was fabricated; this request must **never be sent again**.

A trial v1 microbatch plan was correctly rejected by the original request-SHA gate before its first model Send because sorted JSON keys changed the saved request bytes. The algorithm now preserves original nested key order, sets v2, emits a different immutable plan and revalidates saved prompt hashes before dispatch. The rejected v1 plan remains evidence.

## Remaining G2 acceptance

This technical transport improvement **does not certify** all 74 original utterance source mathematics, 41 unresolved element mappings, independent figure-body semantics, true per-utterance source-bound audio, speech recognition or sample-accurate synchronized decoded MP4 parts (<600 s each). The 14 original slide-level WAVs passing PCM is not that evidence. Do **not** turn any one-pass `SUPPORTED` AI row into final academic agreement, or treat a registered model Send as completed mathematical review. G2/G3, merge, student publication and YouTube upload remain **not authorized** until their distinct substantive gates genuinely pass.

## Final bounded live short-job and health circuit evidence

The v2 physically reloaded source-bound plan's first two-unit job (slide 14, original IDs `s014.utterance.001` and `s014.utterance.002`) passed Pro/Medium owned-tab verification, attached both original PDFs, and registered a single new user turn. After bounded observation the owned tab remained blank and its response could not be attributed: `POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND`. A separate, isolated `job_01_checkpoint` records `SUBMITTED_OR_UNCERTAIN`, no accepted model reply and `can_auto_retry=false`. There was **no second Send**.

Consequently 39/41 changed-source utterances are claimed, not 39 accepted. Two genuine original units (`s014.utterance.003`, `s014.utterance.004`) are still unattempted. The original source-review baseline (28 source-supported / 44 unresolved / 2 invalid original citation rows) is **not** upgraded by the new Pro attempts.

The new `academic_review_transport_circuit` rechecked the SHA-bound persisted model-route and both distinct claimed windows; it registered two original no-accepted-response events under `%LOCALAPPDATA%\\MicroGen_AI_Web_Checkpoints\\.microgen_academic_transport_health\\<source SHA256>`. The ordinary `source_review_autonomous_campaign` CLI then automatically returned `ACADEMIC_GEMINI_RESPONSES_TEMPORARILY_SUSPENDED`, `new_requests_attempted=0`, with no browser entry. It does **not** assert a Google outage; the suspension is source+model-specific and expires after its bounded cooldown. Old uncertain original requests remain blocked permanently.

**Local Dell-115 evidence:** 105 focused source/microbatch/provider/model-selector/academic-checkpoint/mathematical/element-gate tests passed, 2 skipped, no failures; benign third-party warnings. All new in-tree code and README/checkpoint require fresh exact-head GitHub Windows CI after commit. No new WAV, MP4, original-PDF edits, source override, historical check replay, protected merge, YouTube publication or G2/G3 release.
