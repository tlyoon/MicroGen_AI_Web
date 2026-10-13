# MicroGen_AI_Web — Integrated Multidisciplinary Lecture-Generation Blueprint v1

**Date:** 13 October 2026  
**Status:** Architectural specification / implementation proposal; not a deployed feature or end-to-end certification.  
**Repository:** `tlyoon/MicroGen_AI_Web` only; do not change `tlyoon/MicroGen_AI`.  
**Decision:** Build one discipline-independent generation engine with optional, versioned discipline-specific teaching and validation profiles. Develop incrementally on the existing package; do not start the controlled lecture-generation pilot until its entry gates are met.

## 1. Mission, scope and invariants

Transform each textbook `source.pdf` into a coherent, source-faithful **series of narrated, visually synchronized video lessons**, rather than assuming one PDF produces one uninterrupted MP4. Design and validate the series **before** producing slides, scripts, TTS or videos. Preserve existing strengths (Selenium/Flash and optional API transport, figures, Beamer, recovery, FFmpeg and distributed workers); replace incompatible contracts only behind migration gates.

Non-negotiable invariants:

1. The original `source.pdf` is immutable. The independently specified PDF source tree and cloned code tree must not be confused.
2. Every resulting MP4 targets **8–9 minutes**; aim to stay **at or below 600 s**. The narrowly tolerated overshoot is **strictly less than 630 s**. `duration_s >= 630` fails acceptance. This is a final hard guard, *not* the mechanism for deciding how to split lessons.
3. The number of video parts, concept assignments, opening/closing bridges, and per-part narration and figure budgets are determined **top down before generation**. Do not generate a long MP4 and cut it afterwards.
4. Source content, figure panels/captions, scientific notation, facts and qualifications remain faithful. Never achieve a short duration by silently deleting required learning content or accelerating speech unnaturally.
5. Slide elements and spoken meaning are linked by durable semantic IDs **before TTS**. Highlight timestamps come from observed/generated speech timing or verified alignment, **not** guessed from word counts.
6. Each video must clearly identify `Part i of N`, explain its role in the subchapter, and provide a concise appropriate opening/ending bridge; Part 1 has no fictional previous episode and Part N promises no nonexistent next episode.
7. No MP4 receives a `passed` receipt just because it exists, plays, or fits the duration cap. Completeness, scientific/discipline fidelity, figure fidelity, legibility, speech fidelity, temporal alignment and encoding must pass their own gates.
8. A changed source, plan, slide, script, TTS or timing map invalidates affected dependent receipts. Atomic publication must not erase previously verified assets or publish partial work.
9. Uncertain learning meaning or mapping requires `review_required`, not a guessed automatic success. Bounded retry and deterministic evidence are mandatory.
10. All profiles and settings are configurable; the new Thomas Calculus source directory is an **acceptance-test configuration**, never a hard-coded source root for the package.

## 2. Known baseline and explicitly unimplemented capabilities

As inspected on 13 October 2026, `selenium_pipeline/runner.py` and `three_pc_worker.py` expose the legacy sequence:

`figures → slides → narration → script_qa → tts → tts_qa → video`

`runner.py` currently publishes a single `slides.mp4` and `script.txt` per subchapter. `output_paths.py` already enforces a separate local source root, verifies source placement/writability and provides source-adjacent publication. `video_ffmpeg.py` provides MP4 assembly and watchdogs. `slide_narration_sync.py` and related components implement part of the hash-based sync contract. `communication_policy.py` defines Selenium/API/fallback modes. The current narration prompt `selenium_pipeline/vendor_template_v2/gen_script_prompt_v10.txt` starts “You are an expert physics tutor”; this must be removed from the discipline-independent base and replaced by profile-controlled instructions.

Existing Figure RFH work is to be *reused and reconciled, not lost*: PR #56 (multipart figure mapping), PR #57 (Beamer bounds) and the stacked PR #58 (wide-figure legibility) were **open, draft and not merged** when this blueprint was authored. Other recent `main` changes may modify their integration points; rebase and test separately. Previous slide-only or audio-only successes are **not** evidence that lesson-series planning, discipline independence or synchronized highlighting already works.

This document does **not** implement those capabilities. It defines the contracts, migration order and acceptance evidence required to implement them safely.

## 3. Architectural flow: one master plan, many verified parts

