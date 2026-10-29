# PR303 — Windows-only MicroGen_AI_Web development and GitHub CI

**Owner contract amendment effective 25 October 2026.** This supersedes earlier cross-platform testing expectations.

## Authoritative Windows-only policy

- MicroGen_AI_Web is developed, tested and deployed for **Windows only**. No Ubuntu/Linux/macOS runner, platform-support test matrix or parallel cross-platform QA is required.
- **Dell-115 is the only authorized real local machine**. Hosted GitHub Actions Windows runners are authorized for independent test verification. HP, Yoga 6 and Zenbook remain outside the permitted test scope.
- The normal automated implementation and delivery remain non-API Gemini web UI / Selenium where already contracted; do not install Whisper or introduce paid API charges without authorization.
- Keep source-textbook and original WAV/MP4 assets untouched, maintain independent mathematical/source review and figure fidelity, genuine matching voice and audio proof, highlight synchronization and strict **every encoded video part <600 seconds**.
- Windows CI migration never authorizes a release, an independent academic acceptance, a new model request or source-file modification.
- Preserve portable Python that **works on Windows**. Delete Linux-only workarounds only when demonstrated unnecessary and safe. Do not delete useful codec, timing or error-detection regressions merely because they previously ran under Ubuntu.
- Historical CI logs and old incident documentation can continue to mention Linux as provenance; such records are not operative compatibility requirements.

## Actual workflow changes

Both pre-existing workflows were discovered and migrated, not only the main reliability workflow:

1. `.github/workflows/microgen-reliability-tests.yml` — fast `offline-regressions` now uses `windows-latest` and explicit PowerShell array splatting, preserving its **39** original unittest module inputs and **42** Python syntax-check entrypoints. Its `full-regressions` now invokes the unchanged complete `pytest -q tests selenium_pipeline/tests` on **one** `windows-latest` Python 3.12 runner, without OS matrix.
2. `.github/workflows/source-adjacent-output-tests.yml` — the independent source-adjacent publication and FFmpeg assembly tests now use `windows-latest`, retaining their original test names and workflow triggers.
3. `tests/test_windows_only_github_actions_contract.py` — guards the complete set of workflow filenames, Windows-only runner declarations, absence of Ubuntu/Linux/macOS matrices or bash-only commands, the two main Windows jobs, existing test coverage, and source-adjacent safety checks.

The fast job's old POSIX `\\` line continuation is not valid PowerShell. The converted workflow collects the exact historical modules/paths in PowerShell arrays and executes Python with native splatting `@regressionModules` and `@pythonEntrypoints`. A first precommit contract test caught an erroneous `@$regressionModules` construction; this was corrected and the test suite re-run before publication. Production Python source, video rendering, audio duration thresholds and original materials are not changed.

## Acceptance evidence

Run Dell-115:
- Windows-specific workflow contract regression plus existing real codec tests.
- Actual migrated 39-module fast test suite and 42-entrypoint Python compile using Windows PowerShell invocation.
- After pushed GitHub draft PR: both main hosted **Windows** jobs must be green, with **no Ubuntu jobs**. Source-adjacent workflow must also remain Windows-only and be checked when its trigger is applicable.

Dell-115 validation completed before push: (1) **298/298 fast regression unittest cases passed** using Windows PowerShell's native splatting for the exact original 39 modules, and **42/42 entrypoints py_compile passed**; (2) **9/9** Windows-only workflow/real AAC temporal focused tests passed; (3) the separately triggered source-adjacent safety suites passed **17/17** and **7/7** tests, respectively; and (4) PyYAML parsed both workflows successfully and found exactly three Windows runner declarations with the expected 2+1 jobs. Only historical SWIG/SyntaxWarnings were observed, not failing tests. These tests did not open or modify original teaching assets. Hosted Actions CI is still an independent follow-up.

If GitHub branch protection still requires an old OS-specific job name, update that setting **only with separate necessary authorization or after verified ability to do so**. Do not infer protection state from workflow configuration.

This is a platform-contract refactor; it does not complete the still-blocked original Thomas8.4 academic, audio-timing, synchronized media or publication gates.

## Latest exact input state

Based on PR #302 exact commit `4191c59c93e0c15a5625322c495c7595cfade5d6`, fully passing its former three hosted jobs. Historical Ubuntu AAC-test issue was resolved there; the 25 fps synthetic fixture and strict PCM/AAC temporal regression remain intentionally preserved as useful Windows production QA.
