# Gemini UI readiness and verified submission compatibility (13 October 2026)

Scope: isolated MicroGen_AI_Web web-Selenium hardening; no production textbook files overwritten.

## Root causes found in the controlled Thomas Calculus 2.2 pilot

1. Dell-115: Chrome attached and the account was authenticated, but the new Gemini tab did not expose its model-picker button within the previously hardcoded 12 seconds. A passive later probe confirmed the actual selected control reported `Open mode picker, currently Flash High`. The patch uses a bounded configurable wait `MICROGEN_GEMINI_PICKER_WAIT_SECONDS` (default 45, clamped to 12–90), still on the *automation-owned* tab.
2. Both Dell-115 and HP: source PDF and joint storyboard brief uploaded and were reported ready; the prompt editor contained the intended text, and a passive DOM probe on HP verified a single visible, enabled button with the exact accessible label `Send message`. The existing Selenium XPath send selection missed the control and CDP Enter failed to register a new turn. An exact-label DOM-query fallback now clicks only when the editor is nonempty and exactly one visible, enabled matching button exists. Existing positive submission evidence (new user turn / route plus cleared composer) remains mandatory.
3. The strict response-capture fallback used a fixed 60-second DOM wait even when the caller allowed more time for a long structured JSON storyboard. The patch preserves the caller's bounded `wait_cap` (60–900 seconds). This does not imply that the model finished or returned valid output: candidate JSON remains subject to full structural and scientific review.

## Safety

- Do not reuse an arbitrary authenticated browser tab, accept unknown mode selection, type into an unverified UI or mark failed submits as successful.
- The optional native Windows keyboard fallback remains a last resort. A stand-alone unverified ctypes keyboard fallback was **not merged** after it could not identify a uniquely marked Chrome window in the pilot.
- All educational source-review snapshots are AI-labeled, provisional, and require subsequent mathematical review before any narration or MP4 is released.
- The pilot writes only into C-drive isolated staging directories; the original Google Drive Thomas source.pdf and the dirty shared code checkout remain unchanged.

## Tests

- `tests/test_gemini_send_recovery.py` simulates an XPath-missed button, exact DOM-button click, and positive turn verification; tests that a long request budget reaches the response-capture fallback.
- A genuine HP Gemini UI submission with source.pdf plus storyboard brief was confirmed as `new-user-turn+composer-cleared` after the exact-label DOM fallback.
- Passing submission detection is **not** proof that Gemini returned a valid storyboard. A separate source/storyboard gate is still required.
