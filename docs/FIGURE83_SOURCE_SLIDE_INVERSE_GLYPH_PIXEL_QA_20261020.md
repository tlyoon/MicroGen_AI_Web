# PR193 — pixel-correlate exact Figure 8.3 inverse-operator glyphs from original PDF to displayed slide

20 October 2026, Dell-115 ONLY. Original Thomas Calculus 8.4 Figure 8.3 source.pdf page 2 contains actual **tan−1**, **sin−1**, **sec−1** printed inverse-function tokens. Existing slide5.pdf has a three-column bitmap reflow of those plots. The new independent source-to-slide validation:
- Extracts exact original PDF inverse-operator glyph bounding boxes (3x PDF raster) and finds each source-printed black-ink glyph in all three actual displayed slide figure panels, using OpenCV scale-swept binary black ink correlation; NO OCR/ASR.
- Crosschecks three source-printed names and unique panel positions against the original word layout and separately independently corroborated color-curve/black axes plot reflow.
- Requires each source original inverse-function glyph to be visibly present in the corresponding destination slide panel, winning by at least 0.075 normalized correlation against every alternative slide panel AND every competing source operator label for that slide panel, with absolute score >= 0.75.
- Real independently measured source/slide correlation matrix:
  - original tan−1: [.78845, .5830, .5712]
  - original sin−1: [.6943, .80213, .5599]
  - original sec−1: [.5686, .5619, .78747]
  Corresponding original-to-slide pixel score/margin: tangent .78845/.09412, sine .80213/.10780, secant .78747/.21627. All three **original inverse-function OPERATOR glyphs are visibly corroborated**.
- Strict integration into source-bound Figure 8.3 narration-to-panel candidate mapping: the parser now refuses mapping entirely if original PDF labels and displayed slide bitmap label ink fail. Four of eight utterances have one named original trig family candidate; four mention multiple/no families.

This is objective, independent source-to-slide pixel evidence and improves over an unverified assumption about figure order. It does NOT verify every x/a, theta, pi/2, graph asymptote/tick/math label or true curve equation mathematically, nor word-level voice correspondence. All original MP4s and slide WAVs untouched. TTS/audio generation, final narrated highlight acceptance, human math/listening QA and student publication remain blocked. Adversarial tests reject swapped/missing/ambiguous source-to-slide glyphs.
No other PCs, paid Gemini TTS, Whisper, ASR, GCS distributed lease or main merge.
