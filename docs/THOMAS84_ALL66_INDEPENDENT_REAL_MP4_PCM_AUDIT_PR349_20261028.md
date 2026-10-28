# PR349 — INDEPENDENT physical audit of two actual all-66-cue Thomas §8.4 MP4s

This is a source/actual-media SECOND PASS, not merely replaying an
encoder successful-state flag. Only Dell-115 Windows was used.

The auditor physically reopened two actual H264/AAC MP4s saved by
PR348, the protected original 17-slide PDF, all actual protected
historical WAVs, every stored split PCM WAV and every saved
PDF-derived image, and five real corrected source-visual clips from
the earlier SHA-locked PR333 bundle. All checkable claims were
recomputed.

**Real independent source/audio/frame results:**
- Part1 slides1–8 **421.91s**, actual final MP4 SHA256
  `0d97e0e1b13b6561488cab092778318e09b8225817829141177c3eb10c5d1bb4`,
  **57 real H264/AAC source clip checks and 57 independently decoded
  final video source-PDF frame checks PASS**.
- Part2 slides9–17 **312.88s**, final MP4 SHA256
  `746063f4ed235a5f63deb4197e8e2f46aa4b24aa4cb050bbce9251ddbdf9875f`,
  **49 clips and 49 independently decoded final source-PDF frame
  checks PASS**.
- **16/16 original historical source WAV PCM tracks physically
  rechecked byte-for-byte** against all actual saved sample-exact
  encoded source-chip WAVs, with no dropped, duplicated or
  reordered protected source sample.
- **66/66 original source-PDF provisional visual cue events
  independently reverified** against actual PDF block text and
  original rectangle coordinates. **5/5** corrected slide4
  previously encoded source media clips independently rehashed.
- **106/106 actual H264 clips SHA checked** and **106/106 actual
  final MP4 visual frames decoded and compared** against
  re-rendered original-source-PDF reference images.
- Both real AAC streams decoded without error. Both final MP4
  durations verified strictly <600 seconds.
- Original textbook source SHA remains
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
  All original G media, earlier PR333/334/342 videos preserved.

New independent audit module:
`selenium_pipeline/original_thomas84_66_independent_media_audit.py`
and Windows tests
`tests/test_original_thomas84_66_independent_media_audit.py`
(three targeted tests PASS). Actual integrated independent source
and multimedia re-audit PASS. Windows-only CI includes both.

Receipt saved outside originals:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR349_INDEPENDENT_FULL66_REAL_MP4_AUDIT.json`.

**Academic/semantic release status remains FALSE.** Technical
original-data fidelity and 106 measured real final source-PDF
frame comparisons prove physical integrity, NOT that all 66
spoken mathematical statements have correct original PDF
element references. Contextual mappings and five domain-scope
issues need further independent source-math semantic proof.
Zero student release accepted videos, no publication.
No paid Gemini/TTS, Whisper, HP/Yoga/Zenbook or Ubuntu checks.
