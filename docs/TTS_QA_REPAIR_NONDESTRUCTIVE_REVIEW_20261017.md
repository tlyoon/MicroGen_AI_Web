# MicroGen_AI_Web: non-destructive selective TTS QA repair
**17 October 2026 — stacked draft after PR #116, review-only.**

## Defect
Prior `selenium_pipeline.tts_qa_repair.repair` would replace an existing `slideN.wav` *immediately after one TTS model response* and only then repeat narration fidelity QA. If the new voice mispronounced a variable or the request returned low-quality/incorrect audio, the historical WAV was already lost. An unchanged/legacy TTS manifest was insufficient evidence to support a new speech request. The existing runner could publish the replaced audio if QA returned pass even though independent human voice and academic review had not occurred.

## Corrective review workflow
- First perform existing QA against the original folder. If every existing WAV passes, no regeneration occurs and the ordinary report is returned.
- If any slide needs repair, verify a complete original TTS manifest with exact provider, model, voice, slide-to-text mapping, no fallback provenance, and valid original WAVs **before** generating any replacement speech.
- Create a new unique `.tts_qa_review_candidates/<unique-id>` folder containing **copies** of the original narration script, manifest and all slide WAVs. Bind a review receipt to original script hash, manifest hash and each original WAV SHA-256.
- Regenerate only failing slides; every attempt is retained separately as `attemptN_slideM.wav`. The active replacement is applied **only within the isolated review copy**, never to the original `slideN.wav`.
- Run the existing narrated-audio fidelity QA on the **review folder**, not on any original WAV. Produce a review-only receipt including source/model/voice, SHA-256 of original and proposed audio, attempted slide numbers and remaining failures. Leave academic and publication approvals false.
- If proposed audio remains defective, **raise an error and block the next pipeline stage**. Even if automated audio QA passes, **raise a separate independent-review-required error** so no student/video publication follows automatically.
- Any external modification of original audio during the review causes a failure. Each original WAV and every generation attempt remains preserved; no historical WAV is overwritten.

## Explicit limitations
There is **no automatic promotion command in this PR**. Such a command would require independent review and source/voice/audio-bound signoff, backup of all old assets, provenance validation and complete multipart MP4 QA. Existing generated Thomas 8.4/8.5/8.6 lecture assets are not replaced by this change.

This patch does not prove real Gemini 3.8 Flash-Lite TTS/Kore speech works in the browser or Interactions API. Paid requests require their own explicit authorization under PRs #112–#114. No Whisper, no automatic model/voice or expensive Chirp substitution. Original contract still requires synchronized highlighting of the correct spoken equation/figure/paragraph, correct multi-panel figure integrity, and **each video part strictly shorter than 600 seconds**.

## PC verification
All six replacement/exception scenarios in `tests/test_tts_qa_repair.py` run with standard-library `unittest` (no pytest installation required on individual PCs). Tests use fake responses only. HP, Dell-115 and Yoga6 passed 6/6 in isolated temp checkouts; HP also passed PR #116's candidate provenance/final-file/cost authorization checks (27/27). HP's original Drive-sync repo has three uncommitted files and remains preserved. HP has Python 3.12.10 with `google-genai 2.28.0`; other PCs previously verified `google-genai 2.25.0`.

This is a stacked draft/unmerged corrective implementation and is not production deployment, academic acceptance or authorization to spend API credits.
