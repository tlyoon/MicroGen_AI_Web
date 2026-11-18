# 18 November 2026 — Historical source-PDF parser ABI recovery (no Send)

## Historical blocker and evidence

The original Dell-115 reliability record `docs/Dell115_TTS_and_Python_Reliability_20261012.md` already documents a Drive-hosted Python environment without PyMuPDF and a separate pre-enrolled local worker with PyMuPDF 1.27.2.3. Reusing the G: Drive venv for PDF tests reproduced that missing-package error. The installed Miniconda Python had PyMuPDF 1.25.2 and all 58 previously selected source/Gemini UI regression tests passed.

When the same **immutable** original Serway §6.4 source review was checked in the newer isolated PyMuPDF 1.27.2.3 worker, the saved review failed with `Model answer does not belong to this exact source/slides/narration request`. Neither original source nor the saved review had been altered. A source-free, read-only two-interpreter comparison established:
- Identical SHA256 values for original `source.pdf`, `slides.pdf` and `script.txt`.
- PyMuPDF **1.25.2** reproduced all 14 frozen saved request identities.
- PyMuPDF **1.27.2.3** reproduced slide 1 but mismatched slides 2, 3 and 5 in the first bounded check.
- For slide 2, original utterances and physical target descriptors had **identical** SHA256 across both versions; only the `source_page_excerpts` (PDF `get_text()`) hash changed. This exactly explains why the request SHA changed and why the strict identity validator correctly blocked reuse.

The problem is a **historical PDF text extraction ABI mismatch**, not a model failure. Disabling request-SHA validation or rewriting the old source/model receipt would be unsafe.

## Targeted normal-path recovery

The existing `original_source_e2e_acceptance.inspect_source_e2e` continues to validate the original source and actual immutable response. Only its specific `RichMappingError` request-SHA mismatch qualifies for the registered `HISTORICAL_PDF_TEXT_PARSER_ABI_COMPAT` mechanism.

The new bounded `historical_pdf_parser_abi_recovery.recover_readonly`:
1. Requires original source/slide/script SHA256, exact saved fallback manifest SHA and all no-model/no-TTS/no-publication flags.
2. Reuses ONLY a pre-existing local same-user compatible Python at `%LOCALAPPDATA%\miniconda3\python.exe` after path/link validation. No package install, credentials, new account, model API or browser operation.
3. Reruns the same **read-only original source verifier** in a bounded child subprocess. The child cannot request TTS, pass `--execute-prepared`, submit a model response or recursively launch another parser.
4. Accepts only the exact already-blocked source-review status `BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION`, unchanged source SHA, zero provider/TTS calls, no PCM, no render eligibility and no publication permission.
5. Persists a SHA-bound, restart-safe source-only recovery decision receipt outside publisher assets, but **always revalidates** the actual saved review rather than trusting the receipt alone. Tampering, linked files, stale manifests, timeouts or incompatible local Python fail closed.

The read-only normal CLI and direct `inspect_source_e2e` share the same verified recovery path; the source/media execution path cannot use this fallback when new `model_responses` are provided. The live executable mechanism is registered in `recovery_registry_v1.json` and allowed in the fixed handler map. The new regression module is enrolled in native Windows CI.

## Live verification / fault injection

The genuine Serway §6.4 previously failing one-test historical acceptance check now **passes under the original isolated 1.27.2.3 worker** by rechecking its saved 14-slide responses under the existing compatible parser; this does not change the result that 7/74 are saved-verified prose links and 67/74 remain unresolved. The original PDF/slide/script hashes did not change.

Fault-injection cases cover wrong publisher SHA, changed saved manifest, non-qualifying error, supplied new model responses, malformed/falsely authorized child JSON, source altered during the child, absent compatible interpreter, registry retirement, and nested child/execute risk. Local full adjacent Dell regression set: **80 tests passed** in original isolated environment; separate compatible-interpreter tests **24 passed**. No source modification, paid request, TTS, media output or student release was authorized.

## Remaining milestones

This is a **saved historical source-review availability repair**, not academic approval, audio-quality acceptance or successful PDF-to-MP4 generation. Serway §6.4 still has 67 unresolved source-visual-utterance mappings. The independent Serway §1.3 G2 P1 two-PDF Gemini model response remains BLOCKED_EXTERNAL_DEPENDENCY, G2 20/85 accepted, G3 and independent acoustic/video acceptance open. No original one-Send claim may be replayed or fabricated. Draft PR must pass exact-head hosted Windows tests before engineering acceptance; preserve all historical PR dependencies and publication restrictions.
