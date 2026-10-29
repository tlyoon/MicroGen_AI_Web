> **SUPERSEDED FOR NORMATIVE USE — 18 October 2026:** This historical design contains obsolete 600–630-second allowances. Every published MP4 must be **strictly less than 600 seconds, with no exception**. See [the effective contract](EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md). Retained below for historical traceability, not as live authorization.

# MicroGen AI Web — Integrated Multidisciplinary, Multipart Lecture and Synchronized Highlight Blueprint (RFH v2)

**Date:** 13 October 2026 (MYT)  
**Status:** Implementation blueprint / acceptance contract. **Not an implemented feature or production release.**  
**Applies to:** `tlyoon/MicroGen_AI_Web` only; do not modify the separate `tlyoon/MicroGen_AI` repository.  
**First acceptance subject:** Thomas' Calculus, 13th edition. Design must remain useful for physics, mathematics, chemistry, engineering, biology, and other textbook subjects.

## 1. Decision and release boundary

This v2 document extends [RFH v1](MicroGen_AI_Web_Reliability_Fidelity_Hardening_Programme_v1.md), rather than replacing its communication, figure, scientific speech, checkpoint and three-PC requirements. It adds:

1. A **top-down lesson and multipart plan**, decided before producing final slides, narration or videos.
2. **Actual-audio-timed visual highlighting** of the precise item being discussed, including equation terms and labelled diagram regions where source-grounded mapping is possible.
3. A **discipline-neutral lesson contract** instead of physics-specific narration assumptions.
4. A **part-level, hash-bound publication and recovery model** that retains existing verified work and never declares success from mere file existence.

**User-approved operating rules:** The ordinary target is **8–9 minutes per MP4**, every part should be **under 10:00**, and a *small, explicitly reviewable* exception below 10:30 may be tolerated. This exception is **not** a silent automatic pass. Do not cut a completed long MP4 arbitrarily to meet the target. Plan coherent chapters/parts upstream. The user explicitly requested visual highlights synchronized with **actual TTS timing**, not estimated narration length.

**Authorisation at this stage:** Complete and review the integrated blueprint first. No broad lecture campaign, production worker hot-swap, unreviewed merge of draft figure PRs, or uncontrolled live Gemini pilot is authorised by this document. Run offline/static verification during implementation; seek a controlled, source-authorized end-to-end pilot only after the prerequisite code and tests exist.

## 2. Existing architecture and incompatibilities

The current maintained `selenium_pipeline.runner` uses seven ordered stages:

`figures -> slides -> narration -> script_qa -> tts -> tts_qa -> video`

Existing primary output is `slides.mp4`, a **single video per subchapter**, generated from `slideN.pdf` / `slideN.wav`; `slide_narration_sync.py` binds slide/PDF/script/WAV hashes and counts but does **not** verify semantic matching or word-level audiovisual timing. `video_ffmpeg.py` provides resumable static-slide encoding, actual media-progress watchdogs, source-adjacent atomic publication and existing-output preservation. These are valuable foundations, **not** proof that multipart planning or synchronized highlighting already works.

