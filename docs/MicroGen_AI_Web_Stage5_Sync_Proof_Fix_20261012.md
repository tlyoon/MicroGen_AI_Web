# MicroGen_AI_Web Stage 5: Source-Adjacent Structural Alignment Proof

Date: 12 October 2026
Repository: **tlyoon/MicroGen_AI_Web** only. Do not apply to the separate tlyoon/MicroGen_AI package.

## Production defect

During the three-PC end-to-end Gemini Flash pilots, Dell-115 completed Serway 8.2 and passed the source/final-output hash receipt check, but **no slide_narration_sync.json was present beside source.pdf**. The root cause was a missing entry in selenium_pipeline/output_paths.py: the structural proof had been created and verified inside .microgen_work after successful TTS QA, but the tts_qa publication step omitted that JSON, and final cleanup could remove its only copy. The completion receipt did not bind the synchronization proof. This is a real certification defect; a video existing is not enough.

## Permanent correction

- Add slide_narration_sync.json to the tts_qa stage's explicit source-adjacent publication list.
- Before running the video stage, verify both the workspace structural receipt and the source-adjacent structural receipt when TTS QA is recorded as complete. This checks exact PDF bytes, script text, narration block count, WAV enumeration and WAV hashes, rejecting missing or changed files without overwriting the published video.
- On successful cleanup, the existing completed-lecture receipt automatically binds a SHA-256 hash of the published structural receipt. Any subsequent change or removal invalidates completion.
- Do not automatically reinterpret old unbound completion receipts as structurally certified. Review the TTS fidelity report, inspect exact slides/script/WAV files, and reconcile older outputs with a separately verified procedure.

## Regression and acceptance

New tests simulate source-adjacent publication from a synthetic workspace, verify that the structural proof survives deletion of the workspace, bind its hash to the final completion receipt, invalidate a changed WAV, and reject missing proof before video. Existing Stage 4 tests remain in place. Dell-115 isolated checkout passed **265 tests**, 9 non-fatal warnings. CI on Windows and Ubuntu is the merge gate.

## Live run isolation

Two earlier live pilots (HP Serway 9.9, Yoga6 Serway 13.6) were started on commit d5f5023. They continue on their own unchanged local acceptance checkouts while this fix is reviewed. Do not hot-replace an active runtime, mutate source PDFs, or overwrite generated slides or WAVs.

## Scope of remaining certification

After the commit is merged, verify full TTS QA and MP4 stream/duration on HP and Yoga6, and certify/reconcile the legacy local acceptance outputs only after inspecting their fidelity reports and published media. Scientific correctness of the source-grounded figures and lecture content still requires content review beyond structural and acoustic checks.
