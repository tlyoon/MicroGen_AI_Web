# MicroGen_AI_Web — restored approved TTS cost and fallback contract

Date: 2026-10-17. Supersedes the over-restrictive rules in draft PRs #114, #115 and dependent review documentation. This corrective branch is stacked after #119, **draft/unmerged**.

## Standing authorization for routine lesson production

The course owner explicitly authorized ordinary metered Gemini 3.8 Flash-Lite TTS (Kore) and Gemini 3.8 Flash TTS (Kore) as routine production expenses. The standard pipeline runner, standalone TTS CLI and routine TTS QA repair no longer ask for a new Gemini cost flag for every invocation. **Experimental** Gemini API work (trial/handoff/Interactions routes) still requires explicit per-trial cost flags; this standing permission does not approve live scientific experiments or unlimited testing.

## Fixed ordered fallback

1. PRIMARY: `gemini-3.8-flash-lite-tts`, Kore; **minimum three full per-slide attempts** for transient failures before any fallback.
2. FIRST FALLBACK: `gemini-3.8-flash-tts`, Kore; restart the **entire lecture batch in an isolated staging folder** and allow at least three attempts for every failed slide.
3. LAST RESORT: Google Cloud Chirp 3 HD `en-US-Chirp3-HD-Corey` if and **only if** both Gemini model queues were exhausted by transient provider failures. Cloud is *not* reached on disk, parsing, authorization, missing credentials, malformed WAV or permanent API errors. Directly selecting Cloud without a prior verified fallback chain still requires `--confirm-google-cloud-tts-cost`.

All fallback voices for one subtopic must come from ONE successful whole-batch synthesis: **no mixing Kore with Corey, or different Gemini models within the accepted lecture**. A changed narrator is explicitly identified by the effective `primary.provider/model/voice` in `tts_input_manifest.json`; a detailed `requested_primary`, `fallback_chain` and per-slide `voice_consistency` entry records the source/actual identity. The transcript/audio still requires independent human review and MUST NOT be relabeled as the originally selected voice.

If Flash or Cloud fails, the original successful `.tts_candidate` WAVs and receipts remain untouched. The alternative batch exists only in a temporary isolated folder until complete. No original `slideN.wav`, script, PDFs, MP4 or published manifest may be overwritten; initial file collision preflight runs before provider access, and a failed commit removes only new files it created.

### Cost guard distinctions

- Routine Gemini TTS: standing owner approval, no repeated command-line consent required.
- Automatic Cloud fallback: standing conditional approval **only after both Gemini fallback gates**, using `conditional_cloud_fallback=True` internally, never a general Cloud entitlement.
- Manual/direct Cloud: explicit separate flag still required.
- Experimental/reviewed per-element Gemini Interactions API trials: explicit named flags remain necessary.

### Review, release, and distributed execution

Successful audio synthesis alone is **not** scientific or student-publication approval. QA repair uses the actual recorded provider/model/voice and keeps replacement candidates review-only. If fallback changes voice, listening and mathematical pronunciation validation must specifically address the change. A reviewed slide-level WAV must never be invented as multiple per-element recordings. Every eventual MP4 part must be strictly **less than 600 seconds**, with pixel-verified highlighting synced to the correct voiced equation/text/complete multipanel figure.

HP, Dell-115 and Yoga6 are the only authorized distributed PCs; Zenbook excluded. Use isolated temporary Git checkouts and leave dirty Drive-synced source repos intact. No GCS/paid cloud lease or Moodle publication is involved.

Verification is offline-only unless a future specifically authorized production job is explicitly initiated. Passing mocks do not establish service reliability or acoustical voice sameness.