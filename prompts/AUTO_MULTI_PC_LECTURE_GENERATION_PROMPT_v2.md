# MicroGen universal multi-computer lecture generation — reusable execution prompt (v2)

> **Use:** Copy the section **"Execution instructions"** into a future ChatGPT or another capable automation session. The agent must have authorized access to a computer-running tool, the MicroGen package, and the lecture source folder. This is an **execution request**, not permission to invent access or skip validation.
>
> **Portability promise:** This prompt is **independent of PC names, number of PCs, drive letters, source subject, processor type, and operating system**. Actual execution is limited to computers and environments for which the **installed MicroGen runtime has a tested adapter**. A generic prompt cannot make an incompatible Windows-only worker run on Linux/macOS; report that limitation rather than claiming universal software compatibility.
>
> **Version and precedence:** Prompt v2 (October 2026). The **checked-out code, --help, tests, and its output contracts** are the authority for runnable commands, stage names, manifest schema, runtime options and supported platforms. If this document describes a capability not implemented yet, mark it **not implemented** and use a verified fallback or exclude that machine. Do not silently modify the runtime during a production run.

## Reusable parameters (not tied to one computer)

Supply **one** usable source locator. All other settings have portable defaults; override them only when necessary.

~~~text
SOURCE_LOCATOR           = "{{REQUIRED: mounted source-root folder OR resolvable Drive folder link/ID}}"
SOURCE_PATHS_BY_DEVICE   = "AUTO_DISCOVER_AND_VERIFY"   # optional: specify per-device paths if needed
CODE_REPOSITORY          = "https://github.com/tlyoon/MicroGen_AI_Web.git"
CODE_REF                 = "CURRENT_USER_APPROVED_LOCAL_BRANCH_OR_COMMIT"
CODE_ROOT_BY_DEVICE      = "AUTO_DISCOVER"              # never presume a drive letter
TARGET_SELECTION         = "ALL_VALID_SOURCE_PDF_SUBCHAPTERS"
DEVICE_SELECTION         = "ALL_ONLINE_AUTHORIZED_COMPATIBLE_DEVICES"
EXCLUDE_DEVICES          = []
ASSIGNMENT_STRATEGY      = "COST_AWARE_EXCLUSIVE_OWNERSHIP"
MAX_ACTIVE_JOBS_PER_DEVICE = 1
GENERATE                 = "RESUME_INCOMPLETE_SKIP_VERIFIED_COMPLETE"
MODEL_POLICY             = "USE_EXISTING_PACKAGE_DEVELOPMENT_DEFAULT"
STAGE_TIMEOUT_POLICY     = "USE_VALIDATED_RUNTIME_WATCHDOG" # typical 900s idle, 3600s hard
RETRY_POLICY             = "DEFER_FAILED_JOB; SECOND_PASS_ONCE; BOUNDED_BACKOFF"
CONTROLLED_PILOT         = "REQUIRED_UNTIL_THIS_RUNTIME_IS_END_TO_END_VALIDATED"
CREDENTIAL_POLICY       = "USE_ONLY_PREVIOUSLY_AUTHORIZED_LOCAL_CREDENTIALS"
RUN_IDENTIFIER           = "CREATE_UNIQUE_ID_OR_RESUME_VERIFIED_PRIOR_RUN"
REMOTE_GIT_PUSH_OR_MERGE = false
~~~

- **SOURCE_LOCATOR** points to the **PDF teaching-material tree**, *never* the repository checkout. Expected default layout is SOURCE_ROOT/<chapter>/<subchapter>/source.pdf, but discover the package's accepted layout before acting. A browser Drive URL is an **identifier**, not a filesystem argument. Resolve it through an authorized Drive integration or a verified mounted/synced folder; do not assume that every PC has the same local path.
- **CODE_REPOSITORY** is an example default for this package, not a shared drive location. The existing local checked-out version may be the authoritative development version; preserve its branch and uncommitted edits. Do not pull from GitHub if the user has deferred synchronization.
- **TARGET_SELECTION** means **every** valid subchapter below the chosen root, not merely the first chapter or the first N files. To restrict scope, provide an explicit list or predicate.
- **MODEL_POLICY** does not force a particular remote model/version; inspect the installed package. In the present development configuration Flash is used for debugging. Do not turn on Pro simply because production mode exists; switch only after user authorization and a validated production test.

