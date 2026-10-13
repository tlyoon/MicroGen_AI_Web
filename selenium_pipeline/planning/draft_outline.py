"""Unreviewed, source-grounded page outline proposals.

This deliberately DOES NOT infer semantic concepts or claim full source
coverage. It creates an editable scaffold for an authorized reviewer or future
domain-specific LLM concept extractor; planner still requires approval.
"""
from __future__ import annotations

from pathlib import Path
from ..domains import DomainProfile
from .source_scan import SourceScanError, normalize_excerpt, sha256_file


def draft_page_outline(source_pdf: Path, scan: dict, profile: DomainProfile) -> dict:
    try:
        import pymupdf
    except ImportError as exc:
        raise SourceScanError("PyMuPDF required for outline drafting") from exc

    if sha256_file(Path(source_pdf)) != scan["source_sha256"]:
        raise SourceScanError("Source hash changed after source scan")
    concepts = []
    with pymupdf.open(source_pdf) as pdf:
        if len(pdf) != scan["page_count"]:
            raise SourceScanError("Source page count changed after scan")
        for n, page in enumerate(pdf, 1):
            text = normalize_excerpt(page.get_text("text", sort=True))
            if len(text) >= 12:
                evidence = [{
                    "kind": "text", "page": n,
                    "excerpt": text[:min(90, len(text))],
                }]
            else:
                evidence = [{
                    "kind": "visual_unreviewed", "page": n,
                    "description": "Insufficient extracted text; this page requires visual review.",
                }]
            # This is a coarse budgeting placeholder, not a validated voice estimate.
            words = len(text.split())
            teaching_seconds = max(90, min(450, round(words / 125 * 60)))
            concepts.append({
                "concept_id": f"page_{n:03d}",
                "title": f"Unreviewed page {n} — replace with source-grounded concept",
                "source_pages": [n], "evidence": evidence,
                "estimated_teaching_s": teaching_seconds,
                "prerequisites": [], "boundary_after": "allowed",
                "planned_slides": max(1, min(7, round(teaching_seconds / 90))),
            })
    return {
        "schema_version": 1, "source_sha256": scan["source_sha256"],
        "profile": {"id": profile.id, "version": profile.profile_version},
        "title": "UNREVIEWED — enter actual subchapter title",
        "scope": {"included_pages": list(range(1, scan["page_count"] + 1)),
                  "excluded_pages": []},
        "approval": {"status": "unreviewed", "reviewed_by": "pending review",
                     "coverage_note": (
                         "Page-based draft only. Review sections, exclude unrelated pages, "
                         "replace each provisional page entry with meaningful ordered concepts, "
                         "verify evidence, estimates, examples, figures and all learning objectives."
                     )},
        "concepts": concepts,
    }
