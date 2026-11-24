# G3 recovery: separate narration transitions from genuine textbook science claims

This is an executable MicroGen_AI_Web repair, not a narrative instruction to the user to issue another "proceed" command. It acts on the preserved original Serway §8.2 and §8.3 G3 source-rejected worklist V2 and the original source.pdf, slides.pdf, script.txt and historical browser captures.

## Historical source failure

The original source-rejection repair produced six missing-quotation narration units. Initial lexical matching provided qualifying quotations for three; three remained unsupported. The original author textbook and rendered slide PDFs were re-opened from the physically saved Dell-115 G3 state.

On the real source inputs, the remaining three are:
- Serway §8.2 `s002.utterance.005`: "Finally, we will review the key concepts with summary points and conceptual questions." This is a narrator transition introducing the visible "Summary and Review Questions" target, **not a physics derivation**. A fabricated textbook quote would be incorrect; the rendered questions and any scientific statements on that slide still require independent scientific/visual QA.
- Serway §8.2 `s015.utterance.001`: "To conclude, consider these two review questions." This is also a narrator transition. The slide has two actual physics review questions (Example 8.3 cable length R and system/Earth gravity modeling), which still require separately grounded scientific/visual checks. The transition is not an academic acceptance of either question.
- Serway §8.3 `s002.utterance.003`: "From there, we will use Newton's second law to derive an exact work and energy relationship that incorporates friction." This IS a substantive scientific claim. The previous candidate list shared only "friction" with the narration and omitted the actual derivation on original publisher PDF pages 2–3. Full original-PDF context scanning now finds four **physically witnessed contiguous quotations**, including the Equation 8.13 change-of-kinetic-energy relation and an earlier explicit explanation that the work–kinetic energy theorem cannot directly use the point of application of friction in the sliding book. These excerpts are useful REVIEW EVIDENCE, **not mathematical proof or reviewer approval**.

## Executable resolution and automatic forward

New `selenium_pipeline/g3_prepass_source_gap_repair_v1.py` handler:
1. Verify each original source-rejected model claim, raw captured response bytes, original source/slides/script hashes, exact utterance and rendered target and V2 worklist digest. Never regenerate, modify, or replay historical requests.
2. Apply only two extremely narrowly matched narrator transition phrasings and their corresponding original rendered slide targets. Never classify an actual physics claim as a non-science transition through generic stopwords. Preserve an independent visual/source QA obligation and student publication false.
3. For an actual science assertion still missing adequate quotations, scan the full bounded original source.pdf using contiguous adjacent physical publisher text windows with >=2 substantive spoken-term overlaps plus the visible slide target, physical quote SHA and page witness, not general model knowledge or an outside PDF.
4. Stage a new immutable SHA-bound one-original-utterance, distinct initial+independent-challenge model source-review job with exact original source PDF and slides PDF. Do **not** grant G3 mathematical acceptance based on a lexical quote.
5. Integrate into normal `g3_multisection_autoforward_v71` source-only and `--auto-forward-science` paths. The normal G3 global finite-budget dispatcher includes the new prepass task as a fresh, independently eligible source scope and automatically moves to subsequent tasks after genuine completion/disagreement/uncertain Send, relying on the previously merged cross-campaign no-replay guard.

The first V1 diagnostic worklists are preserved outside source files. The corrected classifier is V2 in `state/g3_prepass_source_gap_repair_v2` and will never silently overwrite earlier V1 evidence.

## Real verified result

On Dell-115 original immutable Serway 8.2/8.3 source, V2 source-only results:
- **3 historical missing quotation cases** examined; **2 narrator transitions**, both with mathematical/visual slide QA still pending; **1 new genuine source-science review task** based on **4** physically verified original publisher quotations; **0** cases left unclassified at the source-triage stage.
- **0** Gemini browser Sends, **0** paid Gemini API calls, **0** academic/source/model promotions, **0** student release in V2 staging.
- Next live science stage is a genuinely distinct `Serway_8_3 s002.utterance.003` two-pass Neon/High Selenium review, followed automatically by other eligible source tasks within a bounded new campaign, without resetting the previous 2026-11-24 four-Send campaign or replaying the original §8.2 held context Send.
- Every response must be independently source/provenance validated and saved; any unsupported scientific conclusion, uncertain browser Send, missing authorization or finite budget exhaustion is an explicit named boundary, not an invitation to invent evidence.

## No accidental cross-project / authority changes

This patch belongs to `MicroGen_AI_Web` only. The old read-only v71 daemon and disabled scheduler tasks remain disabled. Paid Gemini API fallback remains strictly disallowed for physics/slide/scientific content. Original textbook-only content grounding, physical quotation witness, independent G3 acoustic/video/second-subsection QA, and user publication controls are preserved.


## Real live Gemini failures and additional automatic repair (same run)

A bounded new source review of §8.3 `s002.utterance.003` ran from a truly new, source-pinned academic task with the full original source.pdf and slides.pdf ready, authenticated Gemini Neon/High and exactly one registered user Send. Gemini then returned `OWNED_GEMINI_UI_ERROR_AFTER_VERIFIED_NEW_USER_TURN` without an independently attributable model answer. It is `SUBMITTED_OR_UNCERTAIN`, no replay, no API fallback. The forward controller correctly held this scope and moved to the next genuinely eligible new §8.3 context task, but its existing source-free health receipt predated the new UI incident, risking a second already-unhealthy Send. That next source-backed task was also held without any scientific acceptance. The finite campaign `g3_new_evidence_serway83_20261124a` is now exhausted (4 possible Send slots reserved; no original historical Send repeated).

Additional executable recovery `g3_browser_post_send_health_gate_v1.py` solves this **historical recurring provider-health boundary**, integrated in normal `g3_continuous_advance_v1`. It scans all original subsection source-science task owners (original distinct, independent context, publisher-prepass), detects the latest genuine unowned/uncertain science Send and requires **new independently owned Neon/High source-free health with an observation timestamp after that event**. An earlier health receipt, even if less than six hours old, is not sufficient. A once-per-original-source/UTC-day health request cannot be silently rearmed or replayed after an uncertain Send. When a fresh diagnostic is unavailable, the next genuine science Send is **not reserved**; the controller can still advance safe offline work without paid API or Student QA bypass. The separate source scopes are isolated: Serway §8.2 provider claims cannot invalidate health provenance for unrelated §8.3 source.

Real source-only Dell probe: original §8.2 and §8.3 both have independently recorded unresolved recent Sends and their prior source-free health receipts do not qualify after those incidents. Both are held for genuinely fresh health, not given fake science outcomes. New tests cover source-scope separation, a newly uncertain first or challenge, independently observed recoverable reply, torn checkpoint, changed source SHA, and global finite budget not consumed by stale model-health evidence. This fix adds `g3_post_send_health_invalidation` to executable registry (92 entries).
