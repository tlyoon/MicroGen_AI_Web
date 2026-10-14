# Real-pilot offline TTS duration preflight

This optional tool compares proposed narration scripts with one exact,
hash-verified real WAV pilot for the same voice. It does NOT call Gemini,
TTS, Chrome or FFmpeg. It does NOT create an approval receipt, allow TTS,
approve a lecture or publish files.

From a clean repository checkout, run in PowerShell:

    python -m selenium_pipeline.tts_duration_preflight --pilot-storyboard "C:\Review\Part1\storyboard.json" --pilot-wav-receipt "C:\Review\Part1\real_audio_alignment_receipt.json" --pilot-video-duration-s 168.36 --candidate "C:\Review\Part2\storyboard.json" --candidate "C:\Review\Part3\storyboard.json" --candidate "C:\Review\Part4\storyboard.json" --out "C:\Review\duration_preflight_UNAPPROVED.json"

The pilot receipt must have the technical status
wave_chunk_timing_verified_spoken_content_unreviewed, and all segments
must match the original exact UTF-8 spoken-text SHA-256, ids and order.
Mixed voices or sample rates are refused. The optional measured final-video
duration can calibrate inter-segment silence separately.

The output reports the pilot word count, actual WAV speech duration,
estimated candidate speech durations at the pilot speed, a scenario with
speech running 20 percent slower and 24 seconds reserved per part, and
parts whose slower scenario would reach or exceed the strict 630-second
limit. The latter should be repartitioned before any real TTS. The report
uses exclusive file creation to avoid clobbering existing QA evidence.

The slow-speed scenario is not a confidence interval or a guarantee.
Expression complexity, voice/model changes, pauses and retries can affect
actual duration. Final TTS WAVs and FFprobe MP4 runtime are mandatory checks.

Observed in Thomas Calculus 13e Section 2.2 Part 1 (experimental):
391 counted words in 11 real pilot WAV chunks, 167.16 seconds of WAV audio,
1.20 seconds of inserted pause, and a 168.36-second video. This corresponds
to about 140.34 counted words/minute. The current unreviewed Part 2/3/4
scripts have 465/527/615 words, predicting approximately 199/225/263
seconds. These are *narration* durations, not the separate 1695-second
Phase 2 conceptual *teaching time* total.

No mathematical scientific approval or spoken-word listening acceptance is
conferred by these measurements. Do not bypass existing outline, storyboard,
TTS, figure or student publication gates.
