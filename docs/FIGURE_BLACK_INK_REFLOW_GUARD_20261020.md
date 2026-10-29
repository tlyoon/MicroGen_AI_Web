# PR171 — fail-closed black-ink geometry guard for reflow

A blue/pink matching graph image may still have **all black axes
and text erased**. Earlier automatic triage accepted the colored
reflow even in that case. The new graph audit retains independent
color matching but requires nonempty *black axis/text ink*
symmetric normalized Chamfer geometry per panel before
**clearing the aspect-only false-rejection flag**. This is
only an ink-presence/shape check; no character recognition,
axis value, semantic formula, figure completeness or academic
correctness is inferred.

For authentic original Thomas Calculus 8.4 Figure 8.3 source p2
→ slide5 black geometry scores 0.02017, 0.004777, 0.035422
remain within a conservative empirically tested 0.045 limit;
all three colored traces and asymptotes still match. For
synthetic slides with the black axes erased, colored traces
still match, but the new black check does NOT clear the layout
false-blocker, and production remains blocked. The threshold
is not guaranteed to generalize to future figure styles.

Only Dell-115; parent PR170 exact SHA
`7b5b82162549e542f601846427c0a0b9a8bbd091`.
No mutation of original PDFs/WAV/MP4, no paid generation,
Whisper/ASR, distributed GCS lease, HP/Yoga6, Zenbook or main
merge. MP4 parts must stay <600s, real narration-synchronized
element highlights and human listening QA must remain separate.
