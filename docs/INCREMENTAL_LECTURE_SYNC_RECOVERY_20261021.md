# PR209 — recover lecture production independent of solved Figure 8.3 layout

21 October 2026, Dell-115, isolated development checkout on PR208.

## Disposition of historical Figure 8.3 issue

The **original graph arrangement/cropping issue is resolved**, demonstrated by
PR169's original textbook vertical-to-generated slide horizontal ink-shape
correspondence and PR170's automatic reflow dispatch. PR193 subsequently
independently verified all three original inverse-function operator glyph
matches against the existing slide. **Do not reopen the layout bug** merely
because a later whole-equation pixel-correlation heuristic is inconclusive.
Full mathematical equations, signs, labels, axes and professional academic QA
remain separate reviews. True narration-timed highlighting remains a genuine
unmet video-production requirement; those are NOT graph-layout failures.

## What changes in PR209

Use the original lecture source PDF, slide PDF, script, and individual slide
WAV files as immutable inputs. Build independently addressable, source-hashed
slide/utterance execution entries and derive strict <=540-second **audio-only**
multipart candidate ranges from actual original WAV PCM frame counts. No
silence-based word-time guesses, new narration, external billed TTS, original
file changes, claimed per-element semantic mapping or production publication.
Independent subchapter/slide entries ensure one unresolved figure or formula
does not automatically block work on unrelated slides.

Dell-115 **actual source** 8.4 / 8.5 / 8.6 audit (complete run):
- 8.4: 17 slides, 17 WAVs, 71 verbatim utterances; candidate audio-only
  parts slides 1–8 (321.8927 s), slides 9–17 (310.818 s).
- 8.5: 20 slides, 20 WAVs, 78 utterances; slides 1–11 (398.6187 s),
  slides 12–20 (362.538 s).
- 8.6: 17 slides, 17 WAVs, 69 utterances; slides 1–9 (330.708 s),
  slides 10–17 (298.4927 s).

All 54 slides / 218 utterances are individually accessible from the durable,
read-only queue written **outside** the original teaching directory at:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\thomas_84_85_86_sync_queue_20261021_1621.json`.

These six windows are **audio-only plans**, not encoded video acceptance.
The historical unsplit MP4s fail the strict <600-second requirement and are
preserved for reference. Existing 8.4 multipart encoded visual-highlighting
previews are still review-only because genuinely source-verified per-element
audio/timing is absent; 8.5 and 8.6 do not have accepted replacements.
No student publication, no automatic claim that all math/figures are correct.

## Next production increments (not another Figure 8.3 shape audit)

1. For each independently queued slide, select and verify exact source/slide
   visible elements and the corresponding original verbatim narration spans.
   Advance unambiguous elements without blocking on unrelated elements.
2. Generate genuinely separated per-element audio using existing approved
   Flash-Lite/Kore TTS policy and observed retries/fallback, only once the
   input mapping is source-grounded; never fabricate original-WAV word times.
3. Encode and pixel/PCM-audit true element-synchronized multipart review
   videos with EVERY encoded part strictly <600 seconds. Verify timing from
   actual segment WAV boundaries and encoded visual changes.
4. Maintain independent academic/listening acceptance before publication.
   Do not overwrite original lesson media, alter protected main, use
   HP/Yoga6/Zenbook, Whisper/ASR or GCS lease.

The queue itself is not an academic review or permission to synthesize.

The queue CLI exits 0 after a new, valid REVIEW-ONLY worklist is
written. A completed read-only staging task is not a production
release; its status and all approval flags remain explicitly blocked.
