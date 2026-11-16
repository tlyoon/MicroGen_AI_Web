# Forward-progress rule: quarantine isolated scientific-review failures and keep advancing

Date: 16 November 2026. Production target: Dell-115 / MicroGen_AI_Web.

## Binding continuing-development contract

After each completed blocker recovery, **do not stop and wait for a new user "proceed" instruction**. The normal executable pipeline should (1) verify the repair and regression result; (2) persist its source/provenance-safe checkpoint; (3) select and execute the next independently eligible stage within the same finite invocation; (4) detect, classify and repair subsequent blockers using a previously verified remedy or a tested new one; and (5) advance further until an actual outstanding eligibility boundary is reached.

This applies to ordinary future development, not just one Serway lecture. It is implemented in the real G2 forward engine and academic review selector; it is not an instruction to loop indefinitely, resubmit uncertain model Sends, bypass scientific/acoustic/figure QA, exceed authorized operations, merge unverified code, or publish without the release gates. No scheduled task is reinstated; autonomous chaining occurs during an invoked foreground workflow, not after process exit.

## Newly proven blocker

The genuine Serway §1.3 slide-5 independent model reply was returned but rejected for `FigureIdentityReviewRequired`. A saved-only reconciliation used zero additional Gemini Sends and was also rejected. The prior selector would return `DEFERRED_SAVED_REPLY_RECONCILIATION_FAILED` globally, preventing the unattempted slide 6 from starting. This was a **queue-level forward-progress defect**, not evidence of global Gemini downtime or scientific QA completion.

## Implemented source-safe response

`selenium_pipeline/ai_academic_review_queue.py` now verifies the exact existing failed reconciliation's slide/mode/attempt, `PRIOR_SAVED_RESPONSE_ONLY` provenance, zero Sends, false academic/publication approval, and immutable receipt SHA. It preserves the scientific gap as `SOURCE_REVIEW_QUARANTINED_INVALID_SAVED_REPLY` in `blocked_other_slides`, refuses a retry of the same consumed request, and independently considers the next genuinely unattempted slide. Every fresh Send still runs through the normal original-source/hash, provider health, single-Send and two-pass scientific source-validation protections. An unresolved source/mode remains incomplete for overall G2 acceptance.

The normal `g2_forward_recovery_engine` already recognizes a failed stage followed by a *different* eligible slide and chains forward subject to its bounded 32-stage ceiling and the supervisor's own one-review-per-stage limit. The failed slide is not counted as scientific consensus.

Additionally, the hosted Windows suite exposed a real semantic reporting error: a returned source-review row containing a false quotation was correctly demoted to `UNRESOLVED`, but the campaign still marked the job completed because one technical review JSON was produced. `source_review_autonomous_campaign.py` now records **zero-supported source evidence as unresolved**, not completed, and applies the same downward-only source-quote validation when resuming the exact saved response. This never alters the model's original reply and never repeats the consumed request.

## Verification requirements

Test the existing benign review progression, invalid saved-response quarantine, source/claim immutability, an independently eligible subsequent slide, restart-safe receipt reuse, the formerly failing hosted Windows false-source-quotation test, whole G2 forward regression, and the full Windows offline suite. Confirm the actual Serway queue chooses slide 6 while retaining slide 5's failed receipt. Execute a bounded live source review only after tests pass; report scientific acceptance separately from transport/queue advancement.

Persist actual test counts, live results, CI and branch/commit status in `CONTINUATION_CHECKPOINT_LATEST.md`. Never mark this as merged into main until exact-head CI and merge are independently verified.
