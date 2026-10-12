# RFH Phase 1C — narration transport and single production mode

**Scope:** MicroGen_AI_Web only. **Phase:** offline integration, not production rollout.

This change completes the initial central Gemini transport wiring across figure/caption mapping (Phase 1A), slides (Phase 1B), and narration (Phase 1C).

## Operator contract

`MICROGEN_COMMUNICATION_MODE=selenium|api|fallback` with **Selenium as default**, and explicit overrides supported by `python -m selenium_pipeline.runner --communication-mode ...` and `operations/Start-MicroGen_AI_Web.ps1 -CommunicationMode ...`.

- Selenium: only Gemini web UI for figures, slides and narration. No content-generation API fallback.
- API: only Gemini API for those three stages; no content-stage Chrome startup.
- Fallback: start each independent task with Selenium; at most three Selenium attempts, then at most two API attempts. Every attempt is subject to the stage's existing content/format checks.
- TTS and audio QA remain API-based, regardless of mode.

`MICROGEN_SELENIUM_ATTEMPTS` and `MICROGEN_API_ATTEMPTS` may override the bounded retry budgets (1–10). The old `MICROGEN_FIGURE_MAPPING_BACKEND` and `MICROGEN_NARRATION_BACKEND` variables are not authoritative over the central mode.

## Narration guarantees

The actual vendored script generator accepts the shared policy. API only reads both PDFs and the rendered grounded narration prompt; Selenium requests use the existing authenticated browser. A fallback on one failed narration request is **not sticky** for the next subchapter. Incomplete responses, failed validation, refusals and broken output cannot create a success receipt. Invalid local paths/permissions are permanent errors, not reasons to exhaust Selenium and API calls. Rejected narrated scripts are archived for diagnosis before retry, and structured request metadata records mode, backend, attempt and quality outcome (no secrets). Script QA and the source-to-video completion gates remain in place.

The runner now uses the existing local browser-lock mechanism for **possible** Selenium use in fallback mode, even though browser initialization itself is lazy. This prevents competing jobs on the same PC from using the same Gemini browser tab simultaneously. No second script mutation occurs after the successful final narration quality check.

## Testing and deployment boundary

The fault-injection suite exercises the actual narration main function without accessing Gemini or real lecture material. It verifies Selenium-only, API-only, fallback order, stop-on-success, rejected-script archiving, refusal of missing source, SDK/Chrome preflight, and production launcher mode precedence. Cross-PC full regression and Windows/Ubuntu CI must pass before merge. The old production checkouts stay pinned until separate isolated end-to-end pilots prove each mode, including real Selenium Flash selection and an API fallback. This Phase 1C merge is **not** itself a declaration of real three-mode production acceptance.

Next gate: Phase 2 Gemini refusal/stall/load orchestration and real controlled multi-PC pilots, followed by image/composite fidelity and mathematical pronunciation work.
