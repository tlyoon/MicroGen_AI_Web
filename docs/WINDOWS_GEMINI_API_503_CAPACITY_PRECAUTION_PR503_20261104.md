# PR503 — Verified Gemini API HTTP 503 and bounded new-task halt

This change advances MicroGen's **general Gemini task handling** on the authorized
native Windows Dell-115 machine. It does not retry, regenerate, correct or
otherwise inspect any particular scientific textbook PDF.

## Real evidence collected on 4 November 2026 (Malaysia, UTC+08)

- The existing PR502 authenticated Gemini browser generic JSON canary
  submitted once at ~16:18 and returned **no verified model response**.
- Following explicit operator permission, one separate generic API
  generate_content request using gemini-3.8-flash was sent at ~17:39.
  The actual structured response was HTTP **503**, Python exception
  type ServerError. The immutable API result has zero response characters.
- Prior Gemini API model metadata lookup succeeded. A metadata GET is
  not a content-generation test.
- The diagnostic request contained only a bounded fixed JSON canary.
  No original PDF, slides, instructor text, audio, TTS or student data
  was sent. The single API generation operation may be billable.
- Both browser and API claims and results are immutable and must **never**
  be resent merely because capacity later recovers.
- This supports a Gemini provider capacity/availability issue **for that
  exact API request**, without claiming that every Gemini server is down or
  excluding a separate browser automation/capture defect.

## Precaution based on positive first-party API error evidence

MicroGen can now import a **previously completed** 429 or 503 generic
API canary using read-only receipts, rather than guessing server status
from an idle screen or a generic timeout.

~~~powershell
$probe = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR502_GEMINI_GENERIC_BROWSER_CANARY_ONE_SHOT_V1'
python -m selenium_pipeline.windows_gemini_differential_probe --canary-root $probe --register-api-capacity-from-canary
~~~

This command creates no API or browser generation call. A structured error
must have a matching SHA-verified and source-free prior one-shot claim;
the whole event is copied into an immutable, validated external
LOCALAPPDATA health ledger. If an event already exists, it is reused.
HTTP 401/403, browser timeout, unproven model output or a mistyped
response cannot be counted as actual provider 429/503 capacity evidence.
The original canary result and its claim are rechecked on each provider
health inspection. Tampering fails closed.

One verified recent 429/503 from the API canary triggers a **30-minute
precautionary pause** on NEW Gemini content-generation work through
either the Selenium browser or the API lane, since they share provider
infrastructure. The two-lane original-stage retry exhaustion and
no-resend safeguards remain separate. Once the time interval expires,
the gate may accept **a distinct new** source/job if all other contracts
pass; it cannot release an earlier ambiguous source attempt.

On Dell-115 the exact original 503 was physically registered without any
new model calls. The source-independent browser and API admission gates
both returned HALT_NEW_GEMINI_TASKS_API_CAPACITY_PRECAUTION, expiring
at **18:09:04 Malaysia time, 4 November 2026**. This is an operational
hold, not proof that all Gemini services are unavailable. No automatic
generation resumes at expiration, and no recurring check was scheduled.

The logic lives in windows_gemini_provider_halt.py and is called before
new original source-stage attempts through the existing PR502 controllers.
The diagnostic CLI in windows_gemini_differential_probe.py exposes a
separate explicit import switch. A future 503 only activates this
precaution if its own independently authorized and actual source-free
API diagnostic exists; MicroGen will not spend money just to look for one.

## Acceptance and remaining scope

Dell-115 tests include real-file synthetic versions of a one-shot 503
claim/result, both-provider admission stop, 30-minute expiry, idempotent
registration, deliberate receipt tampering, historical evidence, and
non-capacity errors. PR502's GitHub Windows CI was green before stacking
this work. This does **not** complete a second genuine source-bound
lecture or approve the full historical draft PR stack for public release.

Contracts unchanged: Dell-115 only, pure Windows, no Yoga/HP/Ubuntu,
no local LLM, no Gemini content fallback, no automatic repeated requests,
no unapproved TTS, no edits to shared G originals or dirty main worktree,
and no student publication.
