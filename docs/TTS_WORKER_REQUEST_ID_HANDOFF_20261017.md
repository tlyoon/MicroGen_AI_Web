# TTS worker: actual provider request-ID handoff

Date: 17 October 2026. Draft change stacked on PR #123. No paid API calls or publication.

## Original gap

The main TTS runner uses isolated Gemini and Google Cloud subprocesses to impose hard request timeouts and retry limits. The subprocess returned only `result.wav` or an error string, so a provider-issued HTTP request identifier exposed inside an SDK success response or error was lost before the main process wrote its source-bound attempt journal. PR #123's independent reconciliation could not match these calls by request ID.

## Implementation

- Worker accepts optional `--evidence-output`, restricted to a not-yet-existing file beside its temporary WAV. It writes a minimal **JSON sidecar**, with `schema_version`, `outcome` (`success` or `exception`), a validated provider-issued HTTP request ID or `null`, and sanitized exception-class name. It does not include the API key, auth token, full headers, prompts, transcript, provider response or exception message.
- Gemini SDK success response: inspect only its `request_id` field and recognized HTTP `x-request-id`, `x-goog-request-id` or `request-id` headers when exposed. **A Gemini `response_id` is not automatically an HTTP request ID** and is deliberately excluded. Cloud worker success may not expose a provider ID, so it is recorded as `null` rather than invented.
- On an SDK exception, inspect its request ID or recognized HTTP request-id headers, including a bounded exception cause/context chain. Unknown or unsafe values are discarded. If the worker times out or crashes before writing a sidecar, no ID is claimed.
- The parent verifies the sidecar outcome/status and safe request-ID encoding. A successful direct slide request propagates its optional ID into the hash-chained `AttemptEvidence` journal. A failed worker attaches the optional ID to the raised exception so the retry journal captures it without exposing the error payload. **Chunked narration is multiple separate TTS requests**, not one request, so its merged WAV is never falsely assigned a single request ID.
- Legacy invocations without `--evidence-output` continue to work and older journal records without provider IDs remain valid but cannot support exact external request-level matching.

## Security, reliability and provenance limits

The short sidecar is inside an exclusive temporary worker folder and is discarded with its folder. It is not a signed provider receipt, cannot establish that a Google charge occurred, and is not proof that an SDK response ID identifies a billing event. The separately exported provider logs still need independent authentication; Cloud Billing SKU/window exports are aggregates only. No API call is made to obtain missing IDs. The PR adds no standing authorizations or changes the owner's Lite×3 → Flash×3 → conditional Cloud fallback hierarchy, source preservation or the audio/figure/video acceptance gates.

Validation covers strict sidecar parsing, mismatched status, invalid/secret-like IDs, success/failure worker paths and synthetic parent subprocess request metadata. All provider calls in tests are intercepted or mocked. HP, Dell-115 and Yoga6 test in isolated temporary clones; Zenbook excluded. Never merge or publish because mocks pass. Every MP4 part must remain strictly under 600 seconds with genuine spoken-element synchronized highlighting, independent academic/voice/multi-panel figure review and explicit publication signoff.