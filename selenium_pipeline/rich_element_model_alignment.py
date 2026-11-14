"""Source-bounded Gemini/ChatGPT proposal bridge for rich lecture element mapping.

Operational contract
--------------------
This is a GENERAL semantic mapping assistant, not source or student publication
approval. Text source quotes, exact authored PDF geometry, all 167 original
narration utterance IDs and source/slide/script hashes are independently
reverified. Figures, uncertain maths, incompatible functions or weak source
links remain explicit review items. Model output cannot directly authorize TTS.

Browser mode is opt-in and uses only the existing authenticated Gemini WEB UI
via the project's approved Selenium transport, not any paid API. A failed
capture is quarantined as an uncertain submission rather than auto-resent.
"""

from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf

from .element_narration_stage import rectangle, ElementStageError
from .rich_element_mapping_checkpoint import _receipt, _source_hashes
from .scene_candidate_authoring import terms
from .series_gemini import decode_storyboard_response


class RichMappingError(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise RichMappingError(why)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf8"))


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u2212", "-")
    return " ".join(value.casefold().split())


# Unlike the older loose math word hint, these terms NEVER match empty text.
# A named incompatible trigonometric family must not be aligned to a different
# explicitly named family merely on a high lexical overlap.
_TRIG = {
    "sine": r"\b(?:arcsine|inverse[\s-]*sine|sine|sin|sin[\s]*[-^][\s]*1)\b",
    "cosine": r"\b(?:arccosine|inverse[\s-]*cosine|cosine|cos|cos[\s]*[-^][\s]*1)\b",
    "tangent": r"\b(?:arctangent|inverse[\s-]*tangent|tangent|tan|tan[\s]*[-^][\s]*1)\b",
    "secant": r"\b(?:arcsecant|inverse[\s-]*secant|secant|sec|sec[\s]*[-^][\s]*1)\b",
}


def trig_families(text: str) -> set[str]:
    value = normalized(text)
    return {k for k, pat in _TRIG.items() if re.search(pat, value)}


def load_accepted_checkpoint(*, folder: Path, checkpoint: Path) -> tuple[dict, dict]:
    folder, checkpoint = Path(folder).absolute(), Path(checkpoint).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and checkpoint.is_dir() and not checkpoint.is_symlink(),
            "Real source folder and external approved no-TTS worklist required")
    source, slides, script = [folder / n for n in
                               ("source.pdf", "slides.pdf", "script.txt")]
    before = _source_hashes(source, slides, script)
    require(not checkpoint.is_relative_to(folder)
            and not folder.is_relative_to(checkpoint),
            "Unreviewed model checkpoint must not overwrite the original PDFs")
    meta = _receipt(checkpoint, before)
    require(meta["student_publication_authorized"] is False
            and meta["paid_tts_authorized"] is False,
            "Mapping checkpoint cannot claim authority for synthesis")
    content = json.loads((checkpoint / "element_mapping_candidates.json").read_text("utf8"))
    require(content.get("status") == "REVIEW_REQUIRED_NOT_TTS_READY"
            and content.get("can_stage_or_synthesize_audio") is False
            and content.get("academic_approval") is False
            and content.get("student_publication") is False
            and content.get("source_sha256") == before["source.pdf"]
            and content.get("slides_sha256") == before["slides.pdf"]
            and content.get("script_sha256") == before["script.txt"]
            and content.get("slide_count") == meta["slide_count"],
            "Untrusted, unbounded or stale original author candidate set")
    require([s.get("slide_number") for s in content["slides"]] ==
            list(range(1, meta["slide_count"] + 1)),
            "Expected every original slide in exact original order")
    return meta, content


