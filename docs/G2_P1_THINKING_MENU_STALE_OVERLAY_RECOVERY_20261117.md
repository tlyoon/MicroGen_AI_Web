# 17 November 2026 — Gemini Thinking-menu stale-overlay recovery; P1 still externally blocked

## Original failure and historical comparison

On Dell-115, original Serway §1.3 academic two-PDF Gemini Pro/Medium submissions for slides 10/11 and two distinct later source-free two-PDF capability challenges (v1, v2) reached their documented one-Send boundary but failed to yield an attributable model reply. The v2 owned-tab quarantine explicitly showed zero assistant reply nodes after 151 seconds, and the existing read-only original primary Chrome history check did not recover a saved reply. Do **not** replay any consumed source or synthetic PDF request or infer a Google backend outage from absence of DOM output.

Historical Selenium model-selection remedies included bounded no-Send menu discovery, authenticated primary-profile reopening, enrolled Account B Chrome restoration, and exact Pro/Medium radio verification. Account B was reopened earlier on port 9225; its owned Pro family was confirmed but its Medium preflight reported `GEMINI_THINKING_LEVEL_UNAVAILABLE_NO_SEND`. A distinct 17-November owned-tab structural inspection verified the **Pro** picker but could find **no unique Thinking expander**, and the opened model menu returned zero accessible atomic options. This does not establish that Medium was positively absent: the submenu may be missing, hidden or inaccessible to Selenium.

A separate once-only primary-account Flash/Medium no-Send preflight returned `GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE`. Flash is not a positive alternative route now. The actual original PDF response remains unverified.

## Concrete production defect reproduced and corrected

The legacy `gemini_thinking._expand_for_thinking` clicked the model picker *before* discovering the nested Thinking expander. If expander discovery then raised, the helper never returned the picker to its caller, so the caller's `finally` could not close the modal. Subsequent retries began with a stale open overlay. A second code weakness classified the repeated missing expander as `REQUESTED_THINKING_LEVEL_UNAVAILABLE`, incorrectly treating a UI-discovery failure as proof of an unavailable level.

**Integrated repair**:
- The normal `_expand_for_thinking` now closes *only* the already identified owned model picker on every expander-discovery exception, then re-raises without typing, uploading or clicking Send.
- Bounded `select_owned_gemini_thinking_level` retries a missing expander only if the exact code-reviewed registry mechanism `GEMINI_OWNED_THINKING_OVERLAY_RECOVERY` remains enabled. The ordinary selector can now recover within the finite pre-Send timeout when a transient UI overlay clears.
- If the expander never became reachable, classify `PRE_SEND_THINKING_EXPANDER_NOT_UNIQUE_OR_MISSING` rather than a missing Medium option. If the expander appeared but **no positive other selectable radio** was witnessed, classify `PRE_SEND_THINKING_OPTIONS_NOT_DISCOVERABLE_NO_SEND`. Only a positively witnessed offered list lacking Medium supports `PRE_SEND_REQUESTED_THINKING_LEVEL_UNAVAILABLE_NO_SEND`.
- The normal Selenium failure classifier maps the missing/unreadable-control states to `GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS`. It does not treat any Pro label, account login or broad text as a Medium radio proof.
- A retired/removed registry entry stops any automatic reattempt; even then the owned menu is closed safely. The shared pre-Send retry controller also avoids rebuilding Chrome clients three times after the full bounded missing-submenu inspection already ended. No old PDF one-Send budget is reset.

## Real Dell-115 acceptance result

The Account B Pro/Medium no-Send preflight **after this cleanup** returned the corrected `GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS`, with zero files uploaded, zero model requests, no paid operations and no scientific approval. This corrects a real UI failure mode but **does not establish selectable Medium or prove that Gemini PDF response generation has recovered**. The original G2 source-science ledger stays 20/85 accepted, 65 unresolved and slide 12 unattempted.

Offline fault-injection includes a transient missing-expander → cleanup → successful Medium radio selection and independent verification in the same finite pre-Send attempt; persistent missing expander → terminal typed discovery failure; empty controls not mislabeled provider absence; observed Low/High without Medium → truly unavailable level; registry retirement → safe stop; foreign-tab and one-Send regression. Focused **58 passed / 1 skipped**, final broader connected G2/provider/recovery tests **158 passed / 1 skipped** on Dell-115, with no failures. Hosted CI conclusions belong to the exact subsequently pushed commit, not prior commits.

## Remaining mandatory P1 boundary and next genuinely eligible route

This is `PATCH_INTEGRATED` and `TESTED_OFFLINE` for UI menu recovery plus a real **no-Send** Account B failure classification; it is **not** `LIVE_CAPABILITY_VERIFIED` for two-PDF requests, `ORIGINAL_OPERATION_RECOVERED` or `NEXT_MILESTONE_ADVANCED`. The mandatory stop remains `BLOCKED_EXTERNAL_DEPENDENCY`.

The normal G2 controller may only continue to a new synthetic *two-PDF* challenge if a genuinely distinct, authorized transport first positively verifies the exact owned model and Medium Thinking, and an independent finite claim is available. The synthetic challenge must return both distinct unprompted PDF secrets and an attributable model answer; only then may the normal controller dispatch an untouched source-bound review, verify its exact original quotes/math and independently accepted output, and advance G2/G3. Any paid API route requires separate explicit cost authorization. If the provider still yields no answer, persist the original stop and do not replay. This restoration proof is not yet available.
