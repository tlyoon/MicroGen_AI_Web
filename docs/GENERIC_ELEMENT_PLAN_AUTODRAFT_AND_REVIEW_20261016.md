# Generic source-bound narration→element plan drafting and guarded review

**MicroGen_AI_Web — 16 October 2026. DRAFT/REVIEW ONLY.**

## Purpose

The original teaching-media contract is to highlight precisely the
equation, text, geometry, or full composite figure *being narrated*, while
each encoded lecture video is **strictly less than 10 minutes**. The
existing rendering integration (PR #106) verifies real MP4 pixel changes,
but initially required a manually prepared element-narration plan. This
next stage reduces preparation effort by extracting geometry and relating
it to the *actual existing* script without inventing mathematical
explanations or granting approval to guessed slide elements.

## What the three generic commands do

### 1. Generate a source-bound candidate mapping

```powershell
python -m selenium_pipeline.element_plan_autodraft `
  --source-pdf "PATH_TO_SUBCHAPTER\source.pdf" `
  --slides-pdf "PATH_TO_SUBCHAPTER\slides.pdf" `
  --script "PATH_TO_SUBCHAPTER\script.txt" `
  --out "NEW_ISOLATED_CANDIDATE.json"
```

Input uses the normal `**Slide N [duration]:` narration header pattern.
The extractor automatically finds visual PDF text blocks, whole figures,
actual bounding boxes, and candidate textbook source pages. It then
partitions existing per-slide script paragraphs into **verbatim source
fragments**, preserving their complete original concatenated text. A
deterministic lexical matcher ranks possible visual anchors and explicitly
flags ambiguous sentence→region assignments. Mathematical syntax,
figure meaning and the accuracy of source-page candidate matches are
**not** inferred as truth by simple word overlap.

The generated `REVIEW_REQUIRED_NOT_TTS_READY` JSON is rejected by the
TTS and element staging validators. It contains **no new audio**, no
invented speech, no approved source mapping and no publication receipt.

### 2. Generate readable review and selection files

```powershell
python -m selenium_pipeline.element_plan_review_worklist `
  --draft "NEW_ISOLATED_CANDIDATE.json" `
  --out "NEW_HUMAN_REVIEW_WORKLIST.md"

python -m selenium_pipeline.element_plan_review_bridge template `
  --draft "NEW_ISOLATED_CANDIDATE.json" `
  --out "NEW_REVIEW_SELECTION_TEMPLATE.json"
```

The worklist shows each slide, the unverified source-page suggestions,
visual target identifiers, literal excerpts from the original narration
and the top-ranked candidate regions, with ambiguity and composite-figure
warnings.

The structured review template deliberately leaves the source page,
source quotation, spoken-element assignments, audio file names and
per-part boundaries **blank**, rather than auto-authoring fictional
evidence. A reviewer must inspect original figures (including multiple
(a), (b), (c) panels), formulas, slide geometries and narration, then
fill the selection with:
- `status: "REVIEWED_SELECTION_FOR_PROCESSING"` and a nontrivial
  `reviewer_note`
- exact `draft_sha256` of the candidate JSON and one declared
  whole-lecture `voice_id`
- on every slide: literal `source_page`, `source_evidence`, a
  `review_note` and nonempty `elements`
- for each spoken visual element: an existing `draft_element_id`,
  ordered original `utterance_ids`, an immutable *existing*
  per-element PCM `wav`, an unchanged `wav.verified.json` Gemini TTS
  evidence receipt, and explicit `tts_model` and `tts_voice` metadata, and an `element_review_note`
- explicit `part_boundaries_after_slides` chosen from the teaching
  structure, with each concatenated actual WAV duration <590 seconds

Wide suspected multi-panel images cannot silently become single-panel
geometry: explicit figure-panel count, panel number and a source-figure
review acknowledgement are required for panel overrides.

### 3. Convert a complete, reviewed selection to a source-bound plan

```powershell
python -m selenium_pipeline.element_plan_review_bridge promote-reviewed `
  --source "PATH_TO_SUBCHAPTER\source.pdf" `
  --slides "PATH_TO_SUBCHAPTER\slides.pdf" `
  --script "PATH_TO_SUBCHAPTER\script.txt" `
  --draft "NEW_ISOLATED_CANDIDATE.json" `
  --selection "MANUALLY_COMPLETED_REVIEW_SELECTION.json" `
  --audio "EXISTING_FINAL_PER_ELEMENT_GEMINI_WAV_FOLDER" `
  --out "NEW_REVIEWED_PROCESSING_PLAN.json"
```

Each immutable per-element Gemini TTS receipt must bind the exact WAV
SHA-256, original spoken-text SHA-256, the declared Gemini TTS model
and one unchanged voice for the whole lesson. This prevents a new
fragment selection from reusing a recording that says something different.

The bridge recalculates the ENTIRE draft independently from the unchanged
source/slides/script, and verifies every selection. It refuses reordered,
missing or duplicated narration fragments, edited speech, stale/hash-
modified PDF geometry, missing source quotations, missing WAVs, selected
duplicate targets, altered voice identity, excessive part duration,
unsafe composite panels and unreviewed/missing reviewer fields. It never
calls Google or synthesizes audio; it cannot create a passing plan for
missing per-element WAVs.

The only allowed output status is
`author_specified_unapproved_element_narration`, which means
**approved to attempt technical processing, NOT reviewed academic
content or verified speech**. Existing stage/generic runner QA must
still verify exact rendered targets and decoded MP4 pixels. Publication,
academic and listening approval are separate, explicit gates.

## Real existing source results

| Source | Slides | Candidate visual targets | Original script fragments | Ambiguous mappings | Multipart figures |
| --- | ---: | ---: | ---: | ---: | ---: |
| Thomas Calculus 8.4 (original deck) | 17 | 121 | 71 | 61 | 2 slides |
| Thomas Calculus 8.4 (isolated corrected Figure 13 deck) | 17 | 121 | 71 | 61 | 2 slides |
| Thomas Calculus 8.5 | 20 | 138 | 78 | 62 | 0 detected |

All draft outputs were generated from actual original source/slides/script
and saved in separately isolated review files. **None were automatically
approved or passed into a TTS/video production run.** The 8.4
corrected-slide PDF has a different SHA-256 from its older slide deck,
and the candidate files are therefore not interchangeable.

A synthetic, completely separate three-slide example was reviewed
with mock signed-off processing choices (not mathematical/academic
approval), exact supplied PCM WAVs, and then passed through the
actual element staging **and decoded-pixel MP4 review renderer**:
3/3 source slides, 3/3 highlights, 2 <600-second review videos.
This exercises all the steps without pretending the original candidate
matches were academically certified.

## Explicit remaining work

1. Most automatically proposed sentence→region matches remain ambiguous
   or refer to equations described differently in spoken English.
   Geometry and lexical overlap alone **do not establish mathematical
   mapping**. More capable text-only Gemini-assisted suggestions could
   reduce this review burden, but must remain clearly unverified and
   must never bypass the source/panel selection checks.
2. The existing slide-level narration/TTS flow does not yet produce
   separately verified per-element Gemini WAVs for arbitrary subchapters.
   This bridge **requires already existing real per-element audio**, and
   cannot derive actual synchronized audio timing from ordinary slide-level
   WAV by arbitrary sentence splitting.
3. Independent Gemini ASR remains incomplete for Thomas 8.4 (14/48
   receipts: 13 machine-consistent, one mathematical uncertainty; 34
   awaiting genuine independent transcription). No Whisper package,
   import, dependency, installation or fallback is permitted.
4. Only real, confirmed geometry + timed video highlights and
   independently checked spoken mathematics and academic approval can
   permit a later separate production release.

**Draft branch stays unmerged and student-facing original files remain
unchanged. No API calls, Whisper or TTS regeneration were used in these
candidate-generation steps.**
