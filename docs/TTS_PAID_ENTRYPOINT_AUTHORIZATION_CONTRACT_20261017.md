> **SUPERSEDED FOR NORMATIVE USE — 18 October 2026:** Historical cost and Cloud fallback prohibitions were superseded by [the restored owner-approved TTS policy](TTS_RESTORED_OWNER_APPROVED_FALLBACK_POLICY_20261017.md). Routine Gemini Lite/Flash TTS is permitted; Cloud Chirp is conditionally available only with independently observed complete Gemini retry chains and billing protections. See [the effective contract](EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md). Historical assertions below are not the current rules.

# MicroGen_AI_Web — mandatory paid TTS authorization across entry points
**17 October 2026. REVIEW ONLY — no paid API call was made during this change.**

## The corrected deviation

In the prior draft implementation, `selenium_pipeline.element_narration_gemini` required `--confirm-gemini-api-cost` **only for** `reviewed_element_tts_request_unapproved` inputs, while `author_specified_unapproved_element_narration` inputs could reach metered Gemini synthesis with `--confirm-live` alone. Similarly, the main slide TTS CLI, TTS repair CLI, standard multi-stage runner and isolated TTS worker did not uniformly require an explicit cost acknowledgement. This violated the project's rule that prior login, configuration, credentials, or a general instruction to proceed cannot by themselves authorize paid synthesis.

## Implemented rule

Every supported command-line path capable of synthesizing fresh paid TTS now requires the provider-specific opt-in **before loading credentials or starting a synthesis**:

- Gemini Flash-Lite TTS (Kore by default): `--confirm-gemini-api-cost`.
- Explicitly selected Google Cloud Chirp 3 TTS: `--confirm-google-cloud-tts-cost`. Chirp is **not** an automatic fallback. This flag is a separate provider-specific opt-in and cannot be substituted with the Gemini flag.
- Reviewed per-element Gemini TTS requests additionally need `--confirm-live` and `--confirm-reviewed-tts-request`; authored per-element Gemini requests additionally need `--confirm-live`.
- The isolated single-shot experiment in PR #112 retains its stricter independent requirement for **all three** `--confirm-live`, `--confirm-gemini-api-cost` and `--confirm-synthetic-trial`.

Entry points covered: `selenium_pipeline.runner`, `selenium_pipeline.tts`, `selenium_pipeline.tts_worker`, `selenium_pipeline.tts_qa_repair`, and `selenium_pipeline.element_narration_gemini`. The full runner propagates provider-specific authorization only to the intended child command. Internal workers launched by the authorized TTS engine also receive the provider's explicit flag, and a whole-batch fallback cannot bypass the subprocess cost check.

Dry-run, doctor and read-only reviewed-element video checks remain available without billing opt-in. Existing TTS code can still support an **explicitly authorized** manually selected Chirp provider, but default Gemini failure never silently falls back to Cloud Chirp. Model and output acceptance rules otherwise remain unchanged.

These are cost *authorization* gates, not pricing guarantees: they do not verify the account's free/paid tier. A user-initiated execution of the explicit paid flags represents affirmative authorization for the particular command. A generic chat instruction like “Proceed” is not automatically translated into CLI flags.

## Preserved production contract

- Per-video-part duration must be **strictly less than 600 seconds**, with automatic multipart segmentation when needed.
- Highlight the **correct slide element** (equation, prose or full correct multipanel figure) in temporal sync with narration.
- Preserve source PDF, existing slides/PDFs, narration scripts and WAV/MP4 outputs until verified replacement and accepted QA; outputs belong alongside each `source.pdf`.
- No Whisper/faster-whisper/ctranslate2; source- and voice-bound Gemini/Kore evidence; no silent alternate voice/model.
- Do not infer mathematical, narration or student-publication approval from passing synthetic regression tests.
- Three-PC Drive-native coordination uses Dell-115, Yoga6 and HP when online; never Zenbook; no automatic reassignment.
- Preserve any uncommitted edits in the older Drive-synced local repo working trees. Work in separate isolated Git branches and checkouts until reconciliation.

## Validating the guard, without billing

```powershell
python -m unittest discover -s tests -p "test_tts_paid_entrypoint_authorization.py" -v
python -m unittest discover -s tests -p "test_element_narration_gemini.py" -v
python -m unittest discover -s tests -p "test_reviewed_element_tts_handoff.py" -v
```

All these suites use test doubles and offline synthetic inputs; they do not spend API credits. No real TTS or production deployment was attempted in this round.

**Release status:** DRAFT only, unmerged. Remaining work includes authentic Gemini audio, formal academic/figure/voice quality review, complete MP4/pixel duration acceptance and reconciliation of local development branches.
