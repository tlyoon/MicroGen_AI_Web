# RFH Phase 3B — deterministic Beamer graphic bounds

**Scope:** generated slide layout in `tlyoon/MicroGen_AI_Web` only. Isolated code branch; do not deploy to the three running production checkouts.

## Reproduced defect
The source `Figure 2.10.png` for Thomas Calculus 2.2 contains three panels. Slide 7 places it in a half-width Beamer column but previously constrains only `height=0.55\\textheight`. Its horizontal extent may exceed its enclosing column even while LaTeX compilation succeeds.

## Implementation
- A deterministic helper `selenium_pipeline/latex_graphics_bounds.py` adds missing `width=\\linewidth`, an appropriate height bound, and `keepaspectratio` to images inside `frame` environments.
- Within an explicit column, a too-broad `width=...\\textwidth` or `...\\paperwidth` is replaced with `width=\\linewidth`.
- Existing valid dimensions, image names, conditional image guards, surrounding scientific content, and unrelated preamble remain untouched; already normalized output is idempotent.
- The helper is wired into the actual vendored slide-generation entrypoint, after LaTeX text sanitization and before the Beamer sanity compilation. The PDF under test is therefore produced from bounded TeX.

## Acceptance
Focused synthetic tests cover the Thomas-style three-panel figure, optionless images, column width, existing safe images, commented-out graphics, unrelated options, and integration timing. Future CI must run complete historical tests on Windows and Linux. Real image bounds and readability still need inspection on a **separate authorized test copy** of Thomas 2.2 before release.

## Limits
A width bound avoids overflowing the intended column, but does not prove that source panel labels are correct or that the resulting text is readable. Two passes of Beamer compilation, full slide PDF visual audit, source-to-figure completeness, and downstream narration/media invalidation remain independent release gates. An already published lecture cannot be silently overwritten.

## Rollback
Revert this commit in a clean development branch. Existing source PDFs, lecture PNGs, slide PDFs, narration, and MP4 files are not modified by these tests.
