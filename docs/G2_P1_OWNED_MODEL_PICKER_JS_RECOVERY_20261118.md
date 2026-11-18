# 18 November 2026 — Owned Gemini model-picker inert native-click recovery

## Critical-path gate: BLOCKED_EXTERNAL_DEPENDENCY, not original-operation recovery

Original target is the Serway §1.3 two-PDF source-grounded independent Gemini acoustic/scientific G2 review. Source-science accepted **20/85** utterances, 65 pending; next unattempted slide 12. The previously consumed original academic and v1/v2 synthetic two-PDF claim identities are unchanged and cannot be replayed. G3/media and student publication remain unapproved. No separate paid transport is authorized.

## 1. Historical investigation and real failure reproduction

Existing remedies for Gemini UI drift included fresh owned-tab selection, model-family checking, finite Thinking-level menu discovery, closing stale overlays, registered Account B profile reopening and one-Send quarantine. After commit `67ffdf0` all three hosted checks passed, but the real Account B Pro/Medium preflight still could not positively verify Medium. Previous source-free menu inspection found native `picker.click()` left the *exact verified owned Pro model picker* with `aria-expanded=false`, no visible menu panels and zero accessible menu options.

A new, bounded **real Dell-115 Account B owned Pro picker** test clicked the *same specific model button* once using its DOM `click()` (not a composer, model option or Send control). That made the Pro picker `aria-expanded=true` and exposed three discrete model menu options. The read-only live option labels were **4 Hydrogen**, **4 Hydrogen Thinking**, and **3.1 Pro**. No independent `Medium` Thinking control was discovered. **A model named “Thinking” is not a positive Medium effort setting.** Do not infer a missing account capability from an undiscoverable submenu, and do not select the new model family without separate model-contract eligibility.

Evidence preserved locally:
- `MicroGen_AI_Web_Checkpoints/accountB_picker_toggle_structural_20261117.json` — inert ordinary picker click
- `MicroGen_AI_Web_Checkpoints/accountB_verified_picker_js_click_once_20261117.json` — same owned picker opened with JavaScript click, 3 options, no Sending
- `MicroGen_AI_Web_Checkpoints/gemini_accountB_exact_menu_semantics_20261118.receipt.json` — 3 actual exact selectable model names and roles
- `MicroGen_AI_Web_Checkpoints/accountB_js_fallback_presend_20261118.receipt.json` — real normal Pro/Medium preflight remained blocked before Send

These are **source-free control diagnostics**, not an external PDF-response capability proof.

## 2. Executable remediation on normal path

The historical `gemini_thinking._expand_for_thinking` normal selector now calls `_open_owned_mode_picker_with_verified_fallback`. This does:
1. Confirm an unchanged owned Gemini tab, unique picker and configured selected family;
2. Try native picker click only once, wait briefly and check its `aria-expanded`;
3. If native click is positively inert and zero visible semantic menu options exist, consult the **enabled exact recovery registry** entry `GEMINI_EXACT_PICKER_CLICK_FALLBACK`;
4. Use at most **one JS click** on that **same unique DOM button**, gated by a visible `Open mode picker, currently Flash/Pro` aria-label and button element identity;
5. Require positive post-click menu expansion or accessible semantic options, otherwise stop before any Send.

All old source/request claims, authorization limits and the independent radio verification of Medium remain authoritative. There is no hidden fallback to the newly shown “4 Hydrogen Thinking” model, no temporary downgrade and no paid API. The normal `_expand_for_thinking` still closes any stale owned popup after nested Thinking discovery failure.

The previously registered `GEMINI_OWNED_THINKING_OVERLAY_RECOVERY` handles transient submenu failure; model-picker fallback and submenu recovery are distinct reusable historical signatures, both invoked through the **normal pre-Send pathway**.

## 3. Tests, real acceptance and restart boundaries

Focused exact fallback/Thinking/registry tests: **67 passed, 0 failures**. Broader source-free G2/one-Send/transport/model/Thinking regression: **180 passed, 2 skipped, 0 failures** on Dell-115 (5 nonfatal dependency warnings). The focused tests inject an inert native click followed by a verified one-click DOM recovery, correct menu with no DOM fallback, retired registry, foreign tab, wrong selected family, wrong control identity, absent menu after JS click, and full normal Thinking selection with exactly one verified Medium radio choice. Tests of the real observed 4 Hydrogen / 4 Hydrogen Thinking / 3.1 Pro menu confirm none is mistaken for Medium.

The genuine no-Send Pro/Medium preflight still ended `GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS`, with zero uploads, zero provider Sends and no scientific approval. Therefore the **model-picker control subproblem** has a verified local UI remedy and a tested normal executable path; the **Thinking-control availability subproblem** remains blocked. This is **PATCH_INTEGRATED + TESTED_OFFLINE** with a real isolated button-click success, **not** LIVE_CAPABILITY_VERIFIED for the required two-PDF modality and not ORIGINAL_OPERATION_RECOVERED or NEXT_MILESTONE_ADVANCED.

## 4. Next eligible operation

Do not issue another synthetic or original PDF-bearing Send merely because the picker now opens. First require an **independent positive actual Medium Thinking radio verification** on an authorized account/model, plus an eligible distinct unique test claim. If Google continues to expose only integrated model-level “Thinking” without a separately verifiable Medium control, document the account/UI limitation, preserve the previous one-Send claims and stop. Any change to model contract or paid API use needs a separately authorized, tested transport; scientific acceptance cannot be inferred from menu state.

A production merge, deployment or G2/G3 completion is **not claimed** by this evidence or by a draft branch commit.
