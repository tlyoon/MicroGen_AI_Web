# PR273: Enforce actual decoded soundtrack fidelity at production acceptance

Before PR273, the production bridge fresh-verifies source identity,
MP4 hash, per-event visual highlights, slide-bound element targets and
encoded container length, but did not independently compare sampled
MP4 audio against the preserved narration WAV. New production-candidate
verifier decodes **both** WAV and actual MP4 audio into 24 kHz mono
signed-16-bit PCM using locally installed FFmpeg. It requires:
- Actual MP4 duration strictly under 600 seconds
- Actual WAV and MP4 decoded speech lengths within 150 ms
- Decoded audio/video container duration within 200 ms
- Independent audio samples at 20%, 50% and 80% each correlated >=0.78
  against one shared fixed source offset no more than 80 ms
- Bounded FFmpeg timeout and duration, no file mutation
- Full source/pixel/element and technical acceptance checks remain active.

This gate is *integrated* into the existing sourcebound production
candidate verification code, not merely a separate report.
Dedicated FFmpeg-encoded test clips reject substituted and delayed
soundtracks, rather than trusting receipt assertions.

This is technically tested with synthetic source materials; original
Thomas Calculus 8.4 is still 0/71 independent mathematical agreements.
It does NOT attest words/pronunciation, physical Kore TTS synthesis,
human listening, mathematical mapping or student publication.

No protected original G: Drive assets, main branch, existing WAV/MP4
modified. No Gemini/API/TTS services or publication.
