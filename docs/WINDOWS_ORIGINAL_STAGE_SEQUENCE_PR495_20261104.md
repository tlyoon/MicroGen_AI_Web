# PR495 — Real-original Windows single-stage continuation and recovery

**General codebase feature**: advance a genuine source through figures →
slides → narration → deterministic script mathematics QA, one verified stage
at a time, without a new provider request on any previously attempted stage.
No Python imports of the original Thomas figure repair campaign.

## Operator entry point

For an existing PR494 original-source trial with **successfully completed**
and physically valid figure extraction/mapping:

```powershell
python -m selenium_pipeline.windows_original_stage_sequence --trial-dir "FRESH_VERSIONED_TRIAL" --stage slides
python -m selenium_pipeline.windows_original_stage_sequence --trial-dir "FRESH_VERSIONED_TRIAL" --stage narration
python -m selenium_pipeline.windows_original_stage_sequence --trial-dir "FRESH_VERSIONED_TRIAL" --stage script_qa
```

Each step requires its previous immutable SHA-bound receipt and the current
physical source PDF. It additionally asks the maintained runner's **actual
stage validity checker** (figures, slides, narration or math-risk script QA)
to verify artifacts before continuing. A non-zero exit, even with some files
written, is not an accepted stage. New output receipts record exact source SHA,
prior receipt SHA, authored artifacts and an external raw Unicode log. Re-entry
of a fully completed stage is read-only and hash-verified; re-entry after
an ambiguous submission or timeout returns `PREVIOUS_STAGE_ATTEMPT_NOT_RESENT`
with no new subprocess.

The controller invokes only the already maintained official runner with
`--from-stage STAGE --through-stage STAGE`. It never runs TTS, video, or
publication, and cannot interpret a partial/model response as accepted.
No source author files outside the isolated stage copy are touched.

## Dell-115 physical evidence, 4 Nov 2026

- 5 offline source-version/tamper/timeout/progression tests **PASS**.
- Real, separate Serway §22.2 source SHA
  `a0c57ec7323d7bdf0636161f0ec1d19e227dcaefbd3b25e54e46d0ff5703fdac`.
- The exactly-once PR494 figures attempt submitted a Gemini browser request
  but **timed out at 300 seconds**, saved immutable evidence and raw log.
  There is no verified completed mapping; the model may have processed it.
- Actual PR495 CLI on that physical source **refused slides before browser**,
  exit code 2, without a new attempt, paid TTS or PDF modifications.
- This is a reusable product stage-continuation component, **not** an
  accepted genuine original source-to-video generated lecture.

**Next general priority:** integrate the EXISTING independently reviewed
element selections, recorded exact-word WAVs, and synchronized true H264
review-to-production path through a single SHA-bound operator bridge.
Do not bypass figure scientific provenance or turn a review-only MP4 into
a student-ready video simply by changing metadata.
