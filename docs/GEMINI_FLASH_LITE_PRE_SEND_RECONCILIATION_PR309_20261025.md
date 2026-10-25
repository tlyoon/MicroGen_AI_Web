# PR309 — Correct Flash vs Flash-Lite picker and pre-send evidence

25 October 2026, isolated Dell-115 Windows-only draft on CI-green PR308 head 646be59e255df5d84fe87724a6ec62b192f1014c.

## Genuine original Slide-4 academic review attempt

Following the owner's instruction, a single initial review attempt was started for the five original Thomas Calculus 8.4 Slide-4 utterances, against the existing protected 71-unit queue. The source/slide/script/queue preflight confirmed zero prior Slide-4 attempts. A separate durable intent was written before opening the Gemini browser.

The runtime attached to the authorized Dell-115 Chrome port and confirmed Gemini login. Gemini displayed 'Open mode picker, currently Flash-Lite', whereas academic source review requires Flash, not Flash-Lite. The built-in selector raised GeminiModelError: Model selection not confirmed for flash. The existing code saved the immutable file 'slide_004_initial_review_attempt_01.json' with provider_submission_state UNKNOWN_AFTER_POSSIBLE_SUBMISSION and manual_retry_eligible false. No successful academic source review was produced. Do not blindly retry or rewrite that receipt.

Root cause: the menu-item filter accepted any entry containing Flash unless it also contained Pro, unintentionally selecting Flash-Lite. The final mode-family verification did reject Lite. The old selector also reused a deadline established before browser attachment for final selection confirmation, sometimes leaving no time for a genuine UI change.

## Permanent fix and conservative provenance

The new _eligible_mode_menu_text function selects only Flash family menu entries, explicitly excluding Lite and Pro. A separate bounded deadline is applied to visible menu selection and later confirmation. Browser model evidence still proves only selected UI family, not exact server model/version.

The original-source review queue classifies future GeminiModelError exceptions from its OWN built-in pre-send transport (not injected transports) as CONFIRMED_PRE_SUBMISSION_MODEL_SELECTION_FAILURE. The built-in mode check always precedes file upload, prompt composition and Send. This classification is eligible only for a subsequent EXPLICIT manual request, never an automatic retry. A custom transport raising the same exception remains UNKNOWN_AFTER_POSSIBLE_SUBMISSION, because an arbitrary callback could already have sent. Historical unknown receipts retain their original classification, including the real failed Slide-4 attempt; no silent reclassification or resend occurs.

## Evidence

Dell-115: 25 focused and neighboring regression tests passed, covering Flash-Lite-first menu order, correct Flash High choice, Lite-only refusal, authenticated mode family checks, confirmed built-in pre-send failures, forged/custom transport ambiguity, old unknown receipts and returned-invalid responses. A real read-only model selection check after the fix returned 'Open mode picker, currently Flash High', selected_family_verified true, exact_model_id_verified false. That check did not send an academic request.

Actual full 71-unit queue has zero independently accepted original mathematical claims. A historical Slide-1 title-only receipt remains separately scoped and must not be pooled. Slide-4 initial source review and five genuine Kore utterance WAVs, audible content, synchronized highlights, decoded MP4 and student publication remain unaccepted.

## Next evidence gate

Independently reconcile the immutable Slide-4 attempt-01 model-family error against the earlier source-code ordering, preserving the original unknown-state receipt. A newly authorized manual attempt can proceed only after the reconciliation, with fresh queue, browser and original-source identity checks. Do not reset queue history, invent academic agreement or launch automated provider retries. Retain Windows-only GitHub Actions; no original source or historical WAV/MP4 changes, Whisper, paid APIs or publication.
