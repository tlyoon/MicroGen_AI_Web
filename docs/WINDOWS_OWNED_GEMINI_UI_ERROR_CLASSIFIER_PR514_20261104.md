# PR514 — Recognize a real Gemini owned-model UI error, not an API outage

This general hardening priority follows the independently staged Serway
§1.1 timeout and the separate PR512 source-free Gemini browser canary.
It is **not** another PDF repair, retry of an uncertain source, or paid API
generation attempt.

## New SHA-grounded evidence (Dell-115, 4 November 2026)

PR512's owned browser canary successfully registered one short JSON
instruction to Gemini through Selenium. The returned JSON canary
result recorded `NO_VERIFIED_RESPONSE` / `SeriesBridgeError`.
The existing quarantine system independently saved the latest *owned
model-response* snapshot and immutable SHA of the text.

The current capture's raw SHA matches its stored quarantine metadata.
The stored `capture_status=visible_model_response`,
`model_response_chars=82` and `generation_active_at_capture=false`.
For this generic, source-free canary, the model-response content was:

> Gemini said
>
> I seem to be encountering an error. Can I try something else for you?

This changes the differential diagnosis: there **was visible model
response text**, so the problem was NOT merely an absent/unreadable
DOM model element. The browser UI surfaced an explicit error
message instead of the requested complete JSON.

**It is NOT proof** of a global Gemini API outage, depleted quota,
HTTP 503/504, or a known cause (account, UI/backend, rate, session or
network). The API metadata GET was successful, but Gemini API
`generate_content` has **not** been tested. A generic source
timeout and this short browser canary cannot authorize an old request
resend or automatically switch keys to retry the same unknown send.

## Codebase-level correction

`selenium_pipeline.gemini_provider_ui_terminal_error` classifies only
the *exact* independently observed owned-model text, optionally
preceded by the standard "Gemini said" header. It rejects partial
text, embedded user prompt strings, foreign/unowned/empty captures,
and in-progress responses. The classification is:
`GEMINI_OWNED_MODEL_VISIBLE_UI_ERROR_NOT_API_OUTAGE_PROOF`.

Integration:

- `gemini_response_recovery.quarantine_snapshot` now preserves a
  safe `known_gemini_ui_error_text_observed` boolean, plus explicit
  false server-outage / retry authorization fields in any new
  immutable metadata. Old evidence is **never rewritten**.
- `series_gemini._browser_request` now quarantines a trusted owned
  error snapshot with `reason=owned_gemini_ui_error_text` and raises
  a safe, specifically classified `SeriesBridgeError`, rather than
  treating it as merely a generic incomplete JSON or silently retrying.
- `gemini_bridge_failure_triage` reports
  `OWNED_GEMINI_UI_TERMINAL_ERROR_TEXT_NOT_API_PROOF`.
- `windows_gemini_differential_probe.run_canary` records a safe
  `browser_bridge_stage` error category for any NEW future
  independent canary. It never exposes the raw error/URL/credentials.
- The read-only `--quarantine-meta` inspector checks legacy bytes
  and SHA from an existing on-disk model-response quarantine without
  a new provider request. The actual PR512 82-character quarantine
  independently returned the new classification, zero model/TTS
  calls and publication blocked.

### Read-only operator command

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR514_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
$folder = Join-Path $env:LOCALAPPDATA 'Microvid\gemini_quarantine'
Set-Location $repo
$latestMeta = Get-ChildItem $folder -File -Filter '*.meta.json' |
   Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
& $py -m selenium_pipeline.gemini_provider_ui_terminal_error `
    --quarantine-meta $latestMeta.FullName
~~~

This merely rechecks the existing quarantine. It does not imply
that every future latest file belongs to this particular canary;
the human/operator must verify the trial association by immutable
context. The classifier is deliberately conservative.

## Regression and release impact

Offline native Windows tests cover exact text matches, model
ownership/capture status, generating vs finished, tampered quarantine
hash, wrong directory, private raw-data suppression, correct
SeriesBridgeError classification and no implied retry/HTTP status.
The established TTS provider model, existing Gemini API-key fallback
for distinctly new requests and native Windows-only CI stay unchanged.

Full release remains **blocked** by the genuine second original
end-to-end lesson, independent human scientific/voice/video
acceptance, formal historic PR integration and publication approval.
PR514 creates no new paid Gemini API/TTS requests, model text,
student content, Git merges, non-Windows dependencies or per-PDF fixes.
