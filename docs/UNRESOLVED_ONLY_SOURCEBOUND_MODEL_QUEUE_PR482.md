# PR482 — Incremental model queue without repeating source-proven work

## What this closes

The earlier existing rich-element mapper attempted every original narration line, including independently proven ordinary prose, on each new model review. If Gemini failed, the same request could be submitted again without any benefit. PR481 accepted 12 simple prose-to-textbook-to-author PDF mappings out of 167 original utterances. These verified links must never be reopened just to make a new model request.

PR482 adds `selenium_pipeline.rich_unresolved_model_queue`, which produces only the unresolved utterance subset for each original source/author/script SHA, retains the 12 accepted prose links unchanged, and creates a source-external immutable queue for later Gemini/ChatGPT semantic candidate generation. It does not send model requests itself.

## Exact integrity boundaries

The queue re-verifies the original accepted PR475 source/author/script worklist and PR481 fallback response, using both stable JSON content hashes and **physical response file SHA-256**. It recomputes physical original PDF visual element geometry and source textual evidence before merging any model reply. Previous independently verified prose decisions are copied unmodified and cannot be submitted or replaced by a model. A model response contains only original unresolved utterance IDs, selected existing PDF target IDs (or null), original source page, exact quote and declared uncertainty. New math/figure semantics remain held for independent mathematical/image proof; no new paid TTS, human academic approval or student publication can follow merely from this queue.

## Usage

Prepare new model queue (no provider calls):

`python -m selenium_pipeline.rich_unresolved_model_queue prepare --source-folder <original> --checkpoint <accepted-PR475-worklist> --fallback-dir <PR481-accepted-prose-response-dir> --out-dir <NEW-external-dir>`

Offline audit of a completed individual **unresolved-only** model response:

`python -m selenium_pipeline.rich_unresolved_model_queue merge --source-folder <original> --checkpoint <accepted-PR475-worklist> --fallback-dir <PR481-accepted-prose-response-dir> --queue-folder <new-incremental-queue> --slide N --partial-response <existing-JSON> --out <new-external-full-response>`

A successful *technical-only* merge can then feed PR480's independent full-deck compiler and the existing source-bound guarded TTS request planner, with no implicit paid generation. Gemini UI response failures should use the existing no-resend state ledger and explicit reconciliation.

## Real original Dell-115 checkpoint

All original 41 slides, 167 utterances and 235 visible PDF candidates: **12 independently accepted safe prose links retained unchanged** (4 §8.4, 3 §8.5, 5 §8.6); **155 genuinely unresolved mathematical, visual or lexical mappings** (61, 42, 52) queued without repeats. All three sections pass physical publisher/author/script SHA and physical accepted fallback response file-byte checks, with no source edits and zero new model/TTS/media calls.

The original externally versioned review-only queue is retained at `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261103_PR482_SHA_PHYSICAL_PROOF_UNRESOLVED_QUEUE_V2`. A preceding V1 exploratory receipt is left untouched, not silently overwritten. PR482 independently verifies V2 byte integrity and blocks tampered old acceptance or fabricated new model claims.

This is an engineering efficiency and provenance milestone. It does NOT claim that 155 unverified utterances have been semantically resolved or that all original lectures now reach final H264 production. Next necessary work is obtaining real source-bound Gemini/ChatGPT proposals using an authenticated responsive UI (Gemini was unresponsive and ChatGPT's Dell automation profile is logged out), plus independent mathematical/figure proof for the selected mappings, then a genuine complete lecture.
