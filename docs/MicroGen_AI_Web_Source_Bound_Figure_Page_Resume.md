# MicroGen source-bound figure mapping page checkpoints

## Purpose

An isolated Thomas Calculus §2.2 test on Yoga 6 mapped figures through PDF page 8, then spent repeated Gemini requests on page 9 (exercise bank) and failed safely after three timeouts. Restarting from page 1 would waste requests and risk collisions.

This module saves a **per-page checkpoint only after a fully validated page mapping** has been published to the isolated work root. Each receipt is pinned to the actual original `source.pdf` SHA-256, rendered page PNG SHA-256, exact Gemini mapping file SHA-256, transport success record SHA-256, every original `fig_N.png` crop SHA-256 and its identically copied mapped target. When source-work figures are published to the work root, their bytes must match too. The status is `validated_source_mapping_not_visual_approval`—no scientific or artistic judgment is inferred.

**Composite safety:** The legacy mapper's post-run `merge_lettered_figs_v3.main([])` call was removed. Filename-based horizontal merges lack source-space panel geometry and can silently corrupt scientific layouts. Original lettered crops stay separate; a complete parent figure must come from the original source or a separately reviewed reconstruction.

The mapper checks every receipt before contacting Gemini. If source/page/crop/mapping/transport/target contents do not match, or no completed receipt exists, it reruns normal mapping. Empty-crop pages require no Gemini call and are not checkpointed. A partial failure does not create a valid checkpoint.

## One-time adoption for the preexisting pilot

The mapping run that exposed this problem predates the checkpoint feature. On its **disposable isolated workspace only**, a developer may explicitly adopt previously mapped pages by calling:

```python
from selenium_pipeline.figure_mapping_checkpoints import save_checkpoint
from pathlib import Path
work = Path(r"C:\MicroGen_Phase5_YogaPilot_Work_20261014\2\2.2")
for page in [1, 2, 3, 6, 7, 8]:
    save_checkpoint(work, page, copy_to_root=True)
```

Adoption verifies that the original crops are byte-identical to all mapped images, that the published work-root copies are identical, that the mapping files are well formed and unambiguous, and that the recorded transport for that page was completed. **It cannot retroactively prove that the old Gemini caption attribution was scientifically correct.** Figure 2.10(a,b,c) had an additional visual inspection and was confirmed intact as a single complete composite.

Never adopt failed page 9, modify the shared source PDF, alter old captions to satisfy hashes, or label a preview as approved source teaching material.

## Validation

`tests/test_figure_mapping_checkpoints.py` covers changed source PDF, changed rendered page, changed caption map, added crop, modified mapped target, published root conflict, malformed mapping, failed Gemini transport, optional no-publication mode and invalid page numbers. Other figure composite QA remains in force. The intended benefit is an **idempotent, fail-closed recovery path**, not increased blind retries.

The student-facing series continues to require approved mathematical coverage, complete figure-panel fidelity, accurate narration and video-duration acceptance before publication.
