# PR522 — General-purpose ChatGPT Selenium recovery integrated into production (5 November 2026)

**Project:** MicroGen_AI_Web Windows-only Selenium lecture-generation; not the separate Gemini API-based MicroGen_AI. **Authorised computer:** Dell-115. **Base:** PR521 verified commit `be429e32228bdbbc84f41519021d6e9b8e5ab9d4`; exact-head Windows CI #666 PASSED all jobs.

## Problem and code-level correction

The genuine source-grounded production dispatcher `selenium_pipeline/rich_mapping_provider_dispatch.py` still called legacy `vendor.ChatGPTSeleniumClient.send_prompt_and_copy_response`, which used brittle text injection, could attempt multiple Send controls, depended on outdated assistant DOM selectors, and closed the temporary tab even when submission was uncertain. Earlier PR520/521 fixed a source-free diagnostic, but not this normal pipeline route.

New `selenium_pipeline/windows_chatgpt_once_transport.py` replaces the production ChatGPT route (not the separate Gemini browser route) with a native Windows-safe, single-submit transport.

- **Authentication + port isolation:** attaches only to an existing authenticated Chrome profile at port 9223; no guest login bypass, credential reads, new Chrome launches or other PC use. Gemini remains on 9222.
- **Input recovery:** detects the current contenteditable ProseMirror composer, inserts text using the Dell-115-verified focused `execCommand('insertText')`, and checks exact DOM readback. It may replace a restored draft only when the entire existing text is identical to a previously SHA-verified, MicroGen-owned, non-clicked source-free checkpoint. A confirmed prior click-intent, unknown draft or unsupported UI blocks safely without overwriting.
- **Submission boundary:** exactly one allowed Send click; a separate exclusive, fsynced `slide_NNN.chatgpt_click_intent.json` is written before clicking and contains only a SHA-256 of the prompt. No fallback Enter, no duplicate click, no other-provider retry after an ambiguous send.
- **Response capture:** supports the observed 2026 visible `You said:` and `ChatGPT said:` conversation layout, requiring one byte-exact user prompt, complete assistant response bounded by the ChatGPT disclaimer, no duplicate prompt, no extra turns, matching `/c/` owned conversation URL, disappearance of a Stop control, and three stable observations. If the UI changes beyond recognised evidence, the reply is quarantined rather than fabricated or resent.
- **Recovery and diagnostics:** source dispatcher distinguishes proven pre-click blocker `CHATGPT_PRE_SEND_BLOCKED_NO_MODEL_SUBMISSION` from `MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND`. Once claimed, the identical original source job is not auto-resubmitted. An uncertain owned browser tab is preserved for read-only later reconciliation; only fully verified completed temporary tabs are closed. User Chrome is never quit.
- **Limited operational scope:** no PDF/figure asset is modified; no paid Gemini API/TTS calls are made; no video is rendered or published by these transport checks. No regression on other providers is asserted beyond tests.

## Evidence

- Same-session Dell-115 source-free ChatGPT V5 one-click real response and immutable read-only reconciliation: `CHATGPT_CANARY_EXACT_RESPONSE_INDEPENDENTLY_VERIFIED`, exactly `MICROGEN_CHATGPT_CANARY_3E0186832307_OK`. This live test was completed in PR521, not repeated for PR522.
- PR522 offline unit/fault-injection integration and actual dispatcher tests **38 PASS** (after adding owned-tab tests). Proves true prod dispatcher chooses the bounded route and writes the click-intent path, while simulated pre-click failure persists zero-submission status and simulated post-click failure preserves ambiguous claim/no-retry. Synthetic JSON/DOM response extraction, stop guards, draft preservation, wrong port, one-click, and source untouched were tested.
- Dell-115 read-only check with 695 checkpoint entries: exact previously owned, non-clicked V3 draft is auto-recognised; unrelated draft refused.
- Relevant additional regression checks to be run at final exact commit and Windows GitHub Actions PR522; no claim that the full original academic multimedia lecture has passed.

## Acceptance boundaries and next work

These safeguards eliminate **known repeatable Selenium mechanisms** and replace repeated human debugging with checks, deterministic errors and safe recovery. They cannot silently defeat manual account login, a true provider outage, uncertain old sends, future unknown ChatGPT UI structure, or independent scientific/AV acceptance.

Next: exact-head Windows CI PR522, then general pipeline readiness and bounded original-source candidate selection for a second complete, independently verified lecture. Preserve the no-per-PDF-perfection-loop rule, Dell-115-only scope, no local models, no Ubuntu or HP/Yoga, no paid API/TTS without explicit stage consent, and no automatic historical PR merge or student publication.
