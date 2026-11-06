# PR527 — Gemini post-submission response attribution, recovery, and no-resend safeguard
6 November 2026 — Windows Selenium MicroGen_AI_Web, Dell-115 only

## Historical evidence and scope

At exact accepted PR526 commit \`ad461f4a7f40bda06ea7f0fd6fc78660d17fd3be\`, GitHub Windows CI run #672 passed both jobs. A genuinely new source, Serway §11.1, completed the figures stage with a source-bound accepted receipt. The next slides stage registered an actual Selenium Gemini user-turn and all uploaded files, but its captured model-response text remained empty. Later the vendor waiter recorded a blank Gemini conversation and returned as though waiting had completed. No valid Beamer reply or slides.tex/slides.pdf was accepted; the original stage receipt is \`STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY\`. Existing SHA-bound diagnosis was \`REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE\`, \`provider_outage_proven=false\`.

This is **not** proof of Gemini 503/504, API key exhaustion, login failure, or a defective textbook PDF. §11.1's failed slides submission is permanently claimed; **do not rerun** that source. The actual cause might be a Gemini-side failed generation or a changed/vanished UI response container.

## Reusable corrections in the standard production transport

1. \`vendor_template_v2/selenium.py\` now treats a persistent blank post-Send conversation as a classified \`GeminiPostSubmitUnverified\` exception after a bounded 12-second grace, rather than returning as if model generation had completed. Transient blank UI transitions followed by model content continue normally.
2. The shared response-scoped copy helper now rejects arbitrary clipboard text when no attributable latest model-response container exists, or that container has no visible content. It never treats a DOM mismatch as proof that the copied text came from Gemini.
3. \`gen_slides_selenium_v11.send_prompt_and_capture_transport_block\` attempts the Send routine once (\`retries=1\`) and, after an uncertain capture, consults the **already-owned tab** using the existing \`gemini_response_recovery.poll_existing_owned_response\` / \`response_snapshot_with_scoped_copy\` mechanisms. A complete, nonstreaming, explicitly structured Beamer reply may be accepted **only from that same tab**. No new prompt, file upload, Chrome tab, provider, or API call is created by reconciliation.
4. If recovery is not independently verified, the slide-generation transport fails with \`POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND\`. Its caller propagates this exception and must not advance to a second model attempt or a paid-API fallback. It never writes an incomplete reply as accepted slides.
5. The source-bound, automatic \`windows_gemini_stage_transport_triage\` adds \`REGISTERED_BROWSER_SEND_NO_ATTRIBUTED_REPLY_NO_RESEND\` when both the positive model-send marker and the new unverified-response marker exist. It still reports \`provider_outage_proven=false\` and \`automatic_resubmission_authorized=false\`. New flags are compatible with older immutable diagnoses; recorded stage results/logs and previous source approvals remain unchanged.

## Source-free verification and boundaries

New \`tests/test_gemini_postsubmit_no_resend.py\` exercises: permanent blank post-send, transient blank followed by completion, absence of response-scoped clipboard attribution, recovery from the previously owned completed Beamer response without a new Send, refusal to recover unrelated browser tabs, refusal to retry an unverified Send, and propagation through the production slides attempt loop.

Related established regression modules verify older Gemini send-visibility, owned-tab, response-quarantine, recovery and automatic stage-triage protections. The initial 7 new source-free cases and extended 61 focused unittest cases passed on Dell-115. Native Windows exact-head GitHub CI and broader regression are still separate evidence gates at the time of drafting.

There was **no new live model request** to §11.1 or any previously failed Serway/Thomas source, no Google API/TTS expenditure, no local LLM, no non-Dell device access, no Linux CI, and no student publication. A real new, distinct source must still pass figures → slides → narration → TTS → synchronised sub-600s MP4 plus autonomous scientific and speech QA before the production lecture release can be certified. Source-bound safety, no-repeat protections, and controlled historical PR integration remain mandatory.
