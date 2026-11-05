# PR521 — Independently verify real ChatGPT Selenium response, reconcile owned drafts (5 November 2026)

**Project identity:** `MicroGen_AI_Web` (Windows/Selenium lecture system), NOT separate API-based `MicroGen_AI`.
**Base:** PR520 exact commit `7acf61ac5b0aa40a711f42f38ec75add9ce00bf4`, isolated Dell-115 worktree `%LOCALAPPDATA%\MicroGen_PR521_20261105`. No previous publisher files, credentials or original PDFs edited.

## Real live result — V5 success, no replay

A uniquely marked new, source-free ChatGPT prompt was submitted **once** from the authenticated dedicated port **9223** in the fresh checkpoint `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261105_PR521_CHATGPT_SOURCEFREE_DISTINCT_V5`. It used the exact locally SHA-verified, unsent *V3* draft only to permit safe replacement; V3 was NOT resubmitted. V5's fsynced send-click intent demonstrates the one-button attempt.

The old automation incorrectly returned `TIMEOUT_RECONCILE_NO_RESEND`, with `user_turn_confirmed=false` and `assistant_response_seen=false`, because ChatGPT's current visible conversation uses `ChatGPT said:` rather than the prior `[data-message-author-role]` DOM selectors. No second live send occurred.

Independent read-only Selenium inspection of the existing V5 conversation showed a newly created `https://chatgpt.com/c/...` page, one exact canonical user prompt and one assistant answer equal to `MICROGEN_CHATGPT_CANARY_3E0186832307_OK` (39 characters), directly under the visible `ChatGPT said:` label; no stop/generation active. New `--reconcile-existing` validates the original immutable one-send claim, prompt SHA, click-intent receipt, timeout receipt, unique existing conversation and exact assistant answer; it writes a *separate*, content-safe SHA-verified `chatgpt_canary_independent_reconciliation.json`, leaving the original V5 timeout unchanged. The actual Dell-115 returned `CHATGPT_CANARY_EXACT_RESPONSE_INDEPENDENTLY_VERIFIED`, `exact_marker_response_confirmed=true`, `model_submissions_this_call=0`.

**Evidence:** V5 response SHA-256 `20ffdbb56bc154b63ec476158386f26afadc4f06538568d25b9356c2f3a16d8e`; original result SHA-256 `25f3c72e5b56ad8c4f53117b942004c138e6239d77d1e41ee0e413d2435d65d9`. These are hashes of existing artifacts, not new generation. No original textbook source, paid API, TTS, video, or student publication was involved.

## Generalised code-level improvements

- `prior_owned_draft(checkpoint)` reconstructs an exact previous source-free draft only from canonical marker, prompt SHA and immutable claim/result; rejects changes, prior send-click-confirmed attempts, same checkpoint, or a foreign draft. It is a replacement authorization for a new independent prompt, **not** authorization to retry the old request.
- Current ChatGPT DOM fallback `_current_ui_exact_canary` accepts only a single canonical user prompt, exactly two marker occurrences, first visible `ChatGPT said:` answer exactly matching marker, bounded text, and following ChatGPT disclaimer. It never treats a user prompt echo as assistant completion, and never sends a prompt itself.
- `--reconcile-existing` reads only existing authenticated browser tabs; validates SHA-bound claim/click/result; does not open new tabs, click Send, call API/TTS, or modify the original receipt; reusing an accepted independent proof is zero-send.
- `_local_root` now resolves both the allowed `LOCALAPPDATA` base and requested checkpoint consistently. This fixes actual PR520 GitHub CI #665 failure: Windows CI temporary directory aliases previously failed an inconsistent `Path.absolute()` vs `Path.resolve()` containment check. Existing symlink and `..` traversal denials are retained, and new regression checks canonical equality and traversal.
- Windows CI already registers the new canary module and entrypoint (introduced in PR520), and PR521 extends tests for exact drafting, spoofed/malformed marker, no-send reconciliation, original evidence preservation, and temp-path aliases.

## Release status and next priorities

**Verified completed:** dedicated Chrome ChatGPT login, one actual Chrome Selenium submission of a new text-only source-free canary, real generation of the exact requested response, independent read-only capture, immutable hashed proof; source-free transport proof only. **Not yet certified:** full lecture PDF-to-figures/slides/script/TTS/MP4 integration, second independent real source, academic/perceptual QA, historical stacked draft PR merge/review, formal student release.

Historical PR520 CI run **#665 failed** on the newly introduced Windows temp-path test fixture, not on live ChatGPT generation. PR521 corrects canonical containment, with Dell-115 focused tests and exact-head Windows GitHub CI required. Never resubmit V5 or V1–V4; do not enter per-PDF fix loops; Dell-115 Windows only; no local LLM, HP/Yoga/Ubuntu, paid API/TTS, historic mass merge or publication.
