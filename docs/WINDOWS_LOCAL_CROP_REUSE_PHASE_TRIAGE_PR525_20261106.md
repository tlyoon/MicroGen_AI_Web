# PR525 — Reuse Docling converter per PDF and classify local cropping stalls (6 November 2026)

**Project:** MicroGen_AI_Web Windows Selenium, Dell-115 only, NOT the separate MicroGen_AI API package. This is a new general runtime improvement built on PR524 `f81027bf278c5830395c2d855c524c60ef67db47` (exact-head GitHub Windows CI #669 SUCCESS).

## Evidence and diagnosis

Do not rerun prior ambiguous source jobs. A read-only inspection of the already timed-out independent Serway §10.1 figures trial showed that the nested `.microgen_work/microgen_figures.log` launched `docling_dell\\python.exe crop_figs_v3.py`. The workspace contained three `page_N.pdf` files, matching page PNGs and extracted image(s), with the last files written near the one-stage timeout. The outer subprocess log had only the environment-loader line and no registered Selenium attachment, model Send or HTTP 503/504. This evidence shows real local PDF preparation progress rather than proving a Gemini outage. It also shows why the old single outer-log triage was too coarse. Exact source SHA was `fb33af9a5fd164702c6b2aac708bd409098476fa48044535d9aec4e4a18a8a1f`. No new model submission, TTS, or source editing occurred.

The source implementation of `vendor_template_v2/crop_figs_v3.py` previously constructed `PdfPipelineOptions` and **a new `DocumentConverter` for every PDF page**. Converter initialization and Docling pipeline model setup can be expensive. This is repeated avoidable work across *all* PDFs, not a special problem with the earlier §10.1 file.

## Reusable code-level fixes

- The crop tool now creates exactly one configured `DocumentConverter` and options per source document, reusing it for every page-level PDF while retaining original `images_scale=1.5`, picture extraction, OCR disabled, table-structure disabled, original figure-size threshold and per-page exception handling.
- Explicit, flushed, secret-free progress markers identify PDF rasterization start/end, Docling initialization start/ready and individual figure-crop page start/done. PR523's `PYTHONUNBUFFERED=1` ensures these nested worker messages survive bounded termination.
- The source-bound `windows_gemini_stage_transport_triage` now reads the **nested workspace crop log** as well as the main stage log, after strictly checking it remains beneath the SHA-locked isolated trial and refusing symlinks/oversized logs. It exposes only phase tokens, flags, and the nested log SHA (never textbook content or secrets). When crop progress is observed without verified Send, it classifies `LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED`, not `Gemini unavailable`; no automatic source resend is authorized.
- Previously written PR524 immutable diagnosis receipts remain unmodified and reusable if all earlier fields and source/log SHA values still match. Only the newly added crop-observation fields and the documented local-crop-vs-unknown category transition can differ; raw evidence changes or tampering fail closed.
- The existing one-shot model request budget and stage deadlines remain unchanged; there is no per-source repair loop, no fallback key request after an uncertain job, and no release authorization.

## Windows CI regression follow-up

The first exact-head GitHub Actions run (#670, commit `4dfddadd01bb6cd460892cefaa682254c62ca0ea`) failed two new nested-crop diagnostics despite 70 local tests passing. This was a **Windows temporary-directory alias** mismatch: `Path.resolve()` for the staged original was compared with `Path.absolute()` for the trial root, repeating the earlier generic path-canonicalization problem. The read-only nested-log containment check now resolves BOTH path operands consistently while retaining symlink/out-of-root refusals. A new regression deliberately passes a benign lexical alias to the same existing local trial. Expanded Dell-115 checks: **71 focused unittest PASS**. A new exact-commit GitHub CI run is required for acceptance; the failed #670 remains historical evidence and is not misreported as green.

## Verification

A source-free physical behavioral regression runs the actual figure-crop script's processing body under fake PDF/Docling drivers for **two pages**, asserting that exactly one converter is constructed, both page-level outputs are produced, the original picture settings remain and phase heartbeats are emitted. Separate synthetic diagnostics exercise nested crop markers, SHA-binding, post-record tamper refusal, and compatibility with older immutable receipts. Dell-115 focused test suite and exact-head GitHub Windows CI are to be independently checked before marking the PR accepted.

This change eliminates repeated converter construction and improves triage, but no new actual performance benchmark has been established; actual Docling page speed and scientific/figure recognition quality on genuine new original PDFs still require distinct acceptance evidence. The existing §10.1 timeout and earlier Serway/Thomas attempted inputs must not be retried. Global completion still requires a different source's fully qualified slides/narration/TTS/MP4 plus independent academic review, bounded historical PR dependency review, and release authorization. No paid API/TTS, no HP/Yoga/Ubuntu/local model, and no student publication are included.
