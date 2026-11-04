# PR504 — Preserve fallback Gemini API keys across verified 503/504 without replaying old jobs

This documents verified behavior in the native Windows MicroGen_AI_Web codebase,
plus the missing single-send fallback selection added after PR503.

## Audit: existing .env and shared API key code

The standard credentials path is
`%LOCALAPPDATA%\Microvid\.env`, loaded by
`selenium_pipeline.runner.load_microvid_env()`. An explicitly selected
`MICROVID_CONFIG_DIR` may take precedence; no secret gets copied into Git.

The following names are recognized by `gemini_keys.get_gemini_api_keys()`:

- `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3` and
  additional numbered entries, in numeric order
- `GEMINI_API_KEYS` (comma-delimited), then
- legacy `GEMINI_API_KEY` last

Duplicate key VALUES are removed. A live, **non-generative** check on Dell-115
confirmed the .env has names KEY_1, KEY_2 and the legacy key and yields
**two distinct key values**. No values, tokens or secret fingerprints were
printed or saved.

Shared `gemini_lane.is_transient_gemini_error()` already classifies
HTTP 503 and 504 as transient, and ordinary calls using
`gemini_keys.call_with_client_failover()` already retry/rotate across
numbered keys when their retry budget is sufficient. Figure mapping, slides,
narration and some TTS/API paths call that shared helper.

## Why the independent original-source Windows campaign did NOT rotate

PR500 deliberately configured `MICROGEN_SINGLE_PROVIDER_SEND=1` inside
the immutable original-source stage worker. Prior to PR504, this forced the
pool to key #1 only. PR502's generic API canary also explicitly called only
one configured key, because its purpose was to distinguish browser vs API
behavior using one authorized source-free request, not to launch unbounded
metered generation.

Consequently, normal library fallback existed but the newer source-bound
single-send campaign could NOT use the second configured key. Retrying the
same ambiguous request with key #2 would violate the existing immutable
no-resend contract, especially for a 504 gateway timeout.

## New safe selection of a different key for a DIFFERENT source attempt

PR504 adds:
1. A source-independent, immutable, checksum-verified positive API 503/504
   (or verified 429) capacity observation may identify key #1 as a poor
   choice for a **distinct future** job. This particular diagnostic's
   audited implementation sent through key #1 only.
2. `windows_gemini_provider_halt.inspect_halt()` continues to pause
   NEW Gemini generation through both browser and API for 30 minutes
   after the structured failure; it also reports the preferred **ordinal**
   (2) for a different source job during the following six-hour window.
   It never returns API key text.
3. At a newly authorized figure, slide or narration stage (after the halt
   expires and only if the original source has NO prior ambiguous stage
   attempt), the Windows controller sets
   `MICROGEN_GEMINI_SINGLE_SEND_KEY_ORDINAL=2`, while keeping
   `MICROGEN_SINGLE_PROVIDER_SEND=1`,
   `MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS=1`, and bounded inner attempts
   at one. The same immutable source SHA/send-intent and prior-output gates
   remain in force.
4. The shared `gemini_keys.call_with_key_failover()` now interprets
   that ordinal ONLY in single-send mode. It picks the second configured
   distinct key for **the one** authorized model operation. Any missing,
   invalid or out-of-range preference refuses dispatch before network
   traffic. Within the already claimed source, **there is no retry and no
   key rotation**. A 504 does not become safe to replay merely because
   the gateway timed out.

This is conservative and currently prefers key #2 based on the verified
first-key canary error. Additional key-specific terminal evidence would be
needed before automatically choosing key #3 after key #2 failed; MicroGen
does not fabricate a claimed second-key failure.

## Test and production evidence

The 4 November 2026 original generic Gemini browser canary submitted but
had no verified response. The independently authorized API canary using
gemini-3.8-flash returned a genuine structured HTTP 503 ServerError.
The API result was imported to provider health without additional calls.
Neither canary was repeated.

On Dell-115, the worker loaded the actual default .env and checked that
the distinct configured key count was 2; a mock model operation selected
the existing key #2 while sending **zero network requests**. The tests
cover library 503/504 rotation, preferred key #2 under one-submit mode,
invalid/no-fallback denial, global provider cooldown, expiry, and exact
new-source environment propagation. The original Serway work was not resent.

Key rotation is *not* a cure for an upstream shared Gemini service outage.
The operator must still respect release, paid content, scientific QA, TTS,
ownership and publication gates. PR504 does not approve another complete
original-source lecture, merge historical drafts, or deploy a release.

No changes to the G: main worktree, publisher originals, credentials,
Moodle, YouTube, local LLM, Yoga/HP or Ubuntu.
