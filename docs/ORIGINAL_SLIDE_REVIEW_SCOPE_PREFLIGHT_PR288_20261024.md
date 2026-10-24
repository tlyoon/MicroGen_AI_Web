# PR288 — Actual per-slide original mathematical-review scope preflight, no model dispatch

24 October 2026 (Asia/Kuala_Lumpur). Dell-115 only; stacked on PR287 exact `422099eff705a3f14c0a55b53b4a5feb4a8dbdb2`.

## Proven source-bound result

Original Thomas Calculus 8.4 Slide 3, *The Three Basic Substitutions*: five original utterances. Read-only audit used the original G: folder and the existing original immutable 71-unit queue `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\real_thomas84_resumable_71_ai_reviews_20261022`.

- Original textbook SHA256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
- Original queue SHA256: `8c00fd5aa74b4ef4ecdebf41c839406c1a5645ff2637d19069feb507e0b541ac`
- Slide 3 INITIAL_REVIEW: no previous success/recorded attempts, next attempt number *potentially* 1, but **NO VERIFIED SLIDE-SPECIFIC CONSENT**.
- Slide 3 INDEPENDENT_CHALLENGE: BLOCKED_MISSING_INITIAL_REVIEW.
- Prior separate Slide-1 exhausted-challenge permission does **NOT** transfer to Slide 3. No model request, provider retry, TTS, public release or human approval executed.

## Durable change

New normal, reusable non-dispatching CLI `selenium_pipeline.source_review_eligibility_preflight`. It verifies original source PDF/slide/script hashes against immutable queue rows and the actual one-slide original narration job, inspects *both* review-stage histories using the existing read-only retry planner, catches out-of-range or symlinked attempt files the legacy 3-attempt iteration would miss, and rechecks source/queue identity after inspection.

Returns explicit **planning/blocked** status and always sets new-scope-consent, browser ownership, model sent, automatic retry, scientific agreement and student release permissions to false. Even existing generic `FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED` receipts cannot establish that the previous provider transaction was proven unsent; the preflight instead demands owner/transport reconciliation for any prior failure before reuse. This code is not a new provider dispatcher and cannot reset exhausted quotas.

## Validation

Dell-115 focused+neighbor tests: `pytest -q tests/test_source_review_eligibility_preflight.py tests/test_review_retry_plan.py tests/test_ai_academic_review_queue.py tests/test_original_math_claim_inventory.py tests/test_scoped_original_math_review_window.py` — **31 passed**, five pre-existing SWIG warnings. Adversarial tests cover original source drift, unexpected fourth attempt, three exhausted attempts, ambiguous in-flight legacy receipt, missing initial challenge, staged first review and no asset/queue writes.

Actual original run on Slide 3 produced expected **NO_PENDING_RECEIPT_BUT_SCOPED_CONSENT_NOT_PROVEN** with accurate five-unit count. Zero live Gemini requests, no modification to source or original historical receipts.

## Next

Without user consent for a new Slide-3 original academic-review scope and positive owned-browser/send safeguards, do not issue a model request. Proceed independently on high-signal mathematical and figure preflight, source evidence, and eventual production QA. Once explicit scope is granted, a separate owned-tab dispatcher must enforce verified actual send, exact response capture and ambiguity quarantine; this preflight is NOT sufficient authority on its own.
