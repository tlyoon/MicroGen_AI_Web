# PR270: Retry Gemini transport health without spending mathematics approvals

Following PR269's separately authorized Thomas Calculus 8.4 slide-1
independent-source review window, this adds a bounded text-only Gemini
transport health diagnostic. It does NOT run original mathematical review,
charge Flash-Lite/Kore TTS, publish student video, or reenable the disabled
MicroGen Autonomous Development task.

A diagnostic prompt between 1200 and 3000 characters requests ONLY an
exact small JSON object. Gemini's own original-user-turn, owned-tab and
model completion checks are required by the existing selenium bridge.
Only exact JSON creates a SHA256-bound response and metadata receipt
inside the separate private AppData review window. The separate review
window can subsequently become eligible for one original academic review
attempt, but all original PDF/book/slide/utterance and independent reasoning
validators still apply.

A failed or unknown diagnostic records no green model-health receipt.
The external append-only health_attempts.jsonl enforces at least 3600
seconds between one-shot checks. It refuses duplicate active claims and
unresolved interrupted probe histories, even after machine restart.
Model errors are recorded by type, without copying unrelated Chrome tabs
or private conversation text. Ordinary model failure does NOT reset the
historic original 3-attempt queue or consume any of the new academic
window's 3 separately authorized actual-math submissions.

The CLI defaults to read-only:
python -m selenium_pipeline.gemini_source_health_probe_cli --window-root WINDOW

The explicit one-shot browser diagnostic needs
--allow-one-browser-canary; even this runs NO mathematical review.
An authorized external hourly scheduler may invoke only that narrow
diagnostic once per due interval after confirming Dell-115, exclusive
browser/worker ownership, and no competing jobs. This PR creates NO
Windows task, ChatGPT automation or recurring process by itself.

Verified live source context: previous 544-character text-only
diagnostic submitted in Gemini on 23 October but failed to yield
complete stable JSON after 149 seconds. It must not be counted as
proof of provider overload, source mathematical agreement or
a successful original 8.4 lecture. Do not immediately repeat.

Original teaching PDFs/slides/scripts/WAV/MP4 unchanged; no user
gradebook/Moodle/YouTube publication, and no paid API calls.
