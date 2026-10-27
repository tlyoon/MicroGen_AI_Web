# PR332 — Real original §8.4 audio word timestamps vs original PDF element geometry (27 October 2026)

## Why this exists

PR331 physically produced two genuine real-source original Thomas8.4 review MP4s (419.73s and 310.81s), both strictly <600s, but correctly identified **16 unchanged slide WAVs** as lacking true utterance-to-visual-element highlighting. Old PR drafts that merely divide a WAV into visually even or amplitude-pause intervals do not prove the spoken content. The owner requires natural synchronization, no human academic bottleneck, and original source fidelity.

## New source-grounded, free/offline evidence

The new `selenium_pipeline/original_thomas84_offline_word_pdf_timing.py` loads original 17-page slides PDF, immutable original source PDF and narration (`script.txt` and `script_tts.json`), runs the existing original-source-only Beamer PDF element-geometry candidate discovery, and uses the locally installed, original SHA-pinned **Vosk offline 0.15 English recognizer** (no Whisper, network ASR or API costs) to obtain actual WORD START/END timestamps from **ALL sixteen original historical WAVs**. It does **not** synthesize or mutate audio or source PDFs.

Genuine Dell-115 runtime result:

- **16 / 16** protected original historical WAVs successfully read and unprompted offline recognized; the protected five source files and all 16 historical WAV SHA-256 rechecked unchanged.
- **65 actual word-timed acoustic sentence-anchor hypotheses** across the old WAVs, from genuine observed Vosk word start/end timestamps and original per-slide narration, NOT equal fractions of slide durations. The sole unmatched utterance is the very short Slide1 title with phonetic recognition differences.
- **Only 5 high-confidence/unique LEXICAL visible-target proposals** out of all expected utterances. This difference matters. The PDF contains mathematical equations, composite visuals and narration that paraphrases rather than quotes the slide, so a lexical system cannot safely assert a unique visual target for most utterances. Do NOT turn the 65 timing anchors into 65 accepted source element synchronization events.
- Entire source-bound worklist JSON (private Dell AppData): `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261027_PR332_16_REAL_OLD_WAVS_WORD_TIMED_SOURCE_PDF_CANDIDATES_UNAPPROVED.json`. Each utterance contains the source narration SHA, actual recognized acoustic word anchor bounds, original slide candidate PDF geometry, lexical score, math/figure review flags and explicit unverified release status. The JSON is not a fabricated reviewer receipt.
- All **5 fail-closed Windows unit tests PASS** (math polarity retained, real acoustic timestamps not dummy bins, ambiguous source visual mapping never self-approved). Normal GitHub-hosted Windows CI exact final PR head must be checked.
- No other PC used; protected G project checkout retains only three preexisting modified files; original WAV/script/slides.mp4 unchanged. No paid Gemini submission, no new Flash-Lite TTS request, no student publication or merge.

## Next actionable production integration

The real acoustic timestamps reveal an immediately tractable, original-PDF-bound math-example candidate: **Slide 3 (three quadratic/radical substitutions)**. Its 5 distinct source narration sentences all have measured audio word anchors (approximately 0–5.43s, 5.43–16.38s, 16.41–28.35s, 28.41–40.20s and 40.44–45.84s in an actual 45.87s original WAV); its PDF separately displays exact tangent, sine and secant formulas with recoverable geometry.

Use a SOURCE-LOCKED mathematical/visible formula selection per sentence, rather than pretending the lexical ranker proved meaning. Encode a visibly review-only Slide3 real PCM-sample-window-aligned 5-frame technical pilot and decode actual output pixels. Only after equivalent source-grounded semantic element mapping is available across ALL original slides can §8.4's two new MP4s meet the element-level highlight requirement. All generated prototype videos remain review-only until independent math source and voice/media QA pass.

**Important:** even a perfect timestamp is not evidence that the correct visible mathematical object was chosen; conversely a visibly correct formula highlight is not evidence that the spoken words refer to it. Both proofs are mandatory for accepted synchronization.
