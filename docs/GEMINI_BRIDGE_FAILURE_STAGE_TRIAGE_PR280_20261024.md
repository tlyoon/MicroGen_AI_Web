# PR280 — Diagnose actual Gemini bridge failure stage without assuming server overload

Date: 24 October 2026. Dell-115 only, stacked on PR279.

## Source of the observed ambiguity

The actual Thomas Calculus 8.4 approved window has two historical text-only health probe beginnings and two failed/unknown terminal events; the most recent failure recorded only `SeriesBridgeError`. The generic class cannot prove whether the Selenium browser setup, composer, Send control, response capture or Gemini service was responsible. The existing healthy-state gate correctly denies new mathematical-review dispatch.

## Implementation

Add `gemini_bridge_failure_triage.classify_owned_gemini_failure`, which maps only known, explicitly defined bridge exception messages onto privacy-safe stage codes. Integrate in the existing opt-in one-shot probe's **failure-only** path. For example: `OWNED_COMPOSER_INPUT_FAILED`, `OWNED_SEND_NOT_CONFIRMED`, `OWNED_RESPONSE_UNVERIFIED_QUARANTINED`, `OWNED_CAPTURE_EVIDENCE_WRITE_FAILED`, `LOCAL_BROWSER_CLIENT_UNAVAILABLE`, or `BRIDGE_STAGE_UNDETERMINED`. Timeouts and generic connection problems are classified as **unattributed**, NEVER confirmed Gemini provider overload or HTTP 429/503.

The new JSONL evidence stores only stage codes and exception class, not prompts, raw replies, account details, tab IDs, filesystem paths, or arbitrary exception text. This does not change the provider request count, 3600-second health cooldown, original math quota, unknown-outcome quarantine, or publication contract.

No historical attempt is retroactively reclassified; the real previous `SeriesBridgeError` remains stage UNKNOWN until independently grounded evidence appears. No Gemini request or other paid service has been invoked in this PR.

## Validation

Isolated Dell-115 focused regression:
`python -m pytest -q tests/test_gemini_bridge_failure_triage.py tests/test_gemini_health_probe_journal_integrity.py tests/test_one_shot_gemini_source_health_probe.py tests/test_gemini_ambiguous_response_resolution.py tests/test_original_math_review_recovery.py tests/test_scoped_original_math_review_window.py`

**31 passed**, zero failures; existing SWIG deprecation warnings only. New adversarial tests assert no false 429/503 conclusion, no accidental retry/academic approval, and no sensitive error-message leak into health journal.

Original textbook source, slides, scripts, WAV/MP4 files, Gemini previous receipts, locked worker trees and protected main all unchanged. No new Kore, full original-source AI mathematical agreement (still 0/71), or release approval is claimed.

## Next step

Use existing read-only checkpoints to distinguish transport/owned-tab readiness from academic scope, then perform a genuine independent source-math challenge only when there is a fresh real verified complete Gemini transport response, no active conflicting worker and allowed retry budget. Until then, continue independent nonproduction multimedia development rather than re-sending unknown requests.
