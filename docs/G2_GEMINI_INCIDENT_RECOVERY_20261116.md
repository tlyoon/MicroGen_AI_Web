# G2 Gemini historical-claim isolation and incident-aware response health

**Date:** 16 November 2026. **Authorized runner:** Dell-115. **Scope:** MicroGen_AI_Web Selenium, authentic Serway §1.3 independent academic review queue.

## The two different states

A. A previously claimed source-bound academic request has an unresolved send/response outcome. The original request and dispatch claim are immutable; retrying that identical request is unsafe. The existing review selector skips it, while existing saved-reply reconciliation may later recover genuinely attributable evidence without another source Send.

B. The current Gemini response route may or may not be healthy. An earlier source-free response is not proof of health after a *newer* uncertain academic Send. Previously the once-per-UTC-day source-free slot could not requalify later source request incidents during that day.

## Production recovery integrated

- `selenium_pipeline/academic_incident_response_health.py` implements a distinct incident-specific source-free nonce diagnostic. The incident identity is SHA-256-bound to original source, verified full-model family, latest unresolved slide/mode/attempt checkpoint and its request fingerprint. The synthetic request never uploads original PDF/lecture text.
- `selenium_pipeline/academic_queue_fresh_send_health.py` first rechecks existing immutable historical health evidence, then an incident-specific independently verified saved result. Only if execution is requested and no qualifying saved evidence exists does it use the legacy once-daily probe. When that daily slot was already consumed *before* the newest claim, a separate incident-specific probe is eligible without repeating the old diagnostic or original source request.
- A valid diagnostic requires an OwnedGeminiResponse, positively observed new user turn and registered send, exact synthetic JSON/nonce, verified same full Gemini family and Medium thinking, and an observation timestamp later than the latest uncertain source claim. A plain text return or an incomplete/incorrect Gemini answer is never proof.
- Incident diagnostic paths: `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/.microgen_g2_incident_response_health_v2/<source_SHA>/<family>/<UTC_day>/<incident_SHA>/attempt_XX/{claim,result}.json`. Exclusive on-disk claim is written and fsynced **before** browser Send; result is written after. Interrupted or uncertain attempts are never replayed, and new attempts use a different nonce.
- No more than two incident-specific source-free attempts per UTC day across all incidents of the same source/model, at least 900 seconds between such probes, and no more than two slots for one incident per day. Repeated invocations reuse a proven original result, rather than consuming another Send. An invalid, tampered or missing proof fails closed.
- This does not disable old source requests' immutable claim protections. The original supervisor selects the **next independently unattempted** academic unit only after response-health requalification and retains its separate source/math/figure/quote evidence checks and finite stage budget.
- The existing `operations/g2_serway13_autonomous_cycle.ps1` already calls `selenium_pipeline.g2_forward_recovery_engine`; the new health gate is reached through the normal supervisor. No scheduled task is installed or recreated. Running a foreground stage chain may end at a provider/cost/source/QA eligibility boundary.
- Paid TTS, generated WAV, MP4, scientific consensus and independent acoustic/ASR are **not** authorized by a healthy synthetic response, and full G2/G3 completion is not implied.

## Regression coverage

New `tests/test_academic_incident_response_health.py` exercises exact owned nonce, restart reuse, missing result/uncertain claimed Send, source request preservation, second incident after first diagnostic, daily request cap, inter-probe cooldown, bad model/thinking and tampered saved reply, and the actual normal G2 health check dispatch. Included in `.github/workflows/microgen-reliability-tests.yml`.

**Initial Dell-115 focused result:** 35 passed, zero failures, 5 nonfatal warnings across new incident tests, legacy health tests, provider requalification, G2 supervisor and forward engine. Later live/expanded verification belongs in the continuation checkpoint and immutable stage journals, not in a guessed scientific acceptance statement.

## Intended safe future behavior

1. After a new uncertain original academic request, persist its unique no-resend claim.
2. Skip that request, choose the next unattempted review only.
3. Examine source-free proof dated *after the latest* uncertain request; if older, run a new incident-bound diagnostic within finite budget/cooldown.
4. If the model response is exact and attributable, advance one eligible source review through the same existing strict QA; otherwise persist a safe stop.
5. On restart use accepted health evidence only if still newer than the latest uncertain source request, and never create duplicate original source Sends.

## Genuine Dell-115 forward acceptance (16 November 2026)

The real source review queue was exercised through the normal `selenium_pipeline.g2_forward_recovery_engine`, with `--execute --max-cycles 2 --no-auto-media` and original Serway §1.3 source/slide/script unchanged. The source-free **legacy daily slot** for the new UTC day returned an actual exact OwnedGeminiResponse on Pro Medium, and the SHA-bound health receipt was saved under `.microgen_academic_response_requalification/<source>/pro/20261116/`. Its result was `SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED`. The previous un-attributed original requests were **not** resent.

Live stage 0003: slide 5 first-pass review was genuinely captured as `SOURCE_VALIDATED_ONE_PASS_UNAPPROVED`, then G2 continued to the next eligible operation. Live stage 0004: slide 5 independent challenge returned a response rejected with `FigureIdentityReviewRequired`; the queue preserved the original response/claim for a subsequent zero-Send reconciliation. The two new forward results were persisted as `0003.result.json` and `0004.result.json` in the existing source-bound forward journal, with `next_action=CONTINUE`. The bounded CLI stopped because its **two-stage test budget** was reached, not because the old requests remained a provider-health blocker.

**Actual academic result:** still 4 of 85 independently source-agreed utterances (81 pending/disputed), no paid TTS, no video, no G2 approval. The new incident-v2 branch was regression-tested with synthetic owned browser responses, but did **not** need to issue a real new incident probe during this run because the fresh daily legacy probe successfully requalified the current provider route. Do not misreport the live recovery as a full v2 provider stress result or scientific closure.
