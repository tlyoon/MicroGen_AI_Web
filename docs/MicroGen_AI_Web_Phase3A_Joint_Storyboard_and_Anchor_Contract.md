# MicroGen_AI_Web — Phase 3A Joint Storyboard and Semantic Anchor Contract

**Date:** 13 October 2026
**Status:** Offline structural development component, NOT production slide/narration generation or synchronized video output.

## Design rationale

The integrated blueprint requires a joint representation linking *reviewed* physics/mathematics textbook concepts, planned slides, visible elements and speech segments **before TTS**, rather than unrelated slide and narration prompts. This phase adds structural building blocks without changing the legacy runner.

Modules:
- `selenium_pipeline/storyboard_authoring.py` — source-anchored, **UNREVIEWED** storyboard scaffold and domain-aware Gemini authoring brief. No model calls. Generated concepts and narration placeholders are not scientifically approved.
- `selenium_pipeline/storyboard_gate.py` — cross-file validation against the canonical lesson-plan SHA-256, source hash and reviewed concept outline, exact domain profile, planned slide count, stable visual element/slide/segment IDs, correct source concept/page and narration relationships, and time estimate.
- `selenium_pipeline/beamer_anchor_contract.py` — source-tag audit for `\MGElement{element-id}{latex visual content}`. Finds duplicate, absent or unexpected tags, skipping effective TeX comments. **Tags alone cannot prove rendered page coordinates or visibility.**
- `selenium_pipeline/storyboard_cli.py` — offline `draft`, `brief` and `inspect` commands with explicit source-root and no-overwrite output behavior.

## Stable relationships and release gates

Each `part_01.s001` slide has unique local semantic visual elements such as `part_01.s001.e01`, each referring to one or more reviewed concept IDs and valid textbook source pages. A narration segment must point to visible elements **on the same slide**. Every required concept must have visual coverage; every visual element must be linked to spoken narration. Speech progresses monotonically through slide order.

Intro/outro titles must identify **Part i of N**. First and final narration segments must include the exact continuity scripts in the approved Phase 2 lesson plan. All planned slides must be accounted for; adding a figure-focused slide requires upstream replanning rather than silent changes to slide count, narration or audio.

The gate refuses stale source/plan hashes, unreviewed outlines, missing concept/visual/speech IDs, mismatched source pages, stray/duplicated identifiers, placeholders, missing series continuity and planned budget overflow.

Even after an inspection passes, the **only** success-like status is:

`structural_pass_semantic_review_required`.

The returned receipt explicitly identifies the still-unverified items: scientific correctness, teaching completeness, image-panel fidelity, actual Beamer/PDF geometry, TTS audio timing, highlighting accuracy and the final MP4 duration. No final-quality certification or output publication is authorized by this stage.

An optional TeX anchor inspection returns `source_tags_present_geometry_unverified`. There is **no** actual Beamer macro definition, LaTeX compilation, PDF coordinate/rectangle extraction or highlighting compositor in Phase 3A. These belong to subsequent work.

## Safe CLI usage

Use a clean code checkout, a real **approved** Phase 2 `concept_outline_REVIEWED.json`, and its exact `lesson_plan.json`. The new Thomas source path is:

`G:\My Drive\Projects\Thomas_calculus_13ed\2\2.2\source.pdf`

Example to generate a placeholder-only storyboard on the PC:

~~~powershell
python -m selenium_pipeline.storyboard_cli draft --source-root "G:\My Drive\Projects\Thomas_calculus_13ed" --source-pdf "G:\My Drive\Projects\Thomas_calculus_13ed\2\2.2\source.pdf" --domain mathematics --outline "C:\Review\concept_outline_REVIEWED.json" --plan "C:\Review\lesson_plan.json" --part part_01 --out "C:\Review\storyboard_UNREVIEWED.json"
~~~

Use `brief` with the same options to generate domain-specific authoring instructions, or `inspect --storyboard C:\Review\storyboard_AUTHORED.json` to check a fully authored candidate; optionally provide `--latex C:\Review\slides.tex` to inspect its semantic anchor tags. None of these tools invoke Gemini, TTS or video generation.

**Critical:** The existing Thomas 2.2 concept outline from Phase 2 is still unreviewed. Therefore these commands will correctly BLOCK until an actual reviewed outline and matching approved lesson plan exist. This documentation is not a claim that those artifacts already exist.

## Independent figure improvements and future phases

Outstanding figure-guard drafts: PR **#56** (panel/caption mapping), PR **#57** (Beamer graphic bounding) and PR **#58** (wide-figure legibility, stacked on #57). Their changes must be reconciled on latest main, tested and carefully integrated before the real Thomas 2.2 end-to-end pilot. This Phase 3A PR does **not** merge those unfinished figure changes.

Next work:
1. Run source-grounded physics/math authoring against this joint storyboard, with scientific QA and complete figures.
2. Implement actual semantic Beamer tagging and bounding-box extraction with real two-pass compilation.
3. Create TTS alignment from **actual** speech and render non-occluding timed emphasis linked to the anchored slide regions.
4. Enforce final recorded MP4 durations strictly <630 seconds and coherent multipart intros/outros.
5. Safe source-adjacent, nonoverwriting publication in `G:\My Drive\Projects\Thomas_calculus_13ed` after staging/acceptance on HP, Yoga6 and Dell-115.

The shared production checkout and prior generated teaching material remain untouched.
