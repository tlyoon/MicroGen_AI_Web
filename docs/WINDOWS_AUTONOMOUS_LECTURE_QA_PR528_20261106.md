# PR528 — Autonomous source–audio–media QA preflight

## Reason and historical mechanisms reused

MicroGen_AI_Web operates on Dell-115 in native Windows. Owner contract does **not** require a manual lecturer academic review: domain checks should be AI-assisted, source-grounded and autonomous. Older `lecture_release_gate.py` has an explicit human-review workflow; it remains available for legacy uses, but should **not** be the only path to engineering acceptance. Student publication still requires separate owner authorization.

Instead of bypassing quality, this change connects **existing** verifiers without making new Gemini, Cloud TTS, audio, FFmpeg render or other model requests:

1. `ai_academic_review_consensus.reconcile_actual_review_queue`: two independently captured AI passes, real source PDF quote witnesses, exact slide target and complete original utterance IDs, zero disputes.
2. `automatic_math_semantic_qa.inspect_math_semantics`: no known blocking sign, domain or algebraic risk. Limited lint is not mathematical proof.
3. `tts_quality_gate.screen`: *existing* WAVs, independent Gemini audio-ASR receipts, relaxed phonetic screening and audio integrity; require complete element coverage, no missing ASR, material phonetic or technical rejects.
4. `production_video_contract.verify_series`: real MP4 bytes, source/plan hashes, actual FFmpeg-measured parts each strictly **under 600 seconds**, audio-aligned cues and encoded transition QA.
5. Source/slide/script/element-plan hashes and original AI review utterance SHA multiset must match exactly. Missing, duplicate, stale or unowned evidence blocks acceptance.

The read-only `windows_autonomous_lecture_qa.inspect` returns `AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED` **only** when all scoped checks pass; it still declares `final_full_lecture_academic_acceptance=false`, `acoustic_voice_identity_independently_verified=false`, and `independent_figure_diagram_semantics_fully_verified=false`. Thus a technically sound model/ASR agreement is never misrepresented as perfect voice identity or verified physical diagrams.

The native release board now accepts optional **all-or-none** arguments `--autonomous-qa-folder`, `--autonomous-qa-queue-root`, `--autonomous-qa-plan`, `--autonomous-qa-audio`, `--autonomous-qa-asr-dir`. It executes the same verifiers again in read-only mode, only attaches the new AI evidence to a **different** SHA-bound independently reviewed original MP4, and never treats an absent or incomplete report as academic approval, a merge decision or student-release consent. Default usage requires none of those options and remains compatible.

## Source-free Gemini connectivity observation (6 November 2026)

An explicitly source-free **single Send** Gemini web browser canary was
executed on Dell-115 using the existing
`windows_gemini_differential_probe --browser-canary-once` code, not an
original-source generation job. The complete Send claim was written in advance
at `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261106_PR528_GEMINI_BROWSER_CANARY_V1`.
Chrome attached; Gemini login and Flash mode were available; the Send was
independently registered. A valid model reply was subsequently captured and
validated as exact JSON. Terminal immutable outcome:
`VALID_CANARY_RESPONSE`; classification:
`BROWSER_SHORT_CANARY_WORKS_LONG_FORM_NOT_CERTIFIED`.

This disproves a continuous, total Gemini-web connectivity outage at the
sample time, but **does not establish sustained long-form textbook
generation**. No 503/504 HTTP API problem was demonstrated, no API billing
occurred, and no previously claimed source was resent. Do not silently
repeat this canary or reuse its prior Send budget.

The existing `windows_provider_route_evidence_preflight` now preserves
positively verified, historical *short-response* evidence as
`prior_short_browser_generation_success_recorded` and selects
`GEMINI_BROWSER_PRIOR_SHORT_CANARY_OK_LONG_FORM_UNTESTED` for an authenticated
unsuppressed Gemini browser. It still reports long-form generation as
unverified, allows no automatic model generation, and does not override
source-bound visible-error or health-halt evidence. The existing immutable
canary claim+receipt verifier remains the trust boundary. Source-free tests
cover positive evidence, invalid partial input and overrides. This change
belongs to PR528 rather than starting another PR.

## Verification and deliberately remaining limits

New source-free Windows fault-injection tests cover success at the *technical-only* scope and rejection of incomplete AI consensus, missing or duplicated WAV evidence, missing independent ASR, changed source/plan/script hashes, incorrectly long MP4 and no pixel-reverified source-bound plan. Production depends on existing unmocked real validators; injected functions are only offline test seams.

**Not yet complete:** A new original lecture successfully passing figures → slides → narration → Gemini Flash-Lite TTS → highlighted multipart MP4; autonomous multimodal source-figure meaning and audible voice-continuity checks; reviewed historical PR dependencies; formal production installation and separate publication permission. Do not revise the definition of release success to match incomplete evidence.

No Serway §10.1/10.2/11.1/11.2 replay, paid API/TTS, local LLM, non-Dell machine, Linux CI, or student publication.

## 6 November 2026 — Source-sized synthetic Gemini health: one-shot failure

A new, **one-time** Gemini web diagnostic profile was added to the existing
`windows_gemini_differential_probe`, reusing the prior synthetic 1,200–3,000
character harmless test prompt generator and the existing immutable Send claim,
owned-tab Selenium capture, SHA-bound receipt verifier and no-resend policy.
The previous short profile remains backward-compatible and unchanged.

Live Dell-115 test at
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261106_PR528_SOURCE_SIZED_SYNTHETIC_GEMINI_CANARY_V1`:
1,535-character text-only prompt, authenticated Gemini Flash, positively
registered browser Send, ONE model request, no PDF or API/TTS. The *exact*
requested JSON was **not** returned. Immutable result
`NO_VERIFIED_RESPONSE`, bridge stage
`OWNED_RESPONSE_UNVERIFIED_QUARANTINED`. The independently owned model-reply
quarantine captured 104 characters of a terminal UI message:
`Gemini said ... I'm having a hard time fulfilling your request...`.
The SHA-verified quarantined text was inspected *read-only*; it is now
recognized by the shared classifier as
`GEMINI_MODEL_COULD_NOT_FULFILL_REQUEST`, not an HTTP 503/504,
login failure, API key-rotation failure, or proven total browser capture failure.

The normal `map_and_rename_selenium_v8` figure-mapping watcher now asks that
ONE strict owned-model-response classifier to inspect all completed responses,
rather than using a separate outdated string heuristic. It stops safely for
recognized terminal errors without retry or paid API fallback.

Read-only provider route preflight now distinguishes prior source-sized
success from prior short success. A verified SHA-bound source-sized failure
plus a verified owned-model UI error suppresses new automatic Gemini-browser
selection and never resets any old source attempt. The actual read-only route
reported `CHATGPT_BROWSER_AVAILABLE_FOR_A_DISTINCT_NEW_JOB_ONLY`, with both
logins authenticated and **no authorization for automatic generation**.
This is an alternative *candidate* for a future distinct source, not proof of
long-form ChatGPT output. No service trial was repeated and no previously
failed Serway PDF was resent.

Local tests: **54 targeted pytest PASS** covering normal figure-mapper failure,
strict owned-model UI variant, immutable quarantine, source-sized/short
profile isolation and no-resend, and provider selection. GitHub exact-head
Windows CI still needs fresh verification after these follow-on changes.
The earlier short Gemini canary and its genuine success remain intact.
