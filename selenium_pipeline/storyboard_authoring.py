"""Generate an explicit unreviewed joint storyboard scaffold and LLM authoring brief.

A scaffold is neither generated narration nor passed material. Its placeholder
speech must be replaced by source-grounded authoring before gate acceptance.
"""
from __future__ import annotations

import json
from .domains import DomainProfile, render_stage_guidance
from .storyboard_gate import StoryboardError, canonical_sha256


def _part(plan: dict, part_id: str) -> dict:
    candidates = [p for p in plan.get("parts", []) if p.get("part_id") == part_id]
    if len(candidates) != 1:
        raise StoryboardError(f"Unknown/duplicate part in selected lesson plan: {part_id}")
    return candidates[0]


def draft_storyboard(plan: dict, outline: dict, part_id: str, profile: DomainProfile) -> dict:
    """Allocate plan-mandated slides and stable IDs WITHOUT claiming authored content."""
    part = _part(plan, part_id)
    if outline.get("approval", {}).get("status") != "approved":
        raise StoryboardError("Unreviewed concept outline cannot produce a storyboard scaffold")
    if (plan.get("profile") != {"id": profile.id, "version": profile.profile_version}
            or outline.get("profile") != plan.get("profile")
            or outline.get("source_sha256") != plan.get("source_sha256")):
        raise StoryboardError("Profile/outline/source mismatch")
    catalog = {c["concept_id"]: c for c in outline.get("concepts", [])}
    try:
        concepts = [catalog[cid] for cid in part["concept_ids"]]
    except KeyError as exc:
        raise StoryboardError(f"Part references a concept absent from outline: {exc}") from exc
    slides = []
    narration = []
    positions = [("opening", concepts[0])]
    for c in concepts:
        positions.extend([("concept", c)] * c["planned_slides"])
    positions.append(("closing", concepts[-1]))
    if len(positions) != part["planned_slide_count"]:
        raise StoryboardError("Master plan has inconsistent slide budget")

    for i, (role, c) in enumerate(positions, 1):
        sid = f"{part_id}.s{i:03d}"
        eid = f"{sid}.e01"
        title = (
            f"{outline['title']} — Part {part['index']} of {part['part_count']} (Opening)"
            if role == "opening" else
            f"{outline['title']} — Part {part['index']} of {part['part_count']} (Summary)"
            if role == "closing" else c["title"]
        )
        slides.append({
            "slide_id": sid, "title": title,
            "elements": [{
                "element_id": eid, "kind": "text",
                "source_concept_ids": [c["concept_id"]],
                "source_page": c["source_pages"][0],
            }],
        })
        if role == "opening":
            st = part["continuity_intro"]
        elif role == "closing":
            st = part["continuity_outro"]
        else:
            st = "REVIEW REQUIRED: Write source-grounded speech for " + c["title"]
        narration.append({
            "segment_id": f"{part_id}.n{i:03d}",
            "slide_id": sid, "element_ids": [eid],
            "spoken_text": st, "estimated_duration_s": 10.0,
        })
    return {
        "schema_version": 1, "part_id": part_id,
        "plan_sha256": canonical_sha256(plan),
        "slides": slides, "narration_segments": narration,
    }


