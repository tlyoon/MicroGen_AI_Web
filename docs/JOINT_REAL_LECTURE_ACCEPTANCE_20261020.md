# Joint original-figure and encoded-media audit — 20 October 2026

Scope: read-only, Dell-115-only isolated development stacked on
draft PR154 `feature/actual-source-slide-figure-gate-20261020`,
exact base `02e93521ca85b3ff022c3335d051440910dfc382`.

The new `selenium_pipeline.joint_original_lecture_acceptance`
CLI composes the independently corrected source PDF source-to-slide
figure gate (PR154) with the existing real video and spoken-highlight
multipart verifier (PR148). It cross-checks original source and slide
SHA256, page/figure identity, all discovered MP4 names and content
hashes, refuses synthetic time probes or claims of publication,
and confirms no assets or media candidate inventory changed between
checks. Returns machine-readable blocker codes and ALWAYS exits 2;
a successfully completed audit is NOT a successful lecture.

## Real original Thomas Calculus 8.4 pilot

Original G: lecture folder inspected without writing:
- `source.pdf` page 2: SHA256
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
- `slides.pdf` page 5: SHA256
  `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`.
- `slides.mp4`: SHA256
  `3398c48199e3f7ac00c1918e71576b8105a81c7064717866499bbb7da3b094c8`;
  actual FFmpeg duration **633.93s**, violates the strict <600s limit.
- Original figure caption's text block shares 8 lines with adjacent
  substitution instruction box; 23 pre-caption vector object candidates
  remain independently unassigned; original graph and panels unverified.
- The original folder lacks verified `lecture_completion.json`
  multipart spoken-highlight proof; legacy single MP4 is NOT accepted.

Status `JOINT_ORIGINAL_LECTURE_ACCEPTANCE_BLOCKED`, exit code 2.
All original teaching/source slides/scripts/WAV/MP4 and three dirty
G: Drive working trees untouched. The separate older
`20261020_pr155_source_vector_visibility_0055` checkout with uncommitted
work is preserved. HP/Yoga6/Zenbook and paid TTS never used.

Strict contract: encoded parts individually <600s, actual
spoken-element highlighted frames, authoritative complete figure
and panel scientific evidence, Flash-Lite/Kore default with three
genuine failed attempts before approved consistent-voice fallback,
no Whisper/ASR, GCS external distributed leases or unauthorized
Moodle/YouTube/student publication. Automated technical verification
is never represented as independent academic/listening QA.
