# Standing paid Gemini 3.8 Flash authorization — MicroGen_AI_Web

**Effective:** 27 November 2026. **Source:** Owner's current explicit
clarification after requesting examination of the project's historical authorization record.

## Binding decision and precedence

The owner confirms that **paid gemini-3.8-flash is automatically
permitted for TTS/audio-quality checking in MicroGen_AI_Web**. No repeated
per-subchapter or per-run --confirm-paid-tts-qa flag is required for this
exact model and purpose. This supersedes only the older 21 November 2026
per-run approval requirement **for this precise QA model/purpose**.

TTS generation through the approved gemini-3.8-flash-lite-tts model
continues under its separate pre-existing TTS authorization. An explicit
per-run approval remains required for other paid TTS-QA models. No standing
authorization is granted to use paid Gemini API for slide generation,
narration-text generation, figure mapping, scientific review, or
browser-failure fallback; all those tasks remain **Selenium-only**.

## Executable contract

- The central egress policy paid_api_policy.require_paid_gemini_api() grants
  standing approval only when purpose == "tts_qa" AND the actual billed
  model is exactly gemini-3.8-flash. The QA model must be passed at both
  preflight and final metered API egress.
- The usual enabled source-code recovery-policy registry is still required.
  No available credits, generic environmental flag, or key rotation may
  broaden QA purpose or bypass source and release checks.
- Preserve chapter/subchapter/model/purpose cost accounting, bounded
  retry/reconciliation, and strict no-replay handling of uncertain billed
  API outcomes.
- Mandatory academic and media QA thresholds remain unchanged. Authorization
  to pay for checking audio does not mean the audio passed.
- Existing --confirm-paid-tts-qa remains available for separately
  approved alternatives; it is not necessary for default
  gemini-3.8-flash TTS/acoustic QA.

## Operational handoff

The HP Chapter 1-7 campaign should use the latest verified GitHub main and
may advance from tts through tts_qa using
--tts-qa-model gemini-3.8-flash without requesting another permission.
It must still repair its independent source-figure blockers, accept a slide
deck and narration before spending on QA, and release video/YouTube/DOCX links
only after validated outputs exist. This contract does not retrospectively
certify incomplete Chapter 1-7 subchapters.
