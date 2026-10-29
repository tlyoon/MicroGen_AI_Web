# MicroGen_AI_Web — preserved development checkpoint (2026-10-18)

> **Review-only development checkpoint. Not a production release, merge approval, or student-publication authorization.**
> Create this record on the dedicated `checkpoint/microgen-2026-10-18` branch, based on the exact PR #129 code commit `cec5431bbe2765c98467961eb0d1b3c5a1762781`. The release and academic approval gates below remain binding.

## GitHub identity and status

- Repository: https://github.com/tlyoon/MicroGen_AI_Web
- Verified baseline `main` remote head at checkpoint time: `84cb105ff3a21411ac6b0de6665d6c832e11b6be`. **Main was not modified.**
- Latest code snapshot: PR #129 head `cec5431bbe2765c98467961eb0d1b3c5a1762781`, branch `feature/flagged-narration-slide-context-review-20261018`.
- Explicit saved branch: `checkpoint/microgen-2026-10-18`, created from that PR #129 head; this document is the only intended checkpoint-branch addition.
- PRs #126 → #127 → #128 → #129 are **stacked drafts** (each PR targets the prior PR's head branch) and must not be merged out of order. Earlier draft development (#120 onward) also remains unmerged.
- The separate preserved original three-PC local edits are archived in GitHub branch `archive/legacy-local-edits-2026-10-18`, commit `8b8381071a5d63a4b4c715934bb6eb0a5b86b734`. This branch is **legacy/unreviewed** and is **not** an implementation patch to cherry-pick or merge automatically.
- A Git tag `microgen-checkpoint-2026-10-18` is intended to mark this checkpoint-document commit once its publication and remote identity are verified.

## Three-PC non-destructive preservation audit

Checked HP, Dell-115 and Yoga6 on 18 October 2026. Each working directory at `G:\My Drive\Projects\MicroGen_AI_Web` was on locally outdated `main`, commit `9e1a0ff6f27a1d9644b208c12a87f9717eac4042`, 50 commits behind its tracking `origin/main`. All three had the same three modified files, with identical SHA-256 per file:

| Modified path | Observed SHA-256 |
| --- | --- |
| `selenium_pipeline/runner.py` | `4FD10061E410E85D54CE539C079A8A25909C02411C421E559502DF65631BBFBE` |
| `selenium_pipeline/tts.py` | `9CF1F0F3CC0F131006A61FFA65EF2ABE074621E8F3921E0F3F602C86CB49E7B0` |
| `selenium_pipeline/vendor_template_v2/selenium.py` | `19BC08AF6A3ED7D502E45E1AEA5C1881994B74BF46676AFC7333A53BE4A7F170` |

On EACH PC a distinct, machine-local directory `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261018_pre_git_checkpoint` contains copies of the above three modified files, `local-modifications.patch`, `git-status.txt`, and `manifest.txt`. The original Drive-synced working directories were not reset, pulled, checked out, cleaned or overwritten.

The archive Git branch was independently assembled in a fresh isolated clone, using copied files whose SHA-256 matched local backups. `git diff --check` and Python 3.12 syntax compilation passed (with an existing invalid-escape `SyntaxWarning` inside a JavaScript regex embedded in one Python string). No production test or academic acceptance is claimed for these legacy edits.

## Mandatory existing project contracts (retain without weakening)

1. **Every delivered lecture-video part MUST be strictly shorter than 600 seconds.** A longer subtopic MUST be automatically split into multiple valid parts. Exactly 600 seconds is not acceptable.
2. Narration MUST be synchronized with highlighting of the corresponding **slide element**, not merely static full-slide display. Pixel-verified encoding and real audio-element correspondence are separate checks.
3. Preserve exact source/caption/figure completeness, all multi-panel subfigures, page ordering, authored spoken mathematics, narration and slide-source identity. A change in page structure/figures can require regenerating narration and audio downstream.
4. Do not silently switch selected model/voice or mix voices. The established generation path uses Gemini Flash for slides and narration; owner-approved TTS uses Gemini Flash-Lite primary, Gemini Flash fallback and conditional Cloud TTS fallback only after documented prerequisite retry and billing/voice guards. No Whisper should be introduced without approval.
5. Outputs are written to each subchapter's source folder as specified by the source root; preserve original source PDFs and prior published or review assets. Keep review artifacts in separate new folders, with byte/hash validation and no overwrites.
6. Three-PC execution fleet is **HP, Dell-115 and Yoga6 only**; Zenbook excluded. Use Drive-native coordination, checksums and FIFO, with **no GCS leasing** and **no automatic reassignment**.
7. GitHub passing tests do not imply scientific correctness, accurate speech, full figures, human listening approval or authority to release material to Moodle/students. Production replacements and student publication are blocked until independently approved.

