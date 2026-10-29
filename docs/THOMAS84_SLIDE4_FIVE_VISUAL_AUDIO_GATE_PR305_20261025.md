# PR305 — Integrate all five original Slide-4 visual review candidates into audio eligibility

Windows-only, Dell-115 isolated branch stacked on **CI-green PR304** (head `8112167b3597a1adbcc9d1569baa6ae298238e9c`).

## Reason for the change

PR304 added two original text candidates to the three Figure8.2 regions, reaching **5/5 review-only Slide4 visual candidates**. But PR301's normal read-only audio eligibility dispatcher still read only PR300's **3/5** visual region report. Without integration, a genuine improvement in visible candidates would be invisible to normal production-readiness reporting and could trigger unnecessary remapping.

## Permanent normal-path correction

`original_slide4_audio_eligibility.inspect_original_slide4_audio_readiness` now invokes the existing (and **still required**) PR300 source-matched three-panel report **plus** PR304's independently SHA-bound five-candidate report. The gate verifies all five original utterance IDs, spoken SHA receipts, exact original source/slide/script hash, three unchanged raster candidate IDs/native crop SHA/rectangles, and two explicit **source-slide text** kinds for the introduction and radical/absolute-value explanation. It refuses changed math approval flags, fabricated start/end timestamps, marked decoded-frame verification, duplicate audio receipts or altered source identities.

The normal output now reports **5/5 original visual candidates, 0/5 unmapped candidates, of which exactly 2 are text**, when the complete original source read passes. Old direct callers without the expanded evidence still get the historical truthful **3/5 + 2 unmapped** result, rather than silently assuming evidence they did not provide.

Improved visual review candidate coverage **does not** promote source scientific review, semantic interpretation, Kore voice content, separate WAV existence, word or utterance timing or synchronized MP4. The historical whole-slide WAV inventory remains **NOT_CHECKED**, and the normal auditor validated **0 real per-utterance WAVs** in this invocation.

## Test and source provenance

Existing real original Thomas8.4 and reviewed 71-unit queue test suites: **33 passed**. The new five-visual integration adversarial suite: **6 passed with the actual original-source and 71-unit saved-review-queue fixture enabled on Dell-115 (an earlier separate no-source run had 5 passed and 1 expected skip)**. Both passing suites exercise false timestamp/acceptance flags, wrong SHA, wrong photo IDs, changed figures, missing/duplicate approval decisions and incorrect original queue denominators. Original source SHA b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068 unchanged.

All GitHub CI Windows-only under PR303; inherited PR304 hosted Windows CI is green. No extra paid API, Gemini web submission, modifications to original G drive assets, Whisper, protected branch merge, audio/MP4 regeneration or YouTube/Moodle release.

## Remaining live blocker

The real 71-unit original source academic queue still records 0/71 accepted two-pass agreements (different special Slide1 title-only scope cannot be pooled). This PR does **not** establish math acceptance. Each original utterance's Kore audio receipt/WAV identity, actual duration and decoded narration-to-highlight frame synchronization are separately unverified. Next priority is an evidence-based, nonpublishing per-utterance audio/timing handoff check, not another guessed preview.
