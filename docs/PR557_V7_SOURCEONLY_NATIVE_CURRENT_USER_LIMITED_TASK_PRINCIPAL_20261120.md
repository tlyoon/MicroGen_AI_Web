# PR557 — Attest the genuine limited current-user Windows task before every source-only restart

**Date and host:** 20 November 2026 (Malaysia time), Dell-115 only.
**Parent:** draft PR556 clean exact commit `a372ccdfffbeb92dd95d5d9d83c8fa854d418151`.
**New isolation:** `%LOCALAPPDATA%\MicroGen_PR557_20261120`, branch
`feature/pr557-sourceonly-scheduler-principal-attestation-20261120`.

## Historical failure review and reason for this boundary

The project already recovered from a direct scheduled Python import failure, an absent-default-True Task Scheduler XML Enabled field, and an overly strict external migration check. PR554 installed and successfully launched a real, limited-current-user 30-minute source-only Windows task; it reconciled six immutable v7.1 stages with zero duplicate dispatches. PR555 integrated the optional-XML-Enabled recovery into the actual scheduler audit, passing 28 focused, 107 broader tests, hosted Windows CI and 6/6 normal stage execution with an independent 0-repeat restart. Its source-only task is *not* configured to send Gemini prompts, upload files, spend paid credits, publish media or approve original science.

A fresh source review of `windows_v71_scheduled_resume._audit_installed` exposed a remaining identity-verification gap: the normal process checked enabled state, exact wrapper and XML `InteractiveToken` but did **not** independently require that the installed principal is the current Windows account with **Limited** privileges. A task configured to another account or elevated run level could therefore potentially appear eligible if it shared the same task name, action and logon type. This is a source-level prospective safety boundary, not an observed unauthorized execution.

Separate genuine Dell-115 native read-only evidence confirmed the existing legitimate task returns `Ready`, `Interactive`, `Limited` and the current user through `Get-ScheduledTask`; `schtasks /XML` contains the exact process SID, `InteractiveToken`, and omits `RunLevel` (Windows's normal LeastPrivilege default). The task was not edited, restarted or reinstalled.

## Targeted production-path repair and recovery registration

The existing source-bound scheduler `_audit_installed` continues to require the real `schtasks /Query /V` Enabled state and physically exact .cmd wrapper before any further check; it then requires the prior XML Enabled safety check. PR557 adds:
1. A single fixed, read-only `powershell.exe -NoProfile -NonInteractive` native `Get-ScheduledTask` query for the exact known task name, returning only an in-memory principal attestation. It does not modify, enable, replace or trigger a task.
2. A strict `_native_current_user_limited_task_attestation` checker requiring one native task, Ready/Running state, Interactive logon, Limited run level and current-user identity. The XML must contain exactly one principal container and one principal, **the exact current process SID** and InteractiveToken. An explicitly elevated or malformed XML RunLevel fails; absent RunLevel is accepted only after the independent native Limited check.
3. An executable, default-enabled recovery registry signature
   `V71_SOURCEONLY_TASK_CURRENT_USER_LIMITED_IDENTITY_UNVERIFIED`, mechanism
   `ATTEST_NATIVE_TASK_USER_SID_LIMITED_PRIVILEGE_BEFORE_SOURCEONLY_RUN`,
   mapped to the pre-existing allowlisted `NORMAL_V71_PROJECT_WIDE_OBSERVABLE_SUPERVISOR` handler. Missing or retired registration blocks before any native principal query. No new scheduler or provider transport is created.

## Genuine source-free model capability review performed first

A separate exact PR556 no-Send owned-tab diagnostic clicked the authenticated **New Chat** control *before* examining model options. On the newly owned page, the selected picker showed the current Neon family, and the atomic selectable options were **Carbon and Hydrogen**; **Pro was not offered**. The test uploaded no source or synthetic PDF and made zero model Sends. Hence changing the preselection order does not restore original G2 Pro and is not permission to substitute a new family, replay the original slides 10/11 or consume another synthetic PDF claim. The source-science ledger remains **20/85 accepted, 65 unresolved**.

## Verification and stop boundaries

- Original native limited-user and exact-SID attestation passed on Dell-115 using real Task Scheduler and process identity (sanitized receipt stored under `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\PR557_REAL_NATIVE_LIMITED_CURRENT_USER_NO_MUTATION_20261120.json`).
- Synthetic failure injection covers other/empty user accounts, foreign SID, disabled or elevated task, noninteractive logon, forged and duplicated XML principal containers, arbitrary/empty RunLevel and missing recovery registry. The first focused suite revealed a real parser gap permitting an extra empty `Principals` container; the code now rejects it. Registry input length validation also caught an overlong precondition text; shortened to the standard 255-character schema without relaxing checks.
- After final exact-SID tightening, **31/31 focused and 127/127 broader regression tests passed**. A second genuine read-only native identity check passed with exact process SID matching and current Limited/Interactive state; sanitized evidence is stored in `PR557_REAL_NATIVE_LIMITED_CURRENT_USER_STRICT_SID_20261120.json` under the external checkpoint root. Next: commit/push an unmerged draft stacked on PR556, verify exact-head hosted Windows CI, run the normal six-stage source-only supervisor with immutable receipts and a separate zero-duplicate restart, then repeat the release board.
- Do **not** reconfigure or overwrite the existing working PR554 schedule merely to test PR557. No after-logout reliability, scientific G2/G3 source/audio/video acceptance, semantic PR stack merge or student publication has been established by this repair.

This is an independent eligible security improvement under the v7 recovery contract. A safe stop at the external Pro/PDF response boundary must not be misreported as scientific completion.
