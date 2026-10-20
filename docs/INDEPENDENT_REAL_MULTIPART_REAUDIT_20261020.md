# PR180 — independent actual MP4 re-audit and future subchapter recovery preflight

New command `selenium_pipeline.independent_multipart_recovery_audit` can **independently recheck completed staged review MP4s** against the ORIGINAL textbook source PDF, original slides PDF and actual per-slide WAVs in any subchapter folder. It never modifies original files or claims academic/production approval.

Specifically it validates: exact contiguous proposed WAV part boundaries; real source PDF/slides and every original WAV SHA; **byte-for-byte PCM sample equality** from the original recorded slide WAVs to the staged concatenated narration WAV; FFmpeg actual audio/video MP4 streams; actual encoded duration strictly <600s and within 0.65s of original audio; original recorded per-part SHA; replayed decoding of every independently saved representative highlighted pixel sample against its source PDF reference frame and review receipt; complete ordered original slide coverage; and all unapproved semantic/publication flags.

On **real original Thomas Calculus 8.4** fresh independent Dell-115 audit returns:
`REAL_ENCODED_MULTIPART_TECHNICAL_REVIEW_VERIFIED_SEMANTIC_ALIGNMENT_BLOCKED`.
Part 1: 321.89s, slides 1–8. Part 2: 310.82s, slides 9–17.
Source PCM exact, encoded strict duration, sampled highlighted pixels and original SHA hashes pass. **Spoken element semantic alignment, source mathematical axes/labels, all narrated visual highlight correspondence, human academic listening QA, original caption collision and student publication remain blocked.** Existing 633.93s original video unchanged.

Also adds reusable read-only source subchapter preflight that safely identifies whole-slide boundary plans for other overlength originals:
- Thomas 8.4, 17 WAVs, 632.7107s: part slides 1–8, 321.8927s and 9–17, 310.8180s; actual staged review videos now exist.
- Thomas 8.5, 20 WAVs: proposed slides 1–11, **398.6187s**, and 12–20, **362.538s**; no replacement MP4 rendered or verified.
- Thomas 8.6, 17 WAVs: proposed slides 1–9, **330.708s**, and 10–17, **298.4927s**; no replacement MP4 rendered or verified.

Automated corrective output is limited to stage/review work, never original production overwrite. Positive source PCM, video duration and image pixel tests cannot substitute actual speech-to-element alignment, original figure scientific correctness or narration listening review. Forged receipt approval, modified PCM narration, changed original WAVs, mismatched encoded duration or decoded highlight image fails closed. CLI exits status 2 even after positive technical re-audit.

Code and real subchapter experiments executed only on Dell-115, with fresh isolated checkout stacked on PR179 exact SHA ca66f93b8a6d60ca880dd4cdcb7b2272707b53f5. Original G: teaching assets and dirty working trees preserved, no HP/Yoga6, paid TTS, Whisper/ASR, external GCS lease, main merge or student publication. Flash-Lite/Kore default and Google Cloud TTS same-voice fallback only after three genuine failures remain unchanged.
