# Thomas Calculus 8.4: isolated Figure 8.6 resize — review only

**Status:** technical figure-layout candidate, NOT approved for student release.
Date: 16 October 2026. This correction is intentionally separate from all
legacy Thomas 8.4 production files and from the two review-only narrated MP4s.

## Source issue

On original slide 13, the reference triangle for the secant substitution was
placed using `height=0.22\\textheight`, yielding only **15.46%** of slide width.
At normal viewing size, labels and relationships in that triangle appear small.

## Reproducible, generic code fix

`selenium_pipeline.figure_resize_review` builds an isolated copy of the
LaTeX deck, copies the existing PNG assets without editing them, replaces
exactly one user-designated sizing expression, recompiles with pdflatex,
and checks:
- All 17 pages are preserved, and **only the requested slide's pixels changed**.
- The nominated image grows beyond the legibility-width threshold.
- The new PDF has no detected out-of-bounds clipping.
- All original source file SHA-256 values remain unchanged.
- The candidate is stamped `REVIEW_ONLY_ISOLATED_FIGURE_RESIZE`.
- No WAV, MP4 or production completion receipt is modified.

### Actual Thomas 8.4 test

```powershell
python -m selenium_pipeline.figure_resize_review `
  --source "G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4" `
  --destination "PATH_TO_NEW_NONEXISTENT_REVIEW_FOLDER" `
  --image "Figure 8.6.png" `
  --old-height 0.22 --new-height 0.30 --slide 13
```

Result: 17 pages, **only slide 13 pixel-different**, figure expanded to
**21.08% slide width**, zero detected PDF clipping blockers. All sixteen
unmodified slides are pixel-identical when rendered at 1.5x. The updated
slide 13 shows all original equations and triangle labels without visible
overlap in the 2x review image. Four isolated safety tests pass.

See the separate Google Drive `MicroGen_AI_Web_Figure13_ReviewOnly_20261016`
folder for the derived slides PDF, before/after images, asset copy and receipt.

## Mandatory downstream steps before release

1. Audit the corrected slide 13 academically and for human legibility.
2. Rebind the 48-element storyboard to the **new** slides.pdf SHA-256,
   regenerating geometry evidence for every narrated element and without
   pretending the old slides-PDF provenance is still valid.
3. Reuse any actual WAV only if content/text/voice/source audio hashes
   and the independent audio-to-text audit remain valid, with explicit
   layout-only rebinding evidence; otherwise regenerate WAVs.
4. Re-render both MP4s from the corrected deck, verify encoded active pixel
   targets, all 17 slides, SHA-256, source mapping and both durations <600s.
5. Keep **student publication disabled** until independent academic,
   figure and speech review are completed.

The corrected PDF is deliberately **not** promoted to the original source
folder. PR #91–#96 must remain draft/unmerged pending acceptance.