`source.pdf + source hash`
→ `source inventory & page/figure/caption/structure provenance`
→ `subject identification + optional operator override + profile validation`
→ `learning-outcome/required-content coverage graph`
→ `master lesson plan (concept order + duration estimates + part boundaries)`
→ `per-part joint storyboard (slides + narration segments + stable visual anchors)`
→ `figures/layout/semantic + discipline quality gates`
→ `spoken script/TTS + actual timing/alignment receipts`
→ `highlight timeline + audiovisual composition`
→ `ffprobe and scientific/visual/synchronization acceptance`
→ `atomic source-adjacent publication, manifest and recovery checkpoints`.

Feedback paths must return to the **earliest affected stage**: a wrong factual claim goes back to content/storyboard planning; tiny figures to slide composition; unaligned speech to alignment/TTS; excessive actual running time to narration/part planning; encoding errors to video composition. Any repair propagates hash-based invalidation to its true dependents.

### Separation of responsibilities

| Component (proposed contract) | Inputs | Outputs / acceptance |
|---|---|---|
| `source_inventory` | immutable source PDF | page/section hierarchy, image-panel and caption provenance, source hashes |
| `subject_profiles` | source hints, operator profile choice | resolved profile ID/version, domain vocabulary and validators, confidence/review |
| `lesson_planner` | inventory, source coverage graph, profile and duration budget | versioned `lesson_plan.json`; complete ordered series and concept allocation |
| `storyboard` | approved plan/part, visual assets | stable per-element visual IDs, slide and narration segment IDs, per-part time budget |
| `slides/figure gates` | storyboard, mapping and dimensions | readable Beamer/PDF, two-pass checks, region geometry and source-fidelity reports |
| `narration/speech` | approved storyboard and per-part slides | exact speech-ready segments linked to visual IDs; verified audio and voice profile |
| `alignment/highlight` | segment IDs, audio time bounds, slide geometry | validated non-overlapping highlight events and timing receipt |
| `video_compositor` | slides, final WAVs, events, intro/outro | per-part MP4, audio/video timing and duration probe |
| `release/worker` | all QA receipts and dependency hashes | immutable success manifest, source-adjacent atomic publish, ownership/rollback |

Use module adapters and schemas around the current vendor scripts rather than replacing all core processing simultaneously.

## 4. Multidisciplinary teaching profiles (new requirement)

The shared engine must not contain a hard-coded “physics tutor” persona or assume all diagrams are graphs and all explanations are mathematical. Subject detection may suggest a profile, but a low-confidence result or genuinely interdisciplinary topic must request review or use explicitly approved multiple profiles, never silently guess.

Define a **versioned profile registry**, loaded by the planner and each relevant QA stage. Profiles contain teaching style, content types, terminology/pronunciation hints, approved visual treatments, source-fidelity tests, and structured feedback rules. A `general` base remains neutral; discipline-specific rules extend it. Support user-configured custom profiles without editing core engine code.

| Profile | Teaching emphases | Specific fidelity / highlighting checks |
|---|---|---|
| `physics` | concepts, equations, graphs, measurements, experiments, units | variable meanings, dimensions, signs/units, axis annotations; highlight derivation steps/graph regions |
| `mathematics` | definitions, proofs, counterexamples, ordered algebraic steps | exact symbols and hypotheses, no invalid logical step; highlight a whole equation line or proof step |
| `chemistry` | molecules, structures, stoichiometry, reactions, conditions, laboratory interpretation | atom/charge conservation when applicable, subscripts/superscripts, stereochemistry, apparatus/safety context; highlight correct species or reaction arrow |
| `biology` | structures/functions, systems, microscopy, physiology and processes | correct labels and sequence/causal relationships, scale and biological classification; highlight named diagram region/process stage |
| `history` | chronology, geography, primary and secondary sources, causes/consequences and interpretation | date/order/attribution checks, distinction between evidence and inference, avoid invented quotations or falsely resolved debates; highlight timeline events, map regions and relevant text |
| `general / interdisciplinary` | readable explanations anchored in source | activate only the validators relevant to detected content; no unjustified subject-specific assumptions |

Rules: (a) **The textbook remains the primary content source**; optional external checking must be separately authorized and attributed in internal review records, (b) a subject profile cannot override source facts, (c) internally retain exact supporting source locations/figure hashes; suppress provenance artifacts from student-facing narration/slides only, (d) profile choice, version and overrides are recorded in the plan and release manifest. A profile may flag a high-stakes topic for review.

The profile schema should expose `id`, `version`, `supported_content_types`, `pedagogy_rules`, `narration_rules`, `tts_lexicon`, `visual_alignment_rules`, `validators` and `review_policy`. A profile without testable validators must not be advertised as quality-equivalent to validated profiles.

