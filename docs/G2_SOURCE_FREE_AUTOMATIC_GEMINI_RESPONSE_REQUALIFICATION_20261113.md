# G2: source-free Gemini response requalification in the normal academic pipeline

**Date:** Friday, 13 November 2026, Dell-115 only. **Repository:** `tlyoon/MicroGen_AI_Web`, draft PR #528. **Binding owner rule:** "automatic recovery must be part of normal pipeline execution, not depend on you repeatedly asking me to fix the next blocker." This remedy uses the same original source/provenance guards and Gemini-only Selenium content generation policy. G2 remains unapproved.

## Reproduced recurrence: cooldown was not provider recovery

Two real original Serway 6.4 source-academic Gemini Pro/Medium windows were source-SHA-bound and registered as `SUBMITTED_OR_UNCERTAIN` without a complete attributable response. The previous `academic_review_transport_circuit.inspect` counted failed responses only within a 3600-second window and suspended new Sends for 1800 seconds. After enough time passed, it returned `distinct_failed_requests=0`, `automatic_new_academic_model_send_allowed=true` although **no new successful response had been observed**. This would have consumed the remaining two original source-review utterances just because a clock expired. Time is not evidence of model generation health.

The source is locked by SHA-256 `64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd`. The global source claim ledger now shows **39 previously attempted, only two still unattempted** (`s014.utterance.003` and `s014.utterance.004`). The original consumed IDs are never eligible for resubmission.

## Structural normal-pipeline correction

1. The original two SHA-validated failure receipts now remain in the model- and source-specific health ledger. A pair within the original finite failure window **latches** against new original-PDF Sends, including after the cooldown expires. It is not deleted merely by elapsed time. The 30-minute cooldown authorizes consideration of a *source-free* health diagnostic, **not** any original source claim.
2. The ordinary `academic_review_model_failover.run` automatically validates the exact model/Medium thinking level in the authenticated owned Gemini tab and, only after cooldown, invokes `academic_provider_requalification.probe_once` before the source-review campaign. No separate user command or per-PDF code patch is necessary in the production path.
3. The source-free diagnostic contains **no publisher PDF, slide, original narration text, figure or student content**. Its exact expected JSON includes a synthetic nonce unique to the original source-SHA scope, model family and UTC day. One durable claim is written **before** any possible browser Send. At most one new synthetic request per UTC day/source/model route is possible. On a crash, timeout, incomplete reply or uncertain Send, the claim is retained, not repeated.
4. A health success requires the exact attributable completed JSON, strict duplicate-key-free parsing, an owned Selenium `OwnedGeminiResponse`, **verified newly registered user turn**, checked Pro/Medium (or exact corresponding model+Medium) before Send, matching saved SHA claim, source/model scope, timestamp and unmodified immutable result. Only then does `academic_review_transport_circuit.inspect` requalify *new* original source jobs. Merely choosing Pro or seeing a Send click does not suffice.
5. Even after successful requalification, `academic_review_model_failover.run` caps every resumed campaign to **one original source job per invocation**, regardless of a larger CLI job budget. An original response may still fail scientific or source quotation validation and cause another source health stop. No two original requests are combined or automatically resent.
6. All recovery status is explicit. A deferred academic transport-health result returns a nonzero CLI exit and **zero original model submissions**, so a parent stage cannot mistake a safe health stop for successful G2 completion. No Google API content-generation fallback, alternate provider or unauthorized machine is introduced. The model health signal does not assert server outage or independent academic approval.

## Actual Dell-115 source-free evidence

The real authenticated Pro/Medium preflight passed at **13:06 Malaysia time** on 13 November 2026. The source-free probe then independently verified the same owned Pro/Medium model at its single Send boundary, registered `NEW_USER_TURN_AND_COMPOSER_CLEARED`, and produced the **exact expected JSON**. One synthetic browser model Send, **zero original-source Sends** and zero uploads. The independent saved health check changed from:

- `ACADEMIC_GEMINI_SOURCE_FREE_REQUALIFICATION_REQUIRED`, two verified historical failures, original source Sends blocked
- to `ACADEMIC_GEMINI_REQUALIFIED_NEW_SOURCE_SEND_ALLOWED`, two original failures retained, new original source jobs eligible but old retries still prohibited

The immutable original evidence is retained under `%LOCALAPPDATA%\\MicroGen_AI_Web_Checkpoints\\.microgen_academic_response_requalification\\<source SHA256>\\pro\\20261113`, with a second read-only verification from the circuit. Scope: genuine **small synthetic browser reply** only, not guaranteed long original-source academic responses.

## Test scope and outstanding G2

`tests/test_academic_provider_requalification.py`, `tests/test_academic_requalification_normal_pipeline.py`, `tests/test_academic_review_transport_circuit.py` and existing fallback/campaign suites cover original claim preservation, late cooldown, valid and invalid provider-owned reply, one-per-day no-resend, family isolation, forged local health proof and model/effort mismatch, normal campaign invocation, and a one-original-job cap. Hosted Windows CI at the new exact commit is still required; prior baseline head `19bd0bb` had already passed both workflows.

**G2 remains blocked until distinct, complete source-cited academic reviews, remaining source-only figure/element mapping evidence, genuine source-bound per-utterance speech, independent acoustic verification and decoded pixel/audio synchronized MP4 evidence pass their own gates.** No G3 merge, textbook edits, TTS costs, or student/YouTube publication are authorized by this health test.
