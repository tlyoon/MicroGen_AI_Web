# PR278 — Read-only reconciliation of the real original mathematics review window

Date: 24 October 2026. Dell-115 only. Based on draft PR277 `03f419f4e912328cee86e4f41e6dcdf07dd60c40`.

## Implementation

New `selenium_pipeline.original_math_review_recovery` reports the state of an existing separately approved, source-bound mathematical review window. It binds the saved manifest and checkpoint SHA256 before and after inspection, calls the established original queue / mathematical consensus and scoped-window validators, verifies all accepted-plus-pending mapping counts, reports transport-health evidence and current worker-lock presence, and refuses drift or mismatched records.

It is **read-only** and neither reclaims an owner lock, resets attempt quota, sends a model request, invents a successful independent mathematical pass, synthesizes audio, publishes, nor modifies original textbook PDFs, narration WAVs, MP4s or protected main.

Invoke from repo root:

```powershell
python -m selenium_pipeline.original_math_review_recovery --window-root "$env:LOCALAPPDATA\MicroGen_AI_Web_Checkpoints\20261023_approved_separate_thomas84_slide1_window"
```

The output is an ephemeral **point-in-time report**, never a sufficient authorization for dispatch. A later owned-tab dispatcher must revalidate the original scope and the newly verified same-session health probe again immediately before any new academic request.

## Actual Thomas 8.4 audit

Run in an isolated Dell-115 checkout against preserved original `G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4`, original immutable queue and existing separately approved new window:

- Original source SHA256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
- Original utterances: 71
- Source-witnessed independent mathematical agreements: 0
- Outstanding/disputed: 71
- Preserved historical slide-1 failure receipts: 3
- Separately approved window confirmed model submissions: 0
- Separate-window checkpoint: READY; checkpoint lock: absent; no reconciliation state observed
- Fresh verified 1200–3000-character same-tab transport probe: absent
- Eligible new dispatch: **FALSE**; no Gemini request sent
- Genuine Kore utterance audio and publishable real highlighted video: **NOT established**

## Tests

Focused Dell-115 local invocation: `python -m pytest -q tests/test_original_math_review_recovery.py tests/test_scoped_original_math_review_window.py tests/test_gemini_review_backoff_checkpoint.py` → **23 passed**, five benign Swig deprecation warnings. Adversarial cases include original tampering, forged historical attempt, false academic ledger totals, occupied checkpoint lock, absence of health, and verified health still not sending.

## Next step

Obtain a genuine fresh same-owned-tab text-only structured transport-health response with the existing bounded one-shot diagnostic, subject to its cooldown and ambiguity reconciliation; **do not** automatically reset or repeat exhausted or unknown requests. Once independently verified, use the already approved isolated slide-1 review window for a single original-source mathematical challenge and save proof. Continue code work on multimedia gates independently if Gemini remains unresponsive. No approved mathematics or student publication may be inferred from CI success.
