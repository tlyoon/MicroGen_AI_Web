# PR148: read-only real lecture technical acceptance audit

Date 19 October 2026. Stack parent PR147 at
c38134f0c20b543a4547fbd7c97e5cbe63e6851d.

## Pipeline

The new `python -m selenium_pipeline.lecture_acceptance_audit` CLI
receives an existing single lecture folder and a named textbook/slide
figure/page. It (1) re-executes PR145's original PDF source figure
evidence preflight, (2) inventories only the expected legacy
`slides.mp4` or proper `part_NN/part_NN.mp4` files, (3) inspects
ACTUAL encoded MP4 duration using existing FFmpeg contract code,
(4) verifies actual multipart audio-timed element/pixel QA only if a
real complete `lecture_completion.json` receipt is present and
passes the established `verify_series` re-verifier,
(5) SHA checks all original PDF/MP4 files before and after.
No source, slide, audio, narration or MP4 is modified.

A legacy `slides.mp4` is never equivalent to an accepted multipart
speech-highlighted lesson even when it is short. Unit-test injected
duration is explicitly recorded as SYNTHETIC and never marketed as
real MP4 evidence. A technically blocked CLI prints machine-readable
JSON and exits with code 2; an ordinary non-zero failure must not be
silently mistaken for a publishable lecture.

## Real Thomas Calculus 8.4 pilot (HP, non-destructive)

Existing actual lecture folder:
G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4

Source Figure 8.3, source PDF page 2 / slide page 5.

- Original source PDF: 44 vector paths, 0 embedded raster images on
  the selected page. No extractable (a)/(b)/(c) source-panel labels.
- Slide page 5: 4 raster image objects, 22 vector paths, and no
  unambiguously extracted PDF Figure 8.3 caption text block.
- Real legacy `slides.mp4` SHA256:
  3398c48199e3f7ac00c1918e71576b8105a81c7064717866499bbb7da3b094c8
- Measured real encoded MP4 duration: **633.93 seconds**. Strict
  contract requires encoded part duration to be **less than 600**.
  Thus this current legacy MP4 violates the contract.
- No valid source-to-slide full-figure-and-panel identity and no
  accepted multipart highlight proof; original files preserved.
  STATUS: TECHNICAL_ACCEPTANCE_BLOCKED. No publication permission.

Note: older anecdotal duration reports need not equal actual present
file metadata. Always record the currently measured original MP4 SHA
and duration as above, not an assumed historical figure.

## Verification

HP synthetic read-only audit and production gate: 13 focused tests
and 19 parameterized subtests passed. Real file execution performed
without output into lecture directory or TTS calls. Full regressions,
CI and independent PC checks must be rerun on exact pushed commit.

## Pending non-trivial work

Independent source-vector scientific panel boundary + label extraction
for textbook Figure 8.3, then source-matched synchronized figure
highlighting, and regeneration into encoded parts **<600 seconds**
without overwriting historical MP4/WAV. Distinguish automated visual,
duration, transcript, math verification from optional human academic
and listening QA. No safety rule can be bypassed with an arbitrary
approval field. Do not merge draft stack into main without consent.
