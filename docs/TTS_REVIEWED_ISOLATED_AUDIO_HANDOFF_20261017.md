# MicroGen_AI_Web — reviewed TTS repair handoff

**2026-10-17. New code is REVIEW ONLY until human listening, math/voice review and separately approved course publication. PR #118 is stacked after #117.**

## Goal and trust boundary

A \`tts_qa_repair\` candidate is not an accepted replacement WAV merely because an AI transcript indicates a pass. The first command in this workflow only **audits** the untouched original and review copy. Its result is not an approval and does not create any files.

An independent person must **listen** to all proposed audio, verify scientific/math pronunciation, the **Kore** narrator voice and fidelity of the changed slides against the original narration. The person creates a *separate external attestation file* that binds their review to exact audio, script and report hashes. The package **never generates or signs this attestation for the reviewer**.

Even after reviewed export, the new audio is copied **only to a fresh separate folder**. The original WAVs, slides, scripts, MP4s and all review attempts are preserved. Reviewed audio does not grant authority to generate or publish student videos.

## Default, offline read-only audit

\`\`\`powershell
python -m selenium_pipeline.tts_qa_promotion --source "X:\Course\8.4" --review "X:\Course\8.4\.tts_qa_review_candidates\<review-id>"
\`\`\`

It fails closed unless all of these hold:

- Original and candidate are source-bound; script and original TTS manifest hashes match the recorded \`review_only_receipt.json\`.
- Fixed **gemini-3.8-flash-lite-tts / Kore** voice/model and exact script text/slide identities. No automatic Flash / Chirp model switching and no Whisper or transcription substitution.
- Original WAV hashes are unchanged; every reviewed WAV hash matches; every recorded \`attemptN_slideM.wav\` matches its hash and the final changed WAV agrees with the last attempt.
- Unchanged slides have unchanged bytes.
- Source-manifest slide \`source_text\` and \`tts_text\` match the script. Review report covers every slide, has a threshold at least **99%**, lists **pass** for every slide, and contains no pronunciation-major issues, critical token issues, or audio defects.
- The receipt still explicitly says **review only**, has no unresolved QA failures, and contains no claims of existing academic or student-publication approval.

All error exits preserve existing assets. An audit passing means **eligible for independent review**, not proof a human already listened.

## External human-review attestation

After independently listening and checking mathematics and voice, a human reviewer creates a JSON file outside the source and candidate folders:

\`\`\`json
{
  "reviewer": "Human reviewer identifier",
  "reviewed_at_utc": "2026-10-17T07:00:00Z",
  "review_scope": "tts-audio-only",
  "audio_listened": true,
  "mathematical_pronunciation_reviewed": true,
  "voice_kore_listening_verified": true,
  "receipt_sha256": "<EXACT SHA from audit>",
  "fidelity_report_sha256": "<EXACT SHA from audit>",
  "source_script_sha256": "<EXACT SHA from audit>",
  "source_manifest_sha256": "<EXACT SHA from audit>",
  "candidate_wav_sha256": {
    "slide1.wav": "<EXACT SHA from audit>",
    "slide2.wav": "<EXACT SHA from audit>"
  }
}
\`\`\`

The SHA values are **placeholders**; the reviewer must copy the actual fields from the audit, not the example. The checks reject a missing, invalid or stale attestation. The file is a human **declaration**, not a digital signature or independent cryptographic proof of the person's identity; this limitation must remain visible to reviewers.

## Explicitly approved, non-destructive export

Only *after* independent listening and external attestation:

\`\`\`powershell
python -m selenium_pipeline.tts_qa_promotion --source "X:\Course\8.4" --review "X:\Course\8.4\.tts_qa_review_candidates\<review-id>" --destination "C:\ReviewedAudio\8.4-review-001" --attestation "C:\HumanReviews\8.4-approval.json" --confirm-reviewed-audio --confirm-isolated-export
\`\`\`

The **destination must not exist** and must be outside the original lecture directory and review folder. The implementation rechecks all hashes immediately before copying, writes into a uniquely named temporary sibling, and renames to the requested destination only after every script, manifest, WAV and \`tts_reviewed_handoff.json\` has been written. It refuses overwrite and cleans up only its own interrupted temp staging. The handoff receipt records \`human_review_approved=true\` solely for that **separately attested audio copy**, \`video_publication_approved=false\` and \`status=AUDIO_REVIEWED_ISOLATED_COPY\`.

### Not authorized or supplied by this functionality

- **No** original \`slideN.wav\` replacements, no source PDF/MP4 mutation, and no changes to production Drive-synced repositories.
- **No** billed Gemini/Google Cloud synthesis request; this handoff is local file/hashes only.
- **No** auto-generated academic approval, human attestation or Moodle publication.
- **No** use of this audio handoff as a shortcut around real timed narration-element highlighting or the strict **less-than-600-second duration per video part** rule.
- **No** automatic merge of development PRs or reassignment of distributed jobs.

All generated course content remains unreleased until authentic provider-produced audio, review of mathematical/figure integrity, figure multipanel scope, narrator fidelity, encoded-pixel/audio highlighting synchronization, review of every split MP4, and explicit publication approval.

The three working PCs are **HP**, **Dell-115** and **Yoga6**; Zenbook excluded. All changes are developed and tested in clean independent temporary checkouts, preserving uncommitted modifications in older Google Drive-synced repos.
