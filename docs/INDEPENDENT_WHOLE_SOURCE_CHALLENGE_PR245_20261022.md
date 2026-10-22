# PR245 — Non-cherry-picked original-textbook challenge evidence

22 October 2026, Dell-115-only isolated checkout, stacked on PR244 HEAD `d959f82fb5f63e849ccdb693663f7e2c95c29149`.

## Problem
PR244's compact independent challenge excerpt used the original first Gemini review's cited source page(s) to select the sole textbook passages for a second reviewer. The second model could not independently identify an alternative textbook page if the first reviewer overlooked it. This was a source-scope limitation, NOT an established Figure 8.3 figure defect or a proof that existing review mathematics was wrong.

## Correction
For a source textbook PDF of one to eight physical pages, include the **complete extractable text of every original physical page**, in source order, rather than only pages named by the first reviewer. Preserve independent citation validation, exact source/slides/script SHA, original narration and target geometry, and 65,000-character maximum evidence packet. Do not silently truncate textbook or slide PDF text. Reject sources exceeding eight pages or the packet bound: a separate explicitly bounded source review is required. Text-inaccessible mathematical figure semantics remain UNRESOLVED. No original source or prior model attempt modified.

## Observed Dell-115 validation
- Four focused real-PDF adversarial tests passed, including uncited alternative pages and fail-closed nine-page sources.
- Real original Thomas 8.4 `source.pdf` has six physical PDF pages. Each page's extracted text was included in a real local packet without model/provider calls.
- Isolated generated packet: `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\pr245_real_84_fullsource_excerpt_verified.txt`; 37,519 bytes; SHA256 `90e8591a0b2d1ad9ff93562fe7cd90780ea61af924646e988562d54ea6817333`.
- A 17-test broad `test_ai_*.py` local run had 14 tests with no assertion failure and three IMPORT ERRORS (local Python lacks NumPy). These missing-dependency failures are not claimed as passes; rely on remote CI for complete regression confirmation.
- No Gemini attempt #3 submitted, no Flash-Lite/Kore TTS invoked, and no student publication.

## Current acceptance truth
8.4: 71 original utterances on 17 original slides; only one imported first-pass original reviewer item and zero independently challenge-agreed utterances. Genuine new element-level Kore WAVs: zero. Final academic/listening-approved synchronized replacement MP4s: zero. Earlier six sub-600s originals-WAV whole-slide review videos are not production acceptance.

## Next
Diagnose Gemini web response/transport health without consuming an academic retry and without unsupported approval. Once demonstrably functional, obtain genuine original-source independent mathematical reviews and coherent original geometry; preserve retry quarantine. Then legitimate source-backed per-element same-voice Flash-Lite/Kore audio, encoded <600s synchronization checks, acoustic/academic QA and separately authorized publication.