# PR502 — Gemini browser/API differential diagnostic and halt policy

Native Windows only, Dell-115. General MicroGen content-generation reliability,
not another per-PDF mathematical, figure, or narration repair.

## What the new diagnostic distinguishes

A registered browser send with no usable reply may reflect a Gemini service
problem, a lost response, a browser-side issue, or large-prompt-specific
behavior. It is NOT sufficient evidence for a Gemini server outage.
A successful API model metadata lookup confirms access to the model metadata,
not that generation works. The actual browser model version may differ
from the exact API model; comparative results are indicative, not proof.

The new windows_gemini_differential_probe module optionally compares one
fixed generic JSON response through each independent route (same harmless
prompt, zero textbook files). The browser route uses the existing owned Gemini
browser tab and attributed response capture; the API route requires explicit
per-call --confirm-api-diagnostic-cost because generation MAY BE BILLED.
The project does not automatically switch between transports.

Each transport uses a separate durable pre-send claim. A crashed process,
blank response, server error, or unresolved request cannot trigger resubmission.
Only a validated response status, nonsecret error type/status, prompt SHA and
length are recorded; raw original PDFs, keys and provider responses are not.

### Read-only operator command (no content generation)

~~~powershell
python -m selenium_pipeline.windows_gemini_differential_probe --inspect-browser --probe-api-model-metadata-once
~~~

Previous actual source attempts may be included using repeated --prior-trial
paths, for example the existing independent Serway §22.2 and §24.4 campaigns.
Neither past data inspection nor model metadata inspection resends a prompt.

### Optional one-time generic browser canary

~~~powershell
$probe = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\NEW_GENERIC_GEMINI_PROBE'
python -m selenium_pipeline.windows_gemini_differential_probe --canary-root $probe --browser-canary-once --inspect-browser
~~~

### Optional API canary only with separate paid-content approval

~~~powershell
python -m selenium_pipeline.windows_gemini_differential_probe --canary-root $probe --api-canary-once --confirm-api-diagnostic-cost
~~~

The API command above is an opt-in example, NOT a command to automatically
run. Re-run the read-only diagnostic with --canary-root to compare the
already persisted browser and API receipts without another model submission.

The diagnostic labels compare small-canary behavior:
- API works but browser response fails: browser capture/automation suspected.
- Both fail: service, shared network or separate transport problems suspected.
- Browser works: confirms short generic response only, not long lecture slides.
- Metadata alone works: diagnosis remains inconclusive.
No case confers academic approval or proves a server-wide outage.

## Persistent cross-task halt before new generation

New windows_gemini_provider_halt consumes existing immutable original-stage
receipts and trusted owned-browser positive-send markers. It records exact
source SHA, stage, backend, accepted-result SHA and terminal outcome as
exclusive immutable events under:

    %LOCALAPPDATA%\MicroGen_AI_Web_Gemini_Transport_Health\events\

**Policy:** two distinct verified browser sends without an accepted result
within 60 minutes (since last successful stage) trigger a 30-minute halt on
NEW browser generation tasks. API is a separate lane. An unverified timeout
or missing response is not classified as confirmed server 429/503.
The producer may resume new tasks when the halt expires, but old ambiguous
tasks NEVER become eligible for automatic retry. A fresh accepted stage
can close the halt, without resetting the old task receipt.

This gate is active before any new figures/slides/narration provider send
in the native original-source trial and sequenced stage controller.
A halted job returns GEMINI_PROVIDER_COOLDOWN_NO_SUBMISSION without a new
attempt claim or any model call. Terminal original-stage receipts are
recorded only after the SHA-bound stage result is safely persisted. Each
health event is exclusive, tamper-checked, source-bound and has no PDF/text.

An operator may explicitly register existing terminal receipts, preserving
their original historical result-file modification time (never pretending an
old incident is a new incident), with:

~~~powershell
python -m selenium_pipeline.windows_gemini_differential_probe --register-terminal-trial "EXACT_IMMUTABLE_TRIAL_FOLDER"
~~~

The code reuses the existing provider readiness, response capture and
no-resend contracts; there is no paid TTS, local model, Ubuntu dependency,
manual Chrome destruction, original source overwrite or student publication.

Tests cover the one-shot generic browser/API canaries, API billing gate,
ambiguous and malformed reply handling, shared halt, cooldown, recovery,
trusted send markers, replay-resistant receipts and correct suppression of
new source stages before their attempt ledgers. Owner-accepted historical
Thomas source-specific media remains valid under its exact SHA scope;
no Figure 8.3 re-review is caused by this improvement.

This is a diagnostic and safe production workflow gate, NOT a second
completed original-source lecture or an approved release of the full stack.
