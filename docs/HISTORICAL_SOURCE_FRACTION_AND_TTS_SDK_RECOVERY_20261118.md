# 18 November 2026 — Reuse existing fraction and isolated TTS SDK remedies

## Historical review / root causes

The Dell-115 full local historical suite at `68fc031` recorded **2,798 passed, 47 skipped, 5 failed** before the configured five-failure cap. These were NOT five independent Gemini model-router failures. Two reflected already corrected dynamic family/Thinking test expectations; one arose from a source-review format change; two reflected the protected default Python environment's obsolete TTS SDK.

1. **Caption/fraction worklist:** the genuine 17-Nov physically witnessed PDF fraction detector (`physical_fraction_review_targets.py`, registered signature `SPLIT_PDF_NUMERATOR_DENOMINATOR_OR_SUPERSCRIPT_UNRANKED`) emitted `math_fraction_review`, but `source_grounded_element_hints.source_evidence_worklist` still accepted only older `image_whole`, `math_row_group`, `text_block`, and `image_caption_panel`. On unchanged genuine Serway 6.4 source, the source worklist reported “Unrecognized or forged visual target kind.” This was an omitted downstream validation branch, not a missing model response or a reason to remove the new physically observed candidate.
2. **SDK:** October 17/27 historic work had already established modern Google Interactions SDK `google-genai>=2.25,<3` as a mandatory TTS condition. Dell-115's protected default Conda Python currently has `google-genai==1.4.0`, but the already initialized **isolated** October SDK virtual environment at `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/20261027_GEMINI38_SDK_ISOLATED_VENV/Scripts/python.exe` has `google-genai==2.33.0` and pytest installed. In that verified historical interpreter, 28 original TTS request-ID/wire/trial offline regressions passed. Neither SDK compatibility nor TTS billing authorization may be bypassed.

## Targeted executable repairs

- `source_grounded_element_hints.source_evidence_worklist` now recognizes `math_fraction_review` ONLY when the original registered source-mapping remedy remains active and the **same original slide PDF** regenerates the exact candidate dictionary, including span locations, glyph-text SHA, bbox, and false semantic-approval flags. The computation is memoized per slide. No invented mathematical equivalence, arbitrary highlight target, provider Send or TTS approval. **Reuses the existing historic registry entry rather than creating a duplicate root-cause signature.**
- `tts._modern_tts_worker_python` now detects an incompatible default SDK before any provider call and, if and only if exact registry entry `TTS_EXISTING_ISOLATED_SDK_RECOVERY` remains enabled, reuses the **existing** October Dell-115 isolated Python. It verifies that executable's genuine installed `google-genai` version and `HttpRetryOptions` via a finite local `python -c` subprocess. It never creates an environment, runs pip, reads keys, sends TTS/audio to Google, or authorizes a paid request. Explicit `MICROGEN_TTS_WORKER_PYTHON` remains authoritative; missing/linked/retired/incompatible fallback fails closed.
- `recovery_registry.py` adds exact category `tts_runtime_repair` and the code-reviewed `NORMAL_ISOLATED_TTS_WORKER_SDK_PREFLIGHT` handler. No registry value is ever executed as code; the TTS helper matches only the exact declared mechanism. The previous `source_mapping_repair` registry entry continues to govern original fraction generation AND revalidation.
- The two fake-client request-ID tests now mock SDK compatibility in their synthetic response tests; their purpose is *request-ID evidence*, not installed SDK compatibility. Three mocked-subprocess/watchdog tests explicitly mock the worker-runtime selector because they must intercept only actual worker invocations, not the preceding isolated-SDK preflight. Separate `test_gemini38_tts_interactions_sdk.py` and new `test_tts_historical_isolated_sdk_recovery.py` preserve fail-closed SDK checks and negative tests.

## Tests and live local proof

- Genuine unmodified Serway 6.4 candidate + worklist: source-worklist and historical fraction tests **21 passed**.
- Fault injection: forged fraction glyph SHA and retired registry both rejected; missing/incompatible/retired SDK venv and invalid explicit interpreter denied before any provider calls.
- Genuine Dell-115 TTS runtime: `_modern_tts_worker_python('gemini-3.8-flash-lite-tts')` selected the real previously enrolled SDK 2.33.0 interpreter with registry match; no source files, TTS text, credentials, audio or API requests involved.
- Genuine old isolated interpreter: **28 original offline TTS tests passed**.
- All five previously failed local test cases plus related safeguards: **47 passed**; broader regression and exact GitHub CI are separately reported after run.

This is **reused historical recovery integrated in the normal executable path**. It removes two local engineering/environment blockers but does not prove an actual TTS waveform, spoken mathematics, scientific approval, viable Gemini Medium thinking radio, attributable two-PDF answer, G2 (currently 20/85) or G3 completion.

## Normal restart contract

After focused + fault-injection + broad regression passes, commit/push to existing draft PR #530; check exact-commit GitHub Windows CI. Restart `g2_forward_recovery_engine` using the same source and queue paths, bounded one cycle, with `--no-auto-media`, preserve existing 20/85 acceptance and all previously claimed Sends. Continue only on genuinely verified new original review evidence and any separately authorized paid provider operations. A green offline test never bypasses original-operation recovery proof.
