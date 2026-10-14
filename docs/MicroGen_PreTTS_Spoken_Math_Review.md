# Pre-TTS mathematical narration: scientific and spoken-scope review

Status: advisory, no automatic scientific approval, no API calls.

The Thomas Calculus Section 2.2 pilot exposed seven spoken-math ambiguities in otherwise valid storyboard JSON: radical scope, fraction grouping, the precise domain of algebraic cancellation, and the distinction between rounded numerical values and actual limits.

Use the pure offline review generator before obtaining an independent qualified reviewer approval. On Windows, run from a clean repository checkout:

    python -m selenium_pipeline.spoken_math_review --storyboard C:\Review\part_03_storyboard_UNREVIEWED.json --source-bindings C:\Review\part_03_source_bindings_UNREVIEWED.json --out C:\Review\part_03_narration_review.md

It creates a source-page and semantic-element crosswalk for every narration segment, and advisory prompts for radical/fraction grouping, cancellation domains, inequality directions, multipart figure fidelity and rounding. It refuses overwrites and mismatched source page bindings. It does not call an LLM, require credentials, synthesize speech, or fabricate an approval receipt.

Mandatory review before real TTS:

1. Verify the complete source outline; read exact source typesetting, not PDF-extracted text alone.
2. For radicals, state aloud exactly which operands are inside the radical. For fractions, state exactly where numerator and denominator begin/end.
3. When canceling common factors, preserve every excluded denominator zero. For instance, (x^2+x-2)/(x^2-x) = (x+2)/x only where x differs from both zero and one.
4. Preserve complete labeled multipart original figures and match the caption to all subfigures.
5. Do not confuse finite-precision table values with the analytic mathematical limit.
6. Obtain independent qualified educator approval of the exact reviewed storyboard SHA-256, as required in Phase 4A. An advisory packet is never that receipt.
7. Listen to actual synthesized WAV files for signs, variables, grouping, pronunciation, truncation and one-provider/one-voice continuity.
8. Only after approval perform geometric PDF validation, TTS, real timing checks, MP4 review and publication acceptance.

The new review generator supplies an additional aid. It does not weaken the existing approved-outline and TTS-review-receipt controls. A clean review packet is not evidence that mathematical content has been fully checked.
