# PR361 — Physically repaired signed-reference-triangle §8.4 source mathematics and regenerated real lectures

This work follows full independent **66/66 actual source-PDF/narration semantic worklist PR360**, which exposed that generated Slide 8 displayed the opposite right-triangle side length as `x` despite tangent substitution admitting `x<0`. Under `tan(u)=x/2`, actual physical side length is `|x|` while tangent retains the sign of `x`. For test case `x=-2` and adjacent side 2, the true tangent is -1 but opposite length is +2; exact SymPy sign/hypotenuse checks PASS.

**Original protected G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4 untouched.** Starting with the existing versioned Slide17-corrected LaTeX source PR355, corrected only source Slide8 displayed `opposite=|x|` and one matching source Slide8 sentence2, preserving original `tan(u)=x/2` and prior complete integral `I=∫dx/√(x²−16),x>4` Slide17. Real original MiKTeX compile produced a full valid 17-page PDF. **All other 16 PDF pages bit-for-bit pixel-identical at 1.8x**; only Slide8 changes. Source/PDF/script receipt:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261029_PR361_SIGNED_TRIANGLE_SOURCE_PDF_SCRIPT_CORRECTED_NO_AUDIO`.

Actual source-locked routine Gemini 3.8 Flash-Lite TTS made **one authorized paid request, zero automatic retries**, existing Kore voice, producing a real decodable mono 24k PCM16 **15.56-second** source-math-corrected WAV SHA:
`e4c6672fff567f7c637cbb7998d44bf258dcd4caa68a02fb2c088513cb3eb0b3`.
Private WAV:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261029_PR361B_SIGNED_TRIANGLE_GENUINE_KORE_TTS_CANDIDATE`.
Fresh independent **unprompted Vosk 0.15** offline exact new PCM check with authenticated original model ZIP SHA returned **PASS_SIMILAR_SOUND**, similarity **0.97143**, **zero critical math/sign/circa contradictions**, and recognized explicitly the `absolute value of x` versus `sign of x` distinction. Receipt:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261029_PR361C_SLIDE8_NEW_KORE_WAV_VERIFIED_OFFLINE_ASR.json`.
Neither model/provider identities alone are claimed to prove actual exact spoken words.

**Actual full review-only media repaired**:
- Part1 source slides1–8, now corrected Slide8 + genuine new 15.56s Kore sentence2, exactly two previous original old sentence2 PCM clips removed and replaced by ONE real new voice clip. **426.89s** actual H264/AAC MP4, SHA `f91cebc44a84767864e5f52a46ae2fb5ebbf4e536434a25a6a79d4ca0a37b5af`. **50** old source clips SHA-reused and **6** new corrected source PDF Slide8 clips encoded; all **56** Part1 H264 source/PDF sample frames verified.
- Part2 source slides9–17 with original fixed Slide17 full-integration problem/Kore narration from PR355, actual video **313.81s**, byte-exact SHA `0a5221f85f235afa5bc911fa0d63ca57e10f04c3351de5a6ec22fb422fce62e9`.
- Both videos satisfy strict **<600s** requirement, original PCM otherwise sample-exact, original old source media untouched.
- An entirely **independent second-pass** source audit reopened final MP4s, fully decoded both AAC streams, independently decoded 56 final H264 frames and recreated 6 corrected Slide8 source PDF images, checked exact old original PCM retained, no old sentence audio duplicated; PASS.
- Private full media `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261029_PR361D_SLIDE8_SLIDE17_BOTH_SOURCE_MATH_CORRECTED_FULL_REAL_MP4S`, independent receipt `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261029_PR361E_BOTH_FULL_MATH_CORRECTED_REAL_MP4S_INDEPENDENT_AUDIT.json`.

**Five reusable Windows code/test modules** automate source-PDF sign-triangle correction, one-shot authorized TTS, source-PCM video selective reencode, independent final physical QA and defensive tests; Windows-only CI updated, no Ubuntu/HP/Yoga6/Zenbook/Whisper and no student publication.

**Strict caveat:** independent mechanical/media and soundalike QA does not by itself prove the detailed academic semantic alignment of all 66 full spoken utterances and their precise mathematical element visual focus. Next combined final academic/media/voice gate; no student-release permission until all academic evidence is accepted.
