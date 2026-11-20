"""Conservative deterministic reconciliation of owned academic Gemini replies.

Only DOWNGRADE source/slide-inconsistent model claims to UNRESOLVED.
A citation is never guessed, rewritten, cross-assigned to another utterance,
or used to assert scientific agreement. The original model response remains
immutable in the one-Send checkpoint. A separate, unapproved audit identifies
every changed row. A complete original utterance identity set and independent
strict source validator are still mandatory downstream.
"""
from __future__ import annotations
import copy
import hashlib
import json

from .figure_source_identity import require


def reconcile_untrusted_review(*, job: dict, response: dict) -> tuple[dict, dict]:
    """Fail closed on malformed identity; downgrade only unverifiable evidence."""
    require(type(job) is dict and type(response) is dict
            and response.get("status") == "ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
            and type(response.get("rows")) is list
            and type(job.get("slides")) is list,
            "Original model review format cannot be reconciled")
    units = [u for slide in job["slides"] for u in slide["utterances"]]
    require(len(units) == job.get("utterance_count")
            and 1 <= len(response["rows"]) <= len(units),
            "Original model review omitted all or added narration units")
    # A Gemini reply can contain only a strict subset. Never infer the
    # absent scientific verdict; insert an explicit machine-generated
    # UNRESOLVED placeholder that CANNOT become supported by two-pass QA.
    # The original text remains immutable in its owned Send checkpoint.
    keyed = {}
    valid_ids = {unit["id"] for unit in units}
    for model_row in response["rows"]:
        require(type(model_row) is dict
                and type(model_row.get("utterance_id")) is str
                and model_row["utterance_id"] in valid_ids
                and model_row["utterance_id"] not in keyed,
                "Unknown or duplicated original narration identity from model")
        keyed[model_row["utterance_id"]] = model_row
    omitted = [u["id"] for u in units if u["id"] not in keyed]
    aligned = []
    for unit in units:
        if unit["id"] in keyed:
            aligned.append(keyed[unit["id"]])
        else:
            aligned.append({
                "utterance_id": unit["id"],
                "spoken_sha256": unit["spoken_sha256"],
                "verdict": "UNRESOLVED",
                "target_id": None, "source_page": None,
                "verbatim_source_quote": None,
                "math_explanation": (
                    "Original Gemini reply omitted this narration unit. "
                    "No model conclusion, source citation or visual mapping "
                    "was supplied; independent scientific review remains pending."
                ),
            })
    packet = job.get("verified_source_quote_candidates_v1")
    require(type(packet) is dict
            and packet.get("status") == "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and all(packet.get(name + "_sha256") == job[name + "_sha256"]
                    for name in ("source", "slides", "script")),
            "No independently verified original PDF quotation whitelist")
    provided = packet.get("utterances")
    require(type(provided) is list
            and len(provided) == len(units),
            "Missing original per-utterance quote bindings")
    targets_by_slide = {
        slide["slide"]: {t["id"] for t in slide["visual_targets"]
                         if type(t) is dict and type(t.get("id")) is str}
        for slide in job["slides"]
    }
    result = copy.deepcopy(response)
    result["rows"] = copy.deepcopy(aligned)
    changes = []
    for i, (unit, entry, row) in enumerate(
            zip(units, provided, result["rows"])):
        require(type(row) is dict
                and row.get("utterance_id") == unit["id"]
                and row.get("spoken_sha256") == unit["spoken_sha256"]
                and entry.get("utterance_id") == unit["id"]
                and entry.get("spoken_sha256") == unit["spoken_sha256"]
                and row.get("verdict") in ("SUPPORTED", "INCORRECT", "UNRESOLVED")
                and type(row.get("math_explanation")) is str
                and len(row["math_explanation"].strip()) >= 25,
                "Review row utterance/argument not genuinely source-identified")
        require(type(entry.get("allowed_citations")) is list,
                "Unbound original quote candidates")
        requested = (row.get("source_page"),
                     row.get("verbatim_source_quote"))
        allowed = any(
            candidate.get("source_page") == requested[0]
            and candidate.get("verbatim_source_quote") == requested[1]
            for candidate in entry["allowed_citations"]
            if type(candidate) is dict
        )
        missing_citation = requested == (None, None)
        valid_target = row.get("target_id") in targets_by_slide.get(
            int(unit["id"][1:4]), set())
        # The pairing must be both source-physically permitted and the
        # same reviewed utterance. Null citation is allowed for unresolved.
        invalid = not (allowed or missing_citation)
        # A named but nonexistent target is never a real slide target.
        bad_target = row.get("target_id") is not None and not valid_target
        unsupported_support = (row["verdict"] == "SUPPORTED" and
                               (not allowed or not valid_target))
        reasons = []
        if invalid:
            reasons.append("NOT_EXACT_UTTERANCE_WHITELIST_QUOTATION")
            row["source_page"] = None
            row["verbatim_source_quote"] = None
        if bad_target:
            reasons.append("NO_SUCH_ORIGINAL_SLIDE_TARGET")
            row["target_id"] = None
        if unsupported_support:
            reasons.append("MODEL_SUPPORTED_CLAIM_LACKED_VERIFIED_SOURCE_AND_TARGET")
            row["verdict"] = "UNRESOLVED"
        if reasons:
            changes.append({
                "utterance_id": unit["id"],
                "original_model_verdict": keyed[unit["id"]]["verdict"]
                    if unit["id"] in keyed else None,
                "reconciled_verdict": row["verdict"],
                "reason_codes": sorted(reasons),
                "scientific_support_added": False,
            })
    original_sha = hashlib.sha256(json.dumps(
        response, sort_keys=True, ensure_ascii=False).encode("utf8")).hexdigest()
    evidence = {
        "schema_version": 1,
        "status": "DETERMINISTIC_DOWNGRADE_ONLY_SOURCE_RECONCILIATION",
        "original_model_response_canonical_sha256": original_sha,
        "source_sha256": job["source_sha256"],
        "slides_sha256": job["slides_sha256"],
        "script_sha256": job["script_sha256"],
        "original_narration_utterances": len(units),
        "model_returned_utterance_count": len(keyed),
        "model_omitted_original_utterance_ids": omitted,
        "machine_inserted_unresolved_placeholder_count": len(omitted),
        "all_original_utterances_actually_reviewed": not bool(omitted),
        "downgraded_or_citation_cleared_rows": changes,
        "new_model_requests": 0,
        "source_citations_added": 0,
        "model_claims_promoted_to_supported": 0,
        "independent_scientific_consensus": False,
        "academic_mathematics_independently_verified": False,
        "student_publication_authorized": False,
    }
    return result, evidence
