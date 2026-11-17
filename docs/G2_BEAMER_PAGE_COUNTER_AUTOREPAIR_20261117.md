# V6 verified real-Beamer page-counter recovery — Dell-115

Date: 17 November 2026. Normal MicroGen_AI_Web Selenium source-locked development on Dell-115, draft PR #530. This is a source/slide **layout production repair**, not academic or media QA.

## Historical issue and diagnosis

Genuine Serway §1.3 authored `slides.tex` contains the historical master-prompt Beamer headline `\\hfill ... \\insertframenumber{} / \\inserttotalframenumber ... \\par`. After a single native MiKTeX compilation, all 13 slides carried numerator `N` with **incorrect denominator `1`**, and page-counter span bounds were on/above the top edge and too close to the right edge: page 1 was `1 / 1`, bounding box y0 approximately -0.189 pt, x1 approximately 362.828 pt on a 362.835-pt-wide slide.

A previous technical preflight counted these simply as 13 small-text *review* findings and falsely reported **0 blockers**. This report does not excuse or erase the defect. The original `slides.pdf` is still the authoritative old source-locked G2 asset and is never overwritten.

## Historical recovery and integrated normal-path fix

The repository already documented an analogous **one-pass Beamer total-frame-count limitation** in `selenium_pipeline/original_thomas84_endpoint_repair.py`; reuse that historical insight, not a guessed new content-generation strategy.

- The normal `vendor_template_v2/gen_slides_selenium_v11.py` production path calls `slide_headline_geometry_recovery.normalize_legacy_headline` immediately after Gemini LaTeX sanitation, *before* source example, figure legibility, compile and acceptance gates. It recognizes only the exact historical Beamer headline and registered recovery signature `LEGACY_BEAMER_TOP_EDGE_SLIDE_COUNTER`. Unknown or multiple definitions are not silently transformed.
- A physically inset `\\vskip7pt` **before** the page counter plus horizontal `9pt` inset and stable `5pt` after-space avoids clipping. Existing source text and all frame body bytes are unchanged by normalization. Three production prompt templates (v19, v20 hybrid, current Selenium v23) now request the safe headline; prompt-whitespace variants are normalized to the exact code-reviewed canonical template.
- The normal `pdflatex_compiles` uses exactly **two bounded, no-shell-escape** native compiler passes for the verified safe template, then invokes `verify_slide_counter_pdf`. It independently requires one physical PDF span `N / total` per slide, the actual total equal to rendered page count, and strict top/right insets. One-pass `N / 1`, clipped glyphs, missing counter, or wrong denominator fail instead of releasing the PDF.
- The normal `academic_visual_preflight.inspect` independently classifies visibly wrong/clipped page counters as technical **blockers**; no benign small-text downgrades.
- The v6 recovery registry contains the exact code-reviewed handler, environment, finite retry policy and regression path. No new Gemini request, API charge, paid TTS, WAV, MP4, or publication claim follows from this page-counter fix.

## Actual original Serway §1.3 acceptance stress test

A brand-new isolated scratch directory, `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/g2_page_counter_scratch_20261117_02/`, copied only existing authored LaTeX and its supporting images. Two real native `pdflatex -interaction=nonstopmode -halt-on-error -no-shell-escape` passes generated a 13-page corrected PDF with correct physical counters:

- First page: **1 / 13**, physical bbox `[331.286, 6.722, 353.857, 14.692]` pt.
- Last page: **13 / 13**, physical bbox `[327.052, 6.722, 353.855, 14.692]` pt.
- Actual native production `pdflatex_compiles` independently recompiled the scratch deck and returned **True** under the new integrated two-pass and physical-geometry gate.
- Exact PDF main-text extraction, after removing only counter text, matched on **all 13 slides**, with the same 13 pages and zero embedded-image count changes. No source physics sentence or narration was rewritten.
- New preflight results on the genuine old source: **13 clipped/incorrect counter blockers**. On the isolated corrected PDF: **0 technical geometry blockers** and 0 counter findings.
- Preserved original `slides.tex` SHA256 `6d55cf5189dd4d4f42f13ad3d7a028e35829a5368b609e9d9845cb5cb1c07b46`; original `slides.pdf` SHA256 `922c309db5c4dfc00e4f8484b1fdcf7177e0537881831b2aa91b6af387a86296`.
- Isolated corrected `slides.tex` SHA256 `e7db0e08838c769f306fa87436e2baab47d8261d756a624814b2f8a6bfaa2df6`; corrected `slides.pdf` SHA256 `16b41ddcc2be81d6636c43bf5843ac95559fcc1db0193f9bc434e83aa65b4bcb`.
- Normal G2 forward engine automatically re-audited the immutable original and stored content-addressed independent-source receipt `8ca9dd6a5d115a2f5190becfe2d421d0da55bd90b8bc62209473942c3270924f.json` SHA `df1c559ea5417fe564f50b36f7c4869488e2b1467c161f8b15ebf1c435ff991b`: 13 geometry blockers on old PDF, 20/85 scientific accepted, 65 pending, 0 model requests.

## Tests and remaining acceptance

`tests/test_slide_headline_geometry_recovery.py` covers old template, v19/v20/v23 prompt agreement, idempotence, exact body preservation, retired recovery registry refusal, two-page physical counters, wrong-total, missing/edge-clipped markers and unchanged mathematical/publication nonapproval. `tests/test_asr_scene_visual_gates.py` remains part of the existing geometry/figure policy.

Locally, the extended source/academic/G2 regression suite passed **187 tests**, 0 failures (seven nonfatal warnings). Exact-head hosted Windows checks still must be observed after pushing the branch.

**Scope:** The executable *future slide-generation failure class* is now fixed and stress-tested on genuine authored lecture geometry. The **original source-locked Serway G2** remains a separate immutable old-review artifact with 13 layout blockers. Replacing that original would invalidate its academic source SHA; it must pass a new source/slide identity and relevant independent scientific acceptance, not be silently overwritten or re-labeled. The external Gemini PDF-response service has not recovered; G2/G3 still OPEN, 20/85 source-agreed, 65 unresolved. No old scheduler was recreated.
