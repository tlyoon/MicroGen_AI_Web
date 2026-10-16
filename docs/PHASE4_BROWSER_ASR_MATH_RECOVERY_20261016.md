# MicroGen_AI_Web — Phase 4 browser transcription and safe TTS repair

**16 October 2026. Review-only development, not production-ready.**

Phase 4 prioritizes cost-aware, resumable transcription and mathematical
spoken-content review while preserving the existing accepted *technical*
Thomas Calculus 8.4 video previews. Do not merge or publish until full
acceptance; original source, slides, WAVs and MP4 files remain read-only.

## Selenium default / API policy

The browser transport is an opt-in layer around existing, already tested
`series_gemini._browser_request` and vendored `GeminiSeleniumClient`.
It opens an owned Gemini tab under the existing machine-local Chrome lock,
uploads **one WAV only**, supplies a fixed *audio-only* transcription prompt
(without its expected narration), and requires a complete two-field JSON
response containing actual recognized speech.

A dedicated model id `gemini-flash-web-ui` is used in ASR job receipts.
The selected Gemini UI mode was observed as **Flash High**; the exact
underlying engine revision is not independently attested by the UI. Hence
this model id must not be mistaken for the versioned API engine. Its
receipts are never silently intermingled with earlier
`gemini-3.1-flash-lite` API transcripts.

**Observed real Dell-115 browser probes:**
- Chrome port 9222 was online; Gemini signed in; mode Flash High selected.
- Real original Kore WAV `s01_e01.wav` upload was verified and the prompt
  was submitted.
- First attempt did not satisfy a 120s response completion check. The
  existing response quarantine contained:
  `Gemini said / {"status":"unsupported","transcript":""}`.
  This is an **explicit UI-level rejection of audio transcription**, not
  valid ASR evidence.
- The second bounded attempt encountered a stale Selenium element before
  a valid response. It stopped without recording any transcript.
- **Zero** browser audio receipts were accepted. No API fallback was
  silently used. Browser audio transcription must therefore remain an
  unproven capability and must not be advertised as production-ready.

The existing browser transport historically requires longer replies.
The browser bridge now supports optional `min_chars=20` and a validated
JSON completion callback for short transcription replies; other storyboard
callers keep their previous defaults. Explicitly unsupported audio and
ambiguous/quarantined completion cause **immediate stop with no blind
resubmission**. Unrelated transient errors use bounded retries.

## Safe, resumable per-WAV evidence

`selenium_pipeline.phase4_asr_recovery` creates a dedicated, immutable
`asr_job.json` bound to the exact authored-plan SHA-256, the Web UI engine
identifier and ordered clip list. Each successful WAV receipt is immutable
and bound to its original WAV SHA, script SHA and ASR transcript SHA.
Existing valid results are skipped; changed files or different-model
results reject the job rather than being silently reused.

Each invocation is opt-in via `--confirm-live`, has bounded
`--max-new`, `--retries`, `--cooldown` and browser wait duration, and
persists review-only recovery status. No new API dependency.

Example (only after browser audio capability is confirmed):

```powershell
python -m selenium_pipeline.phase4_asr_recovery `
  --plan PATH_TO_AUTHORED_NARRATION_PLAN.json `
  --audio PATH_TO_ORIGINAL_WAVS `
  --output NEW_BROWSER_ASR_FOLDER `
  --max-new 2 --retries 2 --wait-cap 180 --confirm-live
```

The older Gemini API audio ASR evidence is available independently.
Using the API again requires explicit, separately documented permission
and a provider-specific job; this code does not switch automatically when
the web UI reports unsupported WAVs. Installing Whisper or any other
offline engine is likewise a separate deliberate decision.

## Mathematical speech comparison strengthened

`tts_quality_gate.math_token_order` extracts an ordered signature of
critical mathematical words, symbols, signs, numbers and operators.
Unlike a Counter, it detects operand reversals such as
`two minus three` vs `three minus two` even if the same keywords occur.
A suspicious order, sign or token difference triggers **review**, never a
claim that an equation is mathematically proven or pronounced correctly.
Legitimate paraphrases may be flagged and require listening.
Simple equivalents like `Section 8.4` and `Section eight point four`
remain accepted as notation equivalents.

## No unwarranted regeneration

`selenium_pipeline.phase4_repair_triage` independently recomputes the
48-clip quality screen from the original WAV and real ASR evidence before
creating any recommendations. Only objectively detected technical audio
failures become potential *segment-only* regeneration candidates. Missing
ASR is a pending-transcription state, not a TTS error; mathematical/ASR
mismatches require listening and/or mathematical review before regeneration.

**On actual Thomas 8.4 frozen narration:**
- 48/48 WAVs passed basic technical audio checks.
- **13/48** were machine-transcription-consistent with no further flags.
- **1/48** (`s05_e03.wav`) remains mathematically/ASR ambiguous.
- **34/48** are awaiting independent recognition.
- No technical regeneration candidates. **No TTS regeneration executed.**
- Corrected 2-part MP4 highlights, durations and original files unchanged.
- Student publication, academic approval and production acceptance all false.

No invented transcripts, no masked errors and no quality gates relaxed.

## Next engineering gate

A browser-only model that *actually listens* to WAVs must be confirmed
before activating this new backend on the remaining clips. If Gemini Web
continues to reject audio uploads, select and explicitly authorize a
different genuine ASR engine (e.g. existing Google Gemini audio API, with
its costs and privacy considerations, or a locally evaluated offline ASR).
Only then process the outstanding 34 segments, review the one flagged
mathematical passage, and implement verified selective TTS regeneration
and production pipeline integration with full three-PC repeatability.
