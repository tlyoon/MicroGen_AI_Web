"""Read-only, fail-closed comparison of two unapproved element-narration drafts.

Lexical ranking changes never authorize TTS, academic signoff or publication.
"""
import argparse
import hashlib
import json
from pathlib import Path


class MappingDriftError(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise MappingDriftError(reason)


def load(path):
    path = Path(path)
    check(path.is_file() and not path.is_symlink(), "Missing or symlinked draft")
    raw = path.read_bytes()
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise MappingDriftError("Invalid candidate JSON") from exc
    check(isinstance(data, dict), "Candidate must be a JSON object")
    return data, hashlib.sha256(raw).hexdigest()


def validated_units(doc):
    check(doc.get("schema_version") == 1 and
          doc.get("status") == "REVIEW_REQUIRED_NOT_TTS_READY" and
          doc.get("draft_kind") == "PDF_GEOMETRY_PLUS_EXISTING_VERBATIM_SLIDE_SCRIPT" and
          doc.get("can_stage_or_synthesize_audio") is False and
          doc.get("cannot_be_used_as_authored_element_plan") is True and
          doc.get("source_meaning_reviewed") is False and
          doc.get("manual_mapping_reviewed") is False and
          doc.get("automatic_author_approval") is False and
          doc.get("academic_approval") is False and
          doc.get("student_publication") is False,
          "Draft must be explicitly unapproved and unsuitable for TTS")
    for key in ("source_sha256", "slides_sha256", "script_sha256"):
        digest = doc.get(key)
        check(isinstance(digest, str) and len(digest) == 64 and
              all(ch in "0123456789abcdef" for ch in digest),
              "Unbound or invalid source hash: " + key)
    slides = doc.get("slides")
    check(isinstance(slides, list) and len(slides) == doc.get("slide_count")
          and bool(slides), "Slides incomplete")
    result = {}
    for i, slide in enumerate(slides, 1):
        check(slide.get("slide_number") == i and
              slide.get("review_required") is True and
              slide.get("approved_for_stage") is False and
              slide.get("source_page_approved") is False and
              slide.get("source_quote_approved") is False,
              "Slides must remain source-review blocked")
        spoken = slide.get("proposed_utterances")
        check(isinstance(spoken, list) and spoken,
              "Missing utterance suggestions")
        original = slide.get("verbatim_slide_narration")
        check(isinstance(original, str) and
              "".join(x["verbatim_script_fragment"] for x in spoken) == original
              and hashlib.sha256(original.encode("utf8")).hexdigest() ==
                  slide.get("original_script_block_sha256"),
              "Authored narration text/hash identity changed")
        for j, u in enumerate(spoken, 1):
            uid = f"s{i:03d}.utterance.{j:03d}"
            check(u.get("proposal_id") == uid and uid not in result and
                  u.get("approved_for_tts") is False and
                  u.get("manual_target_selection_required") is True and
                  u.get("spoken_word_fidelity_verified") is False and
                  type(u.get("mapping_ambiguous")) is bool and
                  isinstance(u.get("candidate_target_rankings_unverified"), list),
                  "Unsafe proposed utterance")
            result[uid] = u
    check(len(result) == doc.get("utterance_count") and
          sum(u["mapping_ambiguous"] for u in result.values()) ==
              doc.get("ambiguous_utterance_count"),
          "Recorded utterance/ambiguity counts inconsistent")
    return result


def compare(old_doc, new_doc, old_sha=None, new_sha=None):
    keys = ("source_sha256", "slides_sha256", "script_sha256",
            "slide_count", "utterance_count", "candidate_target_count",
            "figure_panel_slide_count", "no_new_narration_words")
    check(all(old_doc.get(k) == new_doc.get(k) for k in keys),
          "Drafts do not refer to the same original source/slide/script")
    before = validated_units(old_doc)
    after = validated_units(new_doc)
    check(before.keys() == after.keys(), "Narration coverage changed")
    changes = []
    for uid, old in before.items():
        new = after[uid]
        check(old["verbatim_script_fragment"] == new["verbatim_script_fragment"],
              "Original narration words changed: " + uid)
        ranking_changed = (old["candidate_target_rankings_unverified"] !=
                           new["candidate_target_rankings_unverified"])
        ambiguity_changed = (old["mapping_ambiguous"] !=
                             new["mapping_ambiguous"])
        if ranking_changed or ambiguity_changed:
            changes.append({
                "utterance_id": uid,
                "verbatim_original_narration": old["verbatim_script_fragment"],
                "historical_ambiguous": old["mapping_ambiguous"],
                "refreshed_ambiguous": new["mapping_ambiguous"],
                "rankings_changed": ranking_changed,
                "ambiguity_changed": ambiguity_changed,
                "historical_rankings": old["candidate_target_rankings_unverified"],
                "refreshed_rankings": new["candidate_target_rankings_unverified"],
                "human_mapping_approved": False,
            })
    return {
        "schema_version": 1,
        "status": "AUTOMATIC_HEURISTIC_DRIFT_REVIEW_ONLY",
        "historical_draft_sha256": old_sha,
        "refreshed_draft_sha256": new_sha,
        "source_sha256": old_doc["source_sha256"],
        "slides_sha256": old_doc["slides_sha256"],
        "script_sha256": old_doc["script_sha256"],
        "unchanged_verbatim_utterances": len(before),
        "historical_ambiguous": old_doc["ambiguous_utterance_count"],
        "refreshed_ambiguous": new_doc["ambiguous_utterance_count"],
        "ranking_or_score_changed": sum(x["rankings_changed"] for x in changes),
        "ambiguity_classification_changed": sum(x["ambiguity_changed"] for x in changes),
        "manual_mapping_required_all_utterances": True,
        "approved_for_tts": False,
        "academic_approval": False,
        "production_approved": False,
        "student_published": False,
        "changes": changes,
    }


def markdown(report):
    check(report.get("status") == "AUTOMATIC_HEURISTIC_DRIFT_REVIEW_ONLY"
          and report.get("approved_for_tts") is False, "Not a review-only report")
    lines = [
        "# Element-plan heuristic version drift — REVIEW ONLY", "",
        "**These are lexical/scoring differences, not academic mapping approval.**", "",
        f"Verbatim utterances: {report['unchanged_verbatim_utterances']}. "
        f"Historical ambiguous: {report['historical_ambiguous']}. "
        f"Refreshed ambiguous: {report['refreshed_ambiguous']}.",
        f"Changed rankings or scores: {report['ranking_or_score_changed']}. "
        f"Changed ambiguity labels: {report['ambiguity_classification_changed']}.", "",
        "| Utterance | Historical ambiguous | Refreshed ambiguous | Old candidates | New candidates |",
        "|---|---|---|---|---|",
    ]
    def labels(items):
        return ", ".join(
            str(item["draft_element_id"]) + " (" + str(item["overlap_hint"]) + ")"
            for item in items) or "none"
    for x in report["changes"]:
        if x["ambiguity_changed"]:
            lines.append(
                f"| {x['utterance_id']} | {x['historical_ambiguous']} | "
                f"{x['refreshed_ambiguous']} | {labels(x['historical_rankings'])} | "
                f"{labels(x['refreshed_rankings'])} |")
    lines.extend(["", "The companion JSON documents ALL changed ranking lists "
                  "and their exact original narration.", "",
                  "Source mathematics, figure identity, actual spoken audio and "
                  "every narration-to-element mapping still require human review.", ""])
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--historical", required=True, type=Path)
    p.add_argument("--refreshed", required=True, type=Path)
    p.add_argument("--output-json", required=True, type=Path)
    p.add_argument("--output-md", required=True, type=Path)
    args = p.parse_args(argv)
    outputs = (args.output_json, args.output_md)
    check(len({str(x.absolute()) for x in outputs}) == 2 and
          all(not x.exists() and not x.is_symlink() and x.parent.is_dir()
              for x in outputs), "Two distinct, new review report paths required")
    for output in outputs:
        # resolve() normalizes Windows drive casing and path components.
        # Path.absolute() does not guarantee a canonical, comparable path
        # across GitHub-hosted Windows pytest and standalone local unittest.
        resolved_output = output.resolve(strict=False)
        check(all(not resolved_output.is_relative_to(
                  file.resolve(strict=True).parent)
                  for file in (args.historical, args.refreshed)),
              "Review reports must be outside both original source folders")
    old, old_sha = load(args.historical)
    new, new_sha = load(args.refreshed)
    result = compare(old,new,old_sha,new_sha)
    with args.output_json.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    with args.output_md.open("x",encoding="utf8") as f:
        f.write(markdown(result))
    print(json.dumps({k:result[k] for k in (
        "status","unchanged_verbatim_utterances","ranking_or_score_changed",
        "ambiguity_classification_changed")},indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
