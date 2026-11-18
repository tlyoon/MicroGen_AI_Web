# P1 post-Send passive diagnostics and verified Selenium route selection
**Date:** 17 November 2026 (MYT). **Runner:** Dell-115 only. **Development:** draft PR #530, no main-branch deployment.

## Critical-path evidence and limitation

Original Serway §1.3 G2 science remains **20/85 accepted**, **65 unresolved**. The two original PDF-review claims and two distinct synthetic two-PDF incidents are consumed. The authenticated primary Pro/Medium session previously verified PDF upload and single Send, but Gemini produced no browser-visible model reply. The final preserved v2 DOM diagnostic had zero model-response and zero alternate assistant nodes, so a simple selector miss is not the leading current hypothesis. Google backend, app and network causes remain unproven.

**P1 is BLOCKED_EXTERNAL_DEPENDENCY** until a genuinely attributable live two-PDF readback succeeds, then an eligible original source-bound review is independently accepted and G2 advances under the normal recovery journal. Successful code tests, model picker evidence, upload readiness and a Send registration do not close P1.

## P1-A: Normal-path passive network evidence

New `selenium_pipeline/gemini_owned_network_diagnostics.py` is a versioned, registry-locked, read-only diagnostic. `series_gemini._browser_request` arms the browser's Resource Timing baseline in the exact owned Gemini tab immediately before its single existing Send. On failure of strict model response capture and late-recovery observation, the same exact tab and conversation route are checked again. A normalized allowlist is persisted in the normal quarantine receipt under `owned_tab_network_timing`, alongside previously implemented DOM counts.

The metadata contains only bounded counts: total new resources, same-origin resources, known Gemini API category, other Google category, fetch/XHR initiators, HTTP 4xx/5xx categories and unavailable response-status counts. Resource URLs, request methods/bodies, page content, response text, cookies, bearer tokens, source identifiers, account identity, network headers and screenshots are never returned or saved. If the tab, conversation route or page time origin changes, the diagnostic is explicitly unavailable or route mismatched. Unknown status, missing performance data and no observed new entries are NEVER labeled a provider outage, or a reason to retry a claimed Send.

The diagnostic does not intercept the network and cannot be installed retrospectively on earlier consumed requests. Its purpose is to improve classification on future *new and eligible* operations only. Even positive resource timing is not confirmation the model generated or delivered a usable PDF-grounded answer.

## P1-B: Explicit Gemini transport selection

New `selenium_pipeline/gemini_transport_router.py` is a versioned, registry-selected pre-Send router for the normal **academic Gemini Pro/Medium** worker. It selects the existing primary Chrome debugging session at port 9222, or the previously authorized alternate session at 9225 ONLY when already active, authenticated and positively verified on its own model/Thinking controls. The ordinary `ai_academic_web_review._academic_browser_request` now chooses the verified port before uploading attachments or clicking Send; the normal `academic_review_checkpoint.submit_once` remains responsible for immutable exactly-once source claims. Pre-Send route inability raises a typed no-click browser error for existing bounded claim repair; after a possibly accepted click no provider or account replay is allowed.

The existing Flash-first model preference and its stage-aware selector are left unchanged for other stages. The router's `execute_gemini_api` remains explicitly NON-OPERATIONAL. Environment variables or mere existence of an API key cannot authorize a paid API call, reroute a submitted job or relax two independent Gemini-only scientific reviewer requirements. Actual API support would require its own source-bound one-Send integration, rate/cost limits and explicit user authorization before any chargeable operation.

## Regression and actual remote observation

- Focused integration (new diagnostics/router, v1/v2 PDF proof, DOM response quarantine, registry, original claim protection, G2, alternate browser, previous source response recovery): **154 passed, 1 skipped, 0 failed**, five nonfatal third-party dependency warnings.
- New unit tests inject a true authorized alternate, a missing/ambiguous Thinking control, forged response evidence, changed tab/route, stale page time origin, false outage labels and an API-enabling environment variable. These either return a verified pre-Send Selenium port or fail closed before any Send.
- The source-health gate had a pre-existing mismatch where explicitly supplied observation time could suppress a future successful v2 PDF proof; the new focused test checks this path and the existing historical time guard remains strict. No consumed historical proof was rewritten or accepted.
- A real **READ-ONLY** Dell-115 Chrome attachment to the already-running authenticated Gemini session sampled a baseline and observed no intervening resource activity (`OWNED_NETWORK_NO_NEW_RESOURCE_TIMING`). **0** prompt, upload, API, Send, scientific approval or release operations occurred; this is a passive browser capability proof, not old-incident network evidence. Log: `G2_SERWAY13_CONTINUATION_LOGS/p1_network_real_readonly_20261117.log`.
- The normal original Serway 1.3 foreground G2 journal was re-executed after integration. It must retain the two prior exhausted modality claims and accept no original source-review advancement without new independently verified PDF readback. See `p1_network_router_original_g2_after_integration_20261117.log`.

## Next boundary and engineering priorities

1. **P1:** Obtain new independent evidence of a genuinely eligible two-PDF response path, or inspect an already-owned saved late reply from the same exact prior claim without another Send. No third iteration of the same exhausted source/profile incident.
2. **P2/G2:** Only after live Gemini PDF readback passes, submit untouched source-bound slide 12 and require independent math/source acceptance, not merely text generation. Continue through remaining 65 review units, two ambiguous fractions and original counter geometry correction.
3. **P3/G3:** Acoustic/video and a separate subsection acceptance retain independent QA, finite retry limits and paid-operation boundaries.
4. **P6:** Hosted CI on the exact new draft PR head and code integration are separate from external-science acceptance. This update does not merge to main or install an always-on scheduler.

## Post-integration genuine G2 restart result

The actual foreground invocation `g2_forward_recovery_engine --execute --max-cycles 1 --no-auto-media` completed with `ENGINE_EXIT=0`, `G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY`, `stage_cycles_this_invocation=[]`, `critical_path_recovery_proof.status=BLOCKED_EXTERNAL_DEPENDENCY`, `original_operation_recovered=false`, `next_milestone_advanced=false`, `new_model_requests=0`, `G2_claimed_complete=false` and `next_scheduled_task_created=false`. The content-addressed offline readiness receipt was `dea26539b618dbfeeb19faaf883899324bc1562988059ef78d69566364fc895c.json`, SHA256 `2cae5ebbcf002526f7e532e80e4cfa601f4e34389e2da76410208c55a75d3663`. Original 13 slides, 85 narration units, **20 accepted and 65 pending**, zero missing visual-review candidates, two tied fractions and 13 unmodified legacy PDF-counter geometry blockers remain. The saved v1/v2 two-PDF Send claims were NOT replayed.