The existing RFH figure PRs form separate, unmerged safety work:
- [#56](https://github.com/tlyoon/MicroGen_AI_Web/pull/56): fail-closed multipart figure mapping.
- [#57](https://github.com/tlyoon/MicroGen_AI_Web/pull/57): constrain Beamer figures to available column width.
- [#58](https://github.com/tlyoon/MicroGen_AI_Web/pull/58): reject potentially illegible wide figures and request full-width redesign; #58 is stacked on #57.

Do **not** mistake bounding a three-panel diagram into a half-column for legibility. All three panels and their caption associations must remain source-faithful and readable. Complete the relevant cross-platform, source-image, slide-screenshot and narration/video invalidation acceptance gates before those drafts are merged or deployed.

## 3. Portable directory, identity and ownership contract

The **code root** is the local, pinned Git checkout, separate from the **source root** holding `<chapter>/<subchapter>/source.pdf`. Resolve the source root explicitly per PC (`--source-root` / `MICROGEN_SOURCE_ROOT`), check readability and write permission, and never infer it from the code checkout. Output artifacts belong **beside the subchapter source PDF**; compute-heavy work, FFmpeg caching, transient renders, alignment and temporary files stay on a **machine-local** disk. Google Drive is an output and shared coordination location, not the FFmpeg working scratchpad.

Honor the user's single designated Thomas Calculus source/output tree on all authorised PCs. The former Thomas 2.2 test folders are historical reference material only; never use them as live production destinations. Use deterministic source hashes, a disjoint subchapter owner/lease across machines, and atomic publish operations. Credentials remain in user-local secret storage; neither secrets nor copyrighted textbook assets belong in the public repository.

### Proposed deliverables (not currently emitted)

```text
<source-root>/<chapter>/<subchapter>/
  source.pdf
  slides.tex                       # Full editable source, if a global deck is retained
  slides.pdf                       # Full slide deck / legacy compatibility artifact
  script.txt                       # Source-grounded original narration, immutable after approval
  figures...                       # Accepted, proven source-grounded figures
  lecture_plan.json                # Planned coherent part and scene boundaries
  lesson_manifest.json             # Source, discipline, version, approved dependency hashes
  part_01/
    part_plan.json                 # Learning objectives, continuity, scenes and duration budget
    slides.pdf                     # Exact slide pages for this part
    script.txt                     # Exact slide/scene narration for this part
    speech_ready.txt               # TTS-target text separate from scientific original
    narration_alignment.json       # Actual word/phrase times and mapped semantic targets
    visual_cues.json               # Targets, PDF coordinates/IDs, reveal/highlight times
    part_01.mp4                    # Verified, highlighted, narrated output
    part_receipt.json              # Hash, QA, timing, duration and version proof
  part_02/ ...
  lecture_completion.json          # References every accepted part receipt
  .microgen_work/                  # Managed, resumable staging metadata; not a success signal
```

The exact artifact names and directory layout are **proposed** and must be finalized with migration tests before production. Legacy complete `slides.mp4` and `.microgen_completion.json` must remain readable and untouched; older receipts cannot claim compliance with these **new** multipart/highlight gates without revalidation. Do not delete the global slide deck or original narration solely to introduce parts.

## 4. Subject-neutral instructional plan

Build an explicit, versioned **`DisciplineProfile`** with fields for subject, notation conventions, learning level, prerequisite assumptions, slide-layout needs, pronunciation rules, equation reading, acceptable illustration types, units, source citation style and pedagogical checks.

**Shared teaching behaviours:** State the goal, explain intuition, introduce definitions, develop ideas in an appropriate order, interpret equations in words, work through source-grounded examples, acknowledge common misunderstandings, conclude each part and connect it to the next. Keep the user's preference for simple, direct English. Do not pad with sweeping claims.

**Discipline-specific examples (profile-driven, not hard-coded as global rules):**
- **Calculus:** function notation, limits, continuity, derivative/integral interpretations, graphs, worked steps, domains and sign conventions.
- **Physics:** physical models, units, vector directions, experimental context and approximation limits.
- **Chemistry:** reactions, molecular notation, states, units and symbolic labels.
- **Biology:** mechanisms, diagrams, labels and careful distinction between observation and inference.
- **Engineering:** assumptions, constraints, failure modes and worked quantitative designs.

Profiles influence prompts and QA rules without changing the source-document fidelity requirement. A subject classifier can **suggest** a profile; uncertain classification must be explicitly configured or placed in `review_required`, not guessed. Calculus test materials must never receive physics-only prompts.

## 5. Top-down multipart planning before slide generation

### 5.1 Source and scene inventory

Parse the selected source PDF and accepted figure/caption inventory first. Create a source-grounded concept graph: ordered sections, definitions, propositions, displayed equations, worked examples, figures, panels and citations. Record page references and source hashes. Identify natural lesson boundaries before setting slide counts.

Define each **scene** as a teachable visual focus with one or more narration segments and explicit references to the source, slide elements and intended learning objective. Avoid breaking a definition from its explanation, separating a diagram from its reading, or splitting a multi-step calculation mid-step.

### 5.2 Duration allocation and boundaries

Generate a `lecture_plan.json` containing ordered **parts**, each with a topic title, source span, pedagogical objective, prerequisite/continuity note, ordered scenes, nominal narration-time budget, introduction, conclusion and transition. At planning time:
- **Preferred actual final duration:** 480–540 s per part (8–9 min).
- **Normal maximum:** actual MP4 duration **strictly < 600.0 s**.
- **Conditional narrow overshoot:** `600.0 <= duration < 630.0 s` may be retained **only as `review_required`**, with an explicit justification and user acceptance. It is never silently certified or queued as fully complete.
- **At or above 630.0 s:** **blocked**; rewrite/replan upstream and regenerate only impacted parts.
- Reserve time for part introductions, summaries, transitions and measured TTS drift. Do not use a nominal 600-second script target.
- For short subchapters, one coherent shorter part is valid; do not artificially stretch it.

Plan several parts **before** generating the first final slide so the sequence is globally coherent. Avoid splitting a finished long MP4 with `-ss`, `-t`, or mechanical equal-duration chopping as a substitute for intellectual partitioning. If true TTS duration exceeds the budget, revise script/scene boundaries and regenerate the affected part; preserve the source explanation, meanings and required figures.

### 5.3 Continuity across videos

Every part has a short, natural introduction saying what it covers and how it follows the previous part, and a short conclusion that closes the current concept and previews the next. Do not use a repeated generic opening or a cliffhanger in the middle of a derivation. The first part can introduce the entire subchapter; the last completes the subject.

## 6. Visual target identification and timing

### 6.1 Semantic element map

At slide creation, require every highlightable element to have a **stable target ID**, semantic type and verified location:
- slide title / heading / bullet / sentence span;
- displayed equation, selected equation term and worked calculation step;
- figure, caption, labelled subpanel `(a)/(b)/(c)`, labelled curve/axis or diagram region;
- tables, rows and source-authorised symbols.

Preferred mapping is from **structured Beamer/LaTeX source** to a generated slide element manifest plus verified PDF bounding boxes or named graphic anchors. For rasterized figures, accept explicit source-backed coordinates/regions only. Do not guess equation-term bounding boxes from raw rendered pixels and then assert certainty. If a needed label/region cannot be located confidently, request review or choose a safe full-element emphasis **only when it does not misrepresent what was said**.

### 6.2 Audio timing is authoritative

Preserve `script.txt` and create separate `speech_ready` text with an auditable transformation map. Synthesize final WAV first, including any selective TTS replacements. Derive a **time-stamped token/phrase sequence** from the final audio with a supported alignment method (for example verified TTS marks or forced alignment checked against the final speech). Never use raw character-count, equal-time, script-only predictions, or generic subtitle timestamps as a claimed exact audio alignment.

Link aligned speech spans to semantic target IDs, with timing offsets in seconds relative to the part. Enforce:
- ordered, nonnegative, monotonic onset/offset; `start < end`;
- `end <= measured final WAV duration` (allow only documented encoder tolerance);
- exact source-to-speech mapping for mathematical symbols, units and variable names, with ambiguity sent to review;
- no highlights of the next item while the current item is still being discussed;
- stable visual state during pauses and safe fade timing;
- missing targets, drift or low-confidence alignments = no false successful highlight receipt.

Structural slide/WAV count verification from `slide_narration_sync.py` stays required but is **insufficient** for synchronized highlight certification.

### 6.3 Visual rendering

Render a synchronized overlay/reveal track from `visual_cues.json` over the approved static slide images or a compatible Beamer export, with a **single deterministic clock based on final WAV samples**. Choose a consistent, restrained style: underline, translucent non-obscuring outline, contrast-preserving pointer/spotlight or controlled reveal. Never conceal essential symbols, axis labels or diagram panels. Avoid flashing, rapid motion, unintended slide jumps or cropped panels. Timing must survive segment concatenation and any audio re-encoding.

For complex mathematics, make cues refer to the **specific term or step** being spoken, not only the entire formula. For composite figures, cue the complete figure when necessary and its source-identified panels individually when discussed. Preserve a non-highlighted static export for inspection and compare the highlighted frames with it to rule out loss of content.

## 7. Narration and scientific speech

Use the accepted narration content as the semantic source of truth. Each scene should explain its actual visual objects and figure relationships. A figure insertion or split changes slide counts and/or order; invalidate impacted narration, speech, TTS QA, alignment, visual cues, media and completion receipts. **Do not** reuse old WAV numbers or timing against a changed deck just because the script resembles the previous version.

Use contextual mathematical pronunciation rules and a separate voice-ready file; preserve article `a` versus variable `A`, mathematical `c` versus “circa”, `u` versus “us”, subscripts, powers, Greek letters and units. Keep unchanged, approved per-slide WAV files when their exact upstream inputs and QA version hashes match. Require a pronunciation QA path distinct from text similarity; unresolved acoustics remain `review_required`.

## 8. FFmpeg, slide conversion and crash-safe recovery

Re-use and extend the hardening in [Portable Video and Cleanup](../PORTABLE_VIDEO_AND_CLEANUP_HARDENING.md) and [Stage 2 FFmpeg Recovery](MicroGen_Video_Stage2_Hardening_20261012.md):
- Run PDF splitting and FFmpeg input/output work on **local disk**, not directly against Google Drive placeholders; hash-check material staged in/out.
- Use small-frame-rate static slides only where no animated highlight is active. **A fixed 2 fps source will not necessarily represent timed highlighting smoothly.** Choose an explicit cue-aware segment encoding policy, test readability and visual timing, and use higher frame rate **only** for the portions with animation; benchmark rather than assume speed.
- Time-bound splitting, subprocesses, progress stalls and total encode; monitor **actual media progression** and terminate only the owned process tree when stalled.
- Cache accepted, immutable per-scene or per-part chunks against full inputs: approved PDF/LaTeX/source hashes, original narration, final WAV, alignment, visual cues, frame-rate/profile, FFmpeg version and quality-policy version.
- Write a candidate part MP4 locally, probe **both audio and video streams**, actual duration, decode sanity, scene transition timing and cue alignment, then promote atomically with a saved previous version.
- Never accept a zero-byte/missing or unverified cache segment. Resume at the first invalidated step, not automatically from page one.
- Do not delete generated audio, split-page files, cues or review artifacts until **all parts** have passed and all receipts survive source-adjacent publication. Cleanup of owned transient files is bounded and nonfatal when Google Drive briefly locks files. Never delete unrelated user files.

## 9. Dependency manifests, gate outcomes and failure types

Version all schemas and QA policies. Proposed DAG:

```text
source.pdf + captions -> source inventory -> discipline profile -> lecture_plan
                                                   |
                           figure mapping -> slide source and element targets
                                                   |
                                slides/PDF -> original script -> speech_ready
                                                   |
                                 final WAV -> acoustic QA -> timed alignment
                                                   |
                               visual cues / highlight rendering
                                                   |
                                  per-part MP4 / probe / part_receipt
                                                   |
                                   all-part completion_manifest
```

A changed accepted source or figure invalidates every *dependent* node, not unrelated finished parts. A changed final WAV invalidates alignment, timed cues and video for that segment. A modified Beamer deck invalidates affected narration/audio even if slide count is unchanged. Every part receipt binds the source hash, plan hash, approved slide/figure hashes, narration/speech/audio hashes, cue-map hash, MP4 SHA-256, duration and QA version; no final subchapter completion until **every required part** passes.

Record statuses `passed`, `repaired`, `review_required`, `blocked` and `in_progress`. Keep transport/stall/refusal/quota errors distinct from invalid scientific output. A process heartbeat, PDF compile exit 0, TTS response, or existing MP4 is **not** sufficient proof. Preserve a human-readable explanation and machine-readable defect code when something fails.

## 10. Acceptance matrix and implementation order

| Phase | Deliverable | Deterministic proof | Real controlled proof / release gate |
|---|---|---|---|
| A. Contract | This blueprint, profile and manifest schemas | schema-invalid, missing-parts, old-manifest compatibility tests | Documentation reviewed; **no worker modifications** |
| B. Source/profile | Subject-neutral scene/source inventory; figure + panel provenance | calculus/physics non-leakage; page/figure completeness; duplicate-panel rejection | Thomas 2.2 Figure 2.10 source-to-render check |
| C. Top-down planner | Coherent parts, reserve, duration target and continuity | scene boundaries; undersized, 9m, 10m, >10:30; never arbitrary finished-video chopping | Human inspection of planned Thomas lesson parts |
| D. Audio/targets | Stable Beamer target IDs and final-WAV phrase/word alignment | deliberate word drift; changed WAV; unknown symbol; cue past audio-end; source-panel mismatch | Listen/view sample passages, equations and labelled diagrams |
| E. Highlight video | Cue-aware local rendering, part-level FFmpeg, watchdog and cache | no-obscuration geometry; tamper/hash failure; stalled FFmpeg; duration/stream verification; restart | One exact-source controlled short part on authorised test copy |
| F. End-to-end | Source -> all parts -> coherent narrative -> final manifest | invalidation tests for moved slides/new figures/TTS replacement; unchanged-good reuse | Multi-part Thomas 13th-edition pilot, with audio-visual timeline spot checks |
| G. Three/four-PC rollout | Clean pinned code, resource leases, disjoint subchapters | Windows/Ubuntu CI, full suites, three-PC (and optional Zenbook) tests, lock recovery | Start small assignments only after user-authorised production gate |

**Required adversarial regressions:** a 784×234 three-panel figure trapped in a half-width column; missing caption/panel; page-number mismatch after Beamer edit; wrong narration count; mispronounced calculus symbol; low-confidence alignment; overlong 625s part requiring review; 635s part blocked; FFmpeg hanging while process remains alive; Drive access-denied during owned-temp cleanup; changed WAV with stale highlight; old validated MP4 must remain byte-identical until a fully checked replacement exists.

Every acceptance report must include exact code SHA, source/output acceptance location (in access-controlled logs only), test counts, audio/video hashes and duration, targeted screenshots/frame evidence, QA policy version, and explicit remaining limitations. No copyrighted textbook image, audio, screenshot, PDF, or private link is to be committed publicly.

## 11. Suggested code seams (planning, not claims of implementation)

- `selenium_pipeline/discipline_profiles.py`: explicit subject-neutral and subject-specific settings.
- `selenium_pipeline/lesson_plan.py`: source-grounded ordered scenes and part planning with duration budgets.
- `selenium_pipeline/element_targets.py`: LaTeX/PDF element identifier and bounding-box evidence.
- `selenium_pipeline/audio_alignment.py`: verified final-WAV phrase alignment and confidence checks.
- `selenium_pipeline/visual_cues.py`: speech-span to highlight-target mapping and coordinate QA.
- `selenium_pipeline/highlight_render.py`: reproducible cue-aware scene render.
- `selenium_pipeline/multipart_video.py`: part-level FFmpeg assembler, probing, reuse and publisher.
- `selenium_pipeline/lecture_receipts.py`: manifest and dependency invalidation; keep `slide_narration_sync.py` backward-compatible.
- Extend `selenium_pipeline/runner.py` only after module-level tests pass: introduce `source_inventory`, `lesson_plan`, `target_map`, `audio_alignment`, `highlight_video` and `multipart_verify` as **explicit, individually resumable gates**, without silently breaking existing `STAGES`.

New functions should integrate with the existing `MICROGEN_COMMUNICATION_MODE` contract (Selenium, API, bounded Selenium-first fallback) when a Gemini call is truly required. **TTS stays an API task** and should not be made dependent on Chrome. Under current development settings, keep Gemini Flash as the default; a future model switch requires an explicit validated release, not incidental environment drift.

## 12. Rollout checklist and next immediate action

1. Review this design as **requirements**, not a completed implementation.
2. Reconcile outstanding draft figure PRs #56–#58 and the merged receipt fixes #59–#60 against the current `main`, avoiding blind conflict resolution.
3. Implement isolated, unit-tested schemas and top-down planning before the audio alignment/highlight renderer.
4. Only then authorize a **controlled** Thomas 13th-edition test-copy pilot, compare the real PDF/pages, narration and timed video, and record failures.
5. If validated, deploy a pinned release at safe worker boundaries on the available PCs, preserve existing checked outputs, and resume only unfinished subchapters.

**Stop condition:** Never mark the Thomas calculus campaign complete while a required part is missing, a composite diagram is clipped, a mathematical symbol is spoken incorrectly without review, a highlighted cue is mistimed, an MP4 breaches the allowed duration policy, or an output hash/receipt is inconsistent.
