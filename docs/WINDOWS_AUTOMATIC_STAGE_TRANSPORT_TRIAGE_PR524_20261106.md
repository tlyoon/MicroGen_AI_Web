# PR524 — Automatically persist source-bound stage triage (6 November 2026)

**Project:** MicroGen_AI_Web only; native Windows Selenium, Dell-115 exclusively. This draft is stacked on PR523 at commit `2f1a8f94198209bb7a5725f74cc918a92b1c67b1`; its GitHub Windows CI run #668 passed both jobs. The separate `MicroGen_AI` Gemini API package is out of scope.

## General failure and permanent correction

PR523 fixed the Windows owned-stage subprocess output buffering and added unambiguous supervisor timeout markers. Previously, operators still had to invoke `windows_gemini_stage_transport_triage` manually to distinguish absent browser/send evidence, stage timeout, registered browser send, and source completion. That manual intervention could leave future automated batch executions without structured, auditable fault classifications.

PR524 adds `persist_terminal_triage(trial_dir, stage)`. On **every real terminal figures, slides, and narration stage**, the existing one-shot runners automatically run read-only diagnostic classification **after** the existing immutable model-stage result was committed. The diagnosis is saved in a separate, immutable JSON artifact (`figures_transport_triage.json`, `stage_slides_transport_triage.json`, or `stage_narration_transport_triage.json`) alongside source and send receipts, without modifying the original stage result, stage input PDF, browser or model history.

The durable receipt binds the exact original `source_sha256`, `terminal_result_sha256`, and `terminal_log_sha256` (or null when a log does not exist) and records detection of local extraction, Chrome session attachment, registered provider Send, supervisor timeouts/exit, previous stage acceptance, and uncertainty. It **never** concludes a model outage from a generic timeout or treats an unproven Send as definitely unsent. `original_submission_resend_authorized` and `automatic_resubmission_authorized` both remain false. Neither status permits provider switching or retrying the original source. A repeated diagnostic invocation verifies the live original receipt, log SHA, and full recomputed result before returning `PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND`; an altered or inconsistent historical log/result fails closed.

The direct CLI remains read-only by default and adds optional `--persist-terminal-triage` only for reconciling an **already completed** existing stage. It requires the appropriate source-matched pre-send claim and terminal result; it cannot generate content or open Chrome.

## Actual historical evidence, without replay

The already timed-out distinct Serway §10.1 figures trial at `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261105_PR522_SERWAY10_1_ONE_FIGURES_STAGE_V1` was diagnosed once with this new read-only CLI. It produced `SOURCE_STAGE_HALTED_NO_REGISTERED_SEND`, `FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY`, `provider_outage_proven=false`, `model_requests_during_diagnosis=0`. SHA evidence: original stage-result SHA-256 `50b1ccf3aa02b2dc756d92f7d422cbfc3a1ff36886d325bc26bcf73033fb7a8d`; raw log SHA-256 `f38aab669cddf721e2d660e79eca8ba894c3e22a6c2a3817aff221eee48804c0`. Direct before/after hash comparison confirmed the **original stage-result file remained unchanged**. The real old log lacked PR523's new supervisor marker and is marked as such. No resend of §10.1, Serway §1.1, §22.1, §24.4 or earlier Thomas PDFs.

## Validation and limits

Synthetic/fault-injection tests now prove that the actual `windows_fresh_source_trial.run_trial` and `windows_original_stage_sequence.run_stage` write terminal diagnostics after a mocked single one-shot production invocation, while preserving duplicate-send claims and output safeguards. The triage helper separately proves exact SHA-bound immutable reuse, log tamper detection, and rejection of absent pre-send claims. These tests do not make any live Gemini, ChatGPT, TTS, media or publication calls. Run exact-head Windows CI before claiming merged/production-complete status.

This closes **automatic diagnostic recording**, not a physical Gemini provider outage or scientific/visual/audio defects. Full end-to-end genuine new original source→slides→narration→WAV→synchronized multipart MP4 acceptance, historic stacked PR independent review and final release authority remain separate unsatisfied gates. No other computers, local models, Ubuntu checks, paid API/TTS, bulk merges, or per-PDF retry loops.
