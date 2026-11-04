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
