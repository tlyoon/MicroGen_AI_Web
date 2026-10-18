# MicroGen element-draft heuristic drift audit — 18 October 2026

**Development draft stacked after PR #127. Review-only, offline, no TTS or academic approval.**

## Why

Thomas 8.5 source, slide PDF and narration remained identical between Oct 16 and Oct 18, but heuristic-ranked PDF element suggestions changed in **59/78** utterances, and the ambiguity classification changed for four (62 ambiguous historically vs 58 under the latest scorer). No score is a probability or a mathematical confirmation. The lesson cannot silently proceed to element TTS because a lexical threshold was crossed.

## New reusable module

`selenium_pipeline.element_draft_drift_audit` reads two source-bound **unapproved** `element_plan_autodraft.propose()` JSON drafts. It refuses changed source PDF/slide/script hashes, changed original narration text, missing utterances, false author/mathematical/production approvals and already-stageable TTS. It separately reports *every* changed candidate ranking/score list and the smaller subset of flipped `mapping_ambiguous` labels. Review reports include both input JSON SHA-256 digests, all exact original word fragments, both old/new ranking arrays, and mandatory flags `approved_for_tts=false`, `academic_approval=false`, `student_published=false`.

Example: generate the two new **review-only** outputs outside either original source directory:

```powershell
python -m selenium_pipeline.element_draft_drift_audit `
  --historical 'PATH_TO_ORIGINAL_Thomas85_AutoCandidates.json' `
  --refreshed 'PATH_TO_REFRESHED_Thomas85_AutoCandidates.json' `
  --output-json 'PATH_TO_NEW_REVIEW_DIR\Thomas85_Drift_FromCode.json' `
  --output-md 'PATH_TO_NEW_REVIEW_DIR\Thomas85_Drift_FromCode.md'
```

Both output paths must not exist. Neither original draft, source PDF, slides PDF, script, WAV nor MP4 is modified. The generator does not use Google APIs, Whisper, remote speech recognition or produce TTS. All figure panel semantics and narrated equations remain unresolved until a human checks the actual source and full rendered slide.

## Actual Thomas Calculus 8.5 three-PC result

HP, Dell-115 and Yoga 6 independently ran the new comparator on the original preserved October 16 `Thomas85_AutoCandidates.json` and the refreshed October 18 review-only JSON:

- Historical draft raw bytes SHA-256: `f9e053bf345af3e6ff0f711e8818da0db33f0e2ec4d7c283f17501ed10d4d9eb`
- Refreshed draft raw bytes SHA-256: `19097c109a38bc410c3c6c36abd76fcda89554854478bc0b82ed41d8fa9a5acc`
- Canonical sorted comparison JSON SHA-256 (three PCs identical): `bb93c0197515841b3106e92328b52b083a74a3cee1951542fc36acfe9a124e18`
- Verbatim original utterances: **78/78 unchanged**. Changed rankings or scores: **59**. Changed ambiguity classifications: **4**. Ambiguous totals: **62 → 58**.
- Four altered ambiguity labels: `s003.utterance.004` (new suggestion `s003.text.006`), `s008.utterance.003` (`s008.text.012`), `s009.utterance.004` (`s009.text.012`), `s012.utterance.004` (`s012.text.015`). Each newly suggested match was assigned lexical/mathematical-term **heuristic score 0.35**, not human-validated probability.

An earlier one-off audit and human review report also exists in the shared Drive `MicroGen_AI_Web_Thomas85_RefreshedAutoCandidates_ReviewOnly_20261018` folder; this PR upgrades that exercise to a generally reusable, tested code feature.

## Safety and acceptance boundary

- Draft report can **never** transform a `REVIEW_REQUIRED_NOT_TTS_READY` candidate into `approved_for_stage`, `approved_for_tts`, or a student-facing completed video.
- Figures, multiple panels, exact equations, narration utterances, and source pages need independent manual checking. A false `figure_panel_slide_count=0` is a heuristic non-detection, not evidence no complex figures exist.
- Thomas 8.4 has technical archived video QA 48/48, but the source-bound listening packet still requires human audio and mathematical signoff. 8.5 and 8.6 still need authored element mapping. Historical overlong 8.5/8.6 videos remain unchanged; strict <600s multipart production acceptance is mandatory.
- PRs #120–#127 form a **draft stacked integration chain**; no merge, deploy, production media replacement, student Moodle publication or paid experimental request is implied.

## Verification

Ten new no-network unit tests cover unchanged sources, changed rankings, flipped ambiguity, raw text preservation, unsafe approval rejection, missing SHA, inconsistent counts, CLI safe new files and CSV/report output isolation. The selected legacy/audio/video/MP4-pixel regressions are rerun on HP, Dell-115 and Yoga 6, with full GitHub Windows/Ubuntu suites after opening the draft PR.