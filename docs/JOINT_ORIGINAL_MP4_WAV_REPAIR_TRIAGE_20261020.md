# PR175 — joint original figure/media QA with real WAV repair boundaries

The official read-only original lecture QA now evaluates the existing
slides, Figure 8.3 source-bound color/black reflow, original encoded
MP4(s) and the proposed whole-slide WAV multipart plan in ONE
traceable report. A source-consistent original audio receipt
is attached as `original_wav_multipart_repair_plan`.
Missing, corrupt or mismatched source-bound audio reports
`MISSING_OR_INVALID_ORIGINAL_SLIDE_WAV_BOUNDARY_EVIDENCE`.
When an actual MP4 is measured at or above 600s and
audio evidence is complete, a new actionable blocker
`REENCODE_MULTIPART_WITH_SOURCE_WAV_BOUNDARIES_AND_VERIFY`
identifies a technically justified next generation operation.

The real original Thomas Calculus 8.4 report:
- original 3-graph vertical→horizontal reflow detected;
- original WAVs 17 slides, 632.7107s total;
- proposed part_01 slides 1–8, 321.8927s original speech;
- proposed part_02 slides 9–17, 310.8180s original speech;
- original slides.mp4 still >600s and noncompliant;
- unverified original math axis/label completeness,
  original caption/prose collision and incomplete
  timed narrated-element highlight QA remain blocked.

No actual split MP4 was produced by this PR. A WAV grouping
cannot prove the final encoded MP4 length (<600s), original
source completeness or highlighted speech timing.
This is a source-bound repair plan, NOT approval.
All original source/slide/WAV/MP4 hashes are preserved;
the joint audit exits 2, publication and encoded
acceptance flags false. Synthetic/adversarial unit tests
cover valid WAV receipt, missing WAV and forged hashes.

Dell-115 only, parent PR174 exact head
`6ac6e26f18e5387c631beaa126f186a288f298d2`.
No other PC access; no changes in dirty G: worktrees,
paid TTS calls, Whisper/ASR, external distributed
GCS lease, main branch or student publication.
Voice-consistent Flash-Lite/Kore default and three
genuine failures before approved fallback unchanged.