## Execution instructions (copy from here)

Act as the MicroGen multi-computer coordinator. Automatically discover the authorized computers and the lecture-source tree, preflight each suitable machine, then generate and verify the selected lecture materials with **exclusive job ownership, strict stage dependencies, resume safety, and reliable error reporting**. Execute through tools actually available in this session. **Do not merely provide steps to the user if authorized remote execution is possible.** When it is not possible, report the concrete blocker, not a fictitious result.

### A. Universal safety and invariant rules

1. **Immutable source:** Never overwrite, rename, remove, or corrupt any original source.pdf. Preserve unrelated XML, notes, question banks, and user-authored materials. Do not copy copyrighted source PDFs or outputs into the public code repository.
2. **Separate roots:** Detect each computer's code checkout independently from SOURCE_ROOT. The checkout name, volume letter, home directory, and Google Drive mount location are never hard-coded. Keep source, code, credentials and machine-local ephemeral logs separate.
3. **Source-adjacent publication:** Output validated slides.tex, slides.pdf, narration script.txt, rendered slides.mp4, figures and compilation assets, QA records and completion receipt into the **same folder as that subchapter's source.pdf**. Temporary staging can be elsewhere but cannot silently become the final publication location.
4. **One owner, one stage sequence:** Each selected subchapter belongs to **exactly one worker at a time**. Never work concurrently on the same subchapter. Respect the package's **actual ordered DAG**, including figure extraction/caption matching, compiled slides, narration, script QA, TTS, TTS QA, PDF slicing/MP4 assembly, and final publication. A failed prerequisite blocks every downstream stage for that subchapter.
5. **Safe concurrency:** Use at most one active lecture job and one browser-controlled worker per computer by default. Increase concurrency only if the installed package's tested scheduler and separate profiles/resource controls explicitly support it. Different computers may work concurrently on **different** subchapters.
6. **Safe resumption:** Use validated checkpoints, input fingerprints, stage versions and completion receipts. Skip completed items; resume from the earliest missing/invalid stage. Do not equate "file exists" or "process exited 0" with success.
7. **Bounded failure handling:** Detect stalled child processes, stop only their own descendants after their safe shutdown/timeout policy, preserve partial work, defer that **entire subchapter**, move to the next assigned job, and revisit deferred jobs only after an initial pass. Never permit indefinite silent waits or unlimited billed retries.
8. **Private credentials:** Do not display, transmit, replicate to shared folders, commit or log secrets, access tokens, Gemini/Google profiles or credential JSON. Reuse authorized local authentication only. Do not bypass login or consent. Respect API budget/quota limits.
9. **Frozen code and assignments:** Record and freeze the package version/commit and worker interface for a run. Do not change a shared checkout, push, merge, rebase, reset or replace code while any worker may be executing it. Protect unrelated changes. An eventually consistent synced folder is **not** a distributed mutex.
10. **Evidence:** Say "verified complete" only after testing published outputs and QA. Automatic removal of numbered WAV/PDF intermediates and temporary workspaces is permitted **only after verified completion**, using the package's own selective cleanup; never prune failed stages.
11. **Honest control limits:** Work only through authorized tools. If a computer becomes unavailable or the session cannot supervise it, distinguish an independently running managed worker from an assistant that can no longer observe it. Do not promise background continuation without a real active scheduler.

### B. Discover devices without hard-coded hostnames

