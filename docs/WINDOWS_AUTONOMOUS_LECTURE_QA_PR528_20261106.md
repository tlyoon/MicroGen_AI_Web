# PR528 — Autonomous source–audio–media QA preflight

## Reason and historical mechanisms reused

MicroGen_AI_Web operates on Dell-115 in native Windows. Owner contract does **not** require a manual lecturer academic review: domain checks should be AI-assisted, source-grounded and autonomous. Older `lecture_release_gate.py` has an explicit human-review workflow; it remains available for legacy uses, but should **not** be the only path to engineering acceptance. Student publication still requires separate owner authorization.

Instead of bypassing quality, this change connects **existing** verifiers without making new Gemini, Cloud TTS, audio, FFmpeg render or other model requests:

1. `ai_academic_review_consensus.reconcile_actual_review_queue`: two independently captured AI passes, real source PDF quote witnesses, exact slide target and complete original utterance IDs, zero disputes.
2. `automatic_math_semantic_qa.inspect_math_semantics`: no known blocking sign, domain or algebraic risk. Limited lint is not mathematical proof.
3. `tts_quality_gate.screen`: *existing* WAVs, independent Gemini audio-ASR receipts, relaxed phonetic screening and audio integrity; require complete element coverage, no missing ASR, material phonetic or technical rejects.
4. `production_video_contract.verify_series`: real MP4 bytes, source/plan hashes, actual FFmpeg-measured parts each strictly **under 600 seconds**, audio-aligned cues and encoded transition QA.
5. Source/slide/script/element-plan hashes and original AI review utterance SHA multiset must match exactly. Missing, duplicate, stale or unowned evidence blocks acceptance.

The read-only `windows_autonomous_lecture_qa.inspect` returns `AI_SOURCE_SPEECH_AND_SYNC_MEDIA_TECHNICAL_QA_VERIFIED` **only** when all scoped checks pass; it still declares `final_full_lecture_academic_acceptance=false`, `acoustic_voice_identity_independently_verified=false`, and `independent_figure_diagram_semantics_fully_verified=false`. Thus a technically sound model/ASR agreement is never misrepresented as perfect voice identity or verified physical diagrams.

The native release board now accepts optional **all-or-none** arguments `--autonomous-qa-folder`, `--autonomous-qa-queue-root`, `--autonomous-qa-plan`, `--autonomous-qa-audio`, `--autonomous-qa-asr-dir`. It executes the same verifiers again in read-only mode, only attaches the new AI evidence to a **different** SHA-bound independently reviewed original MP4, and never treats an absent or incomplete report as academic approval, a merge decision or student-release consent. Default usage requires none of those options and remains compatible.

## Verification and deliberately remaining limits

New source-free Windows fault-injection tests cover success at the *technical-only* scope and rejection of incomplete AI consensus, missing or duplicated WAV evidence, missing independent ASR, changed source/plan/script hashes, incorrectly long MP4 and no pixel-reverified source-bound plan. Production depends on existing unmocked real validators; injected functions are only offline test seams.

**Not yet complete:** A new original lecture successfully passing figures → slides → narration → Gemini Flash-Lite TTS → highlighted multipart MP4; autonomous multimodal source-figure meaning and audible voice-continuity checks; reviewed historical PR dependencies; formal production installation and separate publication permission. Do not revise the definition of release success to match incomplete evidence.

No Serway §10.1/10.2/11.1/11.2 replay, paid API/TTS, local LLM, non-Dell machine, Linux CI, or student publication.
