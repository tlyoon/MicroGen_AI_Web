# MicroGen Stage 4 — Three-PC Acceptance Report (12 October 2026)

**Status:** Three-PC offline compatibility and real-lecture video-recovery certification **passed**. Complete unattended Gemini/figure/narration generation and whole-campaign certification **remain open**.

## Release and machine isolation

Stage 4 began from GitHub main commit `57d1abcd1bafce0d95b777f6e004050990013ef1` (merged Stage 3). Dedicated independent clones on **Dell-115**, **HP**, and **Yoga6**, under each machine's local AppData/MicroGenAcceptance/stage4_20261012/repo, were independently confirmed at that exact commit. Running legacy worker installations and source-adjacent lecture materials were not hot-upgraded.

Each machine used an independent machine-local virtual environment. HP and Yoga6 installed ordinary dependencies online. Dell-115's package index DNS was unavailable (getaddrinfo failed), so HP prepared an offline bundle of 44 Windows Python 3.12 wheels. The bundle was transferred via the already-authorized G: Google Drive path and installed locally with pip --no-index. No credentials or browser profiles were transferred.

## Regression acceptance on the actual Windows PCs

| Machine | Full tests (tests and selenium_pipeline/tests) | Result |
|---|---:|---|
| HP | 235/235 | PASS, 4 nonfatal warnings |
| Yoga6 | 235/235 | PASS, 4 nonfatal warnings |
| Dell-115 | 235/235 | PASS, 3 nonfatal warnings |

All PCs ran tests in private, writable local test environments using dedicated pytest basetemp directories.

## Actual lecture video / interruption-recovery acceptance

Tests used **real source-adjacent slides.pdf and slideN.wav** inputs. Each program copied these inputs and split each actual PDF page into a separate PDF **on local disk**, deliberately interrupted after the first encoded slide, proved the validated first segment survived, resumed the remaining slides, validated final H.264/AAC audio/video streams and duration, and verified the source files' hashes had not changed. All MP4 candidates and report JSONs stayed in local acceptance folders, not in production Google Drive lecture folders.

| Machine | Original lecture | Slide/WAV pairs | Validated final MP4 | Local encoding test |
|---|---|---:|---:|---:|
| HP | Calculus 10.3 | 24 | 1,328.70 s; 22,746,425 B | PASS |
| Yoga6 | Serway 12.1 | 17 | 1,067.04 s; 18,329,695 B | PASS |
| Dell-115 | Serway 8.1 | 19 | 978.94 s; 16,967,647 B | PASS |

The original source files were unchanged, as independently established in each test's local JSON evidence. These tests do not establish that Gemini generated correct lecture slides or science content.

## Read-only Serway campaign audit

At the HP audit snapshot, with **46** source PDFs under the authorized Serway root:

| Category under pre-Stage-4 receipt definition | Count |
|---|---:|
| Receipt/hash-verified finished | 18 |
| MP4 published but no matching completion receipt | 0 |
| Partially published slides | 26 |
| No published slide PDF | 2 |

The **20** incomplete source folders with unresolved LaTeX graphics are not certified, nor can source-grounded figure selection be automated solely by caption.

The audit also found a more important inconsistency: Serway **12.1** had a source/output-hash-matching completion receipt but a **stale slide_narration_sync.json** (error: 'Slide, narration or audio changed since synchronization approval'). That was incorrectly counted as a verified completion even though its structural proof had drifted.

## Corrective hardening uncovered during Stage 4

The accompanying Stage 4 correction changes cleanup.completed_lecture to reject any present but invalid slide/narration/WAV structural approval and changes publication/cleanup to verify that approval before stamping a final completion receipt. Newly created receipts bind a hash of the sync record and fail closed if the record is later removed or altered. Legacy folders without the optional record remain supported, while a present invalid record is never ignored.

Four new fixture-based tests cover changed WAV content, removed sync metadata, pre-cleanup safe refusal and legacy receipts with stale approval. **Serway 12.1 is deliberately not restamped or auto-corrected** by this code; it must be reconciled against the actual source, narration, and WAVs first.

After this guard, the old snapshot's 18 completions should no longer automatically count 12.1 as verified. A fresh code-version-matched audit is required for the authoritative count. The changes are tested offline before merge.

## Remaining Stage 4 production gates

1. Demonstrate a completely fresh **Gemini Flash** source-PDF to figures, PDF slides, narration script, TTS, QA and video on each PC, including real browser recovery; avoid collision with older Chrome sessions and only start at a safe job boundary.
2. Validate an actual content change to an important figure, show script/narration/video downstream invalidation, and semantically approve the correct source-grounded figure.
3. Safely retire remaining active old-version processes, verify no orphan encoders, and migrate each production launcher to one accepted release SHA only after checkout and queue boundaries.
4. Reconcile stale synchronization metadata such as Serway 12.1; run one read-only audit after each repair. An MP4 existing is not itself a pass.
5. Resolve the 26 partial and 2 no-slides jobs and get **46/46 genuinely verified lecture completions** without losing existing deliverables.

**No assertion of complete Stage 4 production certification or zero future external-service errors is made.** The successful scope so far is pinned source parity, cross-PC regression compliance and robust real-media interruption/recovery.
