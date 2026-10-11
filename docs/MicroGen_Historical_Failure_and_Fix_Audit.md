# MicroGen historical failure-and-fix audit

**Audit scope:** Serway 46-source-PDF lectures across Dell-115 (chapters 8–9), HP (10–11), and Yoga6 (12–14), plus earlier MicroGen development troubleshooting. This file is a maintained engineering audit, not a claim that all possible faults have been identified. The source folder and Git history remain the primary evidence.

**Evidence:** campaign checkpoints and logs in `G:\My Drive\Serway\Serway_8_14\.microgen_coordination`; source-adjacent artifacts and repair reports; merged GitHub PRs #26, #27 and #28; offline tests. The original `serway_20261010_three_pc` checkpoint is historical and must not be used as proof that a lecture is complete. Current recovery checkpoint: `serway_20261012_recovery`.

**Closeout rule:** Mark an incident **permanently fixed** only if its cause is addressed by supported package code, an automated regression prevents recurrence, and relevant end-to-end or multi-PC acceptance evidence exists. An isolated recovery script or one successful manual run is insufficient.

## Incident-to-protection matrix

| Incident / observed symptom | Root cause or risk | Status and implementation | Evidence / remaining gap |
|---|---|---|---|
| Gemini composer reported stale draft despite an empty editor | Selecting an outer aria-label wrapper or placeholder/body instead of the actual textbox | **Merged**: PR #26 (`bc91535`) selects the real contenteditable, verifies draft clearing, refuses stale text | Five browser-mock regressions; live Dell-115 figure pilot passed; adapt selector if Gemini changes UI |
| Gemini mode picker disappeared on an old HP tab | Retained old editor text and a Gemini tab without a usable model picker | **Merged in PR #28 (3616b765)**: preserve old draft, open one clean Gemini tab, verify Flash, close failed new tab | Fresh-tab mock tests and the original manual recovery; requires live acceptance on clean HP |
| Gemini Flash temporarily unavailable on Yoga6 | Authentication/model availability uncertain | **Partly protected**: Flash model gate fails closed and never automatically substitutes Pro | Live Flash High smoke passed; future outages must defer and retry, not bypass account |
| Missing `Figure12_1.png`, `Figure10_4.png`, etc. | LaTeX may compile without images because `IfFileExists` hides errors | **Merged partial gate**: `figure_audit.enforce_graphics` rejects unresolved references; **not solved generically**: finding/cropping the right image still requires source-grounded semantic verification | Fifteen figures restored from source PDFs via an isolated, reviewed repair. Package-level read-only PDF page candidates added in PR #28; correct crop still requires semantic approval |
| Figure corrections after narration/video | Changed graphics may invalidate slide-to-script and MP4 rendering even with unchanged page count | **Partly implemented**: `slide_narration_sync`, impact and repair-plan modules; manual 12.1/12.4 staged rebuild was successful | Downstream checkpoint invalidation merged in PR #28; semantic narration review and selective rebuild remain to be demonstrated end to end |
| Published video without completion receipt | Failed cleanup or delayed publication leaves usable MP4 unrecognized | **Merged**: PR #27 (`4bb1da9`) worker guard; **merged in PR #28 (3616b765)** extends guard to direct CLI | Offline tests, source hash and QA-based receipts for 9.6 and 12.2; never auto stamp absent semantic checks |
| Cleanup erased prior repair evidence | `.history` and numbered WAVs were considered disposable intermediates | **Merged in PR #28 (3616b765)**: preserve archives and source-adjacent narration WAVs | Cleanup regression cases cover both Selenium and batch paths |
| Job marked successful using stale checkpoint flags | Stage stamp existed even when source or published deliverable changed | **Merged in PR #28 (3616b765)**: checkpoint source hash, model, stage artifacts, published output and graphics must all verify | Offline stale-source, missing-PDF and missing-figure tests |
| TTS QA had zero reported blockers but incomplete audio coverage | `blocking_failures=0` alone was incorrectly treated as a pass | **Merged in PR #28 (3616b765)**: require the correct number of slides and QA passes, zero pending reviews, and minimum fidelity at threshold | Offline cases: missing slide, pending review, below threshold, complete pass |
| Calculus and Serway jobs could share a Gemini browser | Per-worker locks only protected identical worker names, not different CLI invocations | **Merged in PR #28 (3616b765)**: local per-Chrome-port OS file lock around browser-using stages | Tests prove nonreentrant lock and separate browser ports; legacy code without locks remains a deployment limitation |
| Two computers could race on Google Drive ticket files | Google Drive for Desktop does not provide atomic cross-PC lock semantics | **Merged baseline**: ticket system disabled; chapter ownership is disjoint | Check manifest overlap and use local OS locks; no claim of globally atomic Drive coordination |
| Worker inactivity and hard stage limits | Worker could linger silently during crashed browser or FFmpeg processes | **Merged baseline**: 900-second idle and 3600-second hard timeout; deferred second pass | Requires interruption/restart acceptance tests on all PCs |
| Flash TTS or audio repair interrupted | Partial WAVs could survive a failed stage or be overwritten during reruns | **Partly implemented**: TTS fidelity checks and selective repair helpers; **merged in PR #28 (3616b765)** rejects incomplete QA | Inject timeout, low fidelity, and WAV-hash-change failures in acceptance suite |
| Windows consoles emitted Unicode failures | The default console code page could reject symbols, killing output readers | **Merged baseline**: worker output streams use UTF-8 error replacement | Existing regression run; verify in supported Windows environments |
| MP4 assembly succeeded but cleanup failed | Cleanup incorrectly affected perception of valid video completion | **Merged baseline**: publication separated from noncritical cleanup failures, non-destructive receipts | Test for cleanup failure retaining MP4; cleanup history-retention fix merged in PR #28 |
| FFmpeg output lacked audio or duration failed | Successful subprocess exit does not guarantee a playable lecture | **Merged baseline**: FFmpeg checks decodable video/audio streams and duration | Test candidates and validate real source-adjacent MP4s |
| Stale worker checkpoints misrepresented completion | Finished worker attempts still contained many unfinished jobs, and newer manual jobs were absent from checkpoints | **Merged in PR #28 (3616b765)**: read-only `reliability_audit` checks genuine source-adjacent receipts and files | Regression tests distinguish receipts, partial slides, orphaned MP4s and changed file hashes |
| Portable package settings differed between PCs | Hard-coded checkout, Python environment, Google Drive path, auth profile or subprocess assumptions | **Partly merged**: explicit source root, Windows local settings and per-PC Python arguments | Validate fresh clones and portable doctor on Dell-115, HP and Yoga6 |
| Existing valid work was unnecessarily regenerated | Lack of source/output hash validation before retry | **Partly merged**: output protection and per-stage runner checkpoint reuse; **merged in PR #28 (3616b765)** strengthens stage proof | Interrupted generation and idempotent reruns still need controlled acceptance |
| Repaired images need academic review, not arbitrary pictures | A filename or caption is not sufficient to identify a scientifically correct diagram | **Deliberate fail-closed policy**: never invent a replacement figure; surface source-page evidence and require semantic approval | Source-PDF figure extraction workflow should be packaged with accountable provenance |

