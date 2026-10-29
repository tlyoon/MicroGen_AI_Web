# PR332 — Actual original §8.4 historical WAV word-timing and visible PDF candidate audit (28 Oct 2026)

## Why this matters

PR331 physically encoded and verified two complete real Thomas Calculus §8.4 review videos (**419.73 s** and **310.81 s**) with 21/21 final decoded source-slide/element frame samples passing. It still contains static-slide treatment for **16** historical slide WAVs, and only the genuine corrected Slide4 five utterance chunks provide source-element timed highlights. This PR does **not** invent synchronized speech: it advances genuine original media by measuring independently recognized **word-level acoustic times** in all 16 protected historical PCM recordings against actual source-slide PDF boxes.

## Actual Dell-115 evidence

Free Vosk US English small model 0.15, pinned model archive SHA, **NO Whisper, NO paid API or network ASR**. All historical WAVs remained on protected `G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4`. The scanner read the genuine original textbook PDF/17-page slide PDF, `script.txt`, `script_tts.json`, all 16 historical `slide*.wav`, producing a 157,558-byte external-only, one-use, source-hash-bound JSON evidence receipt at:

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261027_PR332_16_REAL_OLD_WAVS_WORD_TIMED_SOURCE_PDF_CANDIDATES_UNAPPROVED.json`

- **16 of 16 real original slide WAVs inspected**, including all except Slide4 (whose five new corrected source-registered voice segments were already generated separately).
- **65 genuine per-sentence acoustic timestamp hypotheses** obtained directly from matching Vosk's original recording word start/end timestamps to the original saved `script_tts.json` sentence tokens. The title-only Slide1 original (3.87s) had no safely anchored token group; this remains unresolved, not given fake even-duration bins.
- **Five** visual target *lexical* hints met the conservative unique-ranking threshold, among which **four** have actual acoustic times and satisfy the source-script-to-original-draft correspondence: Slide5 sentence1 (0.03–11.37s) → original PDF target `s005.text.002`; Slide6 sentence5 (26.16–31.38s) → `s006.text.005`; Slide15 sentence1 (0.00–1.41s) → `s015.text.002`; Slide17 sentence3 (19.05–29.67s) → `s017.text.004`. The fifth (title Slide1 target) has no recognized acoustic timestamp, so it is **not** eligible for word-timed rendering. These four hints are still **semantic-unapproved**; high lexical overlap is not an independent academic endorsement of a mathematical visual mapping.
- Other narrated sentences lack unambiguous original rendered PDF visual targets even though genuine word timestamps exist. Their content must NOT receive invented highlight bbox/timing.
- Original source/media WAV SHA hashes rechecked unchanged after all recognition; no other PC, no cloud provider, no new synthesized audio, no Moodle/YouTube publication.

## What is accepted versus merely observed

**Accepted technical observation:** actual original PCM / source transcript SHA correspondence, measured Vosk word timing for 65 utterances, four audio-timed candidate PDF element rectangles on slides 5/6/15/17, plus one acoustic-untimed title target. This can support a **new private review-only two-part video with four additional provisional highlights** to visually assess the needed development improvements.

**NOT accepted:** “all 17 original slides element-synchronized,” exact spoken content for each historical WAV, textbook mathematical meaning of the candidate geometry, full source-academic two-pass acceptance, original voice identity, or student-ready release. These continue to be strictly false and must remain conspicuously flagged. No manually required academic reviewer; autonomous source/evidence-based QA should continue.

Unit regressions: five dedicated tests PASSED on Dell-115 after fixing one helper-name typo. The next staged change should add true original-PCM-sample splitting and candidate visual emphasis, verify final MP4 decoded frames at acoustic timestamps, and leave 12+ unqualified historical slides static/watermarked rather than claim full synchronization.
