# MicroGen Stage 3 — Comprehensive regression and fault-injection acceptance

**Date:** 12 October 2026
**Scope:** MicroGen_AI_Web source code, isolated synthetic inputs, multi-platform CI.
**Release gate:** Offline regression completion is **not** a substitute for the live three-PC full-length certification planned in Stage 4.

## Purpose and nonnegotiable rules

The historical corrective work should result in permanent, reproducible regression protection. The current Stage 3 test command uses synthetic fixtures and mocks, not the production Google Drive source tree. It makes no Gemini browser interactions and incurs no deliberate generation API cost. Never hot-swap running worker code; Stage 4 will deploy the same Git commit only after live job boundaries are established.

## One-command offline acceptance

On any clean supported Windows or Linux checkout with a Python 3.12 virtual environment, install:

    python -m pip install selenium pymupdf pypdf pillow imageio-ffmpeg pytest "google-genai>=2.25,<3"

Then from the repository root run:

    python -m pytest -q tests selenium_pipeline/tests --basetemp=.pytest-stage3-isolated --disable-warnings --maxfail=1

The dedicated --basetemp is important on Windows: an existing default pytest-of-USER folder can be ACL-denied, causing unrelated tests that use tmp_path to report errors. Never treat failures caused by test-environment permissions as proof of a production bug. However, do **not** waive them: rerun in an isolated writable temp root and require zero errors.

The GitHub Actions workflow also runs the targeted historical-failure tests separately and runs the complete Python test suite on Ubuntu and Windows. CI must pass on the actual proposed head commit; a test that was previously green on a different SHA is not sufficient.

## Incident → permanent regression matrix

| Historical fault | Automated defense (representative tests) | Accepted failure mode |
|---|---|---|
| Wrong Gemini textbox / stale draft | selenium_pipeline/tests/test_gemini_composer_guard.py, tests/test_gemini_mode_recovery.py | Refuse stale submission; verified fresh editor |
| Flash unavailable / unintended Pro substitution | selenium_pipeline/tests/test_gemini_model.py, tests/test_gemini_mode_recovery.py | Stop/defer rather than silently change model |
| Competing browser jobs | tests/test_browser_port_lock.py, tests/test_three_pc_worker.py | Only one owner per local Chrome port |
| Cross-PC duplicate chapter assignment | tests/test_three_pc_worker.py, Stage 3 manifest-injection case | Reject overlapping work ownership |
| Missing/unsafe textbook figures | tests/test_figure_audit.py, tests/test_figure_recovery_candidates.py, tests/test_stage3_fault_injection.py | Do not silently approve or discard needed graphics |
| Slide changes invalidate narration/MP4 | tests/test_downstream_invalidation.py, tests/test_slide_narration_sync.py | Reject stale downstream receipts |
| Narration retry / rejected script lost | tests/test_narration_retry_feedback.py | Targeted bounded correction and lossless rejection archive |
| Incomplete TTS, low-fidelity or pending review | tests/test_hardening_regressions.py, tests/test_tts_qa_repair.py, Stage 3 QA-injection case | Fail closed, no video acceptance |
| Incorrect API keys / timeout failover | tests/test_env_key_conflicts.py, tests/test_dell_tts_deadlines.py | Explicit conflict or bounded key switch |
| Source/output drift; stale completion receipt | tests/test_completed_cleanup.py, tests/test_reliability_audit.py, Stage 3 receipt-injection cases | Do not count as completed or regenerate unsafely |
| Unexpected published MP4 without receipt | tests/test_completed_cleanup.py, tests/test_three_pc_worker.py | Preserve and reconcile before replacing |
| Missing audio / truncated video | tests/test_video_ffmpeg_assembly.py, Stage 3 probe-injection cases | Reject MP4 and preserve original deliverables |
| FFmpeg no real progress, output heartbeat only | tests/test_stage3_fault_injection.py | Timeout and stop only the failed subprocess tree |
| Interrupted video or modified slide/WAV | tests/test_stage2_video_recovery.py | Hash-verified segment reuse; rebuild invalidated segments |
| Runner termination/cleanup | Stage 3 actual child timeout, tests/test_stage2_video_recovery.py | Scoped process-tree termination, no silent hang |
| Cleanup errors / unsafe workspace / history loss | tests/test_completed_cleanup.py | Keep published outputs, figures and archives |
| Unreliable Drive tickets / machine portability | tests/test_three_pc_worker.py, tests/test_worker_portability.py | Disjoint assignments; local environments; no shared-Drive mutex assumption |
| Campaign false positives and missing sources | tests/test_reliability_audit.py, Stage 3 read-only audit case | Count only genuine source-matched receipt proof |

## Additional defect found by Windows CI

The first complete Windows CI run exposed a Stage 2 cache-path portability bug: the encoder canonicalized the lecture folder before hashing its cache identity, while a second caller supplied the unnormalized path. Windows hosted runners could therefore disagree about the cache directory even though the first segment had been successfully encoded. Stage 3 fixes this by canonicalizing the source path inside the cache helper and regresses equivalent path aliases. This is a genuine software fix discovered by the expanded cross-platform test coverage.

The second full-Windows CI attempt exposed a related manifest-portability defect: a worker source-root check compared noncanonical absolute path strings. On Windows, equivalent spellings could incorrectly fail the manifest gate. The worker now resolves both manifest and local paths before comparison while preserving rejection of genuinely different directories. The existing Windows portability integration test exercises this exact fail-closed gate.

## Mandatory acceptance outcomes

1. All offline tests pass on the proposed commit on Windows and Ubuntu, without collecting or rewriting production materials.
2. Controlled faults are **rejected**: stale content, unchanged frame spam, incomplete TTS, wrong media streams, duplicate ownership and old published MP4s.
3. Every tested failure preserves existing validated outputs and creates useful actionable state/log evidence.
4. Successful cleanup/resume is idempotent and never changes source PDFs.
5. Explicitly known limitations are carried to Stage 4: live Gemini account/UI variability, cloud outages, semantic correctness of scientific figure selections, three-PC real lecture interruptions, full campaign completion and user-visible media-quality inspection.

## Stage 4 handoff

Use the Stage 3 merge SHA to pin clean, independent checkouts and test environments on Dell-115, HP and Yoga6. Verify one full representative lecture generation and one injected interruption/resume on **each** PC, with correct figures, narration/WAV fidelity, MP4 playback, output hashes, and no orphan FFmpeg process. Record actual campaign completion receipt counts from the source tree rather than relying on old checkpoints. Do not claim the package finished from offline test totals.
