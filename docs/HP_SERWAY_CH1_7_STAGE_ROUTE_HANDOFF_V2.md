# HP Serway 1–7 stage-isolated model-route handoff (28 November 2026)

## Failure reproduced after PR #683

The first repaired HP production run resumed Section 1.4. It reused verified source figures and slides, and entered the narration Selenium worker. The owned model picker and Medium Thinking were separately verified, but before uploading the source documents or typing/sending a Gemini prompt, `commit_verified_pending_route(stage="narration")` rejected `Pending dynamic route identity changed`.

Root cause: `selenium_pipeline.runner` snapshots a child environment before its stage loop. The parent `ensure_mode()` then selects a **new** model for the next stage and updates the parent's `MICROGEN_DYNAMIC_ROUTE_PENDING`, but the worker's preexisting child environment still inherited a pending record for the **previous stage**.

Section 1.6 repeatedly failed three owned Medium Thinking presend checks before a model Send. Its full latest error record was retained and it was not published. Sections 1.2, 1.3, and 1.5 have distinct earlier uncertain Gemini outcomes; they must remain quarantined.

## Corrective code

- `selenium_pipeline.stage_route_env_v1.sync_stage_route_env` preserves a valid pending route only if its stage matches the upcoming worker. It removes stale parent/child route identity and route metadata at stage boundaries; invalid records fail closed.
- `selenium_pipeline.runner` invokes this handler before each stage and again after each `ensure_mode()`, so a freshly selected, verified task route is forwarded to the child for exact owned model plus Thinking checks.
- `selenium_pipeline.safe_presend_retry_v1` adds a revision-gated rearm only for source-hash-bound, latest-log-proven pre-Send narration route-identity or threefold slide Thinking failures. Uncertain sends, completed videos, missing logs, changed sources and same-SHA attempts are not eligible.
- HP supervisor `scripts/serway_ch1_7_hp_full_horizon_supervisor_v3.py` recognizes only these precisely verified historical quarantines when a different main SHA is deployed; all other quarantined jobs remain protected.

The retry qualification **is not academic acceptance, permission to reissue an uncertain Gemini request, or permission for paid content API transport**. Non-highlight academic/media quality gates, source-figure authenticity and audio acceptance remain in force.

## Validation and operating acceptance

The HP local targeted test run passed 24 tests, including a direct pure-code reproduction of the old stage mismatch and exact `commit_verified_pending_route` now receiving `narration`. Protected Windows reliability CI must pass before merging. The HP generation schedule is kept enabled; deployment uses an exact merged main SHA and checks that the running older supervisor is not active before repinning, then triggers the scheduled task and audits a new section completion or genuine blocker.
