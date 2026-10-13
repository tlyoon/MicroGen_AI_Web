# MicroGen_AI_Web Phase 3B — Rendered-element geometry and measured WAV-segment timing

**13 October 2026. Status: offline, source-independent experimental engineering components; no live Gemini or textbook lecture generation.**

## What this adds

Previous Phase 3A validated IDs in an agreed joint slide/narration storyboard, but did not establish *where* the IDs actually appeared in the compiled Beamer PDF. Phase 3B introduces a real Beamer PDF geometry instrument, a segment-level WAV timeline and a visible highlight PNG preview renderer.

1. `pdf_element_geometry.py` locates the actual PDF bounding rectangle for each semantically identified text/math/graphic/multiline region. It requires a **temporary-instrumented** TeX macro of the form `\newcommand{\MGElement}[2]{\href{microgen-element:#1}{#2}}`. All visual element IDs from the storyboard must appear exactly once, in the correct PDF slide/page, inside the page's geometry. An ID cannot silently attach to another page or missing/clipped/implausible region. The generated geometry record contains absolute PDF-point and normalized 0–1 bounding rectangles plus PDF and storyboard hashes.
2. `strip_instrumentation_links` produces a **static video-source PDF**, not an interactive distribution PDF, without hidden clickable instrumentation. In pdfLaTeX, some hyperlink annotations expose `xref=0` and PyMuPDF's link deletion cannot reliably remove them. Instead, the cleaner imports each rendered page's content into a clean PDF without annotations and confirms **pixel-identical output** at a validation render scale. This intentionally drops *all* page annotations/interactivity, including non-MicroGen links. Original instrumented and textbook PDFs remain untouched. This static output is appropriate for video compositing only.
3. `speech_segment_timing.py` accepts one final uncompressed PCM WAV per **semantic narration segment** and an ordered WAV manifest containing exact narration text SHA-256, approved voice ID and any between-segment silence duration. It fails on missing/unsafe/misordered chunks, hash disagreement, mixed voices and mismatched audio formats. It concatenates chunks once and constructs start/end times from their **actual PCM frame counts**, not guessed word counts, using the existing `alignment.schema.json`.
4. `highlight_frames.py` creates a **static annotated PNG per spoken segment**, with a non-occluding colored outline and translucent backing around the matching, source-verified PDF region. Outputs correspond to measured event timestamps. The decoder/FFmpeg video encoder must later display the right frame during each corresponding speech segment.
5. `geometry_cli.py` exposes independent offline commands `extract`, `clean`, `timeline` and `preview`, requiring explicit inputs/output paths and refusing accidental overwrites.

## Real, two-pass Beamer validation

A synthetic Beamer slide was compiled twice with the TeX macro above on Dell-115, then parsed by PyMuPDF. Four independent markers were recovered at plausible precise page coordinates: a sentence, a mathematical equation, a graphic region and multiline text. The cleaned PDF had the same rendered pixels as the instrumented PDF and no private hyperlink annotations. Test `tests/test_real_beamer_geometry.py` repeats this native pdfLaTeX integration on machines with `pdflatex`; CI hosts without LaTeX skip the native compile but still run synthetic annotated-PDF and audio timing tests.

This is **real rendered-element coordinate extraction**, not OCR and not a method that infers the figure labels from a bitmap.

## Audio boundary precision and what it does *not* guarantee

For example, 1.0 s, 1.2 s and 1.4 s measured speech WAVs with 100 ms pauses between them generate events:

| Segment | Highlight start | Highlight end |
|---|---:|---:|
| 1 | 0 ms | 1000 ms |
| 2 | 1100 ms | 2300 ms |
| 3 | 2400 ms | 3800 ms |

This is exact to sample-frame precision for **supplied segment WAV boundaries**, but the module does not prove that the provider actually spoke the submitted words, where inside a segment a word starts, or how to align a long uninterrupted WAV. The receipt deliberately reports `wave_chunk_timing_verified_spoken_content_unreviewed`. Word-level emphasis needs provider word timestamps or reliable forced alignment. A future provider/QA workflow must obtain WAV chunks in the **same voice** with verified speech text, rather than cutting a long MP4 or audio file after production.

In the synthesized fixture, visual highlight frames differ as the narration advances across a sentence, equation and relevant figure panel. This is a controlled synchronization preview, **not yet a fully encoded video**.

## Integration with the complete educational pipeline

A future successful series run must first pass Phase 2 concept and duration review and Phase 3A slide/narration storyboard; then compile Beamer slides with instrumentation, extract geometry, generate exact narration-segment WAVs, compute event timing, clean the PDF, compose the final MP4 and independently verify speech content, figure-panel correctness, visual emphasis timing and *actual video runtime strictly <630 seconds*. The cleaned PDF's pixel-equivalence test ensures the extracted geometry matches the static frames, but does **not** scientifically verify the figures themselves.

Changes to slides/Beamer/PDF, storyboard content, WAV bytes or voice invalidate downstream geometry/timing/highlight/video receipts. A wrong figure or lost panel needs source-level layout/figure repair, and any additional slide triggers upstream storyboard re-planning.

## Source and deployment boundaries

All development/testing occurs in isolated `C:\MicroGen_Phase3B_20261013` and synthetic temporary fixtures. The canonical Thomas Calculus acceptance root remains `G:\My Drive\Projects\Thomas_calculus_13ed`, whose original `source.pdf` files remain immutable. No production or live TTS job was launched, and no assets in the old Thomas 2.2 directory or dirty Google Drive code checkout were touched. The automated physics/math video pilot remains blocked until the remaining semantic, TTS-content and final MP4 verification stages are implemented.

Tests include PDF marker source/page/geometry checks, stale-hash rejection, rendered-pixel equality of clean PDFs, WAV sample-frame timing, voice/content-hash mismatch fail-closed handling, and visible PNG highlight verification, plus the optional native Beamer round-trip.
