# RFH Phase 3C — wide figure readability and downstream synchronization

**Scope:** `tlyoon/MicroGen_AI_Web`. Development branch based on Phase 3B draft PR #57, **not** a production release.

## Failure reproduced

Thomas Calculus 2.2 Figure 2.10 is a valid 784 × 234 PNG containing three panels. In slide 7, the original half-width column caused horizontal overflow. Bounding it to its column solves clipping but makes the panels too small for effective teaching. A successful LaTeX compile is insufficient for readability approval.

## Correction

- After Phase 3B's width/height normalization but **before** compiling or publishing the Beamer deck, inspect source-image dimensions using Pillow.
- Identify potentially unreadable wide illustrations (default aspect ratio 2.6 or higher and effective figure width at most 0.65 of frame text width). Calculate from explicit `width=...\\linewidth` / `width=...\\textwidth` and, when applicable, column width.
- Unsupported or unreadable images are not accepted as visually verified; the earlier graphics-presence gate still handles missing files.
- For a detected poor layout, save a local `slides_attempt_N_failed_legibility.tex` and review JSON, and **reject the candidate** without publishing it.
- Within the existing communication policy's bounded Selenium/API attempt budget, request an updated LaTeX deck with a full-width figure-focused slide and the original explanation and mathematics intact.
- A subsequent attempt must pass the same gate. Persistent failure exhausts the task and **must not** be certified as a completed lecture. No heuristic panel cropping or automatic scientific reconstruction is performed.

## Slide-count and audio/video contract

Adding a new figure slide may change every subsequent page index. The existing runner invalidates all downstream stage receipts after a slide change; `slide_narration_sync.inspect` refuses a slide/script count mismatch, and the video gate requires an exact hash-matched slide/script/WAV synchronization receipt. Never reuse narration, WAV, or MP4 from a changed deck. New output must be generated only in an isolated approved pilot, with old published material protected.

## Acceptance evidence

- Simulated actual vendored `generate_slides_tex` first returns the wide-image-in-half-column defect; the gate rejects and requests a dedicated figure frame; a second compliant reply is accepted as a two-frame deck.
- A second pair of defective candidates exhausts its budget and produces no accepted `slides.tex`.
- A synthetic PDF with two slides and an old one-slide script is blocked by `slide_narration_sync.inspect`, and `invalidate_downstream(..., "slides")` drops narration, TTS, QA and video checkpoints.
- Narrow portrait figures, already legible full-width composites and commented-out graphics are not incorrectly rewritten.

## Limits and release requirements

This gate uses image ratio and layout width as an interpretable **risk detector**, not an assertion of measured visual/text legibility or proof that all source panels survived extraction. A real full-width Thomas 2.2 slide, including (a)/(b)/(c) and its labels, must still be visually assessed. Also complete final two-pass Beamer footer QA, per-slide narration and speech tests, sound/video synchronization, old-publication backup, complete CI and a controlled full pilot before merging/deploying to three PCs. No source PDF, old lecture, or commercial textbook asset is committed.
