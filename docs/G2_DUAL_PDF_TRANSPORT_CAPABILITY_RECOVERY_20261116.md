# G2 Gemini two-PDF response capability recovery (16 November 2026)

## Root-cause investigation

On Dell-115, Serway §1.3 slides 10 and 11 produced positively registered Gemini **Pro / Medium** new-user turns, with the original source/slides uploaded, yet **no attributable model answer** after the bounded response capture and recovery observation windows. The quarantined response files were **0 bytes**. This does not identify whether Gemini's model service or the browser's model-response DOM path was responsible.

The older source-free canary had returned valid text, but was **not representative** of the two-PDF scientific-review workflow. Treating a successful text-only check as conclusive PDF-response health risked consuming an unlimited series of fresh academic request claims. The existing hard stop after two consecutive original no-response submissions was correct and must remain in force unless a stronger PDF response is established.

## Executable new recovery

- `selenium_pipeline/academic_dual_pdf_capability.py`: Generates **two fresh synthetic one-page PDFs** locally. Each contains a different cryptographic challenge value that is never included in the user prompt. It submits one attributed Gemini Selenium browser request asking to read both files and return exact JSON with the two hidden PDF tokens and a unique nonce. No original textbook PDF, lecture, user document, API key or paid TTS is uploaded. The same strict Pro/Medium model-family and one-Send attribution controls are used.
- A UTF-8/fsync **exclusive claim** is written before any browser Send, including the original source SHA, verified current model family, exact two prior original ambiguous request fingerprints, prompt SHA, two synthetic PDF SHAs and an incident identity. A successful response must have positively verified new Gemini user turn, registered Send, and **exact values sourced from both PDF files**. A short "ok", copied prompt, malformed JSON, or absent/unknown response cannot pass.
- Immutable `claim.json` and `result.json` are saved in `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/.microgen_g2_dual_pdf_capability_v1/<original_source_SHA>/<family>/<incident_SHA>/`. A missing result after a claimed Send never authorizes a duplicate diagnostic; at most one fresh diagnostic per incident and UTC source/model day is permitted.
- The normal `ai_academic_review_queue` continues to quarantine consumed slides 10/11 and any older original no-response requests. The selector returns `DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND` plus the `SYNTHETIC_DUAL_PDF_CAPABILITY_PROBE` action until a newer same-family PDF-capability proof exists. Only after proof may the **next truly unattempted** source review be considered; its original Gemini Send still requires separate source SHA/health/scientific QA validation.
- `academic_queue_fresh_send_health.check` recognizes a stronger same-family, later-than-original-PDF **dual-PDF** capability proof so that a successful PDF test need not be followed by a redundant, weaker, text-only model Send. It does not itself award any academic agreement.
- The normal `g2_forward_recovery_engine` persists the synthetic step as `SOURCE_REVIEW_MODALITY_CAPABILITY_PROBE`, records its version-controlled v6 recovery-registry mechanism, SHA-linked intent/result, and automatically advances to the fresh source review only if the independent PDF proof verifies. On failure it halts; no source/model claim is repeated. A crash between the stage intent and receipt is reconciled by read-only proof inspection, not a repeated Gemini Send. The existing 32-stage and 256-persisted-stage ceilings, source verification, independent science and paid-operation authorization gates are unchanged.
- `selenium_pipeline/recovery_registry_v1.json` includes the new code-reviewed recovery signature, preconditions, retry limitations and regression test location.

## Acceptance and limitations

Focus on original failure, positive two-PDF response, negative incomplete or prompt-echo response, ordinary unowned string, tampered result, claim crash, daily cap, next-incident stale evidence, legacy queue compatibility, source unchanged, and forward-engine conditional advancement under exactly one registry-tracked probe.

This is a **capability diagnostic**, not an assurance Gemini will always return a science reply. Even a passing test cannot certify source correctness or 85/85 review. When provider/DOM attribution remains unavailable the safe outcome is a persisted, named external boundary. G2/G3 remain open until the real two-pass scientific, acoustic, video and release gates are independently satisfied.

## Live proof and completion

The actual Dell-115 native G2 execution started `0019.intent.json` on Serway SHA `181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8`, with a new two-PDF synthetic claim at approximately 16:47 MYT, Gemini Pro/Medium selected and both PDFs positively uploaded. Record the actual result only after the immutable receipt and model response are independently checked. Never count a model Send as an accepted review or assert the broader Gemini issue is permanently cured on the basis of this probe.

## Actual failure-injection and live result

- Dell-115 focused preflight: **152 passed, 0 failed** in the expanded academic/recovery suite before the final no-repeat optimization. After optimization: **57 passed** in the focused dual-PDF, queue, health and forward suite.
- Real immutable `0019.intent.json` and `0019.result.json` source-bound journal: at approximately 16:47 MYT the normal G2 forward engine produced two locally generated one-page synthetic PDFs and positively verified **Gemini Pro Medium**, two file uploads and one registered new user turn. The original textbook, slides and script were not sent during this diagnostic.
- The bounded Gemini browser capture returned **no attributable response**. The saved immutable synthetic receipt has `status=DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED`, `error_type=SeriesBridgeError`, `gemini_new_user_turn_verified=false`, and no academic approval.
- The forward result records `G2_SYNTHETIC_PDF_CAPABILITY_DEFERRED`, `next_action=HALT` and `SYNTHETIC_PDF_CAPABILITY_NOT_VERIFIED_NO_RETRY`. Scientific source consensus stayed **20 of 85**, **65 unresolved**; next unattempted slide **12** was not submitted. The original failed slide 10 and 11 reviews were not replayed.
- The subsequent real **read-only** selector independently reported `DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND`, with `new_model_requests=false`. The normal forward engine now stops this exhausted incident before any additional intent, browser request, or paid action. A newly supported recovery incident or independently verifiable saved original reply is required to resume provider-dependent work.

**Inference limits:** The identical zero-answer condition on generated synthetic PDFs shows the problem is not specific to Serway's textbook content. It still does not distinguish Gemini backend failure from Selenium's model-response DOM attribution. A text-only canary cannot be used to override this result. The code repair has improved safe diagnosis, bounded idempotence and conservation of remaining scientific review attempts; it has **not** cured the live external Gemini PDF response failure.

All saved claims, incident controls and audit evidence are intended to survive new ChatGPT sessions and process restarts. No Windows scheduler, paid API, manual approval loophole, external publication, or G2/G3 completion is implied.

## Final no-retry regression and real restart verification

After integrating the consumed-probe/no-op guard, final Dell-115 combined academic, provider-health, recovery registry, supervisor and forward tests were **154 passed, 0 failed** (5 nonfatal warnings). The actual second normal G2 foreground invocation with `--execute --max-cycles 1 --no-auto-media` independently returned `G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY` with `DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND` and **zero stage cycles**. No new `0020.intent.json` was created and no Gemini submission, paid TTS, or source review was sent. The prior proof is immutable and cannot be repeated for this same failure incident.
