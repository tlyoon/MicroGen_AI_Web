# PR295 — Original Figure 8.2 printed-label order candidates

24 Oct 2026, Dell-115 only; isolated stacked draft based on CI-passing PR294 `b4361fc59f429bd10340a8de2e15c25aa06a91b7`.

## Genuine source and slide geometry

In the original six-page Thomas Calculus 8.4 textbook PDF, physical page 1 contains Figure 8.2 as vector/text geometry, with three separate printed substitution labels directly above its reference-triangle caption. The source label bounding-box x ranges are approximately **282.203–318.035** (tangent), **366.531–401.923** (sine), and **450.339–486.611** (secant) PDF points. Exact physical page/caption and source PDF SHA256 were verified with the existing strict source-quote and source-bound math checks.

The original slide 4 contains one 409×134-pixel composite raster, with independently detected review-only gutter candidates x=120 and x=246. Those yield the three slide PDF x ranges **48.421–126.4618**, **126.4618–208.4046**, and **208.4046–314.4101**. The new tool associates the original SOURCE label ordering with corresponding raster strip candidates by ordinal placement only. Each original-source label and corresponding slide candidate crop carries exact coordinates and the latter a reproducible native-pixel SHA256. All source, slide and narration inputs remained unchanged.

## New generalized engineering check

`selenium_pipeline.original_figure82_source_label_order` requires the existing original source-math preflight (PR294) and original real-image gutter preflight (PR291). It separately witnesses the printed figure number and descriptive caption in the original PDF with PR292's spatial quote guard and checks their physical proximity. It then identifies three distinct original printed formula label text lines above that caption, validates exact token order, non-overlapping source label bounding boxes, three slide candidate strips and before/after original input hashes.

Original Figure 8.2 number appears in two spatial locations on textbook physical page 1 (an earlier reference and the actual printed caption); PDF sorted text exposes only one contiguous occurrence. The new checker therefore associates the physical marker to the unique descriptive caption by geometry instead of arbitrarily selecting the first search result or weakening the strict citation guard. This recorded a reusable extraction lesson.

## Regression and acceptance scope

**22 Dell-115 focused and neighboring tests passed**, including synthetically reversed/missing formula order, missing description, wrong figure-number multiplicity, wrong original file SHA and unverified slide mapping. Full actual original Thomas 8.4 Figure 8.2 source-label audit succeeded. **These are source-layout and review-candidate coordinates, not independent source-to-slide pixel equivalence, original triangle side-length/mathematics verification, academic consensus, visual element highlight timing, genuine Kore TTS or public-release authority.** No Gemini request, paid API call, historical teaching asset mutation or merge into protected branches occurred. Real original two-pass mathematical acceptance remains only 1/71 title metadata; 70 pending.
