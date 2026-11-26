# MicroGen v7.1 — G2/G3 source-ready autonomous dispatch (26 November 2026)

## Verified historical cause

The Dell-115 pinned `development_continuity_executor_v71.py` plan had five tasks. Four were completed; its only remaining task, `release_authorization_required`, was `awaiting_authorization`. Its original state correctly reports `BLOCKED_OR_AWAITING_EVIDENCE`. Do not edit or rehash this original executor or force the release gate.

The separate global handoff queue had only two older `QUARANTINED_INVALID_PLAN` records. The existing daemon did scan independent plans, but no new admissible plan was present, so it repeatedly reported `WAITING_FOR_ELIGIBLE_WORK`. The original G3 8.2/8.3 source-only work was independently complete, the technical media proof had witnessed 32 encoded slide pages, and G3 independent science, acoustic and within-slide highlight acceptance were NOT complete. Historical G3 requests had reached the original finite possible-Send cap.

## Executable remedy

`selenium_pipeline/development_g2g3_eligible_dispatch_v1.py` reads an explicitly supplied, independent, immutable `source_backlog_v1.json` placed in the existing global handoff intake directory. It verifies the original G2 queue SHA, original `source.pdf`/`slides.pdf`/`script.txt` SHA identities and the completed G3 source-only progress SHA and no-Send/no-publication flags. It selects bounded G2 slides without both recorded initial and independent challenge reviews, and writes a single SHA-keyed, immutable `next_g2_source_preflight_<sha>.json` plan using the unchanged v7.1 **allowlisted** `g2_review_preflight` offline worker. It claims each plan once and refuses source drift, altered old plans or unauthorized inputs. The existing `development_continuity_handoff_v71.scan_and_dispatch` then actually starts and receipts child workers. Restarts consume the same receipts and do not replay.

The daemon now differentiates independent eligible handoff dispatch, original-source discovery held, quarantined plan, and **G2/G3 independent acceptance evidence required**. The older fixed-plan status remains recorded for historical fidelity, but it is not presented as the entire project's progress state. A failed new-source lane does not prevent other already admissible handoffs. No paid provider access, science review, source edits, media conversion, publication, G3 budget reset, or code authoring is offered by these offline processes.

The executable repair is registered in both `recovery_registry.py` and `recovery_registry_v1.json` as `G2_G3_SOURCE_READY_OFFLINE_DISPATCH_20261126`.

## Real Dell-115 verification

In an **isolated new checkpoint** `RECONCILE_20261125/G2_G3_ELIGIBLE_DISPATCH_REAL_PROBE_20261126`, the actual archived G2 queue and G3 completion report admitted the previously unresolved G2 slides **3, 4, 10, 11**. The existing v7.1 worker started four original-source preflights, all four produced completed immutable offline results, and a second run started **zero** new workers. The source PDFs/slides/scripts, queue and G3 completion hashes remained unchanged. The actual saved preflight dispositions were:

- Slide 3: `RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND`
- Slide 4: `AMBIGUOUS_OLD_SEND_NO_RESUBMISSION`
- Slide 10: `RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND`
- Slide 11: `RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND`

The source-only preflight is **not** a new scientific acceptance. G2 remains at its independently proven prior 29/85, not four additional agreements. Neither slide 4's uncertain send nor any other old uncertain request may be replayed without an independent, original-request outcome reconciliation. G3 science/acoustic/video QA remain open. The real proof is in the immutable `verified_real_dispatch_receipt.json` in that isolated checkpoint.

Unit fault-injection coverage: `tests/test_development_g2g3_eligible_dispatch_v1.py` (original-source mutation, changed original queue, G3 source drift, duplicate slide, authorization bypass, immutable plan tamper and restart). Existing daemon, handoff, journal recovery and acceptance scheduler regression suites must also pass. GitHub main merges must pass both Windows CI jobs on the **exact PR head**; after guarded deployment only, install the immutable live backlog configuration in the original global handoff directory. Preserve original authorizations, executor hash and campaign identity throughout.

## Remaining genuine boundary

An offline scheduler cannot manufacture independent textbook/physics agreement, authentic spoken WAV inspection or synchronized physics-element video acceptance. These lanes require actual new and independently attributable evidence, within the user's current Selenium-only scientific-review authorization and without replaying ambiguous/historically exhausted sends. When source-only evidence is exhausted, report that exact boundary rather than starting duplicate workers merely to appear busy. The separate hourly ChatGPT automation remains the code-authoring workflow; the Windows daemon remains a source-only, read-only dispatcher.
