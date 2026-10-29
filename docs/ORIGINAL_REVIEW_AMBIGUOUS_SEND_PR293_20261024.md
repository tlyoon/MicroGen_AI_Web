# PR293 - Fail closed on ambiguous original mathematical-review submissions

24 Oct 2026; isolated Dell-115 development stacked on CI-green PR292 d2f49d5fddfd0d87a853620b619a71d038794f24.

## Reproduced control-flow defect

The normal original academic-review queue previously caught any RuntimeError, ValueError or OSError as a generic quarantined FAILED review, without saving whether the Gemini transport had already sent a request. A later caller supplying `attempt=2` could pass the previous receipt check based only on generic FAILED status and attempt number, causing a duplicate model request after an interrupted but possibly accepted prior submission. The separate PR288 read-only preflight did not enforce this boundary inside the normal request dispatcher.

## Durable production-path correction

`ai_academic_web_review.run_web_review` can now signal a return of raw model-response text to the queue without exposing that text in the receipt. The normal `execute_one_review` receipt records `RETURNED_RESPONSE_INVALID` only when a nonempty response was actually returned before validation failed. Otherwise it records `UNKNOWN_AFTER_POSSIBLE_SUBMISSION`, blocks manual retry and requires owner reconciliation. For attempt N>1, the normal dispatcher itself now refuses generic historical failures or unknown state, allowing an explicitly chosen repeat only after all previous relevant failures have proven returned-invalid responses. Existing queue attempts are never reset or overwritten. `review_retry_plan` reports ambiguous histories as blocked instead of suggesting a new attempt number.

## Verification and boundaries

22 focused and neighboring Dell-115 tests passed. New adversarial tests prove (1) a simulated connection loss after possible send is quarantined with ambiguous state and blocked from numbered retry, (2) a returned-but-invalid model answer is distinct and remains eligible for deliberate manual retry, and (3) old generic receipts with no send evidence cannot trigger duplicate submission. A real read-only Thomas 8.4 Slide3 preflight still reports five units, zero historical first-pass sends and no verified scope consent; no request was made.

This is a retry-safety code fix, not proof that any external model was responsive or that source math is independently agreed. All textbook sources, old review receipts, original audio/video and protected main remain untouched. Student release and paid TTS are not authorized by this change. New CI must be verified independently.
