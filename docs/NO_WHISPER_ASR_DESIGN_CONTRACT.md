# Non-negotiable MicroGen_AI_Web speech QA design: no Whisper

This document reaffirms the previously agreed non-API teaching-material
generation architecture and is intentionally enforced by
`tests/test_no_whisper_dependency_contract.py`.

## Mandatory rules

1. **Do not install, bundle, import, call or fall back to Whisper,
   faster-whisper, openai-whisper or CTranslate2-based Whisper ASR** as part
   of MicroGen_AI_Web, including as an optional dependency or silently
   enabled plugin. No local model provisioning, model downloads, or
   Whisper-specific validation jobs.
2. Speech synthesis remains **Gemini Flash TTS**, with the configured
   chosen voice preserved for a complete lecture.
3. The audio QA subsystem checks the original PCM WAV, SHA-bound script,
   verified per-segment model/voice identity, acoustic clipping/silence/
   loudness/pacing, independent transcription where the **approved Gemini
   transcription route actually supports audio**, mathematical signs/
   numbers/operators and synchronized MP4 highlights.
4. **Never present TTS as ASR.** Generating speech with Gemini TTS does not
   prove that the spoken audio matches the intended mathematical script.
5. Preserve independent Gemini transcript receipts and resume the
   outstanding clips only through an explicitly supported and authorized
   Gemini transcription mechanism. If Gemini browser audio is unsupported,
   report the failure and stop. The older Gemini API transcription route
   exists but cannot silently become the default or incur API charges.
6. No unverified clip can be treated as completed. A machine transcript
   discrepancy requires real listening/mathematical review; no false
   approval, automatic threshold relaxation, mixed voices or fabricated
   receipts.
7. This contract applies to all PCs and to users cloning the public
   package. Changes violating it must be rejected before merging.

## Corrective history and release condition

An exploratory offline-Whisper draft was briefly developed in **PR #104**.
That departure from the established contract was **withdrawn and the
unmerged PR closed**. A dedicated experimental Dell-115 virtual environment
and clean experimental checkouts on Dell-115, HP and Yoga 6 were removed.
No original lecture files, approved production environments, or earlier
Gemini audio receipts were modified.

The live Gemini web UI was previously tested with a WAV. It returned an
unsupported-audio response, and a follow-up probe failed at browser DOM
handling. Therefore that route is not currently considered verified ASR.
This must be solved within the approved Gemini-only constraints, not by
adding Whisper.

For the real corrected Thomas Calculus 8.4 review lecture, the available
Gemini independent transcripts still cover 14 of 48 segments: 13
machine-consistent, one mathematical phrase flagged, and 34 pending.
Its 48 narration WAVs pass current technical audio integrity checks.
**Academic and listening approval remain separate, manual gates**, and
student publication remains prohibited until the required checks pass.

## Automated test

```powershell
python -m unittest discover -s tests -p test_no_whisper_dependency_contract.py -v
```

The guard inspects production Python imports (including literal dynamic
imports), dependency manifests and production-module filenames. It uses
only the Python standard library. Comments documenting that Whisper is
forbidden do not trigger a false positive. This protection is additional
to existing TTS and academic QA tests and is expected to run in CI.
