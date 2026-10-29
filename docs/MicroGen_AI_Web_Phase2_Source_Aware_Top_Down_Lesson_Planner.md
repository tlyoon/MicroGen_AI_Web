> **SUPERSEDED FOR NORMATIVE USE — 18 October 2026:** This historical design contains obsolete 600–630-second allowances. Every published MP4 must be **strictly less than 600 seconds, with no exception**. See [the effective contract](EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md). Retained below for historical traceability, not as live authorization.

# MicroGen_AI_Web — Phase 2 source-aware top-down lesson planner

**Date:** 13 October 2026
**Scope:** `tlyoon/MicroGen_AI_Web`, guided by the [Integrated Architecture Blueprint v1](MicroGen_AI_Web_Integrated_Architecture_and_Implementation_Blueprint_v1.md).
**Status:** Standalone pre-generation tools and offline QA. **Not yet wired into the legacy runner; no end-to-end MP4 generation.**

## What this phase implements

1. Read the **operator-selected** source `source.pdf` without changes; record an SHA-256-linked, per-page evidence scan.
2. Produce an explicitly **unreviewed** page-level concept-outline scaffold. A page placeholder is **not** a vetted topic, and PDF text may miss figures, mathematics and captions.
3. Require source-grounded concepts, accurate page scope, ordered prerequisites, reviewed teaching durations and natural boundaries before generating a master lesson plan.
4. Use an order-preserving dynamic-programming partitioner to assign complete concepts to coherent video parts **before** slide/narration/TTS/MP4 work begins.
5. Produce a versioned `lesson_plan.json` with unique Part i/N titles, intros/outros, source pages, complete concept allocation, estimated durations and slide budgets.
6. Keep physics/mathematics as first-class development profiles; future user-supplied domain profiles use the same planner interface without core modifications.

## Controlled usage — review artifacts outside shared production source tree

Example from the clean development checkout:

~~~powershell
$root = 'G:\My Drive\Projects\Thomas_calculus_13ed'
$pdf = "$root\2\2.2\source.pdf"
$review = 'C:\MicroGen_Phase2Evidence_20261013'
New-Item -ItemType Directory -Force $review | Out-Null

python -m selenium_pipeline.planning scan --source-root $root --source-pdf $pdf --out "$review\Thomas_2_2_source_scan.json"
python -m selenium_pipeline.planning draft --source-root $root --source-pdf $pdf --domain mathematics --out "$review\Thomas_2_2_outline_UNREVIEWED.json"
~~~

The draft **cannot pass** the actual planner gate. Review it manually or with a separately audited domain-aware content analyzer, identify the true textbook subsection scope, remove preceding exercises or unrelated material with explicit page-exclusion reasons, replace page placeholders with complete pedagogical concepts, verify all equations/figures/captions, set realistic speech budgets, and attest review.

Then, after actual review and explicit approval:

~~~powershell
python -m selenium_pipeline.planning plan --source-root 'G:\My Drive\Projects\Thomas_calculus_13ed' --source-pdf 'G:\My Drive\Projects\Thomas_calculus_13ed\2\2.2\source.pdf' --domain mathematics --outline 'C:\MicroGen_Phase2Evidence_20261013\Thomas_2_2_outline_REVIEWED.json' --out 'C:\MicroGen_Phase2Evidence_20261013\Thomas_2_2_lesson_plan.json'
~~~

This does not invoke Gemini, TTS, FFmpeg or actual slide generation. New JSON outputs are created with **no-overwrite** semantics. The PDF is never modified.

## Source evidence, approval and schemas

New schemas `schemas/source_scan.schema.json` and `schemas/concept_outline.schema.json` extend Phase 1's six structural schemas. The concept outline declares `source_sha256`, domain ID/version, all included/excluded pages with reasons, and for every concept: ID/title/pages, evidence, estimated duration, prerequisites, boundary choice (`preferred` / `allowed` / `forbidden`), and slide count.

- `text` evidence must occur on the cited PDF page.
- `visual_reviewed` evidence requires a meaningful manually verified figure/region description and a matching source page. This is a **review attestation**, not automated visual proof.
- `visual_unreviewed` may appear in an unreviewed draft but cannot be accepted for planning.
- The planner requires `approval.status="approved"`, a reviewer identity and an explanatory coverage note. It rejects missing approval, stale source hash, missing/overlapping source-page scope, invalid excerpt, unsupported pages, unknown/forward prerequisite, duplicated concepts and missing instructional coverage according to the *reviewed concept catalog*. Expert scientific and visual source-quality review remains necessary.

## Duration planning assumptions

The dynamic program assigns every reviewed concept exactly once, preserving source/content ordering and forbidding an unauthorized cut inside a concept. It balances estimated per-part duration and prefers reviewed natural topic boundaries. It may fail if an indivisible concept is too long, in which case instructional planning must be revised upstream.

| Constraint | Provisional default |
|---|---:|
| Target expected part duration | 510 seconds (~8.5 minutes) |
| Intro/outro + transition allowance | 24 seconds per part |
| Spoken share of transition allowance | 18 seconds |
| Estimated upper-bound multiplier | 1.05 |
| Maximum planned upper estimate | 600 seconds |
| Later hard cap on actual MP4 (FFprobe) | **strictly below 630 seconds** |

A 22-minute conceptual outline generates 3 shorter parts rather than incorrectly forcing 22 minutes into two <=10-minute videos. A 34-minute outline can generate four balanced parts. Condensation to fewer parts is allowed **only through a properly reviewed revised lesson/content plan**, never by cutting a finished MP4, discarding material or unnaturally accelerating speech.

**The 5% margin is an uncalibrated planning heuristic, not proof of future TTS timing.** Actual narration, pauses, introductions, slide transitions and final MP4 duration must be measured and enforced at downstream QA; any real video at or above 630 s will fail release.

## Observed Thomas Calculus 2.2 evidence and release boundary

The new source root is `G:\My Drive\Projects\Thomas_calculus_13ed` (Drive folder `1OvBx-Ryg5f3Pe9iE1CTbcBmfysqXcQQZ`), separate from both the code repository and the earlier Thomas 2.2 comparison folder.

Read-only scan on Dell-115 confirmed `2\2.2\source.pdf`: 11 pages, 26,896 normalized extracted characters, and no low-text warning. The scan was saved **outside** the shared source directory at `C:\MicroGen_Phase2Evidence_20261013\Thomas_2_2_source_scan.json`, with `coverage_status="unreviewed"`. No approved Thomas outline, Gemini generation, slides, TTS or MP4 results are claimed.

Offline tests cover unreviewed-draft blocking, 22→3 and 34→4 splitting, natural boundaries, source hashes/evidence, page scope, prerequisites, continuity, schemas, CLI refusal to overwrite and unsplittable concepts.

Still required in future phases: domain-aware semantic concept extraction with true scientific review; complete figure/caption audit; linked slide/narration storyboards; TTS timing calibration; semantic-to-geometry highlighting; FFprobe final-runtime and series gates; and safe three-PC source-adjacent publication. Legacy `runner.py` is deliberately unchanged. No broader lecture-generation pilot has started.
