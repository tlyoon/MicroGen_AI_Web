# MicroGen_AI_Web — Latest Development Continuation Checkpoint

**Updated 18 October 2026 — draft PR #138 development round.**
See [Standing owner-authorized autonomous development protocol](AUTONOMOUS_DEVELOPMENT_PROTOCOL_20261018.md).

## Durable previous checkpoint

Repository: `tlyoon/MicroGen_AI_Web`.
Latest previously verified draft: PR #137, branch
`feature/automatic-production-highlighted-renderer-20261018`,
commit `f719c9c9f1dd9a4a3e78414cac20418ee1721b4f` (draft, unmerged).
Older draft PRs and archival history remain unchanged; do not merge the
stack to protected main without meeting release-policy conditions.

## Current continuation development

Feature: `feature/element-narration-tts-provenance-20261018`, strictly
stacked on PR #137. Resolve exact current branch commit using
`git rev-parse origin/feature/element-narration-tts-provenance-20261018`
or the corresponding GitHub draft PR once pushed.

Implemented in this iteration:

- Machine-only, exact-source-text/single-block element planner; rejects
  figures, ambiguous rendered text, unmatched source quotations and
  incomplete narration **before** paid TTS.
- Generates true separate original element WAVs through the existing
  Flash-Lite/Kore batch TTS and bounded provider queue, with only
  separately verified Flash/Kore or conditional Cloud/Corey whole-batch
  fallback and observed append-only attempt journal.
- Verifies effective single-model voice, text hashes, PCM, source/slides,
  script and original TTS batch receipts. Calculates coherent <540 s
  narrated-media part boundaries from measured WAV duration.
- Produces source-adjacent non-overwriting element-plan/WAV/manifest
  and passes technical output automatically to PR #137's real highlighted
  multipart renderer via the regular runner and three-PC worker.
- Does NOT claim author/human academic approval, substitute slideN.wav,
  guess figure panel meaning, overwrite originals or publish Moodle.
- Regression tests include mocked-TTS real encoded FFmpeg MP4 and
  original-file preservation plus ambiguity fail-closed behavior.

Limitations: Exact text blocks only, not universal figure/equation mapping.
A real full Serway/Thomas subchapter production with valid original element
mapping and actual paid provider has NOT been certified in this draft.
TTS failures preserve diagnostic local staging and require conservative
reconciliation before retrying; automatic crash recovery remains a possible
next hardening task.

## Original three-PC state to preserve

HP, Dell-115, Yoga6 original Drive repos at
`G:\My Drive\Projects\MicroGen_AI_Web` were last verified at commit
`9e1a0ff`, with exactly these **pre-existing dirty tracked files**:
`selenium_pipeline/runner.py`,
`selenium_pipeline/tts.py`,
`selenium_pipeline/vendor_template_v2/selenium.py`.
Never reset, overwrite, checkout a draft over, or synchronize by deletion.
Zenbook is explicitly excluded. No current YouTube upload, token
modification, Cloud storage lease, Whisper or Moodle publication.

## Acceptance/continuation procedure

1. Verify exact PR #138 branch SHA and current HP full offline suite results.
2. Check GitHub Windows/Ubuntu/reliability/publication workflow outcomes.
3. Check the exact pushed commit on Dell-115 and Yoga6 using **isolated
   clones only**; never touch original Drive synced repos.
4. If any tests fail, fix/retest and update the same draft dependency branch
   without merging prematurely.
5. Next implement reliable ambiguous multi-element and full-figure panel
   source grounding, plus a real isolated lecture pilot with the original
   Flash-Lite/Kore policy. Preserve all prior teaching assets.
6. Checkpoint again before session limits; a new chat may resume from
   this document without a new blanket owner-approval request.

**Important:** ChatGPT cannot automatically open a new conversation or keep
performing work after an ordinary response ends. Only verified local/CI
processes or explicit scheduled tasks can run independently.
