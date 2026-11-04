# PR515 — Canonical Windows Gemini quarantine paths, fail-closed safety retained

A global Windows portability issue—not any particular textbook PDF—broke
PR514's exact-head GitHub CI in BOTH Windows jobs. Windows PR514 CI run
`41832201000` reported:

- The full offline suite stopped at 734 passes when
  `test_prior_immutable_quarantine_reclassified_read_only` rejected
  a legitimate temporary quarantine.
- The fast Windows unittest job also failed that test and a tamper
  test; both were rejected before their intended SHA checks.

## Cause and correction

`quarantine_snapshot()` already persists quarantined Gemini response
files under `Path.resolve()`, which normalizes parent aliases and
Windows temporary directories. The independent PR514
`inspect_quarantine()` compared the **unresolved** `Path.absolute()`
metadata parent with its supplied `Path.absolute()` allowed root.
Unlike `resolve()`, `absolute()` retains `..` path segments and may
retain Windows temp/junction aliases. Thus the same physical trusted
directory could be rejected, before examining the stored SHA.

PR515 normalizes the **two** inputs identically with
`resolve(strict=True)`, after rejecting any direct symlink supplied
as the allowed root or metadata file. The existing safety boundaries
remain: the canonical metadata is required to be an immediate child
of the canonical explicitly allowed root; the file must not be a
symlink or oversized, must have a metadata suffix, valid schema and
quarantine status; the quarantine raw payload must match its existing
SHA, length and preserved immutable content.

The regression suite includes a deliberately noncanonical temporary
allowed-root alias `root / '..' / root.name`, matching a genuine
Windows path spelling that has identical resolved identity but
different `absolute()` identity. Existing wrong-root and raw-payload
tampering tests remain required. The code does not read user tabs,
resubmit Gemini, mutate any historic quarantine, or approve an
incomplete response as academic content.

This is a **general Windows evidence path** correction; it does
not reopen Serway 1.1, 22.2, 24.4 or Thomas Figure 8.3. It does
not certify Gemini API generation or fix browser UI server errors.
Previously observed exact owned-model UI error remains evidence that
Gemini produced an error message, not proof of a general 503/504 or
billing failure.

## Next release work

After native Dell-115 Windows tests, commit this fix atop PR514 as a
draft PR515, obtain exact-head Windows CI and inspect the same two
historically failing suites. Then continue bounded PR dependency
review and genuine distinct-source multimedia acceptance. Do not
mass-merge 400+ historic drafts or claim student release.

No paid Gemini API/TTS calls, publisher-source modifications, local
models, Yoga/HP/Ubuntu work, or student publication.
