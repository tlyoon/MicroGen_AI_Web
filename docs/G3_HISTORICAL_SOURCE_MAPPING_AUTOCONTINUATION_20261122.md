# G3 automatic source-grounded mapping: historical recovery — 22 November 2026

## Why the old blocker recurred

Previously, `rich_element_mapping_checkpoint.py` correctly recognized rich
graphics and mathematical narration and saved a complete full-deck review
worklist, but ALWAYS raised `ElementMappingCheckpointBlocked`. The normal
legacy-to-video handoff never automatically invoked the older
`rich_element_model_alignment.py` Gemini Selenium browser source reviewer,
nor did it resume source-verified model captures after a restart.

Historical code already had source-PDF physical source quotation checks,
author-PDF target geometry, independently registered figure/panel candidates,
one-request Send claims, and a real browser capability presend check.
Implementing another approximate semantic matcher is NOT the solution.
The preceding Thomas source/word/audio/video demonstrations are evidence for
selected specific cases, not a general assertion that all narrated diagram
and mathematical meanings can be proved algorithmically.

## Real Serway §§8.2 and 8.3 evidence

Both exact original PDF/slides/script sets were SHA-copied to local-only
isolated staging; the Google Drive originals were not modified.
The full-deck candidate worklists contain:
- §8.2: 15 slides, 77 original sentence fragments, 178 physical candidate
  visual elements, 47 lexically ambiguous fragments.
- §8.3: 17 slides, 94 original sentence fragments, 194 physical candidates,
  68 lexically ambiguous fragments.

The 115 total ambiguous flags are lexical ranking failures, NOT scientific
errors or a count of independently rejected math propositions. An
unrestricted inclusion of older grouped source text candidates was tested
on all 171 real fragments, but **increased** ambiguity to 146; it was
deliberately not adopted. The existing very strict literal source-PDF/text
matcher validated 0 full fragments, because these lectures paraphrase
source material. The deterministic historical safe-prose fallback therefore
cannot manufacture a complete proof.

The historical `rich_element_model_alignment.py` **did work** on original
§8.2 slide 3 using the authenticated Gemini **Selenium browser** transport:
one claimed Send, real original-model bytes and request fingerprint saved,
real source quote and authored PDF geometry validated. Exactly 2 of its
7 original utterances obtained independent *text* anchors; 5 remain open.
The model proposal, verbatim captured JSON, technical source audit and
persistent one-Send claim are immutable. Academic content acceptance,
spoken math meaning, audio, element highlight timing and student release
are explicitly false. No Gemini Developer API request was used.

## Integrated executable continuation

`selenium_pipeline.g3_rich_mapping_auto_continuation_v71` reuses the
pre-existing model and source/audit mechanism. It:
1. Verifies exact frozen source/slides/script SHA, source-only review
   checkpoint and immutable candidate worklist; stores exact job identity
   outside the source tree.
2. Uses a single exclusive OS-released queue lock to prevent concurrent
   browser owners. Scans every slide in deterministic order and prioritizes
   the most unresolved frozen candidate counts, **not** an automatically
   approved mapping.
3. Revalidates any saved original response's prompt identity, raw model
   capture, source quote, author-PDF geometry, and SHA. One previously
   independently verified source review can be adopted without resending
   the model request.
4. For a fresh untouched slide, invokes the EXISTING Selenium browser-only
   rich mapping CLI. The earlier CLI saves a durable
   `submission_held.json` before the unique model Send, then original
   captured bytes before parsing or source validation.
5. Never retries a claimed original request, even after a timeout, crash,
   malformed JSON or rejected source quote. After two distinct uncertain
   or rejected captured replies, a **persistent across-restart** circuit
   breaker denies further fresh Sends.
6. Bounds a single invocation to 0–3 explicit browser requests. The default
   command (0 requests) is a pure offline inventory/reconciliation. Each
   result remains REVIEW ONLY.
7. Integrates the mechanism and its fault-injection regression into the
   executable `selenium_pipeline/recovery_registry_v1.json`.

It does NOT grant TTS authorization, scientific acceptance, audio
transcription verification, video QA, or student publication. Nothing
removes G2's historic uncertain source review boundaries.

## Repeatable commands (Dell-115)

Run offline recheck (no provider Send):

```powershell
python -m selenium_pipeline.g3_rich_mapping_auto_continuation_v71 \
  --source-folder "<isolated G3 root>/inputs/8_2" \
  --checkpoint "<isolated G3 root>/mapping_checkpoints/rich_element_map_f4972ce51b4626025f7bfe8e" \
  --review-root "<isolated G3 root>/automatic_source_reviews/8_2" \
  --max-new-sends 0
```

Only on an explicitly allowed Selenium-owned source mapping run, set
`--max-new-sends 1`; the browser model picker is independently verified
before its one Send and any unreturned request is quarantined. Never
invoke a second new worker against the same queue while the original
worker is in progress.

## Remaining independent G3 acceptance

Any successfully mapped text anchors remain **technical source reference
candidates** only. The remaining mathematical statements, graphic panels,
word-level acoustic alignment and actual time-varying highlighted video
events require the unchanged independent scientific, acoustic and
encoded-pixel QA. Neither the original slides' static MP4s nor newly
captured model text can substitute for those acceptance gates.


## Historical regression while testing (fixed)

The Dell-115 full run exposed a test-only interaction between a saved real
Gemini task-default family and the old tab-ownership fake picker.
`tests/test_stage5_owned_gemini_tabs.py` was testing tab separation but
implicitly let production-style dynamic model-selection state influence its
fake (which represents Flash only and has no model-switch click).
The test now explicitly isolates its own Flash mode and disables adaptive
model fallback **only within the test fixture**, restoring all environment
settings afterward. The actual Gemini dynamic model router and paid/no-paid
policies are unchanged. Reproduced under ambient Pro and passed 18/18
related owned-tab / G3 controller tests.


## Crash injection after partial adoption of old verified browser evidence

A first implementation assumed importing an earlier model capture would
complete in one run. Crash after copying one or two of four source-audited
files could leave incomplete evidence and prevent normal continuation.
The verified remedy now resumes each individual import only if its
previously copied destination has the EXACT original SHA-256 bytes.
Absent files are copied write-once; changed/linked files reject the import.
The same original response and audited citation evidence are then
revalidated; the original model request is NEVER resent. The first
20 focused source-queue, fake owner and crash-injection tests passed on
Dell-115, including a simulated mid-import crash and malicious replacement.
