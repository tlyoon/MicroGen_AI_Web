# Independent extractable source panel-label evidence — draft PR #150

19 October 2026, Malaysia. Dell-115 ONLY for local development/testing,
stacked on PR #149 at b23f22a91684c8233b09287550318b23ddf7051e.

## Narrow independent evidence

The new read-only `selenium_pipeline.figure_panel_label_evidence` assessor
inherits the strict uniquely caption-anchored source vector candidate.
It independently extracts an exact figure heading line from structured
PDF text and searches ONLY inside the bounded candidate drawing region
for literal `(a)`–`(f)` original-PDF word tokens. It rejects gaps,
duplicates and incomplete label sets as blockers. Label candidates and
their source-space bounding boxes are returned for review, not fabricated
panel region assignments. A word token may still occur in explanatory
text or an unrelated layer; therefore even a positive candidate NEVER
certifies author-intended complete panel extents, scientific semantics,
source-to-slide equivalence, synchronized narration or publication.

Input hash is checked again after the read. The function does not
generate or edit crops, source PDFs, slide decks, scripts, WAVs or MP4s.

## Real textbook result — Thomas Calculus 8.4, Figure 8.3

Read-only examination on Dell-115:
- Original source: `8.4/source.pdf`, source page 2.
- SHA256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
- Parent source drawing candidate: #37,
  `[197.89, 424.406, 557.39, 562.906]`.
- Independently extractable heading: `FIGURE 8.3` (one line).
- Extractable `(a)`, `(b)`, `(c)` words inside candidate: **none**.
- Result: `SOURCE_PANEL_LABELS_MISSING_OR_INCOMPLETE`. Full intended
  source figure, original panel labels/crops and science remain UNVERIFIED.
- Do not turn this candidate into production narrated media.

Focused generated-PDF adversarial tests: **14 passed, 1 skipped** when
run together with PR149 vector discovery tests on Dell-115. These check
unique original heading, distinct/consecutive labels, missing, duplicate,
gapped and outside-region tokens, original PDF SHA preservation, invalid
identifier/path and duplicated figure headings. Full-suite certification
depends separately on actual exact-HEAD no-exclusion regressions and
compatible installed SDK; any failures must be recorded without evasion.

## Next

Scientific validation must recover original author-intended geometry
from independently trustworthy evidence (possibly source vector/text
outline topology or inspectable source crop); lack of extractable panel
tokens is a hard review gate, not permission to invent (a)/(b)/(c).
Do not integrate figure narration or authorize video without such proof.
Preserve strict encoded video part duration <600 seconds, audible element
highlight synchrony, Gemini Flash-Lite/Kore primary and real retry/
fallback policy, immutable historical assets, no Whisper/Zenbook/GCS
distributed lease/Moodle or YouTube publication, no protected-main merge.
