# PR338 — Independent limited mathematical verification of core substitution rules

A new offline SymPy cross-check on Dell-115 verifies the exact algebraic
squared-radicand identities and differential derivatives of the three
standard substitutions used in Thomas §8.4:

- \`x=a tan u\`, \`sqrt(a²+x²)=a sec u\` on \`-π/2<u<π/2\`;
- \`x=a sin u\`, \`sqrt(a²-x²)=a cos u\` on \`-π/2≤u≤π/2\`;
- \`x=a sec u\`, \`sqrt(x²-a²)=a tan u\` on \`0≤u<π/2\`.

All require \`a>0\`. Each rule has independent symbolic squared-radicand
and dx derivative checks plus finite sign/root tests at representative
domain positions, including endpoints where appropriate. Actual output:
**3/3 limited rules PASS** on the original SHA-pinned protected textbook,
five negative/positive Dell Windows Python 3.12 unit tests PASS; wrong
derivative, flipped radicand sign and wrong root sign are rejected.

Important limitation: the finite domain sample checks are NOT a formal
proof of all possible branch values. This work validates the **formulas**
and tested sign conventions, NOT that any specific narration/figure
rectangles match, and is NOT an independent full lecture academic review.
Final student publishing remains false.

Source originals untouched; evidence outside original:
\`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR338_THOMAS84_THREE_TRIG_RULES_SYMBOLIC_PROOF.json\`.
No paid API or Whisper; Windows-only CI.
