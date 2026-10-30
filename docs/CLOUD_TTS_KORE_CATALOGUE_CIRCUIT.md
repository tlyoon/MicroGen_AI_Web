# Cloud TTS single-batch voice-catalogue and permanent-error circuit

This Windows-only follow-up to the original Google Cloud/Kore correction preserves all model/source/voice/attempt provenance.

On each real Google Cloud batch, validate the **exact selected voice** against the live `list_voices(language_code='en-US')` response before any synthesis. If credentials, catalogue, network or named voice are unavailable, fail closed without requesting paid speech. In particular a stale `en-US-Chirp3-HD-Corey` cannot be dispatched. Once preflight succeeds, all 13 genuine §8.6 slides can be attempted with `en-US-Chirp3-HD-Kore`, but no historical Corey failures may be relabeled or deleted.

If a permanent Cloud provider/voice/input error occurs despite preflight, stop further slides immediately rather than issuing the same failed request 13 times. Keep the original append-only hash-linked attempt ledger, full-batch single narrator output rules, and conditional Cloud billing guard. These tests mock the Cloud voice catalogue, fail closed for missing/invalid voice, and verify zero paid synthesis in those cases. A real read-only catalogue query on Dell-115 previously verified Cloud Kore exists and Corey is absent.

No cross-provider acoustic equivalence or MP4/source approval is inferred from matching the Kore voice name.