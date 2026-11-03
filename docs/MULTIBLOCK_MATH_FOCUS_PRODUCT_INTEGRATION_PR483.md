# PR483 — Source-bound multiblock mathematical focus, integrated into normal authoring

## Production problem

Original Thomas PDFs contain displayed equations distributed across multiple PyMuPDF text blocks, so existing source-to-visual mapping may have no complete target even when the correct expression is physically visible. Source-bound narration mapping cannot be completed by rechecking individual symbols forever.

## Production implementation

A generic, bounded `text_group` authored PDF anchor combines 2–3 immediately adjacent physical authored text blocks, with exact SHA-256 of each original block's bytes, ordered PDF block indices, geometry/adjacency checks, title/footer exclusion, and bounded highlight size. `scene_candidate_authoring.draft` automatically offers such targets when mathematical notation spans adjacent blocks; `element_narration_stage.rectangle` independently rereads the original authored PDF and rejects any changed block. `rich_element_model_alignment.assess_response` recognizes these as text targets rather than fabricated figures, and `rich_element_selection_compiler` can prepare a technical text-group selection only when all existing independent source and mathematical claims are genuinely verified. No new paid model or TTS calls, no original assets or scientific acceptance data modified.

**Crucial security boundary:** Grouped *geometry* does not certify symbol signs, equation/domain equivalence, publisher identity, narration correctness or figure semantics. Mathematical statements remain held by the independent QA/proof contract until supported. The new groups are candidate focus regions, not a false academic approval.

## Real Dell-115 original-corpus measured results

On genuine frozen publisher/author/source/script §8.4 (17 slides), §8.5 (11), and §8.6 (13), in independently versioned read-only `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261103_PR483_MULTIBLOCK_MATH_FOCUS_VERSIONED_REAL_SOURCE_V2`:

| Section | New bounded grouped focus candidates | Previous visual candidates | New total visual candidates | Existing independently accepted safe prose links retained |
|---|---:|---:|---:|---:|
| 8.4 | 37 | 101 | 138 | 4 of 4 |
| 8.5 | 42 | 66 | 108 | 3 of 3 |
| 8.6 | 25 | 68 | 93 | 5 of 5 |
| **Total** | **104** | **235** | **339** | **12 of 12** |

This reindexes only *new physical candidate extraction* for enhanced support; all earlier accepted source glyph/figure identity/scientific receipts remain unchanged and are NOT rerun. All original publisher/source, authored slides, and narration SHA values remained identical. Newly versioned mapping worklists, if used, require separately versioned unresolved-only queue; never modify or quietly reinterpret old queued model requests.

## Remaining product completion work

The newly exposed 104 real visual regions are not yet proof that the 155 remaining original narration utterances can be assigned. Next work should use a single guarded model-provider selector and independently verify the actual new mathematical and figure mappings; then complete one true original E2E lecture, restart/recovery, second independent source and native Windows release integration. No HP/Yoga/Ubuntu/local language models and no student publication.
