# PR317 — Crash-persistent, no-resend academic-review checkpoints

**26 October 2026, Windows-only on Dell-115.** Stacked on verified PR316 head `05533f8efeaf97615621e60dfefb22fc6759d817`. Preserve three dirty working-tree files on G:, original textbooks/WAV/MP4, no paid API, no other PCs, no Whisper or publication.

## Exact provider failure

The genuine **corrected** Thomas 8.4 Slide-4 initial review sent an original source+slides two-PDF request at 12:50 Malaysia time with a verified Send control but received **0** model chars, then quarantined the empty response. The prior single-use window is `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261026_pr315_CORRECTED_SOURCE_LOCKED_INITIAL_REVIEW_ONCE`. A timeout/canceled browser connection DOES NOT prove request was never submitted. Silently trying again risks double submission and consumes quota.

## Normal academic request integration

New `selenium_pipeline.academic_review_checkpoint` persists a **unique canonical SHA-256** of the precise review prompt, original source.pdf, slides.pdf, script.txt, academic review mode, and optional corrected utterance SHA-256s. It writes a **write-once exclusive `dispatch_attempted.claim` BEFORE calling Gemini**. If a browser error, process crash, provider no-response, cross-device handoff or session restart occurs, a duplicate call under the same window is refused **even when the last JSON status update was not made**. It does not delete or clear a claim after timeout. The exact original PDF and script hashes are verified before preparing the checkpoint; no original assets are edited.

`ai_academic_web_review.run_web_review` now uses this durable transport checkpoint when a checkpoint directory is supplied; actual browser requests **must** supply one. The public CLI gains `--checkpoint-dir`; local unit-test transports can continue to inject deterministic fake responses without opening a browser. On successful capture, untrusted raw model response bytes and SHA are held privately inside the isolated local checkpoint. A complete source-validated **single-pass** result is returned but may not self-attest full mathematics or authorize TTS/publication; unresolved, zero-byte or mismatched source/hash responses remain blocked.

`academic_review_checkpoint --import-legacy` is an **offline/no-submission** one-time import of the historical exhausted no-response window. On Dell-115 this successfully created
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261026_pr317_IMPORTED_UNANSWERED_REVIEW`, with SHA-confirmed original Thomas source and exact original review prompt hash, `LEGACY_SENT_NO_RESPONSE`, permanent dispatch claim, `model_response_chars=0`, `can_auto_retry=false`. Re-import and re-dispatch are forbidden. No Gemini prompt was sent for this import.

## Validation and scope

Focused adversarial tests require: claim-before-call; fail-closed transport crash; zero-char response; no duplicate send; differing prompt, source or review mode; reject modified saved raw; distinct complete source-validator; rejection of fake auto-approved one-pass; legacy consumed no-response import. The model's claims still require independent source citations and another independent challenge pass. The checkpoint is **not a background agent**, cannot recover a reply already lost after a browser tab is torn down, and does not relax the explicit authorization requirement for a *new distinct submission window*.

Next technical priority is to use actual corrected Kore speech and source-mapped figure timestamp receipts to construct six **new**, safely staged synchronized replacement video parts: Thomas 8.4 slides 1–8 and 9–17, 8.5 slides 1–11 and 12–20, 8.6 slides 1–9 and 10–17 (repartition after genuine replacement audio). Historical MP4s are 10:33.93, 12:42.96, 10:30.96 and remain unmodified. No student-ready output exists yet.
