# MicroGen_AI_Web — exact-head Windows CI merge contract (2026-11-25)

This repo requires both jobs of the active microgen-reliability-tests.yml workflow to complete successfully on the exact current pull-request head before a squash merge to main.

- offline-regressions
- Full offline suite (Windows, Python 3.12)

Enforcement layers: GitHub branch protection for main (strict status checks, admins included, no force push) is the server-side guarantee. The executable selenium_pipeline.development_ci_gated_merge_v1 is an additional fail-closed local gate used by any autonomous development session. A local check alone cannot prevent someone from merging using a different GitHub client while the branch is unprotected.

The gate fetches the current PR, main branch, exact active workflow identity, latest workflow run tied to the exact PR head SHA/branch, all completed jobs of that specific attempt, and checks a complete successful outcome. It repeats the full check immediately before merging, then uses gh pr merge --squash --match-head-commit HEAD without --auto or --admin. If the base or head changes, status is pending/failed, jobs are missing, or a request becomes uncertain, hold only that PR and continue other eligible work. Do not reuse older successful runs, create fake check receipts, or publish student materials.

Usage after PR creation, while signed in with the existing GitHub account:
  python -m selenium_pipeline.development_ci_gated_merge_v1 --pr NUMBER
  python -m selenium_pipeline.development_ci_gated_merge_v1 --pr NUMBER --merge --receipt ABSOLUTE_PATH.json

Every PR triggers both Windows jobs. No Ubuntu testing, no Gemini/ChatGPT API calls and no scientific, acoustic, video, financial or publication acceptance can be inferred from CI status. All original source-identity and finite model-request campaign checks remain independently mandatory.

After the merge-gate code is certified and merged, enable and independently read back server-side main protection:
  python -m scripts.enforce_main_windows_ci_branch_protection_v1
  python -m scripts.enforce_main_windows_ci_branch_protection_v1 --apply
GitHub main protection must include both check-run names, strict branch freshness, admin enforcement, no force pushes and no branch deletion. Configuration refuses to overwrite an existing weaker or different protection rule.