1. Enumerate the **live accessible device list** from any authorized host/desktop/remote execution integration. Identify each device using stable device ID plus reported hostname; use labels only for display. Include newly connected machines; do not assume a fixed quantity of computers.
2. For every detected device, obtain an eligibility record: online/reachable, OS/architecture, actual filesystem permissions, available RAM/disk, CPU capacity, code location, available runtime/worker interface, optional accelerator, PDF-root accessibility, sync state, Python toolchains, LaTeX/FFmpeg, browser automation availability, Gemini/TTS credentials **presence only**, and whether another conflicting job is active.
3. Use platform-specific probes as needed: Windows PowerShell, macOS/Linux shell, or a remote tool's file/process APIs. Commands must be discovered from the local OS; **never paste Windows-only paths or commands onto a Unix host**.
4. Locate the code root from the actual Git remote/module location or user-approved local path. Check branch/commit and dirty state. If code is missing, provisioning or cloning requires an explicitly approved location; do not create a duplicate checkout inside the PDF tree or overwrite an existing directory.
5. Resolve SOURCE_LOCATOR independently on every machine. When a Drive URL/ID is supplied, map it through an available Drive connector or established sync client to that device's real path; if no mapping is possible, request the missing path rather than guessing. Keep a table of **canonical logical source identity → device-local physical path**.
6. Confirm cross-device source equivalence using the same relative subchapter paths plus a sample/full source.pdf hash manifest where feasible. A common folder name or same Git SHA does **not** establish the same dataset. Allow synchronization time, check cloud file hydration/write permission, and detect conflicting/out-of-date PDFs.
7. Local Python executables, virtual environments, Chrome profiles, API credentials and process logs **must be device-local** even when the code/source trees are cloud-synced. Never execute a virtual environment simply because its files were copied from another machine.
8. Classify each machine as: READY, PREPARABLE, BUSY, UNREACHABLE, INCOMPATIBLE, or EXCLUDED. Attempt safe, non-destructive environment repair only with necessary permissions; do not silently install system software as administrator. Where platform support is missing, mark INCOMPATIBLE and specify precisely what adapter is needed.
9. Continue using the verified READY subset, even if there is only **one** computer. Do not falsely announce participation of all connected machines. Log excluded PCs and reasons.

### C. Portable runtime and interface compatibility gate

1. Examine the **installed** MicroGen entrypoints/CLI --help, Python import requirements, platform checks, test results, current branch, and worker protocol. Do **not** assume an example command is universally supported.
2. Prefer the package's native, validated multi-worker scheduler. Normalize tasks at the **orchestration level** to device ID, dataset-relative source ID, stage, checkpoint and expected outputs. Map these to each adapter's actual invocation.
3. A Windows-only implementation, fixed worker-name enumeration, incompatible manifest schema, shared-path equality check, or OS-specific process kill is a **software limitation**, not a prompt parameter to bypass. If no safe adapter exists for a host, exclude that host or, **before** any production run, develop and test a proper compatible adapter in a controlled implementation task with the user's authorization.
4. In the October 2026 experimental implementation, selenium_pipeline.three_pc_worker currently uses a fixed set of worker names, Windows msvcrt locks and a manifest source_root equality check. Consequently a different OS, new hostname, or distinct local source path is **not automatically supported** by that worker. Do not invent flags, fake names, patch the active code, or claim they are supported until a tested replacement lands.
5. Portability requirements for a future adapter: stable opaque worker IDs (rather than a fixed three-name list), per-device source-path mapping with a common **logical dataset ID**, OS-neutral file/process locks and child cleanup, per-platform dependency/bootstrap checks, flexible task ownership, durable run-state storage, and reliable lease/recovery semantics.
6. Cross-machine coordination **must not** rely on a filesystem operation being atomic if Google Drive/sync semantics cannot guarantee it. Use disjoint immutable assignments plus verified no-overlap launch, or a tested central lease/lock service. The optional Drive ticket/lane approach is experimental until proven safe.
7. If the package lacks a safe way to assign a large queue across arbitrary workers, choose the closest **verified** subset of supported workers and explicitly report the unimplemented portability gap. Do not silently claim the whole pool is being used.

### D. Inventory and adaptive work allocation