def request_for_slide(*, source_folder: Path, checkpoint: Path,
                      slide_number: int, max_page_chars: int = 6500) -> dict:
    meta, draft = load_accepted_checkpoint(folder=source_folder, checkpoint=checkpoint)
    require(type(slide_number) is int and 1 <= slide_number <= meta["slide_count"],
            "Requested slide out of original author range")
    original = Path(source_folder).absolute()
    row = draft["slides"][slide_number - 1]
    require(row["slide_number"] == slide_number, "Wrong original slide ordering")
    pages = row.get("source_page_candidates_unverified", [])
    require(isinstance(pages, list), "Invalid source page candidates")
    chosen = []
    with pymupdf.open(original / "source.pdf") as pdf, \
         pymupdf.open(original / "slides.pdf") as deck:
        require(len(deck) == meta["slide_count"], "Wrong authored slide count")
        for page in pages[:4]:
            index = page.get("source_page")
            if type(index) is int and 1 <= index <= len(pdf) \
               and index not in [p["source_page"] for p in chosen]:
                literal = pdf[index - 1].get_text()
                require(len(literal) <= max_page_chars,
                        "Large source page must be split explicitly; do not truncate quotes")
                chosen.append({"source_page": index, "original_page_text": literal})
        # The original mapping checkpoint may contain the later general
        # PDF-backed math-row / raster / caption-verified panel target types.
        # Earlier source-review and safe-prose routes supported only the
        # legacy text/image rectangle helper and stopped on these genuine
        # source-verified targets as if the authored PDF had changed.
        # Reuse THE SAME independent physical verifiers as the normal
        # original-source candidate map, not a guessed bbox or an AI claim.
        # This is review INPUT ONLY. Math / figure meanings remain blocked
        # from automatic semantic promotion by assess_response below.
        target_rows = []
        canonical_panels = None
        for t in row["auto_candidate_targets"]:
            require(isinstance(t, dict) and isinstance(t.get("draft_element_id"), str),
                    "Invalid candidate ID")
            target_kind = t.get("kind")
            try:
                if target_kind == "image_caption_panel":
                    if canonical_panels is None:
                        from .captioned_panel_target_router import (
                            panel_targets_for_slide,
                        )
                        originals = panel_targets_for_slide(
                            source=original / "source.pdf",
                            slides=original / "slides.pdf",
                            slide_number=slide_number,
                        )
                        canonical_panels = {
                            v["draft_element_id"]: v for v in originals
                        }
                    proven = canonical_panels.get(t["draft_element_id"])
                    require(proven is not None
                            and t.get("kind") == proven["kind"]
                            and t.get("anchor") == proven["anchor"]
                            and t.get("visible_text") == proven["visible_text"]
                            and t.get("panel_identity_review_required") is False
                            and t.get("source_caption_panel_meaning_verified") is True
                            and t.get("independent_visual_registration_verified") is True,
                            "Source-caption panel identity or pixel proof changed")
                    r = pymupdf.Rect(proven["bbox_pdf_pt"])
                else:
                    # The legacy anchored-element rectangle verifier ALREADY
                    # supports frozen text groups, physically hashed 2-8
                    # block math rows, and single-placement whole images.
                    # Do not substitute the NEW different-schema visual
                    # review inventory and thereby reject a valid original
                    # source author mapping checkpoint.
                    require(target_kind in {
                            "text_block", "text_group",
                            "math_row_group", "image_whole"},
                            "Unknown author visual target requires review")
                    r, _ = rectangle(deck[slide_number - 1], t["anchor"])
                require(not r.is_empty and not r.is_infinite
                        and deck[slide_number - 1].rect.contains(r)
                        and r.get_area() >= 25
                        and r.get_area() <
                            .85 * deck[slide_number - 1].rect.get_area(),
                        "Original visual region is no longer physically bounded")
                recorded = t.get("rendered_rect_pt")
                # Original V5 author mapping stores two-decimal boundaries
                # (unlike the newer review candidate inventory which uses
                # three decimals). Allow only that physical quantization.
                require(isinstance(recorded, list) and len(recorded) == 4
                        and all(type(v) in (int, float)
                                for v in recorded)
                        and all(abs(float(a) - float(b)) <= .012
                                for a, b in zip(r, recorded)),
                        "Authored PDF region differs from frozen source map")
            except (ElementStageError, ValueError, TypeError, KeyError,
                    RuntimeError) as exc:
                raise RichMappingError(
                    "Stale authored PDF candidate geometry or source panel"
                ) from exc
            target_rows.append({
                "target_id": t["draft_element_id"],
                "kind": target_kind,
                "visible_text": t.get("visible_text") or "",
                "author_rect_pdf_pt": [round(float(q), 3) for q in r],
                "figure_panel_review_required":
                    bool(t.get("panel_identity_review_required")),
            })
    utterances = [{"utterance_id": u["proposal_id"],
                   "verbatim_text": u["verbatim_script_fragment"]}
                  for u in row["proposed_utterances"]]
    require(bool(utterances) and len(utterances) <= 30
            and len({x["target_id"] for x in target_rows}) == len(target_rows)
            and len({x["utterance_id"] for x in utterances}) == len(utterances),
            "Oversized or duplicate source/slide candidate identities")
    require("".join(x["verbatim_text"] for x in utterances) ==
            row["verbatim_slide_narration"], "Original spoken words changed")
    result = {
        "schema_version": 1,
        "status": "SOURCEBOUND_RICH_ELEMENT_AI_PROPOSAL_INPUT_REVIEW_ONLY",
        "source_inputs_sha256": meta["source_inputs_sha256"],
        "slide": slide_number,
        "source_page_excerpts": chosen,
        "visible_targets": target_rows,
        "original_utterances": utterances,
        "figure_source_identification_is_approved": False,
        "audio_generation_authorized": False,
        "student_publication_authorized": False,
    }
    result["request_sha256"] = stable_hash(result)
    return result


