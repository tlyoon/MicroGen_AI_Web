# PR181 — Independent source-PDF highlight-event rebuild + source-bound audio alignment repair

20 October 2026. Dell-115 ONLY. Parent PR180 exact SHA
`e11d5ef7db9071b9c2198db4faba267f5cfad065`.
Branch `feature/source-bound-element-audio-alignment-repair-20261020` in a
NEW clean isolated checkout. No HP, Yoga6 or Zenbook used.

## What was actually verified

The real Thomas Calculus 8.4 two-part, original-audio MP4 review media is
in the immutable separate staging directory
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\staged_thomas_8_4_multipart_review_20261020`.
The independent audit first rechecks: actual encoded H.264/AAC duration of
321.89s for original slides 1–8 and 310.82s for slides 9–17; exact PCM
sample equality with EVERY original recorded slide WAV; original
source.pdf/slides.pdf/WAV hashes and expected slide boundaries.

**Then it reconstructs each original source-PDF text/figure highlight
frame afresh** and checks staged reference PNG SHA against the independent
re-render. Every one of the **86 recorded visual events** is individually
decoded at its actual candidate interval midpoint from the real MP4,
compared to that event's original reconstructed highlight frame and checked
for original WAV-derived timing and correct slide/element order. In the
real Dell-115 test: all 86 of 86 source-regenerated reference/encoded frame
checks passed. This is a full event-level *VISUAL* technical re-audit,
not just three spot checks per part.

## What is NOT verified

The 86 intervals derive from **acoustic silences of original per-slide WAVs**,
not genuine word-level timestamps or independently produced element WAVs.
Original sentence-to-element speech correspondence remains unknown, even if
every decoded orange outline appears at the intended program timestamp.
Six slides use fallback visual emphasis. No source/math/figure academic
completeness and no human listening QA is claimed.

The existing `element_plan_autodraft` was run READ-ONLY against exact
source.pdf, slides.pdf and original script.txt. Actual evidence:
- 17 slides, 71 verbatim existing narration utterances;
- 116 independently extracted source slide visual target candidates;
- 53 ambiguous utterance/visual-element associations;
- 16 slides require new independently segmented element-WAV audio, and
  the remaining slide needs original spoken/title correspondence QA.
- Future all-lecture regeneration must use one consistent effective voice;
  no mixed old/new voices in different parts.

The new source-hash-bound machine-readable repair queue never becomes a
billable synthesis request until an explicit source-grounded utterance-to-
element plan passes existing `element_plan_review_bridge` checks. It
explicitly points to existing `automatic_element_audio_stage` as the
safe segmented-WAV path where source text mapping is truly exact, with
approved Gemini Flash-Lite/Kore primary; same-voice Google Cloud fallback
ONLY after three genuine failures. Do not synthesize speech with guessed
math/graph element identities. No ASR or Whisper was installed or run;
existing source narration audio is not destructively split.

Review evidence is stored in Dell-115 separate local staging as JSON files:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\thomas_84_source_bound_element_review_draft_20261020.json`
and `...\thomas_84_independent_element_event_reaudit_20261020.json`.

## Integrated official acceptance command

PR181 also extends `selenium_pipeline.joint_original_lecture_acceptance`
with an OPTIONAL `--staged-review <fresh separate review folder>` argument.
Without it, previous original-lecture QA behavior is unchanged.
With it, the official gate independently reruns ALL 86 encoded event pixel
and source-PDF reconstruction checks, includes a separate
`staged_highlight_event_review` receipt, and adds blocker
`STAGED_REVIEW_EVENT_PIXELS_VERIFIED_SPOKEN_ELEMENT_ALIGNMENT_MISSING`.
This does NOT confuse newly staged MP4 media with the historical original
MP4 inventory or authorize publication. Real Thomas 8.4 joint gate
returned exit **2**, reported 86/86 source-reconstructed encoded events
and student publication False. Two additional adversarial tests cover
positive staged-review reporting and forged proof of speech approval.

All output authorizations remain FALSE, including
`audio_to_element_semantic_correspondence_verified`,
`technical_production_approved` and
`student_publication_authorized`. This stage must never silently replace
the original historical 8.4 slides.mp4, whose original 633.93s duration
remains noncompliant. Future truly synced MP4s require source-review of
those 53 ambiguous associations, trusted per-element spoken clips, exact
WAV-sample timings, complete decoded pixel QA and separate academic QA.

## Safety/QA

Read-only source/slide/WAV hashes verified; no originals changed. Parser
rejects missing/reordered video events, forged duration or foreign frame
references. The new adversarial tests also cover a substituted staged
reference image and forged source hashes/approval metadata. Protected
main, old dirty G: worktrees, paid calls, GCS lease, Moodle/YouTube
publication and other PCs remain untouched.
