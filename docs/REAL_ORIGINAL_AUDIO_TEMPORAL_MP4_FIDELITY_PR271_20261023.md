# PR271 ? Read-only original WAV-to-decoded-MP4 temporal fidelity

## Motivation

User requested stopping Gemini length-dependent prompt tests and advancing
independent technical work while Gemini service remains intermittent.
Actual Thomas 8.4 second math review remains 0/71 independently agreed;
separate slide-1 reviewed window is 0/3 new attempts used, awaiting
a confirmed healthy Gemini owned-tab response.

Instead, recheck actual archived source-audio MP4 continuity independent
of mathematical interpretation. This decodes original MP4 audio to
24 kHz mono signed-16 PCM, verifies source/WAV/MP4 SHA256 against the
existing source-aware receipt, and checks 20%, 50%, 80% of original speech
using one consistent global offset (not independently adjustable drifts).
Each audio window correlation must be >=0.78 and shared alignment offset
<=80 ms, allowing 150 ms codec padding at the end. Decoded container
duration also strictly below 600 seconds.

## Independently verified real data on Dell-115 (23 Oct 2026)

Original folder: G:/My Drive/Projects/Thomas_calculus_13ed/8/8.4
Review: LocalAppData/MicroGen_AI_Web_Checkpoints/real_84_slide1_source_cited_evenframe_pilot_20261022

Original textbook source SHA256:
b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068
Original WAV SHA256:
7110f2610354409f2eb7cf82fd216b0e873b1048a91db999adcff063bc7aedeb
Original review-only MP4 SHA256:
4d213472bf88c041e4761eaefeb6c3931e36a104b71937de0ef160d22637ab62

Original WAV sample frames 92768 (3.86533s)
MP4 decoded PCM sample frames 92160 (3.84000s)
Encoded container duration 3.85s
Actual WAV-vs-MP4 waveform window correlations:
0.97186, 0.99966, 0.99984
Global audio sample offset 0 samples

This proves continuity of original recorded WAV in the archived MP4,
not mathematical meaning, word fidelity, narration-element highlight
accuracy, actual newly synthesized Flash-Lite/Kore per-element WAV,
human listening review or production release. All such gates stay false.

Adversarial tests encode real synthetic AAC MP4s and verify rejection of
swapped audio, 250ms delayed audio, modified original source files, and
modified encoded MP4. No original media is modified.

Read-only repeat command:
python -m selenium_pipeline.independent_encoded_audio_temporal_cli --original-folder ORIGINAL --review-folder REVIEW

No Gemini/TTS calls, API charges, Moodle/YouTube publication, change to
main, extra device involvement, original teaching-file write or schedule.

## Local regression environment limitation

New encoded-waveform tests: 4/4 passed with the genuine installed FFmpeg
4.0.2 and actual AAC MP4s, including altered/delayed audio rejection.
Six neighboring Dell-115 suites passed (27 tests); two legacy preview
suites, plus the historical original-highlights pilot suite, could not
pass their positive-encode tests on Dell-115 because unrelated existing
encoders use the -fps_mode option unsupported by installed FFmpeg 4.0.2.
This is a local encoder-tool compatibility issue, NOT a WAV-versus-MP4
audio temporal audit failure. Preserve these failures honestly until
the compatibility issue receives its own separately tested PR.
