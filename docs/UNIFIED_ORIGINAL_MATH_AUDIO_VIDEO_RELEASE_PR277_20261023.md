# PR277: unified original source-math plus multimedia acceptance report

The prior code has independent checks for original-source/AI mathematics,
model/voice provenance, exact per-element PCM, decoded highlighted
MP4 pixel changes, strict under-600-second multipart durations and
explicit separately authored academic and student publication approval.
This PR unifies read-only execution and blocker reporting, rather than
mistakenly treating a passing isolated technical check as publishable.

For each real source-backed lecture, it first verifies original source
and complete independent mathematics count and source hash.
An optional isolated technical candidate is rejected if source
does not match. With a candidate, the acceptance code rechecks
real pixel targets, decoded WAV-versus-MP4 audio, and all part durations,
then validates effective uniform TTS manifest, actual human review,
and explicit independent student-publication authorization.
No document, human approval or published output is generated.

For real Thomas 8.4: 71 original utterances, zero independently
source-agreed mapping and no real Kore per-element audio or verified
complete production candidate. Publication remains blocked.

No Gemini/API/TTS calls, original teaching-file mutation,
main-branch merge or Moodle/YouTube upload.

## Full-suite regression tracking

GitHub CI for initial PR273-276 heads exposed one pre-existing synthetic
automatic element TTS fixture that wrote constant 16-bit PCM instead of
a changing voiced waveform. The stricter decoded-audio acceptance gate
correctly failed it. Replaced that synthetic fixture on the earliest PR273
branch; targeted nine automatic source-grounded element-audio tests PASSED.
Newest child branches will be rebased to contain the corrected base.

Dell-115 broader pytest after the fixture correction passed 650 tests
(4 skipped) and then stopped on a pre-existing local Miniconda Google
SDK lacking google.genai.types.HttpRetryOptions. The repo's GitHub CI
workflow installs a newer Google SDK; this local environment issue is NOT
proof of complete Linux/Windows CI acceptance. Report live CI separately.

This audit remains read-only and never self-creates academic/human or
student publication approvals.
