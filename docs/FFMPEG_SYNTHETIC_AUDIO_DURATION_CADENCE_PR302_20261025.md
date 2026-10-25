# PR302 corrective CI evidence — synthetic AAC duration frame cadence

25 October 2026, Dell-115-only isolated checkout. **PR302's first full Ubuntu CI failed**, while the offline-regressions and full Windows jobs succeeded.

## Exact observed failure

The GitHub Actions Ubuntu full historical suite at run **40167862359**, job **121092479154**, failed the existing `tests.test_independent_encoded_audio_temporal_audit.ActualEncodedAudioQA.test_real_encoded_pcm_matches_all_three_temporal_windows` with `Wrong, truncated or padded audio duration in encoded MP4`. The production audio auditor required decoded WAV versus AAC length within **0.15 seconds** and was correctly fail-closed. The change introduced in PR302 concerned mathematical proof and did not modify that audio auditor.

## Minimum corrective change

The synthetic test fixture fed FFmpeg an indefinitely generated black video at **5 frames/s** while using `-shortest` against a precisely **3-second** generated WAV. The output stream end is thus sensitive to **200 ms video frame granularity** and platform FFmpeg EOF/muxing semantics. The positive test's upper 150 ms audio-length tolerance can be violated on Linux even with the intended WAV, without indicating corruption of real user audio.

Change the *test's generated video cadence alone* from `r=5` to `r=25` (40 ms frame periods). No production `independent_encoded_audio_temporal_audit` threshold or MP4/WAV source comparison is weakened. The same tests still require:
- real FFmpeg encoded AAC audio, a verified source-WAV/MP4 SHA chain and three independent waveform-window correlations;
- rejection of replaced audio, 250 ms-shifted audio, tampered source PDFs and altered encoded MP4;
- unchanged WAV/MP4 duration bound, single global time offset and <600-second production contract.

On Dell-115, after modification, **13 focused/neighbor tests passed** (including 4 real encoded audio tests and nine exact principal-root interval tests). Existing SWIG warnings only.

## Required hosted validation

This correction remains a hypothesis about Linux's original timing behavior until **the next Ubuntu hosted CI job passes**. If Linux remains red, examine exact FFmpeg output durations and A/V packet timing before modifying either test or implementation. Never silence or skip the positive test, loosen the 150 ms limit, or claim production audio synchronization.

No provider calls, paid API, user teaching asset reads beyond the previously authorized mathematical audit, modification of original WAV/MP4, protected merges or publication. Record this corrective commit on PR302's own isolated branch before stacking new PRs.
