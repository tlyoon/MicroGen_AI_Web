# PR500 - Enforce no-double-send inside an immutable original source stage

## General defect and correction, 4 Nov 2026

The Windows source-stage controller from PR495/499 writes an immutable
stage `started.json` BEFORE invoking the maintained downstream runner and
refuses a second full stage invocation. However the *inside* of the
maintained slide/narration/figure provider adapters defaulted to **3 Selenium
and 2 API sends**. A single controller invocation could therefore silently
attempt three requests after a response stalled, even though the external
receipt promised only one. This is a product-level duplicate-send bug, NOT
a reason to make a particular PDF perfect.

Dell-115 physical Serway §24.4 live stage illustrates the problem: the
old PR499-generation slide runner verified three Gemini submissions in ONE
bounded invocation; its first two replies contained only invalid/missing
Beamer source, failing \documentclass / frames gates. That old ongoing stage
is versioned and cannot be resent; PR500 changes apply to NEW source stages,
not retroactively to already-running subprocesses.

The isolated Windows `windows_fresh_source_trial` and
`windows_original_stage_sequence` now pass these *stage-local* environment
flags to their owned child subprocess only:

```
MICROGEN_SELENIUM_ATTEMPTS=1
MICROGEN_API_ATTEMPTS=1
SLIDES_MAX_ATTEMPTS=1
MICROGEN_SINGLE_PROVIDER_SEND=1
MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS=1
```

The existing vendored figure/slide/narration clients already honor
`MICROGEN_SELENIUM_ATTEMPTS` and `MICROGEN_API_ATTEMPTS`.
The shared `gemini_keys.call_with_key_failover` now honors the strictly
opt-in `MICROGEN_SINGLE_PROVIDER_SEND=1`: one API key, no response retry or
credentials rotation, even when an inner client asked for `max_retries=1`.
Normal unrelated existing TTS authorization/fallback behavior is UNCHANGED.

Native Dell-115 tests include actual mocked child environment inspection,
outer no-resend receipts, stage fixture stop, and adversarial transient
Gemini errors with two configured fake keys. The explicit one-send test
proves one attempted key and no sleep/second send. The clean PR493 Windows
virtualenv is required for SDK-version-dependent tests. No paid model/TTS
request was run to test this change.

No changes to the user's G: dirty source checkout, original textbook or
historical previous accepted source/math/PCM/video. Student publication
remains unauthorized. The old original Serway §24.4 slides attempt is
quarantined on failure; there is **NO automatic resend**, with a different
Gemini provider or otherwise.

Next step to reach functional completion: a NEW eligible and independently
SHA-pinned source content generation attempt on a healthy provider followed
by full authored deck, script, exact PCM and genuine multipart MP4 proof,
then second-source reuse and safe stack integration. CI passing tests
alone does NOT satisfy genuine full original-source generation.
