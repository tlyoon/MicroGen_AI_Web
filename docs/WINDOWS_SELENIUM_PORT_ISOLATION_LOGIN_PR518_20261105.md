# PR518 — Selenium port isolation and safe interactive ChatGPT login

**Root cause:** The repo used debugging port `9223` for both an alternate
Gemini Chrome profile (`launch_gemini.py` and `runner.py`) and the existing
ChatGPT Selenium fallback (`rich_mapping_provider_readiness.py`).
Worse, the legacy `vendor_template_v2/launch_chatgpt_chrome.py` defaulted
to port `9222`, which belongs to the primary Gemini automation profile.
Some launchers also attempted to reuse *any* listening Chrome DevTools port
without verifying which provider it belonged to. That cross-profile collision
can falsely report a Selenium/login issue or attach to the wrong service.

## New non-overlapping Windows contract

| Provider / profile | Reserved port | Login policy |
|---|---:|---|
| Primary Gemini | 9222 | Existing authorized Chrome login |
| ChatGPT Selenium fallback | 9223 | Dedicated existing persistent Chrome profile; user signs in if required |
| Alternate-account Gemini | 9225 | Dedicated alternate profile; user signs in if required |

- `launch_gemini` and the production `runner` move the alternate Gemini
  port from 9223 to 9225 and reject a Gemini job on reserved ChatGPT 9223
  before any attachment or prompt transmission.
- The legacy ChatGPT Chrome launcher now defaults to 9223 and rejects
  Gemini's 9222 and 9225. Even if a guest-mode ChatGPT composer is visible,
  it checks visible login/sign-up controls and **refuses** to send the
  historical keepalive prompt until logged in. Its teardown stops only
  temporary ChromeDriver, not `driver.quit()` of the user's persistent
  browser, preserving session continuity.
- The new `windows_chatgpt_login_recovery` reports truthful
  `LOGIN_REQUIRED` versus `AUTHENTICATED_COMPOSER_READY` from the
  **existing profile only**, and optionally focuses an EXISTING ChatGPT
  browser tab without opening a new tab, navigating a URL, submitting a
  prompt, reading cookies/passwords, or closing Chrome.
- A guest composer is NEVER treated as logged in, and merely signing in
  never grants permission to replay an old uncertain source.

### Actual Dell-115, 5 November 2026

Read-only Windows DevTools inspection found:
- 9222: existing `gemini.google.com` Chrome tabs, persistent
  `%LOCALAPPDATA%\gemini_automation_Dell-115` profile.
- 9223: an existing `chatgpt.com` Chrome tab, persistent
  `%LOCALAPPDATA%\chatgpt_automation_Dell-115` profile.
- 9224: no Chrome DevTools session.
- The 9223 ChatGPT tab returned `LOGIN_REQUIRED`. The login recovery tool
  **focused that existing tab** successfully, without changing the profile
  or submitting any content.

### Required user action to complete browser authentication

On **Dell-115**, look at the existing Chrome window for ChatGPT
(port 9223). Manually click **Log in** and complete the normal ChatGPT
sign-in in that exact automation Chrome profile. Do not enter credentials
into a terminal, `.env`, repository or ChatGPT message. Do not rely on
a separate personal browser that uses different cookies.

After completing the login, run in an isolated Windows checkout:

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR518_20261105'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
& $py -m selenium_pipeline.windows_chatgpt_login_recovery
~~~

The desired status is `CHATGPT_AUTHENTICATED_FOR_A_NEW_UNSENT_JOB_ONLY`.
If the status remains `LOGIN_REQUIRED`, do not submit model prompts,
attempt to copy cookies, or switch to an unrelated profile.

**The API side is separate.** PR517 independently checked BOTH Gemini API
keys via vetted `models.get` and both metadata calls succeeded. Gemini API
content generation and billing quota were NOT tested; browser login does
not affect API key rotation. A source-free Gemini browser canary previously
returned an owned-model UI error, which also is not an API quota result.

No paid model requests, no original PDF replay, no TTS, no Git mass merge
and no student publication. Windows-only Dell-115.
