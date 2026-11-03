# PR479 — General rich-element alignment bridge

## Product blocker

The normal figures-to-video runner and sourcebound multipart renderer are now connected, but the original Thomas §8.4/§8.5/§8.6 explanatory narration is not verbatim textbook slide text. Existing strict text-only mappings fail on diagrams, equations, and actual author text fragments; the complete 41-slide worklist has 167 original utterances and 235 visible candidates, of which 93 lacked a confident initial mapping. Rechecking Figure 8.3 source similarity is not the solution.

## New reusable execution interfaces

**Request creation:** `python -m selenium_pipeline.rich_element_model_alignment --source-folder <source-folder> --checkpoint <existing-rich-element-map-folder> --slide 3 --out <new-review-prompt.txt>`. This produces the exact original source/author/script SHA-bound candidate targets, genuine on-slide geometry, exact original spoken utterances and publisher source excerpts. It can be supplied to ChatGPT or Gemini. The real 41-slide request bank was produced on Dell-115 without any paid API at `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261103_PR479_DELL115_SOURCEBOUND_AI_MAPPING_PROMPT_BANK_NO_TTS\`.

**Bounded Gemini web option:** Use `--gemini-web` instead of `--response <previous-json>` to submit one request through the existing authorized Flash UI. A submission uncertainty receipt is saved *before* the browser call; if the model times out, returns a placeholder or fails strict JSON parsing, there is NO automatic resend. No cloud model API cost is incurred. The initial unmodified single-slide Gemini browser probe had a completed UI submission but returned no complete valid response; the new bank deliberately does not silently resubmit it.

**Source-independent audit:** `assess_response` rejects changed source hashes, invented visual target IDs, swapped/missing narration, fabricated textbook quotations or unsupported publisher pages. It recomputes the authored PDF element rectangle and flags named incompatible trigonometric functions, mathematical symbol/sign/domain claims, source-quote lexical inconsistency, and all figure/panel semantics as unresolved rather than treating model confidence as proof.

**Selection compiler:** `python -m selenium_pipeline.rich_element_selection_compiler --source-folder ... --checkpoint ... --responses <model-response-dir> --out <new-selection.json>` compiles any complete set of model responses into the EXISTING `element_plan_review_bridge` selection format. All original utterance IDs must remain ordered, every mapped element physically anchored in original source/author PDF bytes, conservative multipart timing retained, and every slide's publisher quote separately verified. Only fully source-checked *nonmathematical text* can become a machine-qualified **technical-only** processing selection. Ambiguous source mathematics, figure semantics, wrong/missing responses or repeated noncontiguous targets remain explicit `REVIEW_SELECTION_INCOMPLETE` and cannot trigger TTS.

**Actual source-bound TTS promotion wiring:** `element_plan_review_bridge.promoted` now detects machine-qualified technical selections and REBUILDS their exact evidence from frozen source/author/script bytes and the original raw model responses at the moment of preparing the reviewed TTS request. Changed responses, modified PDF, changed narration, or changed candidate data fail closed. Existing independent Gemini paid TTS consent and all encoded media / student publication restrictions remain unchanged.

## What is demonstrated and what is still open

Selected native Dell Windows synthetic PDF integration tests show that an ordinary *nonmathematical* source/author/mapped narration scene can enter the existing TTS-request preparation stage **without** synthesizing audio; missing/modified or mathematical messages fail to do so. All 41 true original Thomas request prompts were generated read-only, but there is no claim all 93 uncertain element mappings are accepted or a fresh figure-rich lecture was rendered. The earlier Gemini live UI submitted but did not return valid complete JSON; recovering model proposal service, resolving mathematical/figure evidence and then completing a real end-to-end lecture are still necessary.

No original PDF/PNG/WAV/MP4 or original user checkout was modified. No local LLM, no HP/Yoga/Ubuntu, no paid TTS and no student publication. Do not reopen already accepted original Figure 8.3 full-image similarity.
