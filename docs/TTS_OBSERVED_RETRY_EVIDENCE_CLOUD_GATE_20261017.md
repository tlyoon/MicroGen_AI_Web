# Observed TTS retry journal and Cloud cost gate

**17 October 2026 — stacked draft after PR #121.** Preserves routine paid Gemini Flash-Lite/Kore -> Flash/Kore -> conditional Cloud Chirp3-HD/Corey after both model queues each fail at least three times.

## Why this change is needed

Earlier manifests stated `fallback_chain=[gemini-3.8-flash-lite-tts,gemini-3.8-flash-tts]` without a separate source-bound event record. Such a declaration was not sufficient evidence that a higher-cost Cloud request was justified. QA-repair and reviewed-audio paths could also be misled by a forged manifest.

## Immutable per-observed-call evidence

`selenium_pipeline.tts_attempt_evidence.AttemptEvidence` stores a source-bound journal in `<subchapter>/.tts_attempt_evidence/`. `identity.json` binds the exact original `script.txt` SHA256, every numbered slide narration SHA256, and the approved Flash-Lite/Kore origin. Each completed provider call (returned WAV or caught exception) creates a new exclusively named six-digit JSON record with provider, model, slide number, queue round, observed result (`success`, `transient_failure`, `permanent_failure`), exception class, previous-record SHA256 and a calculated record SHA256. Records are synced to disk and read back to validate the hash chain. A call interrupted before its result is recorded does **not** count as a failed attempt.

Before Flash fallback, the system requires source-matched, sequential rounds recording at least three retryable failures for a slide on Flash-Lite. Before Cloud, it requires the same evidence for **both** Lite and Flash, in correct model order, and rejects any incomplete, missing, reordered, malformed, unexpected or tampered record. Permanent errors, successful retries, circuit-breaker skips, a missing record, or a fabricated model-name list cannot count as exhaustion.

Whole-batch Flash and Cloud fallback stages share the **original subchapter's attempt ledger**, never an ephemeral ledger that disappears when the temporary synthesis batch is cleaned. The ledger's final hash, effective model and observed exhaustion summaries are bound into `tts_input_manifest.json` upon complete successful fallback. A failed batch preserves both its observed outcomes and previously verified primary WAV candidates.

## Human/audio/video handoff

`tts_qa_promotion.audit` verifies the journal against the original transcript, per-slide identity and manifest before it can accept a fallback repair candidate. An external human attestation must separately bind the journal's final SHA256. The optional isolated reviewed-audio export copies the journal with the WAVs and independently re-verifies the copied evidence before finalizing the destination. `tts_reviewed_element_compat` rejects a Cloud/Corey audio handoff without the original retry journal and its matching receipt digest. Selective Cloud TTS QA repair checks the same record **before loading credentials and before any billable repair call**.

**Important limit:** a local SHA256 chain is *tamper-evident* under ordinary accidental edits and omissions, not an externally signed or tamper-proof record of a real Google call. A program with full write privileges can forge an entire new chain; API billing data/provider audit logs are needed for independent confirmation. Likewise, offline mock tests are not real Gemini service proof. No API calls were made during this development round.

The original release requirements remain unchanged: source/figure/mathematics review, independently listened real narration with one consistent model/voice per batch, no silent Kore/Corey mixing, strictly **<600 s** for *every* MP4 part, decoded pixel verification of correct spoken equation/figure/text, and explicit Moodle-publication permission. HP, Dell-115 and Yoga 6 are authorized test PCs; Zenbook excluded. Production repositories and historical outputs remain unchanged. PR remains **draft/unmerged**.