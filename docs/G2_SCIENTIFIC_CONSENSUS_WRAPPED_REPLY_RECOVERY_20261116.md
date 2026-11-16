# G2 independent science consensus: historical source-only repair and exact envelope recovery

Date: **16 November 2026**. Authorized runner: **Dell-115**, isolated `feature/captionless-crosspage-recovery-stress-20261115` worktree. Source: **Serway §1.3**, source SHA `181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8`. Scope is authentic Gemini Selenium academic review; no new API/TTS billing or media publication.

## Verified historical prior

The 15 Nov `docs/G2_ACADEMIC_AUTOREPAIR_SOURCE_EVIDENCE_20261115.md` source-only remedy used `academic_quote_reconciliation.reconcile_untrusted_review` to recover saved, previously source-invalid Gemini replies. That mechanism **only demotes** unsupported `SUPPORTED` rows to `UNRESOLVED`, clears invalid citations and target IDs, inserts explicit unreviewed placeholders only for original utterances actually missing from a response, and reruns the independent original source/slide PDF validator before any two-pass AI consensus. It never fabricates source quotations, model rows, mathematical explanations, approval, or duplicates an uncertain Send. Source-only recovered slide-2 supported 4 genuine utterances across two separate model reviews; slide-4 partial reply remained unsupported.

## New root cause found in saved real Gemini replies

The original academic verifier expected `{"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE","rows":[...]}`. Authentic slide 5 and slide 7 independent challenge responses instead returned `{"job":{"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE","rows":[...]}}`. The old `reconcile_untrusted_review` necessarily rejected the top-level shape with `FigureIdentityReviewRequired("Original model review format cannot be reconciled")`, while correctly preserving original model response identity, one-Send claims and failed reconciliation evidence. This is a *transport response envelope error*, not by itself a scientific or Gemini outage.

## Permanent executable repair

1. `selenium_pipeline/academic_review_envelope_recovery.py` accepts **only** a single exact nested `job` object containing exactly `status` and `rows`; it does not touch the scientific rows. Read-only historical requalification requires the exact immutable request fingerprint and original source/slides/script SHA, already rejected saved response state, original claimed Send, original response SHA/length and matching saved model response identity receipt. It rejects ambiguous, unknown, modified or unclaimed responses.
2. The normal `ai_academic_web_review.validate_source_demoted_review` unwraps only that exact candidate shape, then calls the prior full `reconcile_untrusted_review` and strict `validate_model_review` unchanged. Its explicit envelope audit records **zero** added verdicts, source citations, model requests or support promotions.
3. The normal `ai_academic_review_queue.select_next_safe_review` recognizes one historical failed original saved-reply reconciliation and admits `RECOVER_WRAPPED_SAVED_REPLY_NO_SEND` *only* with the verified owned wrapped reply. It creates a separate successor `*_envelope_recovered_after_attempt_01.json` while keeping the old rejected attempt and failed reconciliation receipts unchanged. It will not attempt the same successor twice. A non-recoverable/tampered/unsupported candidate remains quarantined while other independent slides can continue.
4. `advance_one_safe_review` routes this action exclusively through the saved checkpoint's `validate_saved` path; it does not call Gemini. The original one-Send claim and raw text remain unchanged. The usual independent scientific consensus and media gates continue to govern any result.
5. `g2_forward_recovery_engine` classifies and persists the recovery type in its SHA-linked normal `NNNN.intent.json` / `NNNN.result.json` journal and automatically advances to the next independently eligible stage within a finite single invocation. It does not recreate any scheduled task, resubmit claimed source requests, grant academic approval or bypass paid media authorization.

## Real original-source stress outcomes (16 Nov afternoon)

The normal Dell-115 forward engine selected **slide 5 independent challenge** for no-Send recovery from its previously failed saved reply and wrote an accepted source-validated one-pass response, covering **6 actual original Gemini-reviewed utterances, 0 placeholders**. The regular two-pass scientific reconciliation then increased accepted source-verified utterances from **9/85 to 13/85**, a genuine gain of **4**, with 72 still pending/disputed. This did not add a new model review; it restored usable original evidence.

The SAME bounded foreground invocation automatically continued to **slide 7 independent challenge** using its old saved response. Its nested reply had **1 actual Gemini-reviewed utterance** and **6 absent units**, which remain explicit machine `UNRESOLVED` placeholders. It is a valid technical source-only reconciliation, **not** 7 new independent scientific reviews and not an academic pass for the six omitted units. No extra Gemini request was made for either historical repair.

The next eligible workflow stage is the unattempted slide 8 source review, subject to usual verified provider health and finite stage budget. Record its independent acceptance separately in the durable checkpoint and journal.

## Testing and limitations

Focused academic/G2 regression suite: **62 passed** before the final additional source-only negative test was introduced. Tests cover genuine historical-format reply preservation/no Send, successful onward progression, malicious extra wrapper keys, SHA tampering, insufficient source quotations, missing original model rows remaining unresolved, and independent forward progress. These fixture tests must be rerun after the new negative test, and the full Windows suite / PR head CI must be verified before production merge.

**G2 remains OPEN.** The two older uncertain model Sends, slide 4 and other unsupported units are still distinct unresolved sources of academic uncertainty. Full independent scientific acceptance, figure/geometry evidence, original TTS, acoustic QA, video proof and G3 approval are not implied by recovering an invalid response envelope. Do not assert 85/85, G2 completion, or release until independent evidence supports it.

## Confirmed end-to-end continuation (live Dell-115)

The real, source-bound foreground `g2_forward_recovery_engine --execute --max-cycles 3 --no-auto-media` completed. The immutable forward history advanced through:
- `0011.result.json`: recovered slide-5 challenge (six genuine model rows, no new Gemini Send), independently accepted source-science **9/85 → 13/85**.
- `0012.result.json`: recovered slide-7 challenge (one genuine model row, six explicit `UNRESOLVED` placeholders, no new Send), independent science **13/85** unchanged.
- `0013.result.json`: automatically proceeded to previously unattempted slide-8 initial review through one genuinely registered Gemini **Pro Medium** owned tab Send with both source/slides PDFs uploaded; the source validator marked it a one-pass accepted technical review, but science **13/85** remains unchanged until its independent challenge.

All three stages persisted `next_action=CONTINUE`, original science SHA, and original prior-stage SHA; run ended with `G2_FINITE_FORWARD_BUDGET_REACHED_CHECKPOINT_PRESERVED` at its declared three-stage budget rather than waiting for an operator or repeating a claimed Send. No scheduled task, paid TTS, video or publication occurred.

An additional injected crash-restart regression covers process termination **between** saved model validation and writing a new independent source receipt; the same immutable response can be verified and used to finish the local receipt with zero model submissions. The newer write-once successor receipt also contains explicit provenance: original response SHA, older failed reconciliation SHA, zero new provider requests, zero invented citations or verdicts.

## Final expanded local regressions

Post-fix Dell-115 combined suite (including the new crash-restart and source-only negative tests): **129 passed, 2 skipped, 0 failed** (5 nonfatal warnings). The two skipped SDK-wire tests need a newer google-genai interactions interface, not an academic source or Gemini browser response. Exact-current-head GitHub Windows CI remains to be verified after push.
