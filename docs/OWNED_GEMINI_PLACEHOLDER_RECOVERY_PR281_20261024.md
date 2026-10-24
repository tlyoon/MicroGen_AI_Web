# PR281 — Recover a delayed owned Gemini reply after the actual Thomas 8.4 placeholder

24 October 2026. Dell-115 isolated stacked draft on PR280 `7ed71b13853782ea5aee25c9d06856c52ec99100`.

## Real incident, not speculation about prompt size or Gemini traffic

Read-only inspection of the *original* 23 October 2026, 544-character Gemini diagnostic failure receipt and linked immutable quarantine metadata found:
- diagnostic `SeriesBridgeError`: stable JSON capture failure
- original quarantined snapshot `capture_status=visible_model_response`
- `generation_active_at_capture=false`
- `model_response_chars=11`, original text was `Gemini said`
- no structured or academically usable response

The pre-existing `_browser_request` did NOT attempt its owned-tab grace polling unless the Stop/generating indicator was true, and the existing `poll_existing_owned_response` stopped immediately whenever generation was false but the visible text was incomplete. Consequently it could prematurely abandon an owned tab that still displayed a short loading placeholder. The evidence does not establish a Gemini backend outage.

## Corrective implementation

1. In strict response capture failure, allow a **bounded 12-second** additional *same-owned-tab* observation when the Gemini model appears stopped but its reply is incomplete, including `Gemini said`. Existing active-generation recovery retains up to 45 seconds.
2. Continue polling within the bounded grace for incomplete nongenerating text; accept only a response that passes the caller's original strict JSON acceptance callback **and** whose latest snapshot is verified no longer generating.
3. Immediately reject an unavailable, changed, non-Gemini, or unowned tab; do not use unrelated conversations, arbitrary clipboard, or a model resend.
4. Preserve the existing source/slide identity, challenge retry quota, historical failure receipts, refusal to infer academic approval from JSON structure alone, and separate student publishing gate. If still incomplete when grace ends, quarantine the untrusted reply as before.

## Validation

Dell-115 local focused plus neighboring regression suite: **41 passed, 0 failed**. New tests cover placeholder-to-complete JSON, persistent placeholder remaining unapproved, lost tab, and JSON appearing while still generating. Updated existing mock transport test to prove that an owned scoped Copy response recovered after an ordinary capture timeout returns the valid exact model response rather than incorrectly quarantining it. No new Gemini request was submitted; this patch does **not** prove Gemini has become responsive.

No changes to original PDFs, slides, script, original WAV/MP4, actual Gemini history, shared G: worktree, protected main, Moodle, YouTube or paid model configuration. Original Thomas Calculus 8.4 remains **0/71 independently agreed source mathematical mappings**. Code quality fix does not supersede the one-hour health cooldown or the approved separately scoped mathematical-review window.

## Next

After CI succeeds and no competing owner is present, a separately eligible one-shot transport health probe may be used according to the pre-existing no-resend safety contract. Only a real completed, exact JSON health receipt can enable a distinct original mathematical source challenge. If the provider remains unresponsive, continue technical work without mathematical approval or publication.
