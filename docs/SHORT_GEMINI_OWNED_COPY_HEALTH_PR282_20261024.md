# PR282 — Recover exact short Gemini health JSON from the verified owned-response Copy toolbar

24 October 2026. Isolated Dell-115 draft stacked on PR281 `6d1af8543c98e0efdfce1b982400f683b6c17c0b`.

## Real technical gap

The preserved real original Thomas Calculus 8.4 diagnostic captured only the eleven-character `Gemini said` placeholder as its latest owned model-response DOM text after generation stopped. Independent code inspection found a second deterministic capture mismatch: `response_snapshot_with_scoped_copy` accepted vendor-owned response Copy text only if it exceeded **60 characters** and was longer than the transient DOM placeholder. The exact required Gemini health canary `{"probe":"microgen_source_transport_ok"}` is shorter than that floor. Consequently even a genuinely copied exact JSON canary would be discarded, causing another false-negative transport-health outcome.

## Implemented correction

- Keep every original same-owned-tab and Gemini-domain check; the fallback still uses **only** the existing vendor helper that validates its Copy button belongs to the target model response.
- For copied text larger than the DOM placeholder but shorter than the old threshold, require acceptance by the calling strict complete-JSON validator before promoting that response. Longer response fallback behavior is retained.
- Plumb the existing structured-response acceptance callback to both the first scoped Copy snapshot and the no-resend owned-tab observation in `series_gemini._browser_request`.
- The copied response must still be observed as generation-stopped by the existing caller; subsequent one-shot health receipt uses `json.loads` of exact copied bytes (PR279) and separately checks source hashes and approved scope before academic dispatch.
- No approximate, short prose, unrelated tab, user prompt, generating response or incompletely parsed model output becomes scientific approval.

## Tests and actual original state

**40 Dell-115 focused/neighboring tests passed**. New tests cover the *real incident shape*: an 11-character `Gemini said` placeholder and a correctly formatted under-60-character health response; reject plain prose/fragment JSON and wrong-tab Copy; verify the exact full browser bridge mock path uses **one** send with owned recovery and shutdown. Existing response quarantine and PR281 no-resend grace regressions pass.

No live Gemini request was sent in this PR. Prior actual original review status **0/71** independently agreed mathematical mappings is unchanged. Historical source.pdf/slides.pdf/script.txt, review attempt receipts, original WAV/MP4, billing, protected main, and student publication are untouched. GitHub CI to be checked separately.

## Next

After successful CI and a no-conflict Dell-115 owned-browser preflight, execute at most one explicitly authorized Gemini transport-health canary within the existing 1-hour history/cooldown rules. If it yields exact verified JSON, review a single already approved original-source mathematical request, preserving original second-pass scientific independence and human/listening release gates. If model transport is still unresponsive, no automatic repeated sending or fabricated completion.
