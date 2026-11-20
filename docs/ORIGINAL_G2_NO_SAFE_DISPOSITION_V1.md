# G2 historical no-safe-source checkpoint: normal supervisor recovery v1

## Exact blocker observed 20 November 2026 (Dell-115)

After consolidating PR570/PR571 on merged main, independently reconciled
original Serway 1.3 scientific reviews remain **26/85 accepted** and **59
pending/disputed**. Normal select_next_safe_review() returned
NO_SAFE_REVIEW_UNIT_REMAINING, with **five** blocked units:

- Slides 1, 3, 10 and 11: INITIAL_REVIEW;
  RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND. Their first historical
  request may have been submitted, dispatch_attempted.claim exists, and
  original receipt records UNKNOWN_AFTER_POSSIBLE_SUBMISSION. There was
  no attributable saved model response or identity.
- Slide 4: INDEPENDENT_CHALLENGE;
  AMBIGUOUS_OLD_SEND_NO_RESUBMISSION, with existing dispatch claim.

No provider request was reissued. Standing authority to perform scientific
review never permits replaying uncertain Sends or overwriting old identities.
No G2/G3 or student-publication acceptance may be inferred.

## Executable mechanism

Normal windows_g2_autonomous_qa_supervisor.step() now invokes
g2_no_safe_disposition.preserve_g2_no_safe_disposition() INSIDE the existing
source-locked supervisor process lock when G2 consensus remains incomplete
and no review unit is safely eligible.

- Revalidates original source.pdf SHA, immutable queue membership,
  original attempt receipts, exact claim markers, and source hashes.
- Requires an exact enabled allowlisted G2 recovery registry action with
  zero provider Sends; disabled/foreign handlers fail closed.
- Refuses to treat an uncertain Send as unrecoverable when an attributable
  saved model response is present. Existing saved-response reconciliation
  is mandatory first.
- Persists deterministic SHA-addressed evidence in work_root/
  g2_no_safe_dispositions, never overwriting an old receipt. Repeated
  restarts with unchanged evidence reuse the exact checkpoint.
- Records G2_HISTORICAL_CLAIMS_PRESERVED_NO_SEND, with all five blocked
  histories, no new Sends, no old replay, and explicit false independent QA
  and student-release claims.
- Records independent offline QA preflight as eligible; does NOT falsely
  assert G3 dispatch, an active background executor, or final acceptance.

## Admission and recovery rules

The normal supervisor may resume original G2 only after a verified saved
response or a truly eligible new, distinct source review. Do not reset an
uncertain provider claim or bypass finite retry limits. Meanwhile other
authorized offline code/QA tasks can advance independently.

Tests fault-inject idempotent restart, source mutation, changed registry
handler, new response against an uncertain claim, missing dispatch marker,
fake safe selection and tampered checkpoint. CI must run original G2 and
modern figure-v3 regression suites. No Task Scheduler re-enablement.
