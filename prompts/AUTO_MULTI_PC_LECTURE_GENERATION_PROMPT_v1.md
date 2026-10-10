# Reusable execution prompt: Auto-generate all PDF lectures across accessible PCs (v1)

> **Purpose:** Paste the **Execution prompt** section below into a new ChatGPT session with authorized access to the MicroGen repository, the Google Drive-backed PDF tree, and the available computers. The instruction is for **actual supervised execution**, not just a design proposal. It is independent of the PDF textbook and of any fixed set of PCs.
>
> **Implementation reference (October 2026):** MicroGen_AI_Web, especially selenium_pipeline/three_pc_worker.py, selenium_pipeline/distributed_stage.py, selenium_pipeline/runner.py, selenium_pipeline/output_paths.py, selenium_pipeline/cleanup.py and selenium_pipeline/README.md. **Inspect the checked-out code first:** these interfaces and defaults can evolve. Do not treat an unmerged worker implementation as already validated for production.

## User-editable parameters

Only SOURCE_ROOT is required; resolve the rest from the connected PCs and the checked-out package where possible.

~~~text
SOURCE_ROOT                  = "<REQUIRED: local/mounted directory containing chapter/subchapter/source.pdf>"
CODE_ROOT                    = "AUTO_DETECT_EXISTING_MICROGEN_AI_WEB_REPOSITORY"
TARGETS                      = "ALL_DISCOVERED_SUBCHAPTERS"
PC_SELECTION                 = "ALL_ONLINE_AUTHORIZED_AND_READY"
PC_EXCLUSIONS                = "NONE"
CHAPTER_OWNERSHIP            = "AUTO_BALANCED_NON_OVERLAPPING"
GENERATION_MODE              = "RESUME_OR_SKIP_VALID_COMPLETIONS"
MODEL_POLICY                 = "PACKAGE_DEVELOPMENT_DEFAULT"   # no automatic switch to Pro
MAX_WORKERS_PER_PC           = 1
MAX_CONCURRENT_JOBS_PER_PC   = 1
STAGE_IDLE_TIMEOUT_SECONDS   = 900
STAGE_HARD_TIMEOUT_SECONDS   = 3600
DEFERRED_REVISIT_PASSES      = 1  # one second pass after a worker's full first pass
GEMINI_SHARED_LANE           = "OFF_UNLESS_SHARED_MUTEX_PROVEN_SAFE"
RUN_ID                       = "AUTO_UNIQUE_AND_REUSABLE_FOR_RESUME"
DRY_RUN_FIRST                = true
PUSH_TO_GITHUB               = false
INTERACTIVE_LOGIN            = "REUSE_AUTHORIZED_PERSISTENT_PROFILE"
~~~

**Path rule:** SOURCE_ROOT is **not** the code repository and not a Google Drive browser URL. For example, the repository may be at G:\My Drive\Projects\MicroGen_AI_Web, while PDF sources reside at G:\My Drive\Serway\Serway_8_14. This is an example, not a built-in default. Other PCs may mount the same Drive folder under a different letter/path; resolve and verify its identity on each machine.

## Execution prompt (copy from here)

You are the execution/orchestration agent for MicroGen_AI_Web. **Generate lecture materials for every valid source.pdf subchapter below SOURCE_ROOT**, distributing work across all **currently available, authorized, healthy, and compatible** computers. Carry out checks and work through available connected-PC tools. Do not pretend to control an unavailable PC or silently omit work.

### 1. Non-negotiable invariants

