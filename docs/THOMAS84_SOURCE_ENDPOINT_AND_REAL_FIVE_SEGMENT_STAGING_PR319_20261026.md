# PR319 — Corrected endpoint mathematics and genuine five-segment source-bound production handoff

26 October 2026, Dell-115 Windows only. Stacked on verified PR318 exact `dc4a49f863de0d4ec704b05d89111ded19f96820`; its hosted Windows Actions reliability run #420 is now verified SUCCESS on both jobs.

## A further real mathematical subtlety, not another vague formatting issue

The sign correction in PR314 explained negative angles and `|x|`-valued triangle legs, but **did not yet explicitly account for zero-length legs** at the allowed substitution boundaries. A right triangle with a zero leg is degenerate (a limiting drawing), although the trigonometric squared identities remain algebraically valid. For `a>0`:
- `x=a tan u` on `(-π/2,π/2)`: at `x=0,u=0`, opposite leg length `|x|=0`.
- `x=a sin u` on `[-π/2,π/2]`: at `x=0` opposite leg is zero; at `x=±a` cosine leg is zero.
- `x=a sec u` on `[0,π/2)` and `x≥a`: at `x=a,u=0`, opposite leg `√(x²-a²)=0`.
- The principal-root `√(z²)=|z|` requirement and `a>0` branch signs remain unchanged.

We updated the **five revised source-registered narration texts** rather than the historical `script.txt`, adding explicit degeneracy and angle-domain explanations. Exact SymPy endpoint zero-leg tests guard the mathematics. We added generic `zero_leg_triangle_degeneracy` to the reusable sign/domain pre-TTS detector, triggering on future unqualified claims that a nondegenerate right triangle forms at a zero substitution angle/variable.

## GENUINE source PDF artwork, not synthetic media

New `original_slide4_corrected_segment_handoff` recomputes the five source-registered visual targets against the actual untouched Thomas 8.4 `source.pdf`, `slides.pdf`, and original script hashes, renders exactly five **real-original PDF-derived** highlighted PNGs (including Figure 8.2 three distinct strips), pairs each with one newly revised original-utterance SHA, correct source PDF rectangle, Kore/Flash-Lite TTS instruction, and expected unique WAV name. It never selects another element's original target and explicitly states **no audio time, independent review acceptance, correct spoken words, encoded MP4 or student release**. Output is new exclusive AppData review folder outside G: originals. Read-only original WAV SHA preserved.

**Critical:** the earlier Gemini source-locked corrected-script review returned 0 characters and its one-use window remains consumed/locked (PR317/318). This PR does not resubmit, claim an AI first pass or fabricate a second pass. TTS is still gated until independent source-grounded academic acceptance. Genuine new Kore WAVs and six encoded synchronized <600s replacements do **not** yet exist. This output is a directly actionable production input, not a replacement lecture.

## Test and follow-up policy

Dell focused source/mathematical tests verify exact original source and audio byte preservation, endpoint correctness, zero remaining *known-pattern* sign/domain warnings, exactly five preview PNGs aligned with corrected utterance/visual SHA IDs, and that no corrected WAV is silently manufactured. Hosted Windows CI includes the new source-first tests and syntax checks, with genuine originals skipped on hosted synthetic-only CI (Dell tests run all).

Next: authorize and complete a **new distinct** two-pass source-locked academic review only after reconciling the prior zero-response attempt, then dispatch the staged Kore-only 5 TTS utterances on Dell under the established 3-attempt rule and verify actual spoken content. Replan all six video parts from authentic new audio and accept only real encoded pixel/time verified MP4s under 600 seconds. No Ubuntu/Linux jobs, no HP/Yoga/Zenbook, no Whisper, no protected original modification, no Moodle/YouTube publication without acceptance.
