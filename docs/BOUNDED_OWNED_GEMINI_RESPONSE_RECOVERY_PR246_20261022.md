# PR246: Recover a delayed owned Gemini reply without retrying

Observed original Thomas 8.4 challenge attempts #1 and #2 left separate
failed-attempt receipts and scoped Gemini response-quarantine metadata.
Each captured **zero characters while the owned model appeared to be
generating**. That is evidence of incomplete capture, not of mathematical
approval, and does not prove the remote service was down.

When strict JSON capture now fails with a generating response, wait up to
45 more seconds, observing only the original automation-owned Gemini tab.
Never send a second prompt, reload, change model, access unrelated tabs or
take an unrestricted clipboard copy. If generation ends, the recovered
model-only text must satisfy the original strict response acceptance test.
The existing source/slide hashes, quotations, visible element geometry and
independent mathematical-consensus checks still apply downstream.
Unusable or inaccessible replies are quarantined unchanged and
remain explicit failed attempts. A third challenge attempt is NOT initiated.

The grace period is bounded and synchronous with the explicitly requested
in-flight browser call, not an autonomous background operation. Offline
unit tests exercise late valid replies, still-generating JSON, an unowned
tab, failed vendor replies, malformed responses and invalid wait limits.
No real Gemini interaction, synthesized audio, original teaching-file write,
or publication was performed in this PR.
Dell-115 verification: 6 new focused + 12 existing response quarantine + 2 academic review + 4 compact original challenge + 17 series bridge + 2 queue tests passed (43 total); code compilation passed. Broader Selenium-dependent browser tests could not run locally because this Python 3.12 environment lacks the selenium package; GitHub CI is required for those. These tests do not demonstrate a real Gemini reply was recovered.