## Existing confirmed milestones (historical, not a current live-status claim)

- PR #26: verified composer selection and draft clearing, merged as `bc91535`.
- PR #27: published-MP4 safety guard, merged as `4bb1da9`.
- October 2026 repair: 15 source-grounded figures restored across 8.1, 10.3, 10.4, 12.1 and 12.4, with old PDFs/videos archived.
- October 2026 recovery: repaired 12.1 and 12.4 videos passed H.264/AAC, duration, TTS and synchronization checks, and were receipt-stamped.
- Read-only hardening baseline from 2026-10-11T16:53Z: 46 source PDFs; 6 verified receipts, 7 partial slides, 33 without published slides. Recheck live files each run.

## Closeout requirements

1. Every recurring failure has a reproducible test and documented safe failure behavior.
2. The full offline suite passes on a clean supported environment.
3. Multi-PC tests verify a fresh job, interruption, last-valid-stage recovery, existing receipt skip and orphan MP4 preservation.
4. A real media/figure correction is validated semantically, not merely by file existence or page count.
5. Production outputs remain untouched while branch fixes are developed and reviewed.
6. The merged GitHub main commit and all three local checkouts are verified before activation.
7. The runbook differentiates automatically recoverable faults from authentication, scientific-content and unsafe-state blockers that require review.