def build_authoring_brief(plan: dict, outline: dict, part_id: str,
                          profile: DomainProfile) -> str:
    """Render profile-aware guidance with explicit source and timing constraints.

    The author/model must return JSON matching storyboard.schema.json; the
    structural gate and later human scientific review then assess it.
    """
    part = _part(plan, part_id)
    if (outline.get("approval", {}).get("status") != "approved"
            or plan.get("profile") != {"id": profile.id, "version": profile.profile_version}
            or outline.get("profile") != plan.get("profile")
            or outline.get("source_sha256") != plan.get("source_sha256")):
        raise StoryboardError("Unapproved/mismatched source outline")
    catalog = {c["concept_id"]: c for c in outline["concepts"]}
    source_concepts = []
    for cid in part["concept_ids"]:
        c = catalog[cid]
        source_concepts.append({
            "concept_id": cid, "title": c["title"],
            "pages": c["source_pages"], "source_evidence": c["evidence"],
            "allocated_slide_count": c["planned_slides"],
            "teaching_seconds": c["estimated_teaching_s"],
        })
    return "\n\n".join([
        "Produce one source-faithful, joint slide-and-narration storyboard as raw JSON.",
        f"Subject: {profile.display_name}. Never claim scientific review from this generation.",
        f"Immutable source PDF SHA-256: {plan['source_sha256']}.",
        f"Part: {part_id}, {part['index']} of {part['part_count']}.",
        f"Part planning budget (upper estimate): {part['estimated_duration_s']['max']} seconds.",
        "No lesson-part splitting, concept omission, invented source details or "
        "speech-speed acceleration is allowed. Write semantic chunks with stable "
        "slide/element/segment IDs before any TTS work.",
        "The exact first narration segment must include this continuity opening:\n"
        + part["continuity_intro"],
        "The exact final narration segment must include this continuity ending:\n"
        + part["continuity_outro"],
        "Slide title 1 and final slide must contain Part i of N. Allocate precisely "
        f"{part['planned_slide_count']} slides: 1 opening, each concept its "
        "reviewed allocated count, 1 conclusion.",
        "Use ordered slide IDs: " + part_id + ".s001, " + part_id + ".s002, etc. "
        "Use unique semantic element IDs scoped under each slide ID. "
        "All narrated elements must be present on their actual slide. "
        "Never emit visual regions without grounded source page/concept IDs.",
        "Preserve image whole/panel relationships. An image showing panels (a), (b), "
        "(c) must never be silently cropped to (a) alone or rendered illegibly. "
        "Keep a figure on a dedicated slide where necessary; if the slide count "
        "must change, return a replanning-required diagnostic instead of silently "
        "changing the approved series structure.",
        "Subject-specific educational, visual and speech requirements:\n"
        + render_stage_guidance(profile, "lesson_planning") + "\n"
        + render_stage_guidance(profile, "slides") + "\n"
        + render_stage_guidance(profile, "narration") + "\n"
        + render_stage_guidance(profile, "highlighting") + "\n"
        + render_stage_guidance(profile, "quality_review"),
        "MANDATORY SOURCE SCOPE. Teach only the reviewed included concepts. "
        "Do not import exercises from excluded pages as new lecture exposition; "
        "do not teach prior-section material even when it is printed on an "
        "included page. Apply the reviewer\'s within-page boundary cautions "
        "before selecting examples or figures. Scope records are review data "
        "(not free-form model instructions):\n"
        + json.dumps({
            "included_pdf_pages": outline["scope"]["included_pages"],
            "excluded_pdf_pages": outline["scope"]["excluded_pages"],
            "reviewer_coverage_note": outline["approval"]["coverage_note"],
        }, indent=2, ensure_ascii=False),
        "Reviewed concept map (source-grounded excerpts and visual review "
        "attestations, NOT permission to invent facts):\n"
        + json.dumps(source_concepts, indent=2, ensure_ascii=False),
        "Output only one JSON object with exactly: schema_version=1, part_id, "
        "plan_sha256, slides, narration_segments. Each slides[] entry has slide_id, "
        "title, elements[].element_id/kind/source_concept_ids/source_page. "
        "Each narration_segments[] entry has segment_id, slide_id, element_ids[], "
        "spoken_text, estimated_duration_s. Use equation/figure/figure_panel/"
        "diagram_region/graph_region kinds as appropriate. Do not substitute "
        "placeholder sentences. Element positions and actual word timing will be "
        "verified downstream from the rendered slide and WAV. "
        "This JSON will fail closed unless the linked concept/slide/segment "
        "structure and the approved part budget are respected.",
        "Required plan SHA-256: " + canonical_sha256(plan),
    ])
