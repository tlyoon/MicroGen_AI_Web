# PR509 — Discover independent original-source candidates without model calls

The next general pipeline task is **selecting a genuinely different original
source** for the second full lecture pilot. Repeating an old failed Serway
section's ambiguous submission is prohibited, even if another Gemini API
key appears to work after a 503/504 timeout.

PR509 adds `windows_original_source_candidate_inventory` and a read-only
`LectureCandidates` mode to the native Windows operator. This inventories
PDF files only in the strict `<publisher>/<chapter>/<chapter.section>/source.pdf`
layout, computes their source SHA-256 once, and compares them against the
exact immutable original trial contracts inside a **supplied** registry root.

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR509_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
& .\MicroGen-Windows.ps1 -Mode LectureCandidates `
  -SourceRoot 'EXACT_PUBLISHER_CHAPTER_GROUP' `
  -TrialRegistryRoot 'EXACT_IMMUTABLE_TRIAL_REGISTRY' -Python $py
~~~

The default is **read-only**. It does not stage PDFs or create a new job,
submit Gemini/ChatGPT prompts, invoke a TTS engine, render FFmpeg,
modify previously submitted source paths, or publish student content.
All output is a descriptive source catalog with SHA, size and section.

### Conservative classification

- Exclude any source with the same bytes as the historically pinned
  PR362 accepted original, rather than accidentally counting it again.
- Exclude any PDF SHA already represented by a SHA-validated fresh-trial
  contract in the supplied registry, regardless of whether that prior
  attempt completed, failed or was sent ambiguously.
- Exclude identical physical PDF bytes copied under another chapter/section
  as duplicates, not independent sources.
- Fail closed on malformed original PDF folder layout, symbolic links,
  untrusted trial contract or unbounded inventory size.
- Return an explicit warning that this one registry cannot prove the
  absence of **all** historical attempts stored elsewhere. With no trial
  claims supplied, the result is
  `CANDIDATE_CATALOG_UNVERIFIED_WITHOUT_TRIAL_HISTORY` and not a
  certified new source.

A candidate classification is deliberately
`NOT_IN_SPECIFIED_TRIAL_LEDGER_ONLY`. An operator must still verify
other historical attempt records, identify a different genuine lesson,
and start a **new** immutable one-stage Windows trial under the existing
single-send budget with separately authorized provider cost.

This closes a general source-selection/recovery planning gap without
starting a source-specific PDF-fixing loop. Follow-up source review,
independently authored slides/narration, real TTS, synchronized MP4,
human scientific approval and release remain necessary. Merely listing
a source file is NOT full lecture-generation progress.

### Actual Dell-115 read-only discovery check, 4 Nov 2026

On the **separate** chapter-group root
`G:\My Drive\Serway\Serway_1_7` (not the previously failed chapter
22/24 sources), the native inventory examined 46 structured section
`source.pdf` files and the 3 canonical fresh-trial contract records under
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints`. It found 46 candidate
PDF SHA values **not present in that limited registry** and zero matches,
with no model calls or source modifications. Sections 1.1 through 1.5
are among the catalog entries. This is NOT proof those sources lack other
historical generation requests or that their scientific/media content
has been reviewed; no new original lecture was generated.

Native Dell-115 Windows only. No Ubuntu/HP/Yoga/local models, no G:
publisher/main modifications, no paid Gemini/TTS and no student publication.


## 7 November 2026 — Do not re-queue source PDFs with orphan pre-Send claims

The global source-selection command now scans both immutable
`fresh_trial_contract.json` receipts **and** strictly schema-verified
`figures_attempt_started.json` / `stage_{slides,narration,script_qa}_started.json`
records within the same user-supplied bounded checkpoint registry. The latter
cover prior ambiguous Send attempts with incomplete or missing contracts. A
source SHA in either ledger is excluded from the proposed new-source pool.
The scanner refuses malformed/mismatched claim schemas, symlinks, and excessive
combined receipt counts; it never sends a provider request.

Real, read-only Dell-115 test against `G:\My Drive\Serway\Serway_1_7`
and `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints`: 46 source files,
8 scoped trial contracts, 10 scoped pre-Send intents spanning 8 source SHAs,
**45 potential candidates** and **one exclusion, Serway §1.1**.
That exclusion had *both* a trial contract and send-intent evidence, so it is
not claimed as an orphan-intent-only result; dedicated fault-injection tests
verify the orphan case separately. Local wider tests: **50 PASSED**, including
source inventory, operator launcher, one-stage progression and original stages.
No existing claim, publisher source, model request, TTS, media or publication
was modified. The registry remains *scoped*, therefore no candidate is
automatically authorized for generation, and global never-attempted proof is
always false. The prior 4-Nov inventory reported 46 tentative candidates when
the registry contained fewer claims; the current counts reflect current
checkpoint evidence as well as the stronger detector.


### Production-stage integration (7 November 2026)

The protection is **not limited to the advisory candidate list**.
The real `windows_fresh_source_trial.run_trial(attempt_figures=True)` now
calls the same bounded, strict-schema prior-source claim check before staging
a copied PDF, creating a new `fresh_trial_contract.json`, or creating any
model Send intent. It examines sibling trials within the selected external
trial directory's parent (not the entire PC); an earlier sibling contract or
figures/slides/narration/script QA pre-Send intent with the same SHA makes a
fresh model attempt fail closed. It excludes the *current* trial's own
receipts, which remain subject to the existing single-Send, no-resend logic.

The production check is source-independent and reports no permission to send.
It does not certify that other historical registries contain no earlier
requests. Only an authorized, genuinely distinct source may proceed through
the existing one-shot provider health and cost gates. Native Windows fault
injection confirms: prior sibling intent blocks before source staging, a
different source remains eligible, and a malformed prior intent blocks safely.
The source-inventory and stage-entry tests reuse existing strict evidence
contracts; no browser/API/TTS calls are introduced.
