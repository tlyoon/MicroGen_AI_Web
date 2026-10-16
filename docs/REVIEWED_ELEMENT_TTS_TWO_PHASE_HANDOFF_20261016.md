# Source-reviewed narration element → Gemini TTS → synchronized highlight handoff

**MicroGen_AI_Web — 16 October 2026. REVIEW-ONLY DRAFT.**
Stacked on PR #107; preserves mandatory element highlighting, <10-minute
parts, no-Whisper contract, and no silent paid API execution.

## Fixes the circular dependency

Before this change, a reviewed narration/element selection required
**existing verified individual WAVs** to become a staging-compatible plan,
but Gemini element TTS demanded an authored plan **before** making those
WAVs. The original source-grounded review remains mandatory; the bridge
now exposes two separate, cryptographically linked stages.

1. A reviewer chooses the actual textbook source quotation/page, original
   PDF-rendered text/figure anchors and exact original script utterance
   ranges. PDF geometry and mathematical evidence are checked. This
   step can write an **unapproved TTS request**, without any audio.
2. The complete TTS request can be passed to the existing Gemini element
   TTS generator **only** with explicit reviewer + live + paid-API flags.
   Its one-voice per-element WAVs remain immutable with per-WAV/model/
   voice/script SHA-256 receipts. **There is no verified Gemini web-UI
   TTS output route in this development branch**, so using this existing
   API transport is strictly opt-in; no silent fallback.
3. Final plan promotion re-verifies all source/geometry/narration evidence
   and compares the **exact source-reviewed TTS request** with the frozen
   Gemini synthesis job identity and per-WAV SHA provenance. Then—and
   only then—can it produce a technically stageable but academically
   *unapproved* `author_specified_unapproved_element_narration` plan.
4. The earlier generic synchronized runner handles per-element WAV
   durations, part splitting and independently decoded highlight pixels.
   The separate mathematical, Gemini ASR and lecturer-listening release
   gates still must pass before student publication.

## Offline preparation (no Gemini/API calls)

After generating the source-bound `auto_candidates.json`, readable
Markdown worklist and blank review template using PR #107 tools, an
actual reviewer must fill every source and narration-to-visual decision.
The new command **requires no audio folder**:

```powershell
python -m selenium_pipeline.element_plan_review_bridge prepare-tts `
  --source "SUBCHAPTER\source.pdf" `
  --slides "SUBCHAPTER\slides.pdf" `
  --script "SUBCHAPTER\script.txt" `
  --draft "AUTO_CANDIDATES.json" `
  --selection "REVIEWED_SELECTION.json" `
  --out "NEW_REVIEWED_GEMINI_TTS_REQUEST.json"
```

It verifies that the exact original script content is preserved, figure
panel overrides have explicit review rationale, textbook quotations are
actually present, and scene anchors remain within rendered PDF geometry.
It estimates time using a conservative 70-words/minute rate and fails if
a proposed part is 540s or longer. The true WAV and MP4 durations are
measured again later, and must each remain strictly below 600s.
It returns `reviewed_element_tts_request_unapproved`, with
`api_execution_authorized: false` and no academic approval.

A reviewer note is a processing-decision record, not a mathematical proof
or evidence that the learner hears correct pronunciation.

## Existing API generator: explicitly authorized *only*

**DO NOT execute the following without separate user authorization to use
the Gemini API and incur its possible billing.** This example documents
the optional preexisting Gemini TTS engine, **not the non-API default**.

```powershell
python -m selenium_pipeline.element_narration_gemini `
  --authored-plan "NEW_REVIEWED_GEMINI_TTS_REQUEST.json" `
  --output-folder "NEW_ISOLATED_GEMINI_WAV_FOLDER" `
  --model gemini-3.8-flash-lite-tts --voice Kore `
  --confirm-reviewed-tts-request `
  --confirm-gemini-api-cost `
  --confirm-live
```

Omitting *any* of these three explicit flags forbids the reviewed
request from invoking the existing Gemini API. The model, voice and
declared source hashes are checked before any client creation.
The output is review-only; all segments must share exactly one declared
Gemini TTS model and voice. Resumption requires matching audio receipts.
The generated audio is NOT considered mathematically or perceptually
validated merely because the provider returned a WAV.

Once genuine reviewed individual WAVs exist, finalize the source-bound
stage plan:

```powershell
python -m selenium_pipeline.element_plan_review_bridge promote-reviewed `
  --source "SUBCHAPTER\source.pdf" `
  --slides "SUBCHAPTER\slides.pdf" `
  --script "SUBCHAPTER\script.txt" `
  --draft "AUTO_CANDIDATES.json" `
  --selection "REVIEWED_SELECTION.json" `
  --audio "NEW_ISOLATED_GEMINI_WAV_FOLDER" `
  --tts-request "NEW_REVIEWED_GEMINI_TTS_REQUEST.json" `
  --out "NEW_SOURCE_BOUND_TECHNICAL_STAGING_PLAN.json"
```

The final review bridge checks against TTS `tts_job_identity.json`,
every `.wav.verified.json`, the identical review selection, immutable
audio and spoken-text hashes and the actual measured recording lengths.
It does not accept a merely fabricated or filename-matching recording.

## Improvement to visual mapping hints

Deterministic matching now recognizes equivalent *notation hints*
between natural language and PDF glyphs, e.g. `sine` vs `sin`,
`squared` vs `²`, and `square root` vs `√`. Possible conflicting
single trigonometric terms are explicitly surfaced to the reviewer,
not automatically considered matching equations. This is not an LLM
semantic comparison and cannot verify source-image label completeness.

Actual Thomas Calculus candidates were recomputed:
- Corrected 8.4: 17 slides, 121 visual targets, 71 script fragments.
  Ambiguous lexical/math hints declined **61 → 53** (two slides still
  suspected multi-panel); all remain review-required.
- 8.5: 20 slides, 138 targets, 78 fragments.
  Ambiguous hints declined **62 → 58**.
- Original scripts and figures untouched, no new Gemini WAV generated,
  no API called, no academic or publication claim.

## QA boundary and remaining work

A separate artificial three-slide fixture tests review → TTS request →
**mocked** Gemini TTS response with valid PCM data → cryptographically
bound final plan → real staging and encoded element-highlighting checks.
Mocks prove safe integration and strict authorization behavior, **not
the acoustic/academic quality of actual synthesized narration**.

The real Thomas 8.4/8.5 selections have NOT been independently approved;
blank review forms are not an invitation to bypass the gate. Existing
Thomas 8.4 independent audio ASR is still 14/48 with one mathematical
discrepancy. No student-facing source or historical MP4 was touched.

**For fully non-API unattended operation**, the remaining dependency is
an independently verified Gemini-browser audio synthesis capability;
none is established by this PR. Do not install Whisper or convert
slide-level WAVs into fictitious per-element timestamps.
