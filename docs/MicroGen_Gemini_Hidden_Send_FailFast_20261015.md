# Hidden Gemini Send control: fail-fast Selenium guard

Date: 15 October 2026.

In isolated Dell-115 Gemini browser canaries, a prompt appeared in the
Angular/Quill editable box while the exact Send message button stayed
inside a parent DIV with opacity 0. ChromeDriver therefore judged it
not displayed. Quill setText, JS input events, execCommand insertText and
CDP Input.insertText did not make the Send control visually actionable.

The vendor Gemini client has a DOM-click fallback that could otherwise
attempt to activate this hidden button. It now performs a short read-only
preflight after text entry. If a nonempty prompt editor is accompanied
by exact Send message controls and all have an ancestor with opacity
0 (or CSS display none/visibility hidden) for two stable samples, the
client returns false before any forced DOM click or fallback Enter.

The prompt text itself is never logged by this check. Existing
evidence-bound send/capture methods remain in place for visible buttons,
different markup and transient animation. A successful doctor, editor
text, or browser attachment is NOT considered successful submission.

This does not repair all Gemini text-entry problems. The previous
initial Enter-based canary timed out without confirming an actual
submission, and the follow-up tests all preserved original tabs.
No live TTS or source-document generation was performed here.

Resume a live owned-tab canary only when browser ownership is clear,
and require a registered user turn and a stable completed model answer.
Thomas Calculus 2.2 is still blocked for production by scientific
storyboard review and TTS listening approval.
