# V6 source-literal dimensional-rule focus recovery — review candidates only

Date: 17 November 2026. Normal production mapping on authorized Dell-115, MicroGen_AI_Web, separate draft PR #530.

## Root failure

All but one original narration unit on the source-locked Serway §1.3 lecture had a physically ranked review target after exact-operator and spatial fraction recoveries. The final `s005.utterance.003` says **"You cannot add a length to a time."**, while the actually rendered slide 5 says **"Quantities can be added or subtracted only if they have the same dimensions."** at physical PDF bbox `[32.727, 108.806, 333.46, 133.265]` pt. The existing lexical candidate mapper did not recognize `add` vs `added` and gave no candidate.

This is a *topical focus* relationship, not in isolation a source-validated physics proof: showing a general addition rule does not itself prove the specific spoken claim is scientifically correct without the underlying dimensions being independently corroborated.

## Normal executable repair

`selenium_pipeline/element_plan_autodraft._exact_dimensional_addition_rule_focus` recognizes only a bounded negative/add-or-subtract spoken form with at least two distinct explicitly named fundamental quantities (length, mass, time), together with the **exact physically printed** conditional addition rule in a source-bound PDF text target. It produces a deterministic low-stakes review hint (0.72), not approval.

The code-reviewed v6 registry signature `SPOKEN_DIMENSIONAL_ADDITION_RULE_TOPICAL_PARAPHRASE`, mechanism `EXACT_VISIBLE_DIMENSIONAL_ADDITION_RULE_REVIEW_HINT_ONLY`, must be present and enabled for this new hint to appear in the normal `stable_recommendations`. Retired/missing repair disables it; ordinary mapping and science checks continue unchanged. The offline source readiness algorithm SHA fingerprints both the modified source mapper and registry, so any change invalidates previous receipts.

Explicit tests deny the hint for affirmative statements (adding length/time allowed), two identical named quantities, missing/altered printed rule, wrong topical sentence or an off-topic statement. The original PDF's physically extracted target text, bbox and original utterance SHA remain required.

## Actual real source result and limits

A real model-free original-source candidate map on Dell-115 reported `s005.text.003` as the physical review target for this last utterance, score 0.72, `exactly_matched_visible_text=false`, `spoken_element_semantics_verified=false`. **There are now zero completely unranked original utterances among all 85**, down from 7 initially. However **two distinct slide-6 utterances** still have *tied* physically valid `1/2` target choices; these remain unselected in the independent fraction-ambiguity worklist. Other review-target suggestions still require source-semantic and timing assessment and can prove incorrect.

The 13 original deck's known page-counter geometry blockers remain on the source-locked old PDF, while the isolated repaired PDF and normal production Beamer generator are separately verified. Source-science consensus remains 20/85 accepted, 65 pending. Gemini Pro PDF-response evidence remains unavailable on claimed requests, so G2 and G3 cannot be declared accepted. No original source files, scientific review receipts, provider Sends, TTS/WAV/MP4, scheduled task or user-facing publication is changed.

Tests and final exact-commit CI require verification before release of this new revision.

## Genuine live forward execution and exact-fingerprint receipt

The real one-cycle `g2_forward_recovery_engine --execute --max-cycles 1 --no-auto-media` on Dell-115 performed the new offline source analysis through its **normal executable path**, and produced a new implementation+original-source-bound receipt:
`%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/g2_offline_source_readiness_v1/509280cc9943660ac129f3c054951d406b11e36049d6a13d5d68a8b2eac0e5fe.json`, SHA256 `bd8de8bf1104075308e95dfd98b0ce0d9bcfafb93a9eebcb829923fe6ceded05`.

Verified **0/85 unranked review candidates**, but **2 source-bound slide-6 utterances with unselected tied fraction choices**. Academic source consensus remains **20 accepted, 65 unresolved**; original historical PDF still has **13 geometry blockers** (the verified isolated/production future Beamer fix does not rewrite that source). The next untouched new model review is slide 12, with ten witnessed citation candidates. **Zero new Gemini requests** and no paid TTS, WAV, video, publication or new journal stage. Local extended regression **209 passed**, zero failures (five nonfatal warnings). Await hosted exact-head CI verification after commit/push.
