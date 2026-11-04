# PR497 - Production model route diagnostics and explicit content API mode

General codebase completion work, **not** another Thomas/Serway per-PDF repair.

### Physical Dell-115 provider capability (2026-11-04)

A metadata-only test, using the already existing isolated Windows worker and
configured Microvid environment, reported **two configured Gemini API keys**,
the exact vetted `gemini-3.8-flash` model metadata **reachable**, and the
existing 9222 Gemini Chrome authenticated composer **ready**. This made
**zero model-generation requests** and no paid TTS or video. It does NOT
certify any specific Gemini generation will succeed or that one PDF is ready.
The probe explicitly scrubs exception contents and key bytes, reports only
safe model name/availability/status, and does not share PDF or prompt content.

```powershell
python -m selenium_pipeline.windows_provider_readiness_probe
python -m selenium_pipeline.windows_provider_readiness_probe --inspect-browser --probe-api-model-metadata-once
```

The latter is an explicit, non-generative, single model metadata lookup.

### An alternate *new source* API path without silent fallback

The existing core already supports Selenium, API, fallback for figures,
slides, narration. The safe original-source Windows orchestration previously
hard-coded Selenium even though the API transport was implemented.

`windows_fresh_source_trial` and `windows_original_stage_sequence` now
expose **selenium (default)** and **api (opt-in)**. API generation requires
the separate explicit `--confirm-content-api-cost` flag BEFORE writing any
attempt receipt or invoking a model. Automatic fallback is deliberately
DISALLOWED: retrying an already-submitted Selenium prompt through the API
without source/provider reconciliation would double-submit.

A new, untouched publisher PDF/section + fresh immutable campaign can
use this command only after content API expenditure is explicitly authorized:

```powershell
python -m selenium_pipeline.windows_fresh_source_trial `
  --source-root 'PUBLISHER_BOOK_ROOT' --subchapter 22.7 `
  --trial-dir 'NEW_EXTERNAL_VERSIONED_CAMPAIGN' `
  --communication-mode api --confirm-content-api-cost `
  --attempt-figures-once --timeout-seconds 600
```

After a successful, real SHA-verified figure mapping, each subsequent
slides/narration stage must receive **separate approval** for billed API
content requests, and retains its own immutable attempt/receipt:
`python -m selenium_pipeline.windows_original_stage_sequence --trial-dir ... --stage slides --communication-mode api --confirm-content-api-cost`.
Script QA remains deterministic and does not require a provider.

The legacy original Selenium receipts for Serway §22.1 and §22.2 remain
unmodified and **may not** be retried with this new option.

Physical read-only API metadata probe **PASS**. Unit tests include explicit
billing-permission denial before any attempt file, source/API receipt pins,
no double-submit on restart, deny fallback mode, stage-specific approval,
and the original Selenium happy/error paths. The API generation path has
not been charged or run on a real new source. No student publishing.
