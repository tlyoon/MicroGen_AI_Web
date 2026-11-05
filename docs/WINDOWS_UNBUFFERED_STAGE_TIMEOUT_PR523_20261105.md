# PR523 — Automatically retain stage progress and distinguish owned-process timeouts (5 November 2026)

**Workstream:** MicroGen_AI_Web (Windows-only Selenium), Dell-115. Not the independent API-based MicroGen_AI project. Stacked on draft PR522 `0bf6e9dcd9f0f451559a61c45e4ca523d1535ce8`, whose exact-head Windows CI run #667 passed both jobs.

## Evidence that motivated this general fix

One genuinely different original `G:\My Drive\Serway\Serway_8_14\10\10.1\source.pdf` (SHA `fb33af9a5fd164702c6b2aac708bd409098476fa48044535d9aec4e4a18a8a1f`) passed read-only one-stage preflight. A bounded, **single** Selenium figures invocation then recorded `FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY`, `model_browser_submission_outcome=UNVERIFIED` and shared health `UNKNOWN_SUBMISSION`. The immutable claim and result remain under `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261105_PR522_SERWAY10_1_ONE_FIGURES_STAGE_V1`, outside publisher sources. This PDF must NEVER be re-sent to test a diagnostic correction.

The real raw log contains only the pre-stage environment-loading print (`[microgen] loaded 4 environment setting(s)...`) and **no** independently verified figure extraction, Selenium attachment, browser Send or provider HTTP status. Existing `windows_gemini_stage_transport_triage` explicitly reported `SOURCE_STAGE_HALTED_NO_REGISTERED_SEND`, `owned_browser_send_registered=false`, `provider_outage_proven=false` and `original_submission_resend_authorized=false`. These are lack-of-proof classifications, not proof that no request was sent or that Gemini failed.

The one-shot Windows subprocess supervisor was already terminating its known owned tree at the finite deadline, but it used `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` **without** `PYTHONUNBUFFERED=1`. When Python stdout is redirected to a binary log, buffered progress messages can be lost when the owned child is terminated. An ambiguous failure then yields too little evidence to distinguish an import stall, source extraction, Chrome automation, and a provider response delay.

## Permanent general codebase improvement

- `windows_bounded_stage_process.run_bounded` now always sets `PYTHONUNBUFFERED=1` together with UTF-8 settings for new owned stages (regardless of inherited environment). This preserves new stage progress lines promptly even if a child terminates at its deadline. It does not trigger any retry, model call, browser login, TTS, or PDF edit.
- The supervisor appends a minimal explicit terminal marker **after** an owned process is reaped: `[microgen-supervisor] OWNED_STAGE_TIMEOUT NO_AUTOMATIC_RESUBMISSION SEND_STATUS_UNVERIFIED`; normal exit writes `OWNED_STAGE_EXIT_CODE=N`. These markers carry no prompts, credentials, textbook text or source paths.
- `windows_gemini_stage_transport_triage` detects the supervisor markers and distinguishes `OWNED_STAGE_TIMEOUT_WITHOUT_VERIFIED_BROWSER_SEND` from older buffered logs. It never infers a Gemini outage or authorizes resending the original source.
- Offline Windows fault-injection tests now use a real redirected Python child that prints **without flush** and sleeps beyond the bounded deadline; the retained log must include the print and supervisor timeout marker. Legacy buffered logs and earlier accepted/failed stages remain correctly classified.

## Verification and limitations

Dell-115 focused Windows tests `windows_bounded_stage_process`, `windows_gemini_stage_transport_triage`, and `windows_fresh_source_trial`: **24 PASS**, Python syntax and Git diff checks PASS. This is a source-free offline regression only. A new different source or future provider-health-approved invocation is required to observe improved real diagnostics; never replay Serway §10.1 or earlier failed §1.1 / §22.1 / §24.4 / Thomas sources.

Unbuffered logging cannot itself restore a truly unavailable model service or prove a send. It improves automatic root-cause separation and prevents the same opaque diagnostic failure from recurring. External provider service outages, user sign-in, complete scientific/voice QA, PR stack review and student release remain independently gated.
