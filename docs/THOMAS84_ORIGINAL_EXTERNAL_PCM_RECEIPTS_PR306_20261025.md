# PR306 — Evidence-locked original Slide4 external WAV receipts, read-only

Dell-115 isolated Windows-only draft stacked on fully CI-green PR305 exact head `936699663c0a5a8cfbb16404ef216c8bf4bf15af`.

## Actual need and safe scope

PR305 integrates all **five** original Thomas8.4 narration/visual REVIEW candidates into the normal audio gate, but no real matching per-utterance WAV receipt has been supplied or validated. The existing `external_tts_delivery_proof.verify_external_tts_delivery` can check a single claimed Flash Lite/Kore provider record and PCM file hash, without proving text was spoken or verifying the voice acoustically. This PR reuses that existing verifier rather than inventing a second codec/voice model.

New `selenium_pipeline.original_slide4_external_pcm_receipt_gate` exposes an optional, explicit `--manifest` owner-supplied JSON input OUTSIDE the protected original textbook directory. It validates the bounded JSON schema and source identity/unchanged fingerprints, checks the exact five original Slide4 spoken SHA/utterance IDs and five completed source-bound visual REVIEW candidates, and invokes the existing WAV proof verifier for every separately listed external WAV. It never enumerates original folders, guesses file locations, invokes a provider, or writes historical audio.

It rejects duplicate/reordered/foreign IDs, altered narration text SHA, missing provider execution attestation, mismatched Flash Lite/Kore declarations, WAV SHA drift, WAV symlinks, files inside protected textbook tree, duplicated provider execution IDs or WAV files, inconsistent PCM sample clocks, silent WAVs and combined durations outside a conservative <540s prevideo review cap. It records exact measured sample frames and *hypothetical concatenation sample offsets*; those offsets are not transcript-forced alignment or proven highlighted-video timestamps. Voice identity still requires actual acoustic verification and speech content still requires independent listening/content QA.

**The sample receipt format is only for future already-existing user-owned external files.** The contract's Flash Lite primary and Google Cloud fallback after three real failed attempts remain unchanged. This specific original review pilot checks claimed default Flash Lite/Kore files and does not automatically authorize or block other compliant, separately documented fallback sequences. Paid synthesis, model health probes, Whisper and publication are not invoked here.

## Tests and remaining acceptance

Dell-115 synthetic PCM tests created five distinct mono PCM16 non-silent one-second WAVs under an isolated Windows temp directory and supplied explicit SHA/claimed model/voice receipts. Actual byte-level checks passed; per-utterance measured sample offsets were [0,8000,16000,24000,32000] for 8kHz clips. Adversarial changes to files/receipts/acoustic declaration/silence/rate/inside-source paths were rejected. **12 focused and neighboring tests passed**, 0 failed.

**NO owner-provided original five WAV receipt manifest was supplied during this run.** Therefore **zero real original Slide4 element WAVs** are presently validated. The synthetic test fixtures are not substitutes for genuine narration, academic review, voice or media QA. Full original 71-unit two-pass math queue remains 0 accepted, 71 unresolved, with separately scoped Slide1 title record not pooled.

Next meaningful step: safe sample-clock sequence and intended highlight event preflight from *verified actual external WAV receipts and five source visual candidates*, without pretending audio text content, voice or encoded frame synchronization are accepted. Original source fingerprint remains b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068, unchanged. No original source/media asset writes, release, paid API calls or non-Windows testing.
