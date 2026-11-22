# G3 legacy static MP4 diagnosis and executable video repair — 22 November 2026

## Actual legacy production defect on Dell-115

Serway 8.2 and 8.3 already have source.pdf, slides.pdf, script.txt, per-slide
24 kHz mono PCM narration, and two 600-second-bounded MP4 parts each. Those
files alone do NOT satisfy the required synchronized **element highlighting**
or independent acoustic, video and scientific acceptance.

A real *encoded pixel* audit (not an assumed file count) verified the exact
source and slide hashes, each original PCM SHA/duration, multipart audio-video
duration and MP4 SHA. It then independently decoded 18 frames across
six narrated **content** slides per subsection:

| Section | Content slides sampled | Actual MP4 frames decoded | Slides with measurable within-slide pixel change |
|---|---|---:|---:|
| 8.2 | 2, 5, 8, 9, 12, 15 | 18 | 0 |
| 8.3 | 2, 6, 10, 11, 14, 17 | 18 | 0 |

All observed within-slide RGB differences were negligible against the
0.25 absolute 8-bit channel threshold. This is a decisive *legacy
static-slide* failure, not evidence that highlight timing was independently
accepted. The existing `slides_parts_manifest.json` was produced by
`per_slide_boundary_with_separate_encoder_outputs`, which describes simple
slide presentation rather than synchronized element-level focus events.

## New integrated production-recovery behavior

`g3_legacy_visual_recovery_v71.py` is the registered, executable handler for
`G3_LEGACY_STATIC_MP4_SOURCE_BOUND_REBUILD`. It:
1. Requires signed original source, slides, script, all 24 kHz PCM files and
   contiguous, SHA-checked multipart MP4/video duration manifests.
2. Independently decodes three frames from multiple actual narrated content
   slides in **each** video part using FFmpeg.
3. If all sampled slides remain static, declares
   `G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED` and creates an immutable
   source-hash-bound rebuild worklist **outside the textbook directory**.
4. Records the exact original media SHA and requires new isolated
   element-synchronized highlighting, independent acoustic and video QA and
   source-grounded scientific review before technical and student release.
5. Never changes original WAV, MP4, PDF, source text or Gemini historical
   request; no model Sends, no paid API calls, no student publication.
6. Is idempotent and rejects changed original source/media or modified
   recovery worklists on restart.

`full_pipeline_video_handoff.complete_from_published` now REQUIRES
`production_video_contract.verify_series` (with synchronized event
provenance) to reuse a supposedly accepted multipart series. The previous
shortcut `runner.check_valid('video')` accepted any nonempty `slides.mp4`;
it is no longer used to authorize this handoff. With the original Serway
8.2/8.3 directories, the **normal production handoff** now automatically
stages the exact legacy static media as rebuild work, refuses the old
static output, and preserves the original videos.

The legacy generator's own `.microgen_completion.json` is a technical
generation receipt, not a G3 independent-audio or highlighted-video
acceptance certificate.

## Real original source evidence

- In Dell-115: original §8.2 produced an immutable worklist named
  `g3_legacy_static_c6b300b56133ab03197e1dee.json` on explicit direct
  physical QA, plus a separate production-handoff worklist under
  `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\G3_Legacy_Video_Rebuild_V71`.
- §8.3 likewise produced a distinct immutable worklist named
  `g3_legacy_static_bbd3de7d9fb5662ad45dfaba.json` and its matching
  production-handoff worklist.
- 17 targeted tests passed on the real source-bound audit and the existing
  full-pipeline video tests, including synthetic static vs moving frame
  fault injection, stale source SHA, forged MP4 SHA, broken slide range,
  corrupted WAV, idempotent immutable recovery and strict accepted-series
  reuse gate.
- The read-only original G2 queue remains 27/85 accepted with four claimed
  historical sends (slides 3,4,10,11) lacking attributable model replies.
  Those exact requests remain **no replay**.

## Remaining G3 work

This action closes the dangerous **false-acceptance and diagnosis/repair
admission** boundary. It **does not yet render corrected element-highlight
MP4s** or establish independent source-math, listening/transcription
fidelity or visual cue alignment. A new source-bound audiovisual candidate
must be rendered in an isolated directory, then subjected to actual
independent acoustic + encoded-frame highlighted-event QA. Do not copy or
rename old `slides_partXX.mp4` to manufacture a passing result.

No student release, no new paid Gemini API or lecture/science model Send.


## Full-regression incidental blocker: Chapter 11 caption grounding

The full Dell-115 suite on the merged Chapter 11 source baseline exposed a
newly introduced v3 shortcut: `_caption_block_parser_parity` returned
`True` whenever a caption's PDF bounding box was unchanged, even when
the supplied caption text was entirely unrelated. On original Serway §§11.1
and 11.3, the test also accepted synthetic appendages despite modest
caption-geometry differences across MuPDF versions; those words were not
verbatim printed source captions.

Repair: identical geometry requires identical normalized real source
caption words, figure identifier, source page and panel inventory. A
separate explicitly source-SHA-bound parser grouping recovery still handles
genuine alternate geometry, but cannot claim invented words. The previous
false-positive test expectation was corrected and new positive/negative
identity tests were added. This remedy is registered in the executable
recovery registry, with the real original textbook PDF regression retained.
