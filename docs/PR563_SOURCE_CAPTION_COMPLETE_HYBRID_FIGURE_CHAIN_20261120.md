# PR563 — Restore source-caption-complete cropping, labelled panels and the LaTeX figure chain

**Date:** 20 November 2026 MYT
**Machine:** Dell-115
**Parent:** PR562, exact `9c22d7d69463a2d199c5c423b0eb321eecded19f`
**Authoritative test PDF:** `G:\My Drive\Serway\Serway_8_14\8\8.2\source.pdf`
**Original source SHA-256:** `f72422b7113d11a7adfe55c0fc9e7a85b2470bda84cd32b0add5f847f8f52fd1`

## Historical failure and root causes

The published Serway §8.2 contains only `Figure 8.5.png` (an incomplete force-only crop) and one conditional LaTeX reference to it. Its original seven-page PDF contains **five printed figure captions**: 8.2 (page 2), 8.3 (page 3), 8.4 (page 4), 8.5 (page 5, panels a/b/c), and 8.6 (page 6, panels a–f). A prose reference to Figure 8.7 on page 7 is **not** a printed crop available in this PDF. The original Docling PictureItem extractor missed vector-only illustrations, used a 2.55 kB image deletion threshold, and could produce partial multi-panel crops. The mapping code validated only detected picture crops, the slide generator was not required to include all printed figures, the final `figures_manifest.json` verified only LaTeX references already in the document, and cleanup could remove provenance of unused missing figure candidates.

## Source-first executable correction

`selenium_pipeline/source_caption_figure_chain_v1.py` is a **new deterministic local candidate/recovery mechanism**:

1. Inventories printed figure caption headings using original PDF line geometry **and bold source heading font**, rejecting ordinary prose references to other figures.
2. Selects original PDF vector/raster figure regions from caption-column relationships. Unlike Docling picture detection, source rendering can include arrow diagrams made entirely of vector objects.
3. Requires all lettered panels declared in caption to have independent original PDF word-bbox evidence inside the crop: **8.5 a/b/c and 8.6 a/b/c/d/e/f**.
4. Renders each candidate directly from original source PDF at 3×, checks real drawing/raster objects, pixel-edge clipping, source SHA and per-PNG SHA. A second independent render from the same source and recorded coordinates must be **byte-identical**. This proves source-pixel fidelity; it does **not by itself prove scientific meaning or authorization to publish**.
5. Preserves an isolated, source-bound crop ledger `source_figure_chain_v1.json`. Before any mapping browser calls, the normal `runner.py` figures stage executes local source crop recovery, with no paid/provider calls. After the legacy Docling/caption stages, it rechecks and re-promotes any Figure crop overwritten by a partial legacy output, without retrying Gemini.
6. Uses an exact, reviewed entry in the **executable recovery registry**: match `source_figure_recovery`, signature `FIGURE_CAPTIONED_VECTOR_OR_COMPOSITE_CROP_MISSING`, remedy `GENERATE_SOURCE_BOUND_HYBRID_CROPS_VERIFY_PANELS_THEN_ATOMIC_PROMOTION`. This remedy makes a maximum of **two finite source-only attempts**, persists candidate files for crash-safe reconciliation, and refuses foreign or source-mismatched stage contents.
7. Binds source hash and figure ledger into the runner's artifact reuse evidence, and includes the ledger in the published figures-stage output alongside all numbered PNGs.

## Downstream chain and no silent omissions

- `gen_slides_selenium_v11.py` and its prompt explicitly demand an `\includegraphics` for **every printed captioned source figure**, with source panel annotations intact. Candidate LaTeX that omits a required PNG or hides it using `\IfFileExists` is rejected before acceptance, with bounded repair guidance and failed-draft evidence.
- `runner.valid("figures")` rejects incomplete source crop inventory, even when zero Docling PictureItems were found. `runner.valid("slides")`, `figure_audit.enforce_graphics`, and `cleanup_completed_lecture` require the full **source-caption → pixel-verified PNG → explicit LaTeX reference** chain. Cleanup cannot attest/erase an incomplete figure stage.
- Legacy synthetic test fixtures named `source.pdf` but lacking PDF header are not subjected to the real PDF-layout parser; real malformed PDF files with `%PDF-` still fail closed.
- A valid LaTeX graphics reference is a **necessary** condition; independent render, slide legibility, scientific/academic QA and narration/video acceptance remain separate gates.

## Dell-115 real result and evidence

The seven-page Serway §8.2 PDF has **five source caption headings** with exactly nine lettered panel identities. The improved source-local cropper generated source-bound PNGs:

`Figure 8.2.png` · `Figure 8.3.png` · `Figure 8.4.png` · `Figure 8.5.png` · `Figure 8.6.png`.

The real source-bound verification returned `ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED`, **5/5** printed captions, **9/9** labelled panels, and zero model Sends. The complete Figure 8.5 crop contains the actor/sandbag/pulley scene as well as both force diagrams. Figure 8.6 contains both popgun states and all four energy charts; a final pixel-edge test prevented clipping of the (a) source labels. The full source figure is preferred to dropping a marginal layout rule or original label.

Evidence only, on Dell-115:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\PR563_SOURCE_FIGURE_CANDIDATES_FULLPANELS_20261120\` (all five source-PDF crop PNGs + ledger).

A **real negative test** placed five verified PNGs and the original `slides.tex` in an isolated folder, invoked the new chain audit, and correctly failed:
`LaTeX omitted source figures: Figure 8.2.png, Figure 8.3.png, Figure 8.4.png, Figure 8.6.png`.

The original Drive lecture deliverables were **not overwritten**. These newly generated crops have not been silently promoted into the published lecture until full LaTeX regeneration, render acceptance, semantic QA and audio synchronization.

## Regression, failure-injection and acceptance

- New automated targeted tests exercise vector-only source figures, styled source captions versus prose `Figure 8.7` references, raster/vector compositing, all declared labels, missing panel, changed PNG, source drift, no model Send, stale registry, atomic staged replacement, wrong/missing ledger, missing LaTeX references, `\IfFileExists` and runner figure-stage validity.
- Existing figure-mapping, crop-source-provenance, uncaptioned-source, graphics audit, stage reuse and executable-registry tests are run against the same changes; any failure must be repaired and rerun before admission.
- The next demonstration is a **versioned regenerated §8.2 Beamer candidate**, compiled and independently checked for visible original source figures, scientific content, slide layout and narration sync; this PR does **not** claim that such a final candidate or G2/G3 student publication has passed.

The authorized 30-minute source-only Windows Task Scheduler job remains **disabled** (not deleted), exactly as requested. No automatic scheduler restart is authorized.
