# PR549 — Prevent obsolete Gemini model from consuming an original G2 synthetic-PDF Send claim

Date: 19 November 2026, Malaysia time. Authorised execution host: Dell-115. Parent source is PR548 exact SHA `6dfc394daa7daa5e84385a44eedc53fd7448a1ee` (draft and unmerged).

## Historical failure review and root cause

The original Serway §1.3 review has 20/85 accepted independent source-agreed utterances and 65 pending. Two original browser Gemini source Sends have no attributable replies; they must never be blindly replayed. The original one-shot synthetic dual-PDF v1 diagnostic also failed on 19 November, before a model Send, with `GEMINI_MODEL_PICKER_NOT_READY`. The original diagnostic claim was already consumed, so the correct response is **not** to retry or erase it.

Native Dell browser inspection showed the primary authenticated Gemini UI offers 3.5 Flash-Lite, 4 Hydrogen and 3.1 Pro but no exact Flash model. The existing v2 profile-repaired PDF diagnostic already verifies the exact Pro/Medium owned tab before consuming a new one-Send claim. The original v1 diagnostic did **not** apply that gate. As a result an unavailable model could exhaust one unique source-free diagnostic incident without a useful response.

## Targeted reusable code-level remedy

The v1 production `academic_dual_pdf_capability.probe_once` now reuses the existing registered no-Send academic browser model/Thinking verifier **before creating any synthetic PDF directory or diagnostic claim** when using the actual browser transport. Exact model family, Medium Thinking, primary port 9222, no uploaded files, no typed prompt, no Send, no scientific approval and no publication are verified. The existing v1 claimed outcome and daily-budget gates still take precedence, and previously consumed claims are never retried. A documented model/picker failure returns `V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM` with zero provider requests. A missing/disabled registry mechanism fails closed before the browser is touched.

A sixth independent source-safe stage `original_g2_v1_synthetic_presend_inventory` was added to the normal v7.1 project-wide executable supervisor, dependent on the original G2 read-only claim inspection. It checks the existing original synthetic incident and the current primary model availability **without** sending or claiming a request. The v7.1 event chain must demonstrate a real child dispatch and accepted checkpoint. The new stage's acceptance certifies only a successful no-Send inventory, **not** source science acceptance or model availability. If Flash is still missing, the observed blocker is recorded honestly.

## Actual tests already performed

On an isolated PR549 working tree, the first focused 34 tests passed. A genuine Dell-115 primary Selenium preflight of the exact Flash family observed `V1_SYNTHETIC_PDF_PRESEND_UNAVAILABLE_NO_CLAIM`, `GEMINI_MODEL_PICKER_NOT_READY`, **new_provider_requests=0** and **new_source_review_send_allowed=false**. Another focused combined 59 tests (including executable sixth-stage anti-stall and false-proof injection) passed. No original source mutation, new Gmail/Google provider request, TTS operation, student publication, or old request replay occurred.

Still required: broader local regressions, exact commit and hosted CI, actual normal six-stage execution at a clean exact SHA and post-restart no-duplicate validation. Do not infer G2 improvement from an offline unit test or a synthetic model picker check. G2 65 pending scientific segments, independent G3 voice/video QA, historical semantic review, stacked PR integration and student release remain separate, currently unapproved boundaries.

## Continuation

After verification, advance to the next safe independent boundary: source-free reconciliation of older Gemini response evidence, historical patch/dependency semantic review and original G2 screening without replaying uncertain requests. If no authenticated compatible model is available, keep the original scientific queue blocked while other independent code tasks continue. The finite v7.1 supervisor is not an installed always-on AI software engineer; never claim after-exit background continuation without verified runner ownership.
