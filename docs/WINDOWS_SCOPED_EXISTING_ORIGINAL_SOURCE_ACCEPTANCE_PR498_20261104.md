# PR498 - Source-SHA-specific reuse of an already accepted complete original lecture

This is **release integration of already accepted evidence**, not one more
round of correcting Thomas calculus PDF equations, audio or Figure8.3.

The accepted PR362 final source-math/sound-alike-TTS/MP4 QA receipt from
29 October 2026 is now pinned by its physical SHA256. The generic, read-only
`windows_scoped_prior_full_media_acceptance` checks *exactly* its source PDF,
corrected authored PDF, and the TWO complete full original MP4s against that
unchanged receipt and its built-in trusted acceptance SHA. No video is
re-rendered, no audio regenerated, no word transcribed, no mathematical
semantic check repeated.

### Physical Dell-115 verification (4 Nov 2026)

- Frozen QA receipt SHA **c092169bf945f5aba10c62e55ebea7c02994b33081d0a5cdca983d48756643df**
- Exact preserved Thomas calculus 13th ed. original source SHA
  **b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068**
- Corrected original authored slides PDF SHA **6f9842512c2b12441eff58725b190f34db9fbea29d6eb302080ed78d3ad508da**
- Actual complete part 1 MP4 SHA **f91cebc44a84767864e5f52a46ae2fb5ebbf4e536434a25a6a79d4ca0a37b5af**
- Actual complete part 2 MP4 SHA **0a5221f85f235afa5bc911fa0d63ca57e10f04c3351de5a6ec22fb422fce62e9**
- Owner-approved existing prior audit: 66 source-narration meaning links,
  23 sourcebound relaxed sound-alike PCM checks, 104 actual decoded
  frame/source-PDF checks, real 426.89s and 313.81s complete video parts.
- **One existing full original source multimedia reference verified/reused**.
  This is NOT a fresh pipeline generation and not the distinct second source.
- Human every-word listening/voice identity is NOT certified and student
  publication remains strictly unauthorized.

The default Windows release board still reports release BLOCKED until exact
GitHub CI, safe stacked integration, a SECOND DISTINCT real original-source
lecture, and separate release authorizations. Operator may explicitly opt into
this historical reuse gate via:

```powershell
python -m selenium_pipeline.windows_scoped_prior_full_media_acceptance
python -m selenium_pipeline.windows_release_readiness_board `
  --jobs-dir 'EXISTING_PR489_JOBS' --fresh-trial-dir 'EXISTING_PR490_TRIAL' `
  --worker-python 'EXISTING_ISOLATED_VENV\Scripts\python.exe' --reuse-scoped-pr362
```

The text's 66 source-alignment prior checks and 104 frame checks are reused,
not redone. Other sources with different SHA, media edits, or unrelated PDFs
must never inherit these approvals. No Linux, HP, Yoga, local model, paid TTS,
student release, model resend or shared Git checkout overwrites.
