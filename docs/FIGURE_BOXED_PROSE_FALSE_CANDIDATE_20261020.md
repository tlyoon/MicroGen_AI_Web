# False vector-figure candidate rejection — 20 October 2026

Repository: tlyoon/MicroGen_AI_Web. Dell-115-only development.
This work is a **corrective source-identification guard**, not Figure
8.3 certification or a narrated-video implementation. It supersedes the
apparently unique vector-drawing association described in draft PR #149
and inherited by PR #150.

## Independently observed real source PDF defect

Actual original Thomas Calculus 8.4 `source.pdf`, source page 2,
Figure 8.3; original SHA256
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.

The earlier preflight mistakenly associated PDF vector drawing #37,
rectangle `[197.89,424.406,557.39,562.906]`, with the original
Figure 8.3 because it was the sole large drawing near the Figure
heading. Real PDF text inspection shows that drawing #37 instead
surrounds the separate heading **Procedure for a Trigonometric
Substitution** and its numbered, paragraph-sized instructions. Its
rectangle contains 66 substantial alphabetic words on 8 dense
text lines. The true source Figure 8.3 refers to graphs of inverse
trigonometric functions located before the Figure 8.3 caption.
The complete source graph region and panel mapping are **not** yet
verified. The original text-block bounding box can merge figure
caption and neighboring procedure instructions; its proximity is
not sufficient evidence for artwork identity.

## Implemented conservative guard

`figure_vector_region_discovery.discover_vector_figure_candidate`
now counts independently extracted alphabetic word tokens whose
centres fall inside a candidate drawing rectangle, grouped by
original PDF text-block and line positions. It fails closed if the
rectangle contains either 25+ substantial words, or at least
14 substantial words distributed over 2+ dense prose lines.
The rule rejects boxed textbook prose before the misleading
candidate can reach source panel-label extraction.
Original source file and hash remain unchanged.

The rule is *negative evidence only*. A short-word candidate is
NOT therefore a true figure or author-approved set of full panels.
Even synthetic positive candidates retain all scientific,
source-panel, TTS/video and publication flags false. Long explanatory
text inside a genuine scientific drawing may also be rejected; this
intentional conservative behavior needs review rather than guessing.

## Focused, real and broader QA

- Original source read-only pilot: #37 rejected with
  `FigureIdentityReviewRequired` reason "encloses substantial prose
  or instructions", source SHA unchanged.
- PDF adversarial tests include an instruction box near a
  figure caption, a compressed single-line text case, and benign
  short panel/axis labels that remain **candidates only**.
- Dell-115 exact-head testing and GitHub CI evidence must be
  reported from executed results. No synthetic fixture is
  presented as real scientific verification.

## Next technical increment

First independently delimit actual graph and label geometry from
the original source drawing objects and caption without absorbing
adjacent procedural text. Check source-to-slide content identity
and original figure/panel completeness only with credible evidence.
When the figure remains ambiguous, preserve an explicit review
blocker. Speech-timed figure highlights and video certification
must remain blocked until source provenance is grounded.

Preserve all original teaching assets, dirty G: Drive checkouts,
old isolated checkouts, credentials, main branch and media.
Encoded video parts must be strictly <600 seconds, real element
highlights must follow speech, Flash-Lite/Kore primary TTS with
three genuine failures before approved homogeneous-voice
fallback. No HP/Yoga6/Zenbook use, Whisper, ASR, GCS distributed
lease, unverified publication or paid generation in this change.
