# MicroGen_AI_Web — Latest Development Checkpoint

**Date:** 19 October 2026 (Malaysia). Owner autonomous-development
protocol and the effective production contract remain authoritative.

## Current isolated figure identity candidate

- **Previous submitted draft:** PR #139, branch feature/verified-multielement-narration-20261018, exact dependency SHA 4db850f205030d9a764f86dc34f790d8502e1667.
- **Next draft candidate:** branch feature/whole-figure-source-identity-20261019b, stacked on #139, isolated HP checkout 20261019_pr140_figure_identity_0957; PR number is pending GitHub creation.
- Implementation commit af0058d08f239630cc62597a6fb2df09f7580de0: read-only figure_source_identity.py, adversarial synthetic-PDF tests, and technical scope notes.
- **Verified focused QA, 19 Oct:** 32 passed, 1 skipped (figure_source_identity plus automatic_multielement_narration, exact HP clone).
- **Full QA, CI, Dell/Yoga:** must be independently checked on pushed new HEAD. Do not assume results.
- **Scientific boundary:** exact decoded raster, source/slide caption, placement, dimensions and uniqueness establish only a candidate. Visible completeness, clipping, panel boundaries, or mathematics/semantics are not certified. No paid Gemini TTS, production video or YouTube publication permitted by this result.
- **Other isolated unfinished checkouts:** 20261019_pr140_figure_identity_0758 and 20261018_pr140_figure_identity retain their uncommitted work. Original shared G: Drive repositories on HP, Dell-115 and Yoga6 must remain untouched.
- **Next increment:** independent visible-completeness and multi-panel boundary mapping, adversarial checks, then a non-destructive real textbook pilot.
- Recurring schedules are bounded attempts, not a continuously running background coder. Check the task enabled state independently.

---

## Previous PR #139 checkpoint

# MicroGen_AI_Web — Latest Autonomous Development Continuation Checkpoint

**Date:** 18 October 2026 (Malaysia). Owner's autonomous-development protocol is binding.
**Source of truth:** live GitHub branch HEAD and CI checks, never an assumed background process.

## Most recent stacked development

Repository: `tlyoon/MicroGen_AI_Web`.

- Prior baseline: draft PR #138, branch `feature/element-narration-tts-provenance-20261018`, exact parent commit `41192406252725da7b8e6b475f53a5ba9e78f948`.
- Current development: **PR #139**, branch `feature/verified-multielement-narration-20261018`, created from PR #138 in a **new isolated HP clone**. Fetch the exact pushed branch HEAD from GitHub at continuation time; do not assume the branch has merged.
- Other stacked drafts, including #135 YouTube uploader, #136 course Video 00, #137 source-bound video and #138 upstream audio, must be preserved and reconciled before merging. No blind merge into main.

## Actual new capability (PR #139)

Source-grounded automatic narration formerly accepted only one exact PDF text block per slide. This change accepts **1–12 explicitly paragraph-delimited visible text blocks** per slide. Each paragraph must match exactly one separate, unclipped, non-overlapping text rectangle in strict top-to-bottom reading order. The **entire** concatenated narration must occur verbatim on exactly one original textbook PDF page; text ambiguity fails closed.

The TTS batch now flattens all source-bound element paragraphs in order, generates a distinct original `sNNN_eXX.wav` per element and binds each to exact spoken text, the local observed producer model/voice manifest, PCM SHA and retry evidence. Multipart planning accounts for **every element duration**, never cuts an overlong slide without actual separate anchors, and still requires each final encoded video to be strictly <600 seconds. The existing independently checked production bridge generates actual element-level highlighted MP4s.

**Full-panel figure and math limitation:** Any page image, inline raster block or vector drawing still blocks automatic exact-text mapping. The change does NOT assert that visual figure/panel identities or arbitrary equations can be guessed. These must be tackled as a separate, scientifically audited feature.

## Tests and evidence

Focused real synthetic PDF/FFmpeg tests cover six independently highlighted narration elements on three slides, strict original-source replay, actual video/audio technical QA, correct output reuse, reversed ordering, repeated text blocks, repeated textbook source pages, vector-only diagrams, image figures, source mutation and duration fail-closed scenarios.

Before claiming verified success, check:

1. HP latest full `pytest tests selenium_pipeline/tests` exit code and totals.
2. GitHub exact-commit Windows, Ubuntu, publication and reliability workflows.
3. Dell-115 and Yoga6 independent isolated clones checking out the exact PR139 SHA, no modifications to original three-PC Drive repos.
4. New PR's draft status and base = PR138 feature branch.

**No** real paid Gemini/Cloud request, student-visible YouTube upload, Moodle publication, original lecture overwrite, Whisper, Zenbook or external GCS distributed lease is part of PR139.

## Original three-PC preservation

HP, Dell-115, Yoga6 original shared repo `G:\My Drive\Projects\MicroGen_AI_Web` last observed at commit `9e1a0ff`, with pre-existing dirty tracked files:
`selenium_pipeline/runner.py`,
`selenium_pipeline/tts.py`, and
`selenium_pipeline/vendor_template_v2/selenium.py`.
Never reset, overwrite or checkout the draft branch there. Use isolated clones.

## Next autonomous development objective

After PR139 passes focused, full and cross-PC acceptance, implement verifiable full-image/full-panel source mapping and narration synchronization with rigorous source/crop/multipanel validation, then perform an isolated **real source** pilot without modifying historical Thomas/Serway materials. Respect all voice, FFmpeg, source QA and automatic YouTube release contracts. A real source pilot is not equivalent to the synthetic tests.

Hourly autonomous development scheduled tasks make bounded attempts; they do NOT imply a 24/7 background agent. If an active chat is coding, avoid concurrent writes or moves until the active work reaches a safe checkpoint. Status monitor must honestly report missing progress.