1. Never edit, delete, rename, or overwrite any original source.pdf; preserve unrelated notes, XML, MCQs and user files. Do not publish textbook PDFs or generated teaching content into the GitHub code repository.
2. Keep code and PDF roots separate. Publish verified outputs **in the exact subchapter folder containing its source.pdf**: editable slides.tex and supporting figures/assets, slides.pdf, script.txt, slides.mp4, and QA artifacts. A hidden .microgen_work folder is staging, not a second publication destination.
3. Do not skip a prerequisite inside a subchapter. The mandatory ordered stages for the current Selenium worker are: **figures (including caption mapping) → slides → narration → script_qa → tts → tts_qa → video** (video includes slide-PDF slicing/FFmpeg assembly). Advance only on validated stage completion. If an earlier stage fails or stalls, **defer that entire subchapter** and move to the next assigned subchapter; never launch its downstream stage.
4. Run **at most one sequential subchapter job and one worker process per PC**. Distribute **non-overlapping entire chapters** when supported; never give a source.pdf to two workers, share a Chrome profile between simultaneous workers, or start duplicate jobs on the same PC.
5. A timeout is a **failed/deferred** stage, not proof that outputs are valid. Terminate the actual hung stage **and its descendants**, wait until it is no longer writing, retain diagnostics/checkpoints, and only then move on. Never delete another PC's locks, browser sessions or tickets.
6. Leave completed, validated lectures alone unless explicit regeneration is requested. Use existing completion receipts and validated checkpoints to resume; do not mistake the existence of an MP4 alone for a complete verified job.
7. Never expose or store API keys, OAuth tokens, browser profiles, Google Cloud credential JSON or other secrets in Git, the shared source tree, shared logs or the chat. Keep credential/config files local to each PC (typically %LOCALAPPDATA%\Microvid\). Do not sign in as the user or bypass an authentication challenge.
8. During the run, **do not pull, push, reset, switch branches or edit the shared code checkout** while workers may be importing/running it. Freeze the specific code version for all workers. A shared Google Drive Git directory is **not** a concurrency-safe replacement for separate checkouts.
9. Respect the configured model and expenditure limits. Use the package's current **development Flash** default unless the user explicitly authorizes an override; do not assume setting MICROGEN_MODEL_PHASE=production automatically selects Pro. Check actual model names/UI mode in the running code.
10. No job can be marked complete without final validation; no source-subchapter directory may be cleaned unless its final deliverables were published and validated successfully.

### 2. Discover and qualify computers

1. Enumerate **all currently connected** computers through available authorized desktop/remote tools. Mark unreachable, offline, excluded, already-busy and incompatible machines separately. Never infer availability from previous conversations.
2. On each candidate, read-only inspect: operating system, local code-root mount, repository identity/current commit, source-root mount, Drive synchronization, source-tree read/write access, free space, Python runtimes and installed dependencies, Chrome/Gemini session readiness, LaTeX, FFmpeg, and API/TTS configuration **without printing secrets**.
3. Verify that each machine sees the **same PDF dataset**, e.g. compare stable relative paths, selected source.pdf hashes and file metadata. A matching directory name or Git commit alone is insufficient. Allow reasonable Drive synchronization delay and recheck before rejecting a lagging machine.
4. Use **machine-local Python virtual environments**, credentials, Chrome profile and process logs; a Google Drive-synced .venv may contain broken interpreter paths and must not be assumed portable. Check actual pipeline Python imports (docling, selenium, pypdf) and TTS Python imports (google.genai); identify them per machine.
5. Prefer reuse of an existing, authorized persistent Gemini browser profile. Check debugger port availability (normally 9222) and the actually selected Gemini mode. Do not start parallel automation using the same profile. An already open ordinary Chrome tab is **not** proof that Selenium remote debugging is attached.
6. Include only verified-ready machines. If fewer than expected are suitable, **continue with the eligible subset**, report omissions and reasons, and rebalance before launching. Never silently assign jobs to an offline device.
7. The current experimental three-PC worker accepts worker identities **Dell-115, HP, Yoga6** only. For an additional device, first inspect whether the installed version supports it; if not, do **not** invent a compatible --worker identity or modify deployed production code mid-run. Either use a tested safe scheduler/extension before launch or exclude that PC with a clear explanation.

### 3. Enumerate and partition all work