## 5. Master lesson planning and the 10-minute rule

The planner first inventories **all required learning objectives and major concepts** of the full subchapter and establishes a traceable `source_coverage_map`. **Source scope must be preserved through prompt generation:** carry both excluded PDF pages with reasons and reviewer instructions for within-page section boundaries into every source-grounded authoring brief. A textbook PDF may begin halfway through the preceding section or finish with a separate exercise bank; treating every paragraph of an included page as lesson material can contaminate the lecture. Full containment cannot be proven from page numbers alone: retain section-heading/region provenance as a future structured source-inventory requirement, and treat unresolved within-page boundaries as review-required. It estimates speech time from planned segment word counts and calibrated voice/subject speech rate, plus realistic pauses, demonstrations and continuity slides. Estimates are revisited *during storyboard generation*, before expensive TTS work; they are not treated as exact audio measurements.

**Default budget policy** (version and overrides recorded): target 480–540 s per part; prefer ≤600 s; absolute acceptance strictly <630 s. Reserve a margin for model/TTS variability, slide timing and opening/closing. Use soft bounds to prompt early replanning; use the 630-s hard bound for final release only. The final clip is always measured with `ffprobe` against actual media, including silence and transitions.

Segmentation is **pedagogical**, not arithmetic video cutting:
- Select natural concept boundaries and preserve complete explanations, figures, examples and derivations within one part when feasible.
- Balance parts rather than producing a 9-minute part followed by a 90-second stranded conclusion.
- A source estimated at ~34 min should usually yield ~4 parts around 8–9 min.
- A source estimated at ~22 min **cannot** fit unchanged into two ≤10-min videos. It may be purposefully condensed into two only after a coverage and quality review establishes that no required material is lost and each part stays under the hard cap; otherwise choose three shorter parts.
- More parts are valid when material is dense or formula/process explanations cannot reasonably be abbreviated.
- No plan is valid without a declared rationale for boundaries, a per-part budget including intros/outros, and complete coverage accounting.

For every part require `part_index`, `part_count`, ordered concept IDs, source-page/figure references, learning outcomes, planned narration and pause budgets, transition text intent, expected number of slides, and estimated duration range. Re-plan **upstream** if any downstream stage threatens the budget; never split a finished MP4, drop its middle or increase speech speed to fit.

## 6. Series continuity and output contract

Every part has a brief opening slide announcing the exact subchapter title and **Part i of N**, its learning objective and, for i>1, a correct short bridge from the previous lesson. Every nonfinal part has a concise concluding review and a grounded preview of the next part. Final parts summarize the whole set without referring to nonexistent future parts. Storyboards, script and final MP4 must agree on labels and transitions. These speeches count toward runtime.

**Selected acceptance source root (current Thomas tests):**

`G:\My Drive\Projects\Thomas_calculus_13ed`