def prompt_for_request(request: dict) -> str:
    require(request.get("status") ==
            "SOURCEBOUND_RICH_ELEMENT_AI_PROPOSAL_INPUT_REVIEW_ONLY",
            "Not an actual author/source-bound rich prompt")
    identity = {
        "slide": request["slide"],
        "request_sha256": request["request_sha256"],
        "original_utterances": request["original_utterances"],
        "visible_targets": request["visible_targets"],
        "source_page_excerpts": request["source_page_excerpts"],
    }
    return (
        "You are drafting SOURCE-VERIFIED mathematical lecture narration-to-"
        "visual associations, NOT approving TTS, student publication or figures.\n"
        "Return a single JSON object, no markdown: slide (int), request_sha256 "
        "(unchanged), associations (array exactly in original utterance order). "
        "Each association: utterance_id, target_id (one exact visible target ID "
        "or null), source_page (one provided actual textbook page or null), "
        "source_quote (12 to 240 consecutive literal characters in the supplied "
        "textbook page or null), reason (short explanatory text), "
        "needs_review (bool). No new words, geometry, pages or target IDs. "
        "Natural-language descriptions of equations may be paraphrases, but "
        "do NOT align a tangent formula with a sine/secant formula, alter plus/"
        "minus signs, assign a figure just from guesses, or invent source quotes. "
        "For figure panels without a visible source-verified identity or for "
        "ambiguous semantic matches choose null and needs_review=true. "
        "Missing source proof must remain null; do not force coverage.\n\n"
        + json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
    )


