# Gemini incomplete-response recovery (Phase 4B)

**Status:** Development fix for [issue #73](https://github.com/tlyoon/MicroGen_AI_Web/issues/73). All recovered material remains untrusted until existing JSON, source, subject and storyboard checks succeed. Nothing here marks a mathematical review or lecture as approved.

## Failure this addresses

On Dell-115 a Gemini source/outline audit submitted successfully, and the browser showed its model answer increasing to more than 13,000 characters. Strict structured-response capture rejected it before the timeout. The client then closed its automation-owned tab, leaving no local record. Re-uploading the textbook and rerunning an expensive PDF audit should not be the default response to a failed structured capture.

## New safety behavior

The opt-in series Gemini transport attempts one **bounded, same-tab DOM snapshot** of the latest visible `model-response` after strict JSON capture fails. This happens **before** the owned tab is closed. It never reads user-query elements, composer contents, unrelated tabs, screenshots, cookies or browser credentials.

The snapshot and hash-bound metadata are stored under the Windows user's own local AppData directory (or their local cache on other systems):

`%LOCALAPPDATA%\Microvid\gemini_quarantine\gemini_<UTC timestamp>_<random>.raw.txt`

with accompanying `.meta.json`. Unique filenames are exclusively created; prior captures are never replaced. Metadata records `status=incomplete_untrusted`, capture success/absence, generation activity, SHA-256, character length and failure reason. If the model reply is blank or the browser disconnected, an empty raw file plus an accurate failed-capture receipt is retained. No source PDF or response is written into the teaching source tree.

**Quarantine does not prove model completion, correctness, successful PDF reading, human review or source fidelity.** A model response can contain sensitive quoted material: protect the local evidence files and avoid syncing them to shared/public folders.

## Recover without a second Gemini request

For an already **approved** source outline and matching plan, attempt offline recovery of a complete *storyboard* reply:

~~~powershell
python -m selenium_pipeline.series_cli recover-candidate ^
  --source-root "G:\My Drive\Projects\Thomas_calculus_13ed" ^
  --source-pdf "G:\My Drive\Projects\Thomas_calculus_13ed\2\2.2\source.pdf" ^
  --outline "C:\Review\concept_outline_APPROVED.json" ^
  --plan "C:\Review\lesson_plan.json" ^
  --domain mathematics --part part_01 ^
  --authoring-folder "C:\Review\part_01" ^
  --quarantine-file "%LOCALAPPDATA%\Microvid\gemini_quarantine\gemini_...raw.txt" ^
  --output "C:\Review\storyboard_RECOVERED_CANDIDATE.json"
~~~

The above uses Windows CMD continuation syntax (`^`); in PowerShell use backticks or a single command line. It makes **no** Gemini/browser call and needs no `--confirm-live`. It verifies the quarantine hash before parsing, then uses the existing source/plan-linked structural gate. Truncated output fails without generating a candidate. Complete valid output is only `candidate_structurally_valid_scientific_review_required`, never final scientific approval.

Free-form source audits can be inspected from the raw quarantined reply but are **not** storyboard JSON and cannot automatically be accepted through `recover-candidate`. The historical Thomas audit predated this fix and was not saved: it cannot be recovered by inventing files.

## Testing

`tests/test_gemini_response_recovery.py` uses driver fakes to check wrong-tab refusal, latest-model-only access, interrupted-browser handling, 14 KB partial replies, Unicode and size limits, empty receipts, checksum mismatches and no-overwrite uniqueness. `tests/test_series_bridge.py` verifies that an intact snapshot can be used for offline storyboard candidate recovery without contacting Gemini and that a truncated reply fails without generating a candidate.

This is a **fail-closed recovery mechanism**, not a replacement for other Selenium reliability guards or permission to generate student-facing materials. Thomas 2.2's eight-concept outline remains **UNREVIEWED**, so its actual Gemini/slide/TTS/video campaign remains blocked until adequate mathematics and figure review.
