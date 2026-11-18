# Gemini owned-response diagnostic generalization — 16 November 2026

## Incident / historical record

MicroGen_AI_Web, authorized runner **Dell-115**, G2 Serway §1.3. The authentic Gemini **Pro/Medium** source-bound submissions for slides 10 and 11 registered one new user turn apiece but ended without attributable response. A later **two-synthetic-PDF, one-Send source-free** transport probe also failed, with a zero-sized untrusted reply and saved `0019.result.json`. A successful older *text-only* canary cannot establish PDF-response capability.

The existing response recovery system already correctly: (a) preserves the original claimed request without resending; (b) observes only the owned Chrome tab in a finite response window; (c) captures any actual model-owned response text for quarantine rather than scientific approval; and (d) stops the scientifically dependent G2 queue at the explicit exhausted-capability boundary. Source-science agreement remains **20/85; 65 unresolved**. This latest development addresses the *diagnostic evidence gap*, not the unproven cause of the external provider/browser failure.

## Reusable verified implementation

**New:** `selenium_pipeline/owned_gemini_dom_diagnostics.py`. It is an exact version-controlled, read-only diagnostic for the `OWNED_POST_SEND_RESPONSE_MISSING` failure signature. It first validates the **actual current owned Chrome tab** and optional exact conversation route. It checks the existing v6 recovery registry and fails closed when the handler is disabled or mismatched. It inspects only fixed DOM **counts/lengths**, never prompt text, raw response text, HTML, passwords, URLs, screenshots, other tabs, or clipboard content.

It distinguishes the following *observations*, not conclusions: model-response elements absent; alternative assistant-semantic elements present without model-response elements (possible selector drift); model-response elements present but empty; model-response subtree has some text; tab or route changed; DOM unavailable. Every result explicitly reports `provider_outage_proven=false`, `selector_defect_proven=false`, `academic_approval=false`, and `retry_authorized=false`.

**Normal production wiring:** `selenium_pipeline/series_gemini.py` calls that diagnostic immediately before writing the existing untrusted quarantine receipt **while the same tab is still owned**, on a failed strict JSON response or unattributable user turn. `selenium_pipeline/gemini_response_recovery.py::quarantine_snapshot` persistently writes only an allowlisted nested `owned_tab_response_dom` metadata object along with the original raw-response SHA, without altering response bytes, original source identity, one-Send controls or downstream scientific validation. No new request is made by the diagnostic.

**Versioned historical intelligence:** `selenium_pipeline/recovery_registry_v1.json` now includes `GEMINI_OWNED_DOM_DIAGNOSTIC`, with the exact code-reviewed mechanism `READONLY_SAME_TAB_RESPONSE_DOM_METADATA_NO_RETRY`, handler `OWNED_GEMINI_SELENIUM_RESPONSE_QUARANTINE`, applicability and test. The registry loader recognizes that permitted *transport-diagnostic* handler explicitly; arbitrary handlers remain rejected.

## Test and live evidence

- On Dell-115, targeted tests **89 passed** before the added full shared-browser fault-injection and registry negative test.
- Expanded real-code regression after those additions: **185 passed, 0 failed**, 5 nonfatal warnings across shared Gemini transport/capture, academic, source-evidence and G2 forward/restart suites.
- Tests include actual `series_gemini._browser_request` mocked one-Send failure with same-tab diagnostic saved before shutdown, route/owner loss, alternative assistant node, empty response element, poisoned telemetry, duplicated/mismatched/retired registry mechanism, no second Send, and unchanged quarantine SHA / QA protections.
- Read-only live inspection of the **currently active authenticated Dell-115 Gemini browser tab** returned `OWNED_DOM_MODEL_ELEMENTS_ABSENT` (zero visible model-response and alternate assistant nodes) without any Send or upload. **That live tab is not proven to be the original failed slide/PDF conversation**. This observation must not be misreported as proving backend outage, changed selectors or recovery of the historical failed response.
- A real G2 foreground restart previously confirmed `DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND`, zero new stages and preserved unattempted slide 12. The newly added diagnostic does not relax that same state.

## Decision and continuing acceptance

This is a **tested, reusable, privacy-safe diagnostic improvement**, not a successfully restored provider service. If future PDF-bearing Gemini requests fail *after an eligible independently authorized new operation*, they now persist more discriminating same-owned-tab metadata so that a future repair can be grounded in actual live DOM evidence. The current incident has exhausted its single-use diagnostic and **must not be replayed** merely to exercise new instrumentation.

The provider-dependent G2 scientific stages remain blocked until genuinely new independent attachment-response evidence or a validated saved reply becomes available. The executable normal recovery system continues other truly independent eligible development/QA work; no scheduled task is recreated, paid API is used, TTS/video is generated, external release is performed, or scientific QA is bypassed.

**PR status:** Commit and exact-head Windows CI must be verified separately; no claim of full-suite green or merge into `main` until actually observed.
