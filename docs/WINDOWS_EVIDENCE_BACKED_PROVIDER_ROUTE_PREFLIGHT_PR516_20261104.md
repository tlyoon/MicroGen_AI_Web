# PR516 — Evidence-backed Windows model-provider route preflight

The user requested progression towards codebase completion rather than repeated
PDF-specific provider retries. The original source-free Gemini browser canary
registered a model send and captured a real owned-model UI error; Gemini's API
model metadata was separately reachable using existing configured keys, but
**no API generate_content call has been authorized or performed**.

At the same time, Dell-115's dedicated ChatGPT Chrome debugging port 9223
reported `LOGIN_REQUIRED`, while Gemini's 9222 browser had an authenticated
composer. Simply choosing an authenticated Gemini composer would wrongly
classify this as a healthy generation path; silently falling back to ChatGPT
would also be wrong, because that browser was not authenticated.

## Safe source-independent mechanism

New `windows_provider_route_evidence_preflight` combines existing
independent, read-only evidence:

- Check Gemini/ChatGPT browser readiness only on the existing dedicated
  ports, with no login, new tab, navigation or prompt submission.
- Optionally GET Gemini model *metadata* using the existing key list;
  this does not prove successful paid generation.
- Read an already-written, immutable, SHA-linked, source-free browser
  canary (e.g. PR512), without repeating it.
- Independently re-check an **existing** owned-model Gemini quarantine
  with its raw-response SHA and trusted parent path, incorporating the
  PR515 canonical Windows temporary-root fix. No raw model text is
  exposed in the resulting diagnostics.
- Respect separately recorded browser and API provider capacity halt
  policies, without conflating a browser UI error with API 503/504.

A recent unverified source-free browser canary or independently verified
owned Gemini UI error suppresses any **automatic** selection of that
Gemini browser lane. A genuinely authenticated ChatGPT browser, if present,
may be listed as a route for a *new, distinct, never-sent source only*.
An API model metadata hit may be listed as a candidate with **separate
explicit paid-generation cost consent**, not as a successful generation
test, quota proof, or permission to auto-fallback.

Everything remains `new_model_or_tts_calls=false`,
`automatic_new_model_generation_authorized=false`,
`old_uncertain_lecture_retry_authorized=false`,
`student_publication_authorized=false`.

## Dell-115 read-only ground truth (4 November 2026)

Executed against original PR512 source-free browser canary and actual
SHA-verified owned UI-error quarantine. The result was:

- `gemini_browser_authenticated=true`
- `chatgpt_browser_authenticated=false` (separate ChatGPT session requires login)
- `prior_source_free_browser_canary_unverified=true`
- `owned_gemini_ui_error_sha_verified=true`
- `gemini_browser_auto_selection_suppressed_by_prior_evidence=true`
- `api_model_metadata_reachable_not_generation_proven=true`
- `suggested_new_unsent_job_route=GEMINI_API_METADATA_REACHABLE_COST_APPROVAL_REQUIRED`

This is *not* a paid API test, not verification that Gemini can generate
content, and not an automatic authorization to switch the previous
uncertain source. No new source PDF or user prompt was sent.

### Non-generating read-only operator command

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR516_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
$canary = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR512_SOURCE_FREE_BROWSER_DIFFERENTIAL_CANARY_V1'
$quarantine = Join-Path $env:LOCALAPPDATA 'Microvid\gemini_quarantine\gemini_20261104T121928Z_0fbb05564ff4.meta.json'
Set-Location $repo
& $py -m selenium_pipeline.windows_provider_route_evidence_preflight `
  --inspect-browsers --check-api-model-metadata `
  --prior-browser-canary-root $canary `
  --prior-owned-ui-quarantine-meta $quarantine
~~~

The real parent PR515 CI run `41852066286` passed **both** native
Windows jobs. PR516 adds the new source-independent preflight tests
to the same Windows regression workflow.

## Remaining release blockers

A genuinely distinct *fully generated* original lesson with independently
reviewed figures, mathematics, spoken audio and synchronized MP4 is still
missing. The 426 open GitHub PRs (145 most-recent contiguous draft tranche
as of PR515) have **not** received independent dependency approvals or
been merged. The Windows engineering technical candidate from PR511
remains verified but does not equal academic or production release.

No attempt to repair or replay failed Serway §1.1/22.2/24.4 or any
Thomas figure was made. No provider/API/TTS/FFmpeg generation, paid
model calls, historical mass merge or student publication. Native
Dell-115 Windows only, no Ubuntu/HP/Yoga or local LLM.
