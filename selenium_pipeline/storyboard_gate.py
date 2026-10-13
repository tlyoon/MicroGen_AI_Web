"""Cross-file semantic *structure* gates for joint slide/narration storyboards.

A structurally valid storyboard is NOT a fact-checked, pedagogy-reviewed lecture.
This module never calls Gemini, TTS, LaTeX or FFmpeg.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .domains import DomainProfile
from .planning.lesson_planner import LessonPlanError, validate_outline

_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,95}$")
_PLACEHOLDERS = ("REVIEW REQUIRED", "PLACEHOLDER", "TODO", "INSERT NARRATION")
_ALLOWED_KINDS = frozenset({
    "text", "equation", "figure", "figure_panel", "diagram_region",
    "graph_region", "timeline_event", "map_region",
})


class StoryboardError(ValueError):
    """Broken plan reference, incomplete coverage, or unsafe media storyboard."""


def canonical_sha256(obj: dict) -> str:
    """Canonical content hash; unaffected by JSON indentation/key order."""
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _check(ok: bool, message: str) -> None:
    if not ok:
        raise StoryboardError(message)


def _ids(values: Any, label: str) -> list[str]:
    _check(isinstance(values, list) and bool(values), f"{label} must be nonempty")
    _check(all(isinstance(v, str) and _TOKEN.fullmatch(v) for v in values),
           f"{label} has invalid identifiers")
    _check(len(values) == len(set(values)), f"{label} has duplicate identifiers")
    return values


def inspect_storyboard(
    storyboard: dict, plan: dict, outline: dict, profile: DomainProfile,
    *, source_pdf: Path | None = None, scan: dict | None = None,
) -> dict:
    """Validate plan/slide/visual/segment relationships, with fail-closed receipts.

    Requires source_pdf+scan together for full revalidation of outline evidence;
    source validation is mandatory for publication, but independent offline
    structure tests may use the already-validated plan hash as trust boundary.
    """
    _check(isinstance(storyboard, dict) and isinstance(plan, dict)
           and isinstance(outline, dict), "Storyboard, plan and outline must be objects")
    _check((source_pdf is None) == (scan is None),
           "source_pdf and scan must be supplied together")
    if scan is not None:
        try:
            validate_outline(outline, scan, profile, source_pdf=source_pdf)
        except LessonPlanError as exc:
            raise StoryboardError(f"Unapproved or stale source outline: {exc}") from exc
        _check(plan.get("source_sha256") == scan["source_sha256"],
               "Plan source hash does not match source PDF")
    _check(plan.get("profile") == {"id": profile.id, "version": profile.profile_version},
           "Plan domain profile mismatch")
    _check(outline.get("profile") == plan.get("profile")
           and outline.get("source_sha256") == plan.get("source_sha256"),
           "Outline not from the selected domain/source")
    _check(outline.get("approval", {}).get("status") == "approved",
           "Only reviewed concept outlines can be storyboarded")
    _check(type(storyboard.get("schema_version")) is int
           and storyboard["schema_version"] == 1, "Unsupported storyboard schema version")
    _check(set(storyboard) == {
        "schema_version", "part_id", "plan_sha256", "slides", "narration_segments",
    }, "Storyboard keys do not match version-1 schema")
    _check(storyboard.get("plan_sha256") == canonical_sha256(plan),
           "Storyboard plan hash is stale or incorrect")
    parts = plan.get("parts", [])
    _check(isinstance(parts, list), "Plan parts missing")
    part_matches = [p for p in parts if p.get("part_id") == storyboard.get("part_id")]
    _check(len(part_matches) == 1, "Storyboard must belong to exactly one plan part")
    part = part_matches[0]
    expected_concepts = _ids(part.get("concept_ids"), "Part concept_ids")
    catalog = {c["concept_id"]: c for c in outline.get("concepts", [])}
    _check(all(cid in catalog for cid in expected_concepts),
           "Part concept missing from reviewed outline")
    _check(set(expected_concepts) == set(cid for cid in plan.get(
        "coverage", {}).get("assigned_concept_ids", []) if cid in expected_concepts),
        "Part concepts inconsistent with master plan coverage")
    slides = storyboard.get("slides")
    segs = storyboard.get("narration_segments")
    _check(isinstance(slides, list) and isinstance(segs, list)
           and slides and segs, "Storyboard needs slides and narration segments")
    _check(len(slides) == part.get("planned_slide_count"),
           "Storyboard slide count deviates from agreed per-part budget; replan upstream")
    slide_ids = _ids([s.get("slide_id") for s in slides], "Slide IDs")
    _check(slide_ids == [
        f"{part['part_id']}.s{i:03d}" for i in range(1, len(slides)+1)
    ], "Slide IDs must be stable and sequential within part")
    by_slide, global_elements, referenced_concepts = {}, set(), set()
    for slide in slides:
        sid = slide["slide_id"]
        _check(isinstance(slide.get("title"), str) and slide["title"].strip(),
               f"Missing slide title: {sid}")
        elements = slide.get("elements")
        _check(isinstance(elements, list) and elements, f"Slide {sid} lacks visual elements")
        local = set()
        for el in elements:
            _check(isinstance(el, dict) and set(el) == {
                "element_id", "kind", "source_concept_ids", "source_page",
            }, f"Malformed element on {sid}")
            eid = el["element_id"]
            _check(isinstance(eid, str) and _TOKEN.fullmatch(eid)
                   and eid.startswith(sid + ".")
                   and eid not in global_elements,
                   f"Duplicate or mis-scoped element ID {eid!r}")
            _check(el["kind"] in _ALLOWED_KINDS, f"Unsupported visual element kind: {eid}")
            ec = _ids(el["source_concept_ids"], f"Element {eid} concepts")
            _check(set(ec).issubset(expected_concepts),
                   f"Element {eid} references concepts outside assigned video part")
            page = el["source_page"]
            _check(type(page) is int and page >= 1
                   and any(page in catalog[cid]["source_pages"] for cid in ec),
                   f"Element {eid} does not match its source concept/page")
            # Diagram region/panel proof still requires figure manifest + geometry QA.
            if el["kind"] in ("figure_panel", "graph_region", "diagram_region", "map_region"):
                pass
            local.add(eid)
            global_elements.add(eid)
            referenced_concepts.update(ec)
        by_slide[sid] = local
    _check(referenced_concepts == set(expected_concepts),
           "Storyboard omits one or more required concepts")
    _check("Part " + str(part["index"]) + " of " + str(part["part_count"])
           in slides[0]["title"], "Missing Part i of N first-slide heading")
    _check("Part " + str(part["index"]) + " of " + str(part["part_count"])
           in slides[-1]["title"], "Missing Part i of N closing-slide heading")

    seg_ids = _ids([seg.get("segment_id") for seg in segs], "Speech segment IDs")
    _check(len(seg_ids) == len(segs), "Duplicate narration segments")
    used, last_index, speech_seconds = set(), -1, 0.0
    for seg in segs:
        _check(isinstance(seg, dict) and set(seg) == {
            "segment_id", "slide_id", "element_ids", "spoken_text", "estimated_duration_s",
        }, "Invalid narration segment structure")
        sid = seg["slide_id"]
        _check(sid in by_slide, f"Speech segment points to unknown slide: {sid}")
        idx = slide_ids.index(sid)
        _check(idx >= last_index, "Speech narration is not ordered by slide")
        last_index = idx
        eids = _ids(seg["element_ids"], f"Segment {seg['segment_id']} target IDs")
        _check(set(eids).issubset(by_slide[sid]),
               f"Narration segment {seg['segment_id']} targets another slide")
        st = seg["spoken_text"]
        _check(isinstance(st, str) and len(st.strip()) >= 12
               and not any(p in st.upper() for p in _PLACEHOLDERS),
               f"Segment {seg['segment_id']} contains missing or placeholder speech")
        duration = seg["estimated_duration_s"]
        _check(type(duration) in (float, int) and math.isfinite(duration)
               and 0 < duration <= 300, "Each speech segment must have a realistic finite time")
        speech_seconds += duration
        used.update(eids)
    _check(global_elements == used, "Slide element(s) have no linked narration segments")
    _check(segs[0]["slide_id"] == slide_ids[0]
           and segs[-1]["slide_id"] == slide_ids[-1],
           "Narration must cover series introduction and conclusion slides")
    _check(part["continuity_intro"].strip() in segs[0]["spoken_text"],
           "Intro narration does not contain approved Part i/N continuity")
    _check(part["continuity_outro"].strip() in segs[-1]["spoken_text"],
           "Outro narration does not contain approved Part i/N continuity")
    _check(speech_seconds <= part["estimated_duration_s"]["max"],
           "Narration estimates exceed approved planned part budget")
    return {
        "status": "structural_pass_semantic_review_required",
        "part_id": part["part_id"],
        "profile": profile.id,
        "plan_sha256": canonical_sha256(plan),
        "storyboard_sha256": canonical_sha256(storyboard),
        "slide_count": len(slides),
        "element_count": len(global_elements),
        "segment_count": len(segs),
        "narration_estimate_s": round(speech_seconds, 3),
        "source_revalidated": scan is not None,
        "unverified": [
            "scientific_accuracy", "pedagogical_completeness",
            "figure_panel_visual_fidelity", "rendered_anchor_geometry",
            "tts_timing", "highlight_alignment", "final_mp4_duration",
        ],
    }
