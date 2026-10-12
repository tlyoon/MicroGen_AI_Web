# RFH Phase 1B — slide-generation communication modes

**Scope:** `MicroGen_AI_Web` slide generation. This does not change the production Windows launcher; full three-mode rollout awaits narration integration and controlled live pilots.

The slide generator now uses the shared `MICROGEN_COMMUNICATION_MODE=selenium|api|fallback` policy. Selenium is the default. API mode never launches Chrome; it calls `selenium_pipeline.slides_api` via the configured Gemini-SDK-capable interpreter. Fallback makes up to three Selenium content requests before up to two API requests, resetting to Selenium on the next independent lecture. Configurable attempt budgets remain 1–10 per backend.

All backends must pass the **same** existing LaTeX response sanitation, Beamer compile/sanity checks and citation-artifact rejection before `slides.tex` is accepted. The API transport includes the exact original `source.pdf`, rendered slide prompt and `png_dimensions.json`; it writes an isolated raw response only. It never directly publishes `slides.tex` or `slides.pdf`. Rejected Gemini responses and malformed PDF/metadata cannot be treated as valid output. The full image geometry/parent-subpanel fidelity and two-pass PDF footer checks remain future RFH gates.

No-network tests use the actual vendored slide-generation function body and mocked Gemini SDK clients to prove Selenium-first escalation and fail-closed rejection. The old shortcut of always opening Chrome at `__main__` is removed, so standalone pure API has no browser dependency. The runner only prelaunches Chrome for pure Selenium; fallback handles a failed browser connection as a bounded attempt rather than failing before API escalation.

**Remaining:** RFH Phase 1C must integrate narration with the same central mode and remove all conflicting hardcoded production API defaults. Afterwards a single CLI/launcher override and real three-PC controlled acceptance can certify the complete three-mode workflow. Audio TTS and audio QA stay API-based.