def assess_response(*, source_folder: Path, checkpoint: Path, slide_number: int,
                    proposed: dict) -> dict:
    req = request_for_slide(source_folder=source_folder,
                            checkpoint=checkpoint, slide_number=slide_number)
    require(type(proposed) is dict
            and proposed.get("slide") == slide_number
            and proposed.get("request_sha256") == req["request_sha256"],
            "Model answer does not belong to this exact source/slides/narration request")
    require(proposed.get("student_publication_authorized") in (None, False)
            and proposed.get("audio_generation_authorized") in (None, False),
            "Model output may never confer publication or paid audio authority")
    choices = proposed.get("associations")
    require(type(choices) is list and len(choices) == len(req["original_utterances"]),
            "Model answer did not cover exactly every original spoken utterance")
    ids = {x["target_id"]: x for x in req["visible_targets"]}
    original_units = req["original_utterances"]
    source_pages = {x["source_page"]:x["original_page_text"]
                    for x in req["source_page_excerpts"]}
    outcomes=[]
    for expected, candidate in zip(original_units, choices):
        require(type(candidate) is dict and
                candidate.get("utterance_id") == expected["utterance_id"],
                "Model swapped/repeated/omitted one original narration utterance")
        target_id = candidate.get("target_id")
        number = candidate.get("source_page")
        quote = candidate.get("source_quote")
        reason = candidate.get("reason", "")
        require(target_id is None or
                (type(target_id) is str and target_id in ids),
                "Model invented nonexisting author PDF visual element")
        require(number is None or
                (type(number) is int and number in source_pages),
                "Model invented publisher page not supplied for this slide")
        require(quote is None or (type(quote) is str and
                12 <= len(quote) <= 240),
                "Model submitted an invalid textbook quote")
        require(type(reason) is str and len(reason) <= 600,
                "Model explanation not a bounded string")
        if quote is not None:
            require(number is not None and
                    normalized(quote) in normalized(source_pages[number]),
                    "Model fabricated or changed textbook page quotation")
        if target_id is not None:
            require(quote is not None, "Model asserted a visible match without "
                    "exact physical publisher quote")
        problems=[]
        selected=ids.get(target_id)
        if selected is None:
            problems.append("unassigned_original_utterance")
        else:
            if selected["kind"] not in {"text_block","text_group","math_row_group"}:
                problems.append("figure_visual_semantics_require_independent_source_image_proof")
            if selected["figure_panel_review_required"]:
                problems.append("composite_figure_panel_identity_requires_independent_review")
            visible = selected["visible_text"]
            spoken = expected["verbatim_text"]
            # Named incompatible mathematical functions are hard failures,
            # never laundered through a confident LLM statement.
            a,b = trig_families(spoken), trig_families(visible)
            if a and b and a.isdisjoint(b):
                problems.append("incompatible_named_trigonometric_math_function")
            if quote:
                qwords = set(terms(quote))
                if len(qwords & set(terms(visible))) < 2 or len(
                        qwords & set(terms(spoken))) < 2:
                    problems.append("original_textbook_quote_has_weak_substantive_overlap")
            if not visible.strip():
                problems.append("rendered_target_has_no_source_verifiable_text")
            if len(set(terms(spoken)) & set(terms(visible))) < 2:
                problems.append("narration_to_author_text_paraphrase_needs_review")
            # An LLM-approved lexical overlap is NOT an algebraic/sign/domain
            # proof. Equations and spoken mathematical symbols require their
            # existing independent mathematical/semantic certification.
            if re.search(r"[=+\u221a\u222b\u2264\u2265\u03b8\u03c0\u00b1^]|[a-z]\s*[-\u2212]\s*[a-z0-9]", visible) or re.search(
                    r"\b(?:equals|equal|squared|square root|minus|plus|negative|"
                    r"integral|pi|theta|domain|inverse|derivative|divided|"
                    r"greater than|less than|absolute value)\b",
                    normalized(spoken)):
                problems.append("mathematical_equation_or_domain_requires_independent_proof")
            if re.search(r"\b(?:figure|graph|diagram|plot|triangle|panel)\b",
                         normalized(spoken)):
                problems.append("narrated_figure_requires_independent_visual_source_proof")
        if candidate.get("needs_review") is True:
            problems.append("model_explicitly_requested_review")
        if candidate.get("needs_review") not in (True,False):
            problems.append("model_missing_explicit_uncertainty_decision")
        outcomes.append({
            "utterance_id":expected["utterance_id"],
            "original_verbatim_spoken_text_sha256":sha_bytes(
                expected["verbatim_text"].encode("utf8")),
            "selected_visible_target_id":target_id,
            "publisher_source_page":number,
            "exact_source_page_quote":quote,
            "author_visual_kind":selected["kind"] if selected else None,
            "source_and_visible_text_anchors_independently_verified":
                selected is not None and quote is not None and not problems,
            "remaining_independent_scientific_review_reasons":problems,
            "model_reason_unverified":reason,
            "tts_authorized":False,
        })
    require(len(outcomes) == len(original_units), "Loss of original narration")
    return {
        "schema_version": 1,
        "status": "SOURCEBOUND_AI_MAPPING_INDEPENDENTLY_AUDITED_REVIEW_ONLY",
        "source_inputs_sha256": req["source_inputs_sha256"],
        "original_request_sha256": req["request_sha256"],
        "slide": slide_number,
        "utterances_total": len(outcomes),
        "text_source_and_author_anchors_passed": sum(
            x["source_and_visible_text_anchors_independently_verified"]
            for x in outcomes),
        "remaining_review_items": sum(bool(x[
            "remaining_independent_scientific_review_reasons"]) for x in outcomes),
        "entries": outcomes,
        "original_pdf_author_script_mutation_permitted":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }


def parse_response(raw: str) -> dict:
    # Reuse the existing strict Gemini/ChatGPT JSON parser with duplicate-key
    # and truncated/fenced-response protections.
    try:
        return decode_storyboard_response(raw)
    except Exception as exc:
        raise RichMappingError("AI proposal must be one complete strict JSON object") from exc


