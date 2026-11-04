# PR499 - Fix generic original-source stage validator workspace routing

This is a reusable source-independent Windows bug fix, not a Thomas or Serway
PDF-specific science/diagram correction and not a new QA definition.

### Root cause and actual Dell-115 reproducibility

The already-existing template_v2 runner performs figure-mapping, slide
compilation, narration and script/math checks in each original section's
`.microgen_work` staging directory, then publishes accepted deliverables
beside the original (staged) `source.pdf`.

PR495's safe per-stage controller originally queried
`runner.check_valid("figures", source_folder)`. The **general runner's**
true Figure stage requires physically populated `crops/` and `pages/`
folders in `.microgen_work`, not the published lecture folder.
This made a genuinely successful source look invalid and prevented ALL
source progression, encouraging irrelevant repeated model attempts.

The fixed controller now:
- Verifies the original publisher, staged and actual `.microgen_work/source.pdf`
  all have the exact same SHA; symlink/missing workspaces are rejected.
- Runs the **existing** `runner.check_valid` against the actual isolated
  runner workspace for figures, slides, narration and script/math QA.
- Separately checks SHA of each officially published slides/script artifact.
- Reuses intact pre-send/no-resend receipts and never changes a semantic,
  audio, paid TTS, original source or student-release gate.

### Real physically accepted independent source, 4 November 2026

- Original Serway §24.4 `source.pdf` is a genuinely separate **two-page**
  electricity section on `E=-grad(V)` relationships, never a Thomas PDF fix.
- SHA **c7a26075414527bfbc3fdbc32b9c93ab60d18100d4a4d6f4f46de5e367ad16da**
  in publisher, staged original and runner workspace.
- Existing single bounded Selenium figures stage **completed with exit 0**
  (553.50s), created `Figure 24.11.png` and `Figure 24.12.png`.
- Before fix, `check_valid("figures", staged_section)` returned FALSE because
  the isolated workspace's pages/crops are absent from published folder.
- Corrected `check_valid("figures", staged_section/.microgen_work)`
  returned **TRUE**, with physical pages and crops present.
- The next original-source slides stage was started from this valid receipt,
  with its own immutable pre-send ledger; no billing, paid TTS or publication.
  Its final completion must be verified from the original job receipt.

### Scope of QA

Native Dell-115 unit tests exercise stage sequence, actual workspace routing,
workspace tamper, source/output SHA, timeouts and no automatic resend. No new
PDF-specific mathematical checks. CI is Windows-only. Release remains blocked
until a distinct real end-to-end original lecture and deliberate stack review.

Existing historical Thomas PR362 media is reused solely under its
scope-matching SHA, and the two timed-out Serway §§22.1/22.2 attempts remain
quarantined. Only Dell-115; no Ubuntu/other PCs/local model/student release.