It is the Google Drive-synced copy whose folder ID is `1OvBx-Ryg5f3Pe9iE1CTbcBmfysqXcQQZ`, available on HP, Yoga6 and Dell-115 during the initial path checks. The **old** Thomas 2.2 folder `1zmVR3Zx5iLWeIOn-_7MfhaO7JvPuImko` remains read-only reference material for comparison; it is not the new generation destination. The cloned package is elsewhere, e.g. `G:\My Drive\Projects\MicroGen_AI_Web` for production or isolated `C:\` clones for development. Zenbook is **not** a planned active worker without an explicit new instruction.

Illustrative *future* generated layout (do not create it simply by approving this document):

~~~text
<source_root>/<chapter>/<subchapter>/
  source.pdf                       # immutable
  source_inventory.json            # source references and hashes
  lesson_plan.json                 # shared series master plan, subject profile + budgets
  series_manifest.json             # per-part receipt hashes and state
  part_01/
    slides.tex
    slides.pdf
    script.txt
    storyboard.json
    speech_segments.json
    alignment.json
    highlight_events.json
    slide_images/
    wav/
    part_01.mp4
    qa/
  part_02/...
~~~

Artifacts for different parts **must not** collide with legacy `slides.pdf`, `script.txt` and `slides.mp4` in the subchapter root. Preserve existing source-adjacent verified outputs in place or separately archived with hash receipts; never destructively migrate them without explicit release procedure. Actual temporary workspaces should be isolated from synchronized Drive until atomic publication.

## 7. Joint slide–narration storyboard and visual anchors

Generate slides and narration as **two renderings of one reviewed storyboard**, not two unrelated prompts. Each pedagogically meaningful element carries a stable ID: e.g. `part02.slide05.eq03`, `part02.slide05.bullet02`, `part01.slide04.figure10.panel_b`. Each narration segment references one or more of these IDs and the source concept ID(s). The figure registry records whole-figure/lettered subpanel relationships, caption association and immutable source provenance.

Anchor extraction must be deterministic: use Beamer source annotations or equivalent layout instrumentation to connect IDs to rendered PDF/page pixel coordinates, accounting for scaling, crop boxes, coordinate transforms, font and page-size differences. Mapping based on OCR alone or guessed nearest words is **not** a release-quality substitute. Support bounding regions for multi-line equations, diagrams and multiple subregions; a full-page highlight is not an acceptable workaround for unresolved targeted mapping.

Preserve original academic meaning and mathematical/chemical notation. If an element cannot be mapped unambiguously, classify `review_required` and repair source-level markup or storyboard rather than place a misleading highlight.

## 8. Timing: audio-first synchronization, not guessed highlights

Write speech as *short, semantically coherent chunks* attached to visual IDs. Speech text is plain spoken language but must preserve a link to the academic source and original on-screen notation. Prefer consistent-voice TTS with provider timing metadata if available and demonstrably trustworthy; otherwise produce independently timestamped segments or use a tested offline forced-aligner against the **actual final speech**.

Create a **monotonic media timeline**:
- For each event: `part_id`, `slide_id`, `element_id(s)`, `speech_segment_id`, `t_start_ms`, `t_end_ms`, `timing_method`, `confidence` and upstream hashes.
- Timings must refer to the exact WAV used in the released MP4; include per-segment offsets, silence, intro/outro and slide-transition durations.
- Use subtle non-occluding outlines/translucent emphasis; no flashing, clipping or text obstruction, and avoid highlighting the wrong object merely to have an animation.
- Target a median audiovisual emphasis onset error ≤250 ms and ≥95% of manually sampled events within 500 ms, calibrated separately across disciplines; these are **proposed acceptance targets**, not an existing guarantee.
- Unsupported/ambiguous timestamps, unmapped elements or excessive alignment drift **block synchronized-highlight acceptance**. Optionally export a clearly marked review-only static preview, never claim it meets the new highlighting standard.
- The compositor may create highlights using deterministic FFmpeg overlays or timed pre-rendered assets **after the semantic links are planned upstream**. That is rendering, not forbidden post-hoc lesson splitting.

For mathematics/chemistry, verbalized formulas rarely have a one-to-one textual match with notation; do not depend on raw transcript word matching. For biology/history, named diagram regions/timeline events must be mapped using source-verified IDs. Re-render video when only styles change; redo alignment when speech timing changes; redo storyboard when the actual meaning-to-element relationship changes.

## 9. Validation and fail-closed release gates

Every series/part receives explicit `planned`, `running`, `blocked`, `review_required`, `passed` or `published` state with reason codes and hashes. A successful exit code is not a `passed` gate.

| Gate | Automated requirements | Separate human/semantic review where needed |
|---|---|---|
| Input | writable source-adjacent destination; immutable SHA; authorized profile; no traversal | confirm source scope and discipline selection |
| Plan | ordered, non-overlapping parts; all required concept IDs allocated; duration budgets; correct Part i/N bridges | pedagogical boundaries and completeness |
| Figures | correct caption/panel graph, source hash; no destructive rename, missing panel or page clipping | visually confirm composites and specialized diagrams |
| Slides | LaTeX compiles twice; page numbers/page count, bounding boxes, readable text and correct element anchors | legibility and scientific accuracy |
| Narration | linked to correct visual IDs; no invented claims; stage-specific transcript and number alignment | semantic completeness and terminology |
| TTS | same verified voice; audio durations, script/phonetics risk tests and hashes | sample variables, chemical names, technical vocabulary |
| Highlight | every required event mapped to real visual bounds and final audio, monotonic/no out-of-range timestamps | sample correct object selection and actual synchronization |
| MP4 | ffprobe audio/video streams, decode sampling, audio end/slide end consistency, final duration <630 s | meaningful continuity and absence of distracting effects |
| Series | Part numbers/titles/order/coverage and source hashes consistent; no missing/duplicated part | coherent whole-subchapter learning experience |

Track review metrics across subject profiles rather than claiming “equally good” by analogy from physics. Use at least one representative **source-authorized** sample each from mathematics, physics, chemistry, biology and history with discipline-specific expert review before claiming comparable quality. Calibration and thresholds must be published with test evidence; do not invent benchmark scores. Confirm any domain requiring special caution (e.g. lab safety, medical statements, historical contested claims) with appropriate source-aware review.

Final duration validation must use actual media output, not the `[NN sec]` header or WAV sum alone. At or above 630 seconds: **no publish**; return a versioned duration error to the storyboard/lesson planner, preserving all currently approved source and intermediate assets where safe.

## 10. State, dependency graph, migrations and recovery

Proposed new DAG:

`ingest → subject_profile → source_inventory → lesson_plan → storyboard(part) → figures/slide_assets → slides(part) → narration_segments(part) → script_qa → tts(part) → alignment(part) → highlight_render(part) → video(part) → part_qa → series_qa → publish`.

A complete step records input and output hashes, schema version, profile ID/version, model/voice, command/software versions, worker identity, timestamps and acceptance reasons in a receipt. A retry is valid only if all upstream hashes still match. Dependency invalidation examples:

- Source/profile/learning-objective change: invalidate planning and every dependent part.
- Plan/part boundary/part count change: invalidate all affected storyboards and their downstream outputs; regenerate intros/outros referencing Part i/N as necessary.
- Figure crop or slide layout change: invalidate its slides, geometry anchors, semantic alignment, narration if page/content count changes, and subsequent media.
- Narration/speech text change: invalidate its WAV, alignment, highlights and video; preserve verified unaffected parts.
- WAV/audio duration or voice change: invalidate alignment, highlight timeline and MP4 but not scientifically correct slides.
- Highlight color/position-only change: re-render overlay and MP4; preserve exact narration and audio where hashes prove identity.
- FFmpeg output error: retry video composition only if source hashes and timing remain valid.

Introduce a migration flag (suggested `MICROGEN_LESSON_MODE=legacy|series`; **not currently implemented**). Keep `legacy` as default until schema, stage and pilot gates pass, then change the default only in a reviewed release. Legacy files/receipts cannot be silently promoted to the new `series` format. Existing stage checkpoint semantics and rollback must be maintained.

## 11. Three-PC operations and safe generation workspace

Source content resides under the selected root `G:\My Drive\Projects\Thomas_calculus_13ed` on HP, Yoga6 and Dell-115; the same Google Drive-synced directory may appear on multiple computers. The Drive web folder link is a **reference**, not a local path accepted by `MICROGEN_SOURCE_ROOT`. The designated machine-local path must be resolved and checked on every worker at job admission. Keep authentication secrets under authorized per-user AppData configuration and out of Git.

Enforce ownership at the **subchapter/part and stage** level through a centrally auditable lease/manifest, not just per-PC locks. Two PCs must never simultaneously write to the same shared output part or its series plan. Acquire safe exclusive leases with expiration/heartbeats and conservative stale-lock recovery; reconcile Drive sync latency before promoting results. Use immutable input hashes, isolated PC-local temporary workspaces, atomic local-to-Drive publication and readback/hash verification. Resume/checkpoint without rerunning passed parts, protect known-good MP4s and do not launch broad textbook campaigns while release gates remain open.

## 12. Implementation plan, dependencies and objective exit criteria

| Phase | Deliverable | Minimum exit evidence |
|---|---|---|
| **0 — Blueprint approval (this document)** | Invariants, contracts, profile registry, budgets, stage DAG and migration plan | reviewed repository document; current-baseline and gap table; no runtime behavior change |
| **1 — Schemas and source/profile inventory** | versioned JSON schemas, neutral profile base plus physics/math/chemistry/biology/history plugins | schema round-trip and invalid-input tests; sample fixtures for each profile |
| **2 — Top-down duration-constrained planner** | master coverage map, concept-aware series segmentation, continuity budget | fixtures for 8, 22, 34 min; verify natural boundaries/coverage, 22 min not falsely fitted into two unchanged parts; all estimated budgets |
| **3 — Joint storyboard and asset mapping** | source/figure/panel/slide/narration stable IDs; RFH #56/#57/#58 reconciled | Thomas 2.2 multi-panel visible/readable; math/chem/biology/history element mapping fixtures; two-pass compile |
| **4 — Speech, alignment and highlights** | segment-level TTS, stable voice, timestamps, visual anchors, highlight timeline and renderer | deterministic injected timing faults, test equation and panel overlays, sampled audio-visual error audit |
| **5 — Part-series MP4 and gate integration** | per-part FFmpeg assembly, continuity, hard duration verifier, receipts and recovery | <630-s probe for every MP4, deliberate 630-s rejection, no post-hoc splitting and no false completion |
| **6 — Multi-profile educational evaluation** | subject-aware source/visual/narration QA harness | expert-reviewed representative physics, math, chemistry, biology, history sets; recorded deficits and repairs |
| **7 — Three-PC staged pilot/deployment** | isolated Thomas 2.2 end-to-end pilot, genuinely long subchapter multipart pilot, then controlled 3-PC rollout | full Windows/Ubuntu CI, all three PC-local focused suites, actual MP4 and highlight inspection, hash/readback and rollback proof |

Do **not** label phase 0 completion as phases 1–7 completion. Each phase requires code tests on a clean branch, CI and a reviewable acceptance report before merge. Gate failures must trigger the smallest valid upstream redesign; no “proceed anyway” default.

## 13. Acceptance scenarios and failure injection backlog

1. **Thomas 2.2:** all Figure 2.10 panels and letters survive, no clipped/tiny half-column; exact per-slide scientific narration and TTS; source root is the new Thomas copy, not the old reference folder.
2. **22-minute scenario:** no unchanged 2×10-minute fiction; produce three parts, or demonstrably valid/approved two-part editorial condensation with all content accounted for; each MP4 independently passes.
3. **34-minute scenario:** plan ~4 natural parts around 8–9 minutes **before** generating slides; Part i/N intro/outro text consistent.
4. **629.9 versus 630.0 seconds:** acceptance only below 630.0; FFprobe tested including outro/silence.
5. **Math equation narration:** correct variable pronunciation and highlight of *the intended derivation line*, not nearest unrelated formula.
6. **Chemistry reaction:** subscripts and reaction conditions preserved; highlight actual reactant/product/arrow being discussed; balancing/checks where applicable.
7. **Biology process:** all labels/panels preserved and correct stage highlighted in process sequence.
8. **History timeline:** chronology and attribution retained, event/map location highlighted when spoken; no fabricated quotations.
9. **Figure repair shifts page count:** dependent narration/TTS/alignment/video fail closed and regenerate in correct order.
10. **TTS time shift without text change:** reject stale alignment receipt; keep verified slides and narration.
11. **Duplicate multi-PC claim, Drive sync conflict, worker death, interrupted FFmpeg:** no double publish, lock failure handled, old output retained.
12. **Low-confidence subject detection / misleading script-to-element match:** review-required; no automatic false certificate.

## 14. Open engineering decisions to settle before implementing Phase 1

- Choose the versioned JSON Schema/tooling and minimal record requirements for `source_inventory`, `lesson_plan`, `storyboard`, `alignment`, `part_manifest` and `series_manifest`.
- Select a reliable element-ID-to-PDF-coordinate instrumentation strategy (Beamer macro/export, tagged PDF or equivalent), including image subregions, and a way to QA it across slide themes.
- Benchmark actual TTS speech segmentation/forced alignment on mathematics and chemical terminology; determine confidence/error thresholds from evidence, not assumptions.
- Define canonical voice, narration speed and safe source-grounded editorial condensation policy; the hard <630-s cap remains invariant.
- Decide how custom/interdisciplinary profiles are approved and which subject experts review them.
- Resolve branch/PR integration order for unmerged figure-guard work and newer main commits without overwriting shared uncommitted code.
- Define production-grade cross-PC distributed locks suited to Google Drive sync semantics; do not rely on stale directory presence alone.

## 15. Definition of a successful pilot

A pilot is **not** successful until it can show: (a) immutable correct source and chosen subject profile, (b) approved comprehensive top-down part plan before generation, (c) complete traceable concept/figure coverage, (d) readable factual/scientific slide/voice alignment, (e) real synchronized on-screen emphasis of the narrated element, (f) each final MP4 **strictly <630 s** with appropriate Part i/N links, (g) no hidden overwrite and full source-adjacent hashed publication, and (h) reproducible acceptance/audit receipts. Test the Thomas 2.2 defect and at least one naturally longer subchapter. Only after this controlled evidence can a broad three-PC generation campaign be considered.

---

**Design record:** This document integrates the original reliability/fidelity hardening programme with the newly accepted user requirements: top-down planned ≤10-minute series with <30-second tolerance, serial continuity, speech-synchronized visual highlighting, and **multidisciplinary subject-aware teaching/QA**. It is the proposed **design authority for the next implementation**, not a claim that the current code already supplies those capabilities.
