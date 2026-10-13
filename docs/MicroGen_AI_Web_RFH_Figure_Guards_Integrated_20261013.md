# Integrated RFH figure safeguards — 13 October 2026

**Scope:** Consolidates previously independently tested, unmerged draft PRs #56, #57 and #58 on top of current MicroGen_AI_Web main, which already contains Phase 1, 2 and Phase 3A storyboard contracts. **No live Gemini/TTS/MP4 video campaign started.**

## Why this integration exists

The previously defective Thomas Calculus subchapter 2.2 slide 7 included `Figure 2.10.png`: a complete wide source figure with panels (a), (b), (c). The old half-width column let an unconstrained figure overflow and crop. Simply bounding that figure inside a narrow column made panels unreadable. Wrong figure panel naming/collisions can silently replace the source image. Three separate checks are required and must be combined into one tested pipeline.

## Changes integrated from original PRs

- **PR #56, Phase 3A mapping guard:** Canonicalize target figure filenames, reject duplicate/mislabeled whole/panel targets and existing conflicting destination contents; **no blind concatenation of parent and subpanel crops**. Guard is integrated in `vendor_template_v2/map_and_rename_selenium_v8.py`.
- **PR #57, Phase 3B bounding:** Automatically add `width` and `height` graphic constraints with `keepaspectratio` in `vendor_template_v2/gen_slides_selenium_v11.py` before compile, avoiding horizontal overflow.
- **PR #58, Phase 3C legibility:** After bounded placement, identify overly narrow wide figure layouts and reject candidates within bounded retries, requesting figure-focused full-width slides without deleting scientific content. Persist failed local candidates for review; do not publish a rejected `slides.tex`.

A new `tests/test_rfh_figure_pipeline_integration.py` verifies these gates together using a synthetic 784×234 wide composite. This is a **synthetic regression**, not publication of textbook images or proof of scientific accuracy.

## Important interface conflict for future series mode

The legacy figure-retry prompt may permit increasing slide count. The new Phase 3A storyboard gate **requires exact planned slide count** and its speech-to-visual IDs. Therefore:

1. When running in the **legacy mode**, existing vendor behavior and downstream content invalidation remain governed by the legacy runner; valid changed slides require rebuilt narration/TTS/video.
2. In the **future series mode**, a figure layout that needs an extra slide must return an upstream **replanning required** condition, revise the affected approved part storyboard, update semantic IDs, slide references, narration segments, audio alignment and derived hashes, **then** continue. It must **not** silently add slides behind the lesson plan.
3. Image width heuristics can only detect certain at-risk layouts. Neither the aspect-ratio check nor a clean compile proves all source panels, annotations or source figure labels survive. Expert source-based visual QA remains mandatory.

## Safe source, code and deployment boundaries

- Development runs use dedicated `C:\MicroGen_FigureIntegration_20261013` clone.
- New Thomas test source root is `G:\My Drive\Projects\Thomas_calculus_13ed` (Drive folder `1OvBx-Ryg5f3Pe9iE1CTbcBmfysqXcQQZ`); its `2\2.2\source.pdf` must remain immutable.
- The **old Thomas 2.2 Drive folder** remains a comparison reference, not a new output target.
- Shared production code clone `G:\My Drive\Projects\MicroGen_AI_Web` has older uncommitted edits; **do not reset, force pull or overwrite** before reconciling worker changes.
- Zenbook excluded from three-PC test campaigns unless explicitly reauthorized.

## Required acceptance

Run 13 multipart guard, 7 bounds, 11 legibility and 2 integrated synthetic tests; full historical regression suite on both GitHub Windows and Ubuntu; and pinned independent tests on Dell-115, HP and Yoga 6. Preserve existing production jobs, and do not claim live textbook-figure repair until the authorized isolated end-to-end pilot reproduces, corrects and visually verifies Thomas 2.2 Figure 2.10, including all three panels and new narration synchronization.

This integration should supersede the three earlier draft PRs only after the combined tests and reviewed merge into `main`.
