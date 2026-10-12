# RFH Phase 1A — figure/caption communication modes

**Scope:** Figure/caption mapping only, in `tlyoon/MicroGen_AI_Web`. TTS stays API based; slide and narration adapters are future Phase 1B/1C work. Production Windows launcher **is not switched by this PR**.

## Mode contract

The figure mapping script uses `selenium_pipeline.communication_policy`. `MICROGEN_COMMUNICATION_MODE` defaults to `selenium`. `api` never starts or attaches Chrome, and `fallback` tries Selenium three times before up to two API attempts. Each source-page mapping is independently planned and starts on Selenium again even if a prior page fell back.

Control retry budgets with `MICROGEN_SELENIUM_ATTEMPTS` and `MICROGEN_API_ATTEMPTS`, each bounded from 1–10. A successful validated page ends the attempt series. Selenium mode is explicitly checked against `MICROGEN_GEMINI_UI_MODE=flash` before a Gemini request.

The older `MICROGEN_FIGURE_MAPPING_BACKEND` setting cannot force API when the common mode requests Selenium; it remains in the compatibility code only until all stages have been migrated.

A mapper rejection, stalled UI response, or Chrome startup failure is retryable. Missing files, validation-input errors and permission failures are permanent; no API fallback occurs for them. A machine-readable trace, `crops/page_N/gemini_transport_attempts.json`, records backend, attempt, error type and validation status without storing credentials or prompt data. A page only passes when its mapping has been validated; exhausting all attempts halts the stage and downstream generations.

**Important limitations:** This adapter implements **mapping transport**, not the separate composite/panel fidelity or rendered-slide clipping fix. Those remain in RFH figures/visual integrity stages. Nested legacy submission retries are reduced to one when this policy manages the request, avoiding an accidental nine-Selenium-attempt explosion. Current API mapping already has source-PDF/PNG-grounded validation; keep it.

## Acceptance and rollout

- No-network tests exercise actual `run_mapping` orchestration from the vendor function body, not just a hypothetical mode planner.
- Cases cover pure Selenium, pure API with zero Chrome starts, successful recovery before fallback, strict Selenium-first fallback, complete exhaustion, permanent permission errors, missing browser session and invalid modes.
- The full repo suite must pass on HP, Dell-115 and Yoga6, plus Windows/Ubuntu GitHub CI.
- After merging, do **not** update the pinned production launcher yet: Phase 1B and 1C must provide genuine slide and narration parity before the single central mode can be safely advertised as functional for the complete pipeline.
- Live user-authenticated Gemini page mapping should be piloted on an isolated copy after all three adapters exist, subject to quota/workload limits.

All textbook source PDFs and existing MP4s stay untouched by this branch.
