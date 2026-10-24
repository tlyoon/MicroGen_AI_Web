# PR279 — Strict Gemini transport-health response and attempt-journal evidence

Date: 24 October 2026. Stacked draft after PR278; local work on Dell-115 only.

## Corrected gap

The older text-only health probe decoded the complete response with a permissive storyboard parser, then saved the **unmodified** raw content. As a result, a fenced Markdown JSON block or a prose-wrapped JSON object could be labeled `GEMINI_TRANSPORT_HEALTH_VERIFIED`, even though `inspect_window` reads the persisted bytes with strict `json.loads` and would refuse downstream use. That mismatch can lead to false-positive health reports and redundant attempts.

Now the health probe accepts ONLY a direct parsable JSON object equal to `{"probe":"microgen_source_transport_ok"}` before writing a success receipt. Extra keys, surrounding Markdown, wrong types, or garbage are treated as unverified. No mathematical approval is inferred.

The durable `health_attempts.jsonl` log is now validated as a bounded, chronologically ordered sequence of uniquely identified BEGIN + matching terminal SUCCESS/FAILED_UNKNOWN events. Forged orphan terminal rows, duplicate IDs, overlapping probes, truncated log lines, out-of-order or future timestamps fail closed. Genuine unresolved BEGIN continues to quarantine follow-up sends without stealing any owner lock.

## Actual preserved original-state evidence

Read-only validation of the existing Dell-115 Thomas Calculus 8.4 approved window's four preexisting health journal entries succeeds: two recorded starts, each with terminal `HEALTH_PROBE_FAILED_UNKNOWN`; latest entry FAILED_UNKNOWN. The original queue still has 71 pending independently agreed mathematical mappings as of PR278. No new Gemini probe, academic submission, voice generation or publication was executed for this PR.

## Validation

`python -m pytest -q tests/test_gemini_health_probe_journal_integrity.py tests/test_one_shot_gemini_source_health_probe.py tests/test_scoped_original_math_review_window.py tests/test_original_math_review_recovery.py tests/test_gemini_ambiguous_response_resolution.py` — 28 passed, five existing third-party SWIG deprecation warnings. Added six adversarial tests including false fenced-JSON success and forged journal records.

Retain the separate scope and no-retry-on-unknown policy. No historical source, WAV, MP4 or original queue edits; no disabled scheduled task reenabled. A future live request must obey the prior source-sized health and verified same-owner transport conditions; this change does not itself request a new probe.
