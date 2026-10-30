# PR #368: Restore original Google Cloud Chirp 3 HD Kore default

**Authoritative owner requirement:** Google Cloud TTS must not default to **Corey**. The original shared `main` repository constructed the Cloud voice dynamically using `_named_voice(voice)` and `en-US-Chirp3-HD-{named}`. Under the existing production default Gemini Flash-Lite/Kore, this is exactly **`en-US-Chirp3-HD-Kore`**. The original tracked test `selenium_pipeline/tests/test_tts.py` also expected this Cloud Kore ID.

## Verified regression and cause (Dell-115, 30 October 2026)
- Isolated development checkout was wrongly hardcoding `en-US-Chirp3-HD-Corey` in `tts.py`, fallback provenance `tts_effective_identity.py`, downstream video recognition, QA repair and expected tests. `git blame` attributes the hardcoded fallback to commit `1da1095`, dated 2026-10-28.
- Real §8.6 source-bound TTS stopped after both Gemini model tiers exhausted, because Google Cloud returned a permanent **400 InvalidArgument** for nonexistent `en-US-Chirp3-HD-Corey`.
- A **read-only Google Cloud list_voices(language_code='en-US') query using the project's configured Dell credentials** independently verified `en-US-Chirp3-HD-Kore` **available** and `en-US-Chirp3-HD-Corey` **unavailable**. The query did not synthesize or bill for speech.
- Original source textbooks, previously generated §8.4 and §8.5 WAVs, source manifests and dirty shared Drive Git checkout remain unchanged.

## Corrective code / safety guarantees
1. Restore the original `tts._fallback_specs` same-named-voice construction: default Flash-Lite/Kore -> Flash/Kore -> Cloud `en-US-Chirp3-HD-Kore`, retaining actual three-attempt exhaustion and fallback ordering.
2. Define a single canonical `CLOUD_KORE` in `tts_effective_identity.py`. Repair/production video and full-batch evidence checks now consume this canonical identity, eliminating scattered wrong copies.
3. **Reject stale Corey fallback specs prior to paid Cloud calls.** Do not rewrite a historical Corey voice receipt into a Kore receipt or silently reuse unverified audio.
4. Preserve **full-batch single-provider/single-voice** delivery, no partial mixing, and an independent post-provider audio review requirement; Gemini Kore and Cloud Kore naming does not establish acoustic identity.
5. Update Windows-only tests, Cloud/Kore-specific fallback status and listening evidence field, and add a regression comparing the original default chain, dynamic selected voice, rejected Corey spec and rejected stale Corey manifest. Keep rejected historical metadata intact; do not modify existing WAVs.

## Verification
- Dell targeted fallback/provenance tests and fault injection run without paid requests.
- New test module `tests.test_original_cloud_kore_default_regression` is included in Windows CI reliability and full suite.
- §8.6 production can be **resumed after this fix is merged/validated**, preserving source and genuine retry evidence; full fallback remains subject to the existing conditional Cloud authorization and math/audio QA.
- No Ubuntu/Linux/WSL checks, other devices, Whisper, student-facing publication or unsafe repo reset.