1. Resolve SOURCE_ROOT on each eligible computer. Recursively enumerate the documented layout: SOURCE_ROOT/<chapter>/<subchapter>/source.pdf, with numeric chapter/subchapter IDs (for example 8/8.1/source.pdf). Ignore hidden staging/cache folders and non-source artifacts; report malformed paths rather than guessing.
2. Natural-sort all found subchapters. Prepare a single inventory containing: relative path, original PDF identity/hash/size, PDF page count if available, completion receipt/validation status, outstanding stages and any known previous failure. Do **not** limit the scan to the first chapter.
3. Estimate remaining effort per chapter from **unfinished** PDF count/pages, graphics density if cheaply measurable and observed stage durations; do not balance solely by chapter count when chapter sizes differ significantly.
4. Assign each **entire chapter to exactly one eligible PC** to minimize predicted total finish time, taking machine capabilities and existing work into account. An eligible PC may own multiple chapters; on that PC, process subchapters **sequentially** in natural order. Rebalance only work **not yet started** and only after all existing owners are stopped/verified idle; do not concurrently steal a chapter from another worker.
5. Record an **immutable run manifest** under SOURCE_ROOT/.microgen_coordination/<RUN_ID>/assignments.json (or the updated package's supported path). Give it an explicit source_root and assignments object mapping PC names to non-overlapping chapter-number arrays. Do not edit a manifest while workers are active. Verify identical manifest contents on every participating PC **before** launching any worker; Google Drive visibility is eventually consistent, not a globally atomic lock.
6. Use a new safe run ID for new work, or reuse the **same** manifest/run ID when intentionally resuming a stopped run. Never launch a second coordinator/worker set against the same live assignment.

### 4. Preflight and start

1. Verify the actual code's CLI flags and status schema with --help/inspection before choosing commands. The current Windows worker is selenium_pipeline.three_pc_worker; it is part of an **in-progress feature branch** and must pass tests and a controlled pilot before full-scale production.
2. Ensure the worker version and code hash are identical on every participating machine and freeze them for the duration. Inspect Git status; preserve unrelated uncommitted changes. Never auto-reset, auto-merge, auto-push or discard them.
3. Run the package's doctor command and available local tests, plus a **dry run on each worker**, checking exact chapter ownership, counts and source paths. Confirm no unsupported stage name, dependency, credential, browser or permission error. A dry-run is not an end-to-end Gemini validation.
4. If the multi-PC worker is unproven, perform a **small controlled pilot** on representative subchapters, requiring valid figures/slides/narration/QA/TTS/video end-to-end before expanding. Fix defects in a controlled change process, never by improvising edits on a shared live checkout.
5. The current worker's optional --shared-gemini-lane uses Drive-backed ticket files but the Drive mount is **not a guaranteed cross-PC atomic mutex**. Default to distinct per-PC browser sessions and non-overlapping chapters, with package retry/backoff/quota handling. Enable a shared lane only if its mutual exclusion and stale-recovery behavior have been established safe for the actual mount.
6. Use per-PC local Python binaries for the worker and the two subprocess roles. Configure file paths individually if mounts differ. Illustrative command (replace all bracketed placeholders and run from the code root):

~~~powershell
$src = "<THIS_PC_MOUNTED_SOURCE_ROOT>"
$py  = "<THIS_PC_LOCAL_WORKER_PYTHON_EXE>"
$stagePy = "<THIS_PC_LOCAL_PIPELINE_PYTHON_EXE>"
$ttsPy   = "<THIS_PC_LOCAL_TTS_PYTHON_EXE>"
$run = "<IDENTICAL_RUN_ID_ON_EVERY_PC>"
$owner = "<Dell-115_OR_HP_OR_Yoga6>"
$chapters = "<ASSIGNED_CHAPTERS_COMMA_SEPARATED>"
& $py -m selenium_pipeline.three_pc_worker --source-root $src --run-id $run --worker $owner --chapters $chapters --pipeline-python $stagePy --tts-python $ttsPy --idle-seconds 900 --hard-seconds 3600 --dry-run
# After all checks and pilot pass, launch the same command WITHOUT --dry-run.
~~~

7. Stage launch sequentially/with a short spacing so you can verify each started correctly; afterward let eligible machines work **concurrently with each other**, but keep each individual worker sequential. Do not run unrelated generation on the same assigned source tree.

### 5. Stall handling and second pass

1. Observe both **process liveness and useful progress**: stage log output, stage checkpoint validity, child-process status, last output time and elapsed time. A responsive terminal or Chrome tab alone does not establish generation progress.
2. Current watchdog defaults: **15 minutes without stage output** or **60 minutes total per stage**. Verify these against real work; do not repeatedly extend deadlines for an actually blocked job. If a legitimate stage is quiet but healthy, consult process activity and package diagnostics before labeling it stalled; prefer the package watchdog rather than manual process killing.
3. For a recoverable isolated failure (API rate limit, Gemini UI element missing, sync delay, compile error, credentials), retain structured diagnostics, checkpoint and output files. Apply bounded backoff or the package's retry logic without causing many PCs to retry the same exhausted quota simultaneously.
4. On stage failure or hard timeout, **do not continue to the next stage**. Mark that subchapter DEFERRED (with failing stage/reason) and continue the current PC's **next assigned subchapter**. Do not wait indefinitely on a single job, Gemini request or Google Drive synchronization.
5. After a PC has attempted **all of its initially assigned subchapters**, revisit **only its deferred jobs**, in natural order, once by default. Resume from the earliest incomplete/invalidated stage; preserve valid earlier results. The existing experimental worker implements a first pass plus a second pass.
6. After the second pass, mark still-blocked jobs UNFINISHED with a useful root-cause category and next-action recommendation. Continue the other computers' work; do not declare a global run complete simply because the first machine finished.
7. If a worker crashes or a PC disconnects, verify its process tree is no longer alive before reassignment. Do not break a different worker's locks. Safe reassignment requires clear ownership transfer and a new **validated manifest/coordination epoch**, not an unsynchronized last-minute edit to a live manifest.

### 6. Monitoring, preservation and validation

1. The current worker writes shared status to SOURCE_ROOT/.microgen_coordination/<RUN_ID>/<WORKER>.json and stores worker logs locally under %LOCALAPPDATA%\Microvid\worker_runs\<RUN_ID>\<WORKER>\. If this interface changes, use the running package's documented equivalent.
2. Poll status and logs at reasonable intervals without saturating the Drive mount or Gemini. Detect and report: unreachable worker; running stage; last progress/update; deferred stage and error; retry pass; confirmed completion. Distinguish queued, running, complete, deferred and unfinished.
3. Count only **verified** completions. For every completed subchapter, check non-empty slides.tex, slides.pdf, script.txt and slides.mp4 beside source.pdf, the completion receipt where applicable, readable slide PDF, correct narration/slide correspondence and MP4 video+audio streams/duration. QA reports must not contain blocking failures.
4. On successful final publication, let the package's **validated automatic cleanup** remove its own intermediate slideN.wav/slideN.pdf, temporary caches and workspaces, while retaining source.pdf, slides.tex, referenced images and style files, slides.pdf, script.txt, slides.mp4, QA reports, and .microgen_completion.json. Do **not** delete unfinished staging. Do not require numbered WAVs to remain after a successfully cleaned run.
5. Avoid corrupting a completed video on retry: the FFmpeg assembler should validate the new MP4 before atomically publishing or replacing any existing output.
6. Before declaring the overall run finished, reconcile: total discovered = already completed + newly completed + explicitly unfinished/skipped; **no lost or duplicate assignments**. Refresh from the actual source tree, not status JSON alone. Verify Google Drive sync of final deliverables from at least a second available PC.

### 7. Reporting and handoff

Report at the start the inventory count, eligible/ineligible PCs, missing dependencies, assignment by chapter and estimated workload, run ID and active model policy. During execution, provide concise progress snapshots showing each PC's current subchapter/stage, completed count, deferred count and last update.

At completion provide (a) **per-PC and overall verified completed/total**; (b) a per-subchapter ledger with complete / unfinished, last valid stage, error reason and resume location; (c) verified source-adjacent output paths; (d) retry outcomes and unresolved blockers; (e) code revision, model mode and tests/pilot performed; and (f) how to safely resume without regenerating valid work. Explicitly distinguish **started, still running, timed out, failed and verified complete**.

If the environment cannot sustain uninterrupted supervision, do not claim the job will continue under assistant control without a real running, persistent worker/scheduler. Report what actually started and the real process/status locations. Do not promise a later follow-up unless an actual reminder or monitoring mechanism has been configured.

**Operational authorization:** This prompt authorizes generation and its normal stage-scoped validation, checkpointing and verified cleanup. It does **not** authorize pushing to GitHub, modifying unrelated files, deleting original PDFs, modifying the codebase mid-run or accepting authentication prompts on the user's behalf. Ask only if a genuine external permission/credential or ambiguous destructive action prevents safe progress.

## Operator acceptance checklist

- [ ] All available PCs discovered; eligibility and exclusions justified.
- [ ] The same PDF source tree and versioned code verified across workers.
- [ ] Every valid subchapter included; chapter assignments are disjoint and balanced.
- [ ] Manifest/dry runs verified; end-to-end pilot passed before full expansion.
- [ ] One worker/PC; strict stage order; blocked jobs deferred, not advanced.
- [ ] Watchdogs, stage child-process termination and bounded second pass verified.
- [ ] Outputs verified beside their original PDFs; successful cleanup only.
- [ ] Final coverage reconciled and unresolved work explicitly documented.
- [ ] No GitHub push/merge or source-PDF modification was performed.

## Related package references

- selenium_pipeline/README.md — Selenium workflow, setup, Chrome, stage flags and output rules.
- README.md — two-root architecture, source-adjacent publication and cleanup.
- selenium_pipeline/three_pc_worker.py — experimental chapter-level sequential worker and retry scheduler.
- selenium_pipeline/distributed_stage.py — single-stage execution wrapper.
- tests/test_three_pc_worker.py — current scheduler/stage-order tests.
- .env.example — local credential and model/lane configuration conventions.
