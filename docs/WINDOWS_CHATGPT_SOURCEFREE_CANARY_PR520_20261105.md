# PR520 — Dell-115 source-free ChatGPT one-send Selenium diagnostic (5 November 2026)

**Correct workstream:** `MicroGen_AI_Web` Windows/Selenium lecture-generation pipeline, stacked from PR519 `ff32800b4221328ef980bd5cd494941081b0479b`; NOT the separate API-based `MicroGen_AI`.

## Goal and strict protections

Test exactly one new, short, text-only ChatGPT browser prompt on **Dell-115** via the existing signed-in dedicated Chrome debugging port **9223**; no original PDF/figure, Gemini API, paid model API, TTS, publishing, Git merge or login bypass. New immutable, external `%LOCALAPPDATA%` checkpoint before each distinct test. Never resubmit any checkpoint or ambiguous model job, even if another provider becomes available.

New `selenium_pipeline.windows_chatgpt_sourcefree_canary` attaches to authenticated port 9223, opens only an owned new ChatGPT tab, refuses guest login, records the prompt SHA and one-send claim before any click, and requires exact uniquely generated marker attribution for success. It does not call `driver.quit` on persistent user Chrome. An independently fsynced **send-click intent** file now separates pre-click failures from a possibly clicked and therefore never-retryable send.

## Actual Dell-115 observations: no model prompt submitted

| Distinct checkpoint | Evidence | Outcome |
|---|---|---|
| `20261105_PR520_CHATGPT_SOURCEFREE_ONCE_V1` | send_click_attempted=false, no assistant response | `PROMPT_NOT_CONFIRMED_NO_SEND`. Current contenteditable ChatGPT ProseMirror ignores Selenium `send_keys()` even though it returns normally |
| `20261105_PR520_CHATGPT_SOURCEFREE_DISTINCT_V2` | send_click_attempted=false, no assistant response | `COMPOSER_NOT_EMPTY_NO_SEND`. ChatGPT restored an unsent draft from a self-authored editor diagnostic |
| `20261105_PR520_CHATGPT_SOURCEFREE_DISTINCT_V3` | no matching user/assistant turn, own marker visible in composer; read-only DOM showed enabled button `aria-label="Send"` | `TimeoutException` before send due to old `Send prompt` selector, not a ChatGPT generation failure. This pre-click conclusion comes from **independent postmortem DOM evidence**, not the original V3 receipt alone |
| `20261105_PR520_CHATGPT_SOURCEFREE_DISTINCT_V4` | send_click_attempted=false, no assistant response; exact later read-only DOM check identifies the persisted V3 unsent prompt | `COMPOSER_NOT_EMPTY_NO_SEND`. The allowlist only matched a different exact owned editor diagnostic and correctly refused to overwrite anything else |

**Do not replay V1–V4.** The prior live V3 claim is immutable; even though its DOM audit establishes no observed send, a future development trial requires its own fresh claim and proven clean composer.

Confirmed functional typing-only test on a fresh, owned tab with no Send: Selenium `send_keys()` leaves editor text length 1, but focused `execCommand('insertText', false, known_text)` yields exact DOM readback. This method is now used in the one-shot canary, with an exact check before one click.

Current ChatGPT UI's enabled Send button carries `aria-label="Send"` and no `data-testid="send-button"`. Updated selector includes both current and historical forms, with no fallback Enter or duplicate click. A separate fsynced `chatgpt_send_click_intent.json` will now record the boundary before a click is attempted. Unit tests confirm that an exception before the marker produces zero model submissions and that an exception after the marker stays ambiguous/no-resend.

## Verified engineering state

- Existing authenticated ChatGPT browser port 9223 and Gemini port 9222 remain separate; no user tabs or session cookies transferred.
- Direct source-free real model **generation/response has NOT passed**. Four distinct attempts all stopped before any observed Send; there is no basis to call ChatGPT generation unresponsive.
- Focused offline native Windows diagnostic and prior login/port tests: 23 PASS; syntax checks PASS. Workflow includes new test module and Python entry point.
- Key rotation metadata via PR519 remains independently reachable for both Gemini keys; API model generation remains untested and not authorized.
- No original-source replay or publisher modification, no paid API/TTS, and no student release.

## Next prioritised generic fix, without repeated blind canaries

Implement a read-only **owned-draft reconciliation** stage that identifies a prefilled ChatGPT composer against exact prior local canary claims and proven no-click evidence; never overwrite an unrelated or uncertain user's draft, and never imply that a previous prompt was sent. Only after safe clean-composer proof should a distinct new canary be dispatched. If that eventual test really clicks Send, independently confirm matching user turn, stable assistant response and correct marker before promoting transport availability.

Full academic/source-bound lecture-generation, second independently accepted complete audio/video source, historical PR dependency review and release approval remain pending. Do not allow repeated PDF-specific repairing or blind provider failover.