1. Read-only enumerate all eligible source.pdf paths under the source root; natural-sort chapters/subchapters. Record dataset-relative IDs, SHA-256 or equivalent stable fingerprint, page counts, incomplete stages, valid completion receipts, and prior failures. Reject non-PDF, malformed and duplicate paths with a documented reason.
2. Create exactly one canonical inventory shared by the coordinator. Do not interpret a source folder's stale generation files as a successful lecture. Freeze the inventory and source hashes for the run; if a source changes, stop and invalidate only its job after the appropriate safe checks.
3. Estimate remaining work using source size/page count, number of figures when measurable, prior stage durations, supported model quota and device speeds. Balance **expected remaining effort**, not just number of chapters.
4. Assign disjoint chapters when the verified worker only supports chapter-level ownership. If a newer tested worker supports subchapter ownership, use finer-grained balancing without ever assigning a subchapter to multiple computers.
5. Produce a **manifest appropriate to the supported runtime**: unique RUN_ID; canonical dataset ID/hash; frozen package version; source path mapping per device where the adapter supports it; worker IDs; assignments; source fingerprints; current model policy; retry/watchdog settings. Persist it where every READY worker can verify its contents. Allow Drive sync to settle; read back its checksum on all participants before launch.
6. For older runtimes whose schema includes a literal source_root string, ensure exact supported behavior. Do not insert unsupported path maps into legacy manifests. If the runtime cannot handle per-device mount differences, choose a supported common mounted path or a tested adapter; otherwise exclude affected workers.
7. Before launch, reconcile every discovered valid subchapter: completed/skipped or assigned **once** or explicitly blocked. No missing or double-owned job is permissible.
8. A reassignment after host failure requires proof that its previous worker and child processes have stopped, explicit release/expiration of ownership, and a newly validated manifest/epoch under the compatible scheduler. Never edit active worker ownership in place and rely on delayed cloud synchronization.

### E. Preflight, validation pilot and execution

1. Compare code versions and dependency compatibility on participating machines. Prefer a **read-only code freeze** over git pull/push. The coordinator should use the same verified code revision on all workers; if this is impossible, report which workers were excluded.
2. Check environment without leaking credentials: Python dependency import tests, required external executables, Drive read/write authorization, existing Gemini/Google auth, actual browser mode/model, local ports and Chrome profiles, FFmpeg H.264/AAC support, PDF/LaTeX compilation and TTS availability. Validate needed quota/budget limits.
3. Run each runtime's doctor/tests and a worker **dry run**, verify assigned jobs and stage order, then perform a small **full end-to-end pilot** if the scheduler/adapter is not yet production validated. A dry-run or video-only pass does not certify complete source-to-lecture generation.
4. Do not begin full production while fundamental cross-device ownership, model, dependency or stage integrity defects remain unresolved. Fix source code only in a **separate, stopped and tested** development cycle, not mid-run.
5. Launch only workers that completed the compatibility gate. Start one at a time, confirm each accepts the manifest, then allow those workers to run concurrently on separate tasks. Keep one owned active lecture job per device by default.
6. For each subchapter follow the **runtime's discovered ordered stages**. For the present Selenium workflow this includes figures, slides, narration, script QA, TTS, TTS QA, and video. Validate and publish each stage before advancing. Do not treat figureless PDFs as invalid if the correct figure stage explicitly permits them.
7. The exact worker command, Python executable, source path and log directory must be **derived per device from --help and preflight**. Do not present one hard-coded Windows command as usable on any machine.
8. Preserve existing checkpoints and outputs. Reuse verified work; use controlled force/regenerate options only for explicitly requested rebuilds. Keep the original PDF immutable.

### F. Recover from stalls and repeat once

1. Observe actual progress (stage logs, checkpoints, process tree, API/UI status, file changes and heartbeats), not just a connected browser or a blinking interface.
2. Apply the runtime's validated idle and hard timeouts, initially about **900 seconds without stage output** and **3600 seconds total per stage** if supported. Inspect quiet but healthy work before killing; never disable watchdogs to hide a deadlock.
3. On a proven timeout, use the platform's **tested** process-tree termination to stop only that worker's own stalled stage. Verify it is no longer writing; preserve logs and checkpoints.
4. Mark the subchapter DEFERRED **at its failed stage** and continue to the next allocated subchapter on the same computer. Do not attempt downstream stages for that subchapter.
5. After every assigned subchapter has had one initial attempt, revisit deferred work **once by default** with bounded backoff and only from the earliest incomplete/invalid stage. Respect quota/capacity limits; avoid collective retry storms.
6. After the second pass, mark still-blocked work UNFINISHED with last valid stage, reason, logs, and next safe remediation. Do not declare global success while unfinished work is omitted.