## Latest tested development state (not release state)

- PR #126 introduced source-bound, real-WAV Thomas 8.4 two-part review video recovery and independently decoded element-highlight QA. Archived review parts were **291.40 s** (slides 1–8, **23/23** regions) and **322.96 s** (slides 9–17, **25/25** regions). Hash-bound video pixel correctness passes; that does **not** prove audible math correctness.
- PR #127 preserved all **48 original Thomas 8.4 WAVs** and created a human listening worklist. It also prepared review-only 8.6 element drafts. All human approvals remain false.
- PR #128 added an immutable, source-bound audit of ambiguous element-ranking drift in Thomas 8.5. Historical and refreshed heuristics disagreed on **59/78** utterance rankings; **four** ambiguity labels flipped, with a refreshed **58 ambiguous** proposals. This changes no human approval state.
- PR #129 created a **six-WAV/five-slide-PNG** reviewer packet for flagged Thomas 8.4 narration, sourced from immutable historical WAV/slide receipts. Flagged IDs: `s05_e03.wav`, `s07_e01.wav`, `s10_e01.wav`, `s12_e01.wav`, `s12_e02.wav`, `s13_e02.wav`. All 48 WAVs still need human listening/academic clearance. Review Drive folder: https://drive.google.com/drive/folders/1dptAPjjq2oJYj84Q0alAKCi7bLCCGuyH
- PR #129 description reports HP, Dell-115 and Yoga6 each passing **275 selected offline tests** (825 executions combined), all three isolated checkouts clean, and GitHub Actions workflow **#39087424997 SUCCESS** (Windows/Ubuntu full tests and reliability subset).
- Original overlong single-file Thomas 8.4/8.5/8.6 MP4s are preserved; the overlong originals must not be mistaken for compliant reviewed replacements. The 8.5/8.6 element mappings and source-bound compliant multipart video replacements remain unresolved. Thomas 8.6 has **50** ambiguous element mappings across **69** authored utterances.

## Outstanding acceptance gates and safe next actions

1. Human-listen to the **48/48** original Thomas 8.4 WAVs (six flagged clips first), inspect the exact slide images, math expressions, radical/fraction scope, figure panels and pronunciation, and save explicit independent decisions.
2. Review and resolve ambiguous Thomas 8.5 and 8.6 narration-to-element mappings without treating machine scores or ASR transcription formats as academic approval.
3. Only after academic/listening/figure approval, conduct real-production end-to-end smoke runs of source-bound multipart and element-highlight output, verify duration and full figures, then separately authorize any output replacement or student publication.
4. Reconcile stacked PRs in dependency order after technical/human gates and review CI. **Do not** directly merge PR #129 into `main`, force-update `main`, or change original Drive assets during checkpoint work.
5. If legacy archived three-file edits remain needed, port and independently test them against the current modern code; do not apply their old patch blindly because the old Drive working tree is far behind upstream.

## Scope and recovery references

This document captures **known tracked Git development and the discovered three-file dirty legacy working tree**. It does not claim to archive ignored local credentials, all possible transient worktrees, Drive lecture PDFs/WAVs/MP4s, or inaccessible unpublished changes. The video/review folders and original assets remain in their existing storage; commits are not a substitute for asset backups.

Recovery starts from this checkpoint branch/tag for code, the latest stacked PR heads for review context, and the separate archive branch for legacy differences. Do not use a normal `git pull` in the dirty, outdated Drive-synced main working directories before a deliberately planned, tested migration.
