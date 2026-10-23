# PR272: Compatible frame timing on Dell-115 FFmpeg 4.0.2

## Real environment defect found while validating PR271

Dell-115 default FFmpeg: version 4.0.2; existing video encoders requested
-fps_mode cfr or -fps_mode vfr, which FFmpeg 4 does not recognize. This
blocked local element-highlighting encodes independent of the original
Gemini browser/server response problem. An already installed Dell-115
Miniconda Python 3.12.9 has numpy, PIL and pymupdf; no installation or
modification of the original G: Drive repo was required.

## Safe corrective increment

Introduce ffmpeg_fps_mode_compat.fps_mode_flags(), interrogating the
FFmpeg executable's real version. For FFmpeg major 3 or 4, choose the
documented legacy equivalent -vsync cfr/vfr. For >=5, preserve the
existing modern -fps_mode cfr/vfr output options. Unknown/broken
versions fail closed; do not invent frame timing. Preserve the existing
H.264, audio AAC, odd-pixel padding, source slide visual appearance,
spoken timeline checks, strictly less than 600 seconds acceptance,
and review-only release flags.

Changes limited to two previously failing review encoders and a pure
version-compatibility helper. No old source slides, recordings or MP4s
are modified; isolated temporary synthetic test output only.

## Actual Dell-115 evidence

Eight combined neighboring test suites, 25 tests PASSED on existing
Miniconda Python 3.12.9 and FFmpeg 4.0.2, including:
- original source WAV highlight MP4 pilot,
- encoded highlight video preview,
- rebuilt read-only video review,
- PR271 original decoded MP4 audio fidelity,
- source-reviewed PCM pilot and true-sync acceptance validators,
- original math/audiovisual readiness gate,
- adversarial FFmpeg version selector.

This is a technical playback/encoder compatibility fix only.
Original Thomas Calculus 8.4 71 source-backed narration mappings
remain ZERO independently math-agreed, 0 of 3 new slide-1 source
review submissions used, no new genuine Kore element TTS generated.
No academic/listening approval, paid Gemini requests, changed historic
MP4/WAV, Moodle/YouTube publication or development schedule restarted.
