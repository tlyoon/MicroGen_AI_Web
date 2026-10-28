# PR343 — Independent physical re-audit of TWO real full §8.4 MP4s

**Real Dell-115 Windows original-source/media audit PASS** on
28 October 2026. This is an independent second implementation path,
not a replay of the original PR342 success flag.

Against actual original PDF/WAV bytes, all 16 untouched 24kHz mono PCM16
WAVs were independently reopened, and their physically stored source
PCM chips checked byte-for-byte for complete, contiguous sample
coverage. The audit rehashed every real H264 source clip and the two
complete MP4 outputs and independently decoded both actual AAC streams
and the source PDF frames in the final video container.

**Measured actual results:**
- Part1 original slides1–8: **420.85 s**, SHA256
  `eed4f7de3164245763537df9fe39166cf2c7a0c4f198848b8a6b3fc13bd2552b`,
  **32 real clips + 32 independent final MP4 PDF frame checks PASS**.
- Part2 original slides9–17: **312.13 s**, SHA256
  `f03972e43351de1d08e5b7f2d12957327562f7c85db45494951ce533cdb3b9c5`,
  **31 clips + 31 independent final MP4 PDF frame checks PASS**.
- **29 acoustically timed historical original-PDF provisional highlight
  events and five earlier corrected Slide4 source highlighted segments**.
- **16/16 original source WAV PCM payloads byte-verified**; full
  sample coverage; 63/63 stored encoded clips and 63/63 independently
  decoded actual final MP4 source-PDF frame checks PASS.
- Original textbook/source PDF SHA
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
  remains unchanged.
- 3 new targeted fail-closed regression tests PASS; original source
  integrated physical run PASS.

The 29 **acoustic highlight events** are NOT 29 necessarily distinct
PDF rectangles; more than one utterance may legitimately refer to
the same visible block. The auditor separately proves actual source
geometry, physical PCM contents, FFmpeg AAC, MP4 H264 and timing.

**IMPORTANT: NO student release.** Neither geometric provenance nor
recording authenticity proves every historical sentence matches its
chosen mathematical element. Other spoken elements remain static.
Full independent academic source mathematics acceptance and all
utterance-level synchronization remain **FALSE**; zero accepted
replacement MP4s, no Moodle/YouTube publishing or original mutations.

Files added:
- `selenium_pipeline/original_thomas84_29_independent_media_audit.py`
- `tests/test_original_thomas84_29_independent_media_audit.py`
- Windows-only CI reliability regression and syntax entries.

Private external evidence, not uploaded to GitHub:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR343_INDEPENDENT_29_SOURCE_MP4_AUDIT.json`.

Only Dell-115 was used locally. No HP, Yoga6, Zenbook, Ubuntu tests,
Whisper, or new paid model requests. Next: close missing source-math
semantic mapping across the remaining narrated sentences, then
rerender final fully synchronized videos <600 seconds each.
