"""Deterministic, source-anchored *pre-generation* lesson series planning.

This does not draft concepts from a textbook. It accepts a REVIEWED outline
of concepts and evidence, checks it against a READ-ONLY PDF scan, then optimizes
pedagogically legal boundaries. No TTS or video runs here.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from ..domains import DomainProfile
from .source_scan import SourceScanError, verify_source_evidence

PLANNER_VERSION = "2.0.0-draft"
TARGET_SECONDS = 510.0
INTRO_OUTRO_SECONDS = 24.0
SPEECH_TRANSITION_SECONDS = 18.0
TIME_UNCERTAINTY = 1.05
PREFERRED_PLANNED_MAX_SECONDS = 600.0
ABSOLUTE_FINAL_CAP_SECONDS = 600.0
MAX_CONCEPTS = 500
MAX_PARTS = 40
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,95}$")


class LessonPlanError(ValueError):
    """Missing source evidence, unapproved scope or infeasible segmentation."""


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise LessonPlanError(message)


def _positive_number(x: object) -> bool:
    return type(x) in (int, float) and math.isfinite(x) and x > 0


def _pages(pages: object, max_page: int, field: str) -> list[int]:
    _require(isinstance(pages, list) and pages, f"{field} must have page numbers")
    _require(all(type(n) is int and 1 <= n <= max_page for n in pages),
             f"{field} has invalid page number(s)")
    _require(len(pages) == len(set(pages)) and pages == sorted(pages),
             f"{field} pages must be unique and sorted")
    return pages


def validate_outline(outline: dict, scan: dict, profile: DomainProfile,
                     *, source_pdf: Path) -> list[dict]:
    """Check a reviewed outline without claiming machine-proved source completeness."""
    _require(isinstance(outline, dict), "Outline must be a JSON object")
    required = {"schema_version", "source_sha256", "profile", "title", "scope",
                "approval", "concepts"}
    _require(set(outline) == required, "Outline fields are missing or unsupported")
    _require(type(outline["schema_version"]) is int and outline["schema_version"] == 1,
             "Unsupported concept outline schema version")
    _require(outline["source_sha256"] == scan["source_sha256"],
             "Outline source hash does not match the actual PDF")
    _require(outline["profile"] == {"id": profile.id, "version": profile.profile_version},
             "Outline domain/version must match selected profile")
    _require(isinstance(outline["title"], str) and outline["title"].strip(),
             "Outline title is required")
    approval = outline["approval"]
    _require(isinstance(approval, dict)
             and set(approval) == {"status", "reviewed_by", "coverage_note"}
             and approval["status"] == "approved"
             and isinstance(approval["reviewed_by"], str)
             and len(approval["reviewed_by"].strip()) >= 3
             and isinstance(approval["coverage_note"], str)
             and len(approval["coverage_note"].strip()) >= 15,
             "Concept coverage must be explicitly approved with reviewer and note")
    scope = outline["scope"]
    _require(isinstance(scope, dict) and set(scope) == {"included_pages", "excluded_pages"},
             "Scope must declare included and excluded pages")
    n = scan["page_count"]
    included = _pages(scope["included_pages"], n, "Included")
    excluded = scope["excluded_pages"]
    _require(isinstance(excluded, list), "Excluded pages must be a list")
    _require(all(isinstance(e, dict) and set(e) == {"page", "reason"}
                 and type(e["page"]) is int and 1 <= e["page"] <= n
                 and isinstance(e["reason"], str) and len(e["reason"].strip()) >= 10
                 for e in excluded), "Every excluded page requires an explicit reason")
    ep = [e["page"] for e in excluded]
    _require(len(ep) == len(set(ep)) and set(included).isdisjoint(ep),
             "Source page scope has duplicate or overlapping entries")
    _require(set(included) | set(ep) == set(range(1, n + 1)),
             "Source scope must account for every page, including excluded pages")
    concepts = outline["concepts"]
    _require(isinstance(concepts, list) and 1 <= len(concepts) <= MAX_CONCEPTS,
             "Expected 1–500 reviewed concepts")
    ids, covered, all_evidence = set(), set(), []
    for c in concepts:
        _require(isinstance(c, dict) and set(c) == {
            "concept_id", "title", "source_pages", "evidence",
            "estimated_teaching_s", "prerequisites", "boundary_after",
            "planned_slides",
        }, "Every concept must use the prescribed required fields")
        cid = c["concept_id"]
        _require(isinstance(cid, str) and _ID.fullmatch(cid) and cid not in ids,
                 "Concept identifiers must be unique and safe")
        _require(isinstance(c["title"], str) and c["title"].strip(),
                 f"Missing concept title for {cid}")
        ids.add(cid)
        cp = _pages(c["source_pages"], n, f"Concept {cid}")
        _require(set(cp).issubset(included), f"Concept {cid} uses an excluded page")
        covered.update(cp)
        _require(_positive_number(c["estimated_teaching_s"])
                 and c["estimated_teaching_s"] <= 3600,
                 f"Invalid reviewed duration for concept {cid}")
        _require(type(c["planned_slides"]) is int and 1 <= c["planned_slides"] <= 99,
                 f"Invalid planned slide count for {cid}")
        _require(c["boundary_after"] in ("preferred", "allowed", "forbidden"),
                 f"Invalid concept boundary rule for {cid}")
        prereqs = c["prerequisites"]
        _require(isinstance(prereqs, list) and len(prereqs) == len(set(prereqs))
                 and all(isinstance(p, str) and p in ids and p != cid for p in prereqs),
                 f"Prerequisites for {cid} must refer only to earlier concepts")
        ev = c["evidence"]
        _require(isinstance(ev, list) and ev, f"Source evidence required for {cid}")
        _require(all(isinstance(e, dict) and type(e.get("page")) is int
                     and e["page"] in cp for e in ev),
                 f"Evidence for {cid} must cite concept pages")
        all_evidence.extend(ev)
    try:
        verify_source_evidence(source_pdf, scan, all_evidence)
    except (SourceScanError, ValueError) as exc:
        raise LessonPlanError(f"Source evidence failed: {exc}") from exc
    _require(covered == set(included),
             "Every included source page needs at least one evidenced concept "
             "(or must be explicitly excluded after review)")
    return concepts


def _partition(concepts: list[dict], *, max_upper: float) -> list[tuple[int, int]]:
    """Global optimal order-preserving iterative DP; never slice a concept."""
    n = len(concepts)
    prefix = [0.0]
    for c in concepts:
        prefix.append(prefix[-1] + float(c["estimated_teaching_s"]))

    # Bottom-up avoids recursion limits for large (up to 500-concept) outlines.
    dp: list[tuple[float, tuple[tuple[int, int], ...]] | None] = [None] * (n + 1)
    dp[n] = (0.0, ())
    for start in range(n - 1, -1, -1):
        answer = None
        for end in range(start + 1, n + 1):
            if end < n and concepts[end-1]["boundary_after"] == "forbidden":
                continue
            expected = prefix[end] - prefix[start] + INTRO_OUTRO_SECONDS
            upper = expected * TIME_UNCERTAINTY
            if upper >= max_upper:
                break
            child = dp[end]
            if child is None:
                continue
            boundary_penalty = (0.0 if end == n or
                                concepts[end-1]["boundary_after"] == "preferred" else 0.45)
            cost = ((expected - TARGET_SECONDS) / 120.0) ** 2
            if expected < 350.0:
                cost += ((350.0 - expected) / 80.0) ** 2
            cost += boundary_penalty + child[0]
            candidate = (round(cost, 10), ((start, end),) + child[1])
            if answer is None or candidate < answer:
                answer = candidate
        dp[start] = answer

    result = dp[0]
    if result is None:
        raise LessonPlanError(
            "No pedagogically legal part plan fits the duration budget. "
            "Redesign an oversized atomic concept or review natural boundaries; "
            "do not split an existing MP4 or silently remove content."
        )
    _require(len(result[1]) <= MAX_PARTS, "More than 40 video parts: review the outline")
    return list(result[1])


def plan_series(outline: dict, scan: dict, profile: DomainProfile, *,
                source_pdf: Path) -> dict:
    """Produce a structured part plan from a previously approved source outline.

    The estimate is prospective, not a measured final video runtime.
    """
    concepts = validate_outline(outline, scan, profile, source_pdf=source_pdf)
    groups = _partition(concepts, max_upper=PREFERRED_PLANNED_MAX_SECONDS)
    n = len(groups)
    parts = []
    for i, (start, end) in enumerate(groups, 1):
        group = concepts[start:end]
        ids = [c["concept_id"] for c in group]
        pages = sorted({p for c in group for p in c["source_pages"]})
        teaching = sum(float(c["estimated_teaching_s"]) for c in group)
        expected = teaching + INTRO_OUTRO_SECONDS
        low, high = round(expected * 0.94, 2), round(expected * TIME_UNCERTAINTY, 2)
        _require(high < PREFERRED_PLANNED_MAX_SECONDS and high < ABSOLUTE_FINAL_CAP_SECONDS,
                 "Internal planning duration invariant failed")
        if n == 1:
            label = group[0]["title"] if len(group) == 1 else (
                group[0]["title"] + " through " + group[-1]["title"])
        else:
            label = group[0]["title"] if len(group) == 1 else (
                group[0]["title"] + " — " + group[-1]["title"])
        intro = f"{outline['title']}, Part {i} of {n}: {label}."
        if i > 1:
            intro += f" Previously: {parts[-1]['title']}. Today: {label}."
        if i < n:
            next_group = concepts[groups[i][0]:groups[i][1]]
            outro = (f"Part {i} of {n} concludes with {group[-1]['title']}. "
                     f"Next, Part {i+1} of {n}: {next_group[0]['title']}.")
        else:
            outro = f"This completes {outline['title']}, Part {i} of {n}."
        parts.append({
            "part_id": f"part_{i:02d}", "index": i, "part_count": n,
            "title": label, "concept_ids": ids, "source_pages": pages,
            "estimated_duration_s": {"min": low, "max": high},
            "speech_budget_s": round(teaching + SPEECH_TRANSITION_SECONDS, 2),
            "continuity_intro": intro, "continuity_outro": outro,
            "boundary_rationale": (
                f"Reviewed concept boundary after {group[-1]['concept_id']}; "
                f"boundary policy: {group[-1]['boundary_after']}. "
                "All concepts stay intact."
            ),
            "planned_slide_count": sum(c["planned_slides"] for c in group) + 2,
        })
    ids = [c["concept_id"] for c in concepts]
    return {
        "schema_version": 1, "source_sha256": scan["source_sha256"],
        "profile": {"id": profile.id, "version": profile.profile_version},
        "coverage": {
            "required_concept_ids": ids, "assigned_concept_ids": [cid for p in parts for cid in p["concept_ids"]],
            "review_required_concept_ids": [],
        },
        "title": outline["title"], "parts": parts, "planner_version": PLANNER_VERSION,
    }
