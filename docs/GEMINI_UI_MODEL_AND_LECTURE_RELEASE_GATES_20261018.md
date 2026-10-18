> **SUPERSEDED MANDATORY-HUMAN STAGE GATE (18 October 2026):** The owner now explicitly authorizes **unattended internal stage progression on verified technical QA**. This document's human approval requirements are optional for internal generation and review handoffs; they do **not** control whether the next internal stage starts. External student publication remains a separate authorized action. See [latest owner amendment](OWNER_AMENDMENT_AUTOMATIC_INTERNAL_STAGE_PROGRESS_20261018.md). The original narrative below is historical.

# Gemini UI model evidence and explicit lecture-release gates

**18 October 2026 — supplemental contract hardening, draft only.**

The binding contract remains the 18 October effective contract and supersession document. No release or student publication is authorized by this technical change.

## Model identity: requested versus observed

The chosen text-generation target is Gemini 3.8 Flash. The authenticated Selenium browser model picker can substantiate the **Flash family**, but it cannot independently verify the exact deployed server model ID or version.

The new browser model evidence records the requested model ID, observed mode picker text, verified UI family, an explicit FALSE exact model ID verification flag and a NULL observed provider model ID. It rejects Flash Lite, ambiguous Flash/Pro labels, and conflicts between requested model family and actual UI selection. The storyboard client re-verifies selection after opening a new chat.

**Do not claim an exact 3.8 server version on the basis of a Flash browser label.** Exact identity requires separate provider-origin evidence.

## Three distinct levels of verification

1. Technical synchronized media verification: verifies hashes, cue and timing structures, actual encoded duration strictly less than 600 seconds, and declared synchronized transitions. The historic technical status does not certify mathematical, figure, narration or student release acceptance.
2. Academic lecture acceptance: requires technical verification plus a separately authored, hash-bound human review of mathematics, complete and legible figures, original speech listening and spoken-element highlights. It also requires a reviewed script-linked, uniform effective TTS model and voice.
3. Student publication authorization: requires a second explicitly human-authored approval bound to the actual academic review and current technical series. Neither a green CI nor a technical video nor academic review alone grants student publication permission.

The code never creates these authorizations and does not publish anything to Moodle. Human approval JSON is a record of a person's explicit decision; it is not cryptographic proof of real-world identity.

## Academic approval format

The separately authored file lecture_human_approval.json must contain: schema_version 1, status human_academic_review_approved, reviewed_by, approved_at_utc (ISO UTC), human_authored_explicit_approval true, subject entire_source_bound_lecture, source_sha256, slides_sha256, narration_script_sha256, technical_series_sha256, tts_input_manifest_sha256, effective_tts_model and effective_tts_voice.

The four independently reviewed flags must all be true: mathematics_approved; all_figures_complete_and_legible; original_narration_listened_and_approved; spoken_element_highlights_approved.

The independently authored student file lecture_student_publication_authorization.json must contain: schema_version 1, status explicit_student_publication_authorized, student_publication_permitted true, human_authored_explicit_approval true, authorized_by, approved_at_utc, human_review_receipt_sha256 and technical_series_sha256.

Do not generate or prefill true approvals on behalf of an unperformed human review.

## Safe runtime behavior

The normal runner and the three-PC worker now require academic acceptance before declaring a lecture complete. The worker defers a technically verified lecture when human approval is missing, without regenerating or modifying its source/output assets. Legacy batch remains fail-closed.

The current highlighted multipart production pipeline is not certified as a fully approved, unattended end-to-end generator. These checks do not remove the existing Thomas 8.4, 8.5 and 8.6 review blockers. No paid provider call, Whisper, Zenbook, GCS lease, merge, source-file overwrite or Moodle publication is authorized by this draft.