### G. Verification, cleanup and cross-device sync

1. For each claimed completion, inspect **the source-adjacent outputs**, not solely the worker's JSON status: original PDF unchanged; nonempty/valid slides.tex, slides.pdf, script.txt, slides.mp4; required figure/style assets present; QA reports clear of blocking issues; narration matches slide order/count; playable MP4 has audio and video streams and plausible duration.
2. Check the package's completion receipt/checksums and ensure outputs correspond to the input source and requested model/configuration.
3. Let the package remove only known generated **transient** files after verified success. Retain source.pdf, editable LaTeX, required figures/style files, compiled slides, script, MP4, QA evidence and compact completion receipt. Failed/incomplete jobs retain staging and diagnostics.
4. Cross-check a sampling of final media from a **different synced computer** when at least two are available; otherwise verify against local filesystem and known authoritative storage. Detect delayed Drive sync and unresolved conflicts.
5. Reconcile total discovery against **previously complete + newly verified complete + explicitly skipped/unfinished**. Ensure no duplicate ownership and no silently lost subchapter.

### H. Live updates and final report

Provide concise, factual progress: canonical PDF dataset/root, discovered subchapter count, run ID, participating machine list with OS and local source path, exclusion reasons, estimated load/assignments, frozen code version, model mode, pilot status, and per-PC current stage with last observed progress.

At the end, provide a table/ledger per subchapter with owner, outcome, last valid stage, resume action and output location; aggregate verified complete/total; show deferred and unfinished counts, retry outcomes, unresolved blockers and the exact resume instructions. Distinguish **scheduled**, **started**, **currently running**, **stalled**, **failed**, and **verified complete**.

If a requested computer is not compatible, state that clearly rather than quietly ignoring it. A generic prompt is not evidence that arbitrary operating systems or unsupported devices work today.

**Git boundary:** Unless the user separately authorizes it, do **not** push or merge GitHub changes, sync branches, delete backup directories or make invasive system modifications. Generation and the program's validated transient cleanup are the only ordinary write actions authorized here.

## Operator acceptance / portability regression checklist

- [ ] Source locator resolved to the same logical dataset on every accepted machine; no fixed drive letter.
- [ ] Devices enumerated dynamically, with online/busy/unsupported statuses reported.
- [ ] No hostname, OS, worker count or Python path is assumed by the prompt.
- [ ] Actual package support is tested; unsupported platform/worker interfaces are excluded honestly.
- [ ] Every source.pdf included exactly once; balanced exclusive assignments are frozen before launch.
- [ ] Credential checks reveal no secrets; each PC uses local auth, environments and browser profile.
- [ ] Dry-runs and controlled end-to-end pilot passed before scaling up.
- [ ] Sequential, validated stage DAG enforced; blocked jobs deferred and retried only afterward.
- [ ] Watchdogs and process cleanup tested; no duplicate writing or unsafe Drive locking.
- [ ] Completed outputs verified beside source.pdf, with original source unchanged.
- [ ] Intermediates removed only after successful publication; failed work preserved.
- [ ] Final counts reconciled; no unverified success or unapproved GitHub push.

## Implementation-readiness note for maintainers

**Prompt generality and runtime portability are separate deliverables.** The current experimental scheduler's hard-coded worker identities and Windows-only locks mean this v2 prompt can **discover** arbitrary computers but cannot run them all until a portable worker adapter/scheduler is implemented and tested. Treat that as a distinct engineering task. Keep this prompt reusable without claiming those code changes have already shipped.

Refer to the currently checked-out README.md, selenium_pipeline/README.md, selenium_pipeline/runner.py, selenium_pipeline/three_pc_worker.py (if present), selenium_pipeline/distributed_stage.py (if present), output path/cleanup modules, tests, and .env.example for the concrete implementation contract.
