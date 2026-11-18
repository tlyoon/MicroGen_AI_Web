# 18 November 2026 — Dynamic task-scoped Gemini Apps model/Thinking router

## Critical path: G2 still externally blocked
Serway §1.3 original two-PDF scientific review is **20/85 accepted**, with 65 unresolved and slide 12 unattempted. Earlier original academic and source-free two-PDF requests remain exhausted and must not be replayed. Neither source-science approval, two-PDF capability proof, acoustic/video G3 completion, paid operations, nor release can be inferred from this model-picker improvement.

## Historical blocker and new root-cause evidence
Previous Selenium code recognized only `flash-lite`, `flash`, and `pro`. Account B's actual Gemini UI on Dell-115 on 18 Nov 2026 offered **4 Hydrogen**, **4 Hydrogen Thinking**, and **3.1 Pro**, but no standard Flash. A hard-coded Flash selection could not choose the new advertised family. Worse, an inert native picker click could masquerade as a missing model before the menu was genuinely opened; the existing exact owned-picker JS fallback was therefore reused in the ordinary model selector. Earlier model/Thinking overlay recovery remains unchanged.

Google's current Gemini Apps Help (the authoritative product-specific source for browser model names) and Google's API model catalog were fetched **independently** from their official HTTPS pages on Dell-115. Public API endpoint existence is **not evidence** the connected user's Google plan or Chrome UI offers that same model. The official Apps Help text positively showed the families Argon, Carbon, Hydrogen, Flash, Flash-Lite, and Pro. The browser's actual menu is the source of runtime availability; Google Help cannot authorize clicking locked or missing options.

Sources:
- https://support.google.com/gemini/answer/18648722?hl=en
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/deprecations

## Executable path / ownership

**Files added:** `selenium_pipeline/gemini_official_catalog.py`, `gemini_task_profiles.json`, `gemini_dynamic_task_router.py`, and related tests.

**Normal-path updates:** `gemini_model.select_owned_gemini_with_recovery` invokes task routing only after a positive owned-tab model option snapshot proves the previous default absent. `gemini_model.select_owned_gemini_mode` reuses the exact registered, one-click model-picker repair even if the old current model differs from the requested one. `gemini_stage_policy` recognizes only individually classified supported browser families. The normal `vendor_template_v2/selenium.py` generation path binds the authenticated port to each task and persists a new task default ONLY after New chat, owned-model re-selection and verifiable Thinking radio. `gemini_thinking.select_owned_gemini_thinking_with_recovery` now consults task-specific minimum thinking requirements for a positively observed non-downgrading radio fallback.

An exact `GEMINI_DYNAMIC_TASK_MODEL_ROUTER` entry is registered in `selenium_pipeline/recovery_registry_v1.json`; retirement disables new-model discovery. The prior strict source-bound academic reviewer is not silently rerouted: a changed academic model requires a separate, independently verified response transport and scientific-requalification evidence.

**Catalog:** Official Apps Help and API docs are fetched with finite HTTPS timeouts and approved domains only, with 24-hour TTL and at most seven days of previously verified stale cache on outage. The cache stores only model family evidence, URL, fetch time, and source digest; never prompt, login, account, conversation, model reply or browser content. Unknown or unsupported marketing families cannot be promoted from an API endpoint or textual guess.

**Task policy:** `figures` prefers low-cost Lite; `slides`, `narration`, and `rich_mapping` prefer balanced Flash/Hydrogen and Medium or better; `academic_review`, `acoustic_qa`, and `repair_analysis` require higher reasoning and positive task-level minimum effort. Integrated `Thinking` in a model name is not a standalone Medium radio. No task may automatically use a lower-than-minimum effort, locked model, unlisted new family, or Gemini auto mode for source-science review.

**Persistence:** Existing verified defaults are stored per task and per authorized browser profile at `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/gemini_task_defaults_v1.json`, with process lock, atomic replacement and source/selected label evidence. A proposed or failed fallback is NEVER persisted. Exact API model IDs are marked unverified for new browser-only UI names (`ui-only-...`), never invented as real API endpoints. Original source claims are unchanged.

## Real Dell-115 test and acceptance boundary
A source-free, **no-Send**, bounded genuine Account B `slides` task test used the production `select_owned_gemini_with_recovery` code with preferred Flash. Flash was absent. The official catalog + exact model menu selected and confirmed **4 Hydrogen** with `PREFERRED_MODEL_MISSING_OFFICIAL_AND_LIVE_UI_FALLBACK`; then `select_owned_gemini_thinking_with_recovery` found no unique Medium submenu and returned `PRE_SEND_THINKING_EXPANDER_NOT_UNIQUE_OR_MISSING`.

Receipt: `MicroGen_AI_Web_Checkpoints/real_dynamic_gemini_accountB_slides_presend_20261118.receipt.json`.

Result: `model_family_exactly_verified=true`, `task_default_persisted=false`, `new_model_requests=0`, `pdf_uploads=0`, `prior_source_claim_replayed=false`, `paid_operations=0`, `original_science_approved=false`. This proves on-flight **model replacement**, not full task-route readiness or P1 two-PDF recovery.

## Required executable recovery contract
1. Historical model absent / selector failure recorded under immutable request and task identity
2. One code-reviewed registry route and finite official catalog lookup
3. Exact selectable owned menu model vs official Gemini Apps evidence; never pick unknown/locked entries
4. Model click and independent selected-label verification; model replacement alone is not success
5. Task-specific minimum Thinking level selected from positively witnessed radio, never inferred from a marketing label
6. Save only the successful task/profile default after new-chat model and effort revalidation; no Send during discovery
7. On model/Thinking drift, reset only the pre-Send selection path, not prior exhausted source Send claims
8. Advance original academic G2/G3 only after separate original-operation source-science and two-PDF transport acceptance

The engineering repair is **PATCH_INTEGRATED + TESTED_OFFLINE**. Live model switching is verified on Account B. **LIVE_CAPABILITY_VERIFIED** for required Medium and two-PDF responses, **ORIGINAL_OPERATION_RECOVERED**, and **NEXT_MILESTONE_ADVANCED** remain false until independently established. Passing CI on an unmerged PR is not production deployment.
