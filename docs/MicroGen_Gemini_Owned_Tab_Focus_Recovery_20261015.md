# Owned Gemini tab focus and visibility recovery

Date: 15 October 2026. Applicable to the Selenium non-API MicroGen pipeline.

On HP and Dell-115, a Selenium-created clean Gemini tab remained in the
document.visibilityState hidden state. Its Angular Send entrance animation,
normally 250 ms, stayed running with currentTime equal to zero for four
seconds. The Send wrapper remained at opacity zero despite a complete
prompt in the Quill editor. Screen capture and DOM hit-test were not
sufficient evidence of a real active page.

Chrome Page.bringToFront, Target.activateTarget, a new Chrome window, normal
Selenium clicks, browser pointer events and CDP Enter did not produce a
verified model submission. Manually finishing the frozen animation made
Send appear but likewise did not produce a registered user turn.

The supported Chrome DevTools Protocol command
Emulation.setFocusEmulationEnabled with enabled true changed the owned
document state to visible and let the Send animation complete naturally.
In a controlled real Dell-115 canary, one native Selenium Send click
then produced a confirmed new user turn and a completed model response
containing the expected one-token marker. The prior Chrome tabs were
preserved, no source files were touched and no lecture TTS/MP4 was made.

The shared GeminiSeleniumClient now checks the currently selected tab
against the exact MicroGen-owned handle before changing focus state.
It skips emulation for already-visible tabs, uses CDP focus emulation only
when hidden, confirms the page becomes visible before proceeding and
stops on unsupported CDP, other-tab selection or failed visibility.
Before closing its owned tab, it attempts to reset target-specific
focus emulation. Existing hidden-Send fail-closed protection remains.

The behavior is not an authorization for mathematical production.
Source outline and narrations remain unreviewed until an independent
scientific reviewer signs off. Full unattended multi-PC acceptance
requires further real replay across all target machines.

CDP reference: https://chromedevtools.github.io/devtools-protocol/tot/Emulation/
