# PR512 — Provider-wide Gemini browser/API differential with immutable phase triage

On Dell-115, 4 November 2026, the previous Serway 1.1 single-send figures
attempt timed out **after local PDF figure extraction** but produced no
registered Selenium owned-send proof. That is not evidence that Gemini
generation servers were down, and MUST NOT cause another individual-PDF
repair/retry.

## Actual independent provider checks

The existing source-free preflight was run on the current Dell browser and
model configuration. It returned:

- Windows model route `gemini-3.8-flash` metadata **reachable** via the
  API, with **two configured API keys** (count only, never secret values).
- The existing Selenium Chrome UI was **authenticated, composer ready**.
- These two metadata/readiness checks performed **zero paid content calls**.
- Existing Serway §1.1 raw log: PDF extraction completed, an active Chrome
  remote-debugging session reported, but no owned browser Send proof in the
  source-stage raw log. The stage's immutable terminal receipt remained
  `FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY`.

A *new and independent*, **source-free** browser transport canary was
run exactly once in
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261104_PR512_SOURCE_FREE_BROWSER_DIFFERENTIAL_CANARY_V1`.

It selected an owned Gemini Flash tab, logged a
`Gemini submission registered via new-user-turn+composer-cleared`
event, but did **not** return a verified JSON response within its
bounded window. Its immutable browser result reports
`outcome=NO_VERIFIED_RESPONSE`,
`error_type=SeriesBridgeError`, `response_character_count=0`,
`request_may_have_been_submitted=true`. No source PDF was sent. There
was **no API content-generation call** and no TTS/video call.

This is significant: one source-specific task failed before a
registered send, while one independent, short browser canary
successfully registered its send but failed to return verifiable text.
The shared browser submit/receive/copy path is a stronger suspect than
one publisher PDF. A Gemini **service outage is not proven**, because
there is no independent successful or failed API *generation* canary;
metadata GET is not generation proof. Key credit depletion is not proven
either.

## New general mechanism, not a one-document fix

`selenium_pipeline.windows_gemini_stage_transport_triage` reads
already-existing immutable Windows original-stage receipts plus bounded,
non-symlinked log files. It reports only flags and classifications:

- Did local figure extraction actually finish?
- Was the Chrome 9222/Selenium browser session observed?
- Was the attributed owned browser Send completion **registered** by
  the trusted vendor marker? Generic source prompt text is NOT proof.
- Did a separate immutable stage result report accepted technical
  completion or only a terminal unknown/timeout?
- Is the stage still only a pre-send intent without a final result?

Inputs must be SHA-consistent with the original trial and the provider
send intent. It is read-only; no model, no retry, no credentials, no raw
log or prompt in the output. No timeout by itself proves Gemini server
outage or Selenium capture failure. The existing
`windows_gemini_differential_probe` now includes a
`prior_stage_transport_phase_triage` array when `--prior-trial`
is supplied.

### Operator usage: independent read-only inspection

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR512_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
$original = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR510_SOURCE_ONLY_DIFFERENT_1_1_DRY_RUN_V1'
$canary = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR512_SOURCE_FREE_BROWSER_DIFFERENTIAL_CANARY_V1'
Set-Location $repo

# Safe: inspect only immutable old receipts; never resubmit.
& $py -m selenium_pipeline.windows_gemini_stage_transport_triage `
  --trial-dir $original --stage figures

# Safe: read prior canary without --browser-canary-once, and model metadata GET.
& $py -m selenium_pipeline.windows_gemini_differential_probe `
  --inspect-browser --probe-api-model-metadata-once `
  --prior-trial $original --canary-root $canary
~~~

A new API **generate_content** canary is intentionally *not* dispatched
without separate `--api-canary-once --confirm-api-diagnostic-cost` and
a fresh immutable external canary folder. Existing prior source sections
22.2, 24.4 and 1.1 and the new browser canary MUST NOT be repeated.

An API-backed, truly new and previously unattempted lecture source
requires separate paid authorization and the existing one-stage
immutable source generation ledger; the fallback key mechanism applies
to distinctly new API operations only, not to uncertain sends.

## Release progress

PR511 source-review package and Windows engineering technical
readiness are independently verified; the academic/production release
is still **BLOCKED** by the missing second original full multimedia
lecture, human scientific/figure/audio review, historical PR-stack
consolidation and formal publishing approval.

PR512 adds no new academic PDF fixes, no Ubuntu/HP/Yoga/local model,
no extra browser canary, no billable API/TTS call, no merge and
no student publication.