def complete_json_response(raw: str) -> bool:
    # Gemini capture callbacks see partial streaming tokens. A malformed
    # *intermediate* JSON response should return False, not raise and abort
    # a legitimate still-running owned browser response.
    try:
        return isinstance(parse_response(raw),dict)
    except RichMappingError:
        return False


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-folder",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--slide",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--response",type=Path,
                   help="Existing Gemini/ChatGPT JSON response, no network")
    p.add_argument("--raw-response-out",type=Path,
                   help="New immutable raw model JSON beside a Gemini browser audit")
    p.add_argument("--gemini-web",action="store_true",
                   help="Explicit one-time authenticated Gemini browser proposal")
    p.add_argument("--browser-port",type=int,default=9222)
    p.add_argument("--wait-s",type=int,default=85)
    a=p.parse_args(argv)
    require(not (a.response is not None and a.gemini_web),
            "Choose exactly one existing response or one browser proposal")
    request=request_for_slide(
        source_folder=a.source_folder,checkpoint=a.checkpoint,
        slide_number=a.slide)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(Path(a.source_folder).absolute()),
            "Create NEW source-external model proposal receipts only")
    if not a.gemini_web and a.response is None:
        with a.out.open("x",encoding="utf8") as stream:
            stream.write(prompt_for_request(request) + "\n")
        print(json.dumps({"status":"EXACT_SOURCE_BOUND_BROWSER_PROMPT_WRITTEN_REVIEW_ONLY",
             "slide":a.slide, "out":str(a.out),
             "student_publication_authorized":False}))
        return
    if a.response:
        require(a.response.is_file() and not a.response.is_symlink(),
                "No existing model response JSON to audit")
        result=parse_response(a.response.read_text("utf8"))
    else:
        require(5 <= a.wait_s <= 180 and 9222 <= a.browser_port <= 9323,
                "Model requests must be bounded to an authorized browser port")
        # Create a no-resend ledger before submitting. A browser timeout may
        # mean the model already received the prompt; NEVER automatically retry.
        attempt=a.out.with_suffix(".submission_held.json")
        require(not attempt.exists(), "Previous Gemini submission may be in flight; "
                "reconcile its browser-owned response before another attempt")
        with attempt.open("x",encoding="utf8") as stream:
            json.dump({"status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
                "request_sha256":request["request_sha256"],
                "source_inputs_sha256":request["source_inputs_sha256"],
                "student_publication_authorized":False},stream,indent=2)
        from .series_gemini import _browser_request
        raw=_browser_request(prompt_for_request(request),[],port=a.browser_port,
            wait_cap_s=a.wait_s,min_chars=120,
            accept_fn=complete_json_response)
        result=parse_response(raw)
    reviewed=assess_response(source_folder=a.source_folder,
         checkpoint=a.checkpoint,slide_number=a.slide,proposed=result)
    # Revalidate original source/author/script and prior immutable gap report
    # after any untrusted model/browser interaction, before persisting.
    load_accepted_checkpoint(folder=a.source_folder,checkpoint=a.checkpoint)
    if a.gemini_web:
        raw_out = (a.raw_response_out or
                   a.out.parent / f"slide_{a.slide:03d}.json").absolute()
        require(raw_out.parent.is_dir() and not raw_out.exists()
                and raw_out != a.out
                and not raw_out.is_relative_to(a.source_folder.absolute()),
                "Actual Gemini raw JSON must be saved separately and immutably")
        with raw_out.open("x",encoding="utf8") as stream:
            json.dump(result,stream,indent=2,ensure_ascii=False)
            stream.write("\n")
    with a.out.open("x",encoding="utf8") as stream:
        json.dump(reviewed,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    if a.gemini_web:
        import os
        completed=attempt.with_suffix(".verified_pending_review.tmp")
        with completed.open("x",encoding="utf8") as stream:
            json.dump({"status":"CAPTURED_SOURCE_AUDITED_REVIEW_ONLY",
                "request_sha256":request["request_sha256"],
                "original_source_inputs_sha256":request["source_inputs_sha256"],
                "raw_model_response_sha256":sha_bytes(raw_out.read_bytes()),
                "technical_audit_sha256":sha_bytes(a.out.read_bytes()),
                "paid_tts_authorized":False,
                "student_publication_authorized":False},stream,indent=2)
        os.replace(completed,attempt)
    print(json.dumps({"status":reviewed["status"],"slide":a.slide,
        "text_source_anchors_passed":reviewed["text_source_and_author_anchors_passed"],
        "requires_review":reviewed["remaining_review_items"],
        "student_publication_authorized":False}))
if __name__=="__main__":
    main()
