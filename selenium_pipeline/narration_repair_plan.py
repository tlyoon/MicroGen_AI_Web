"""Create a fail-closed narration repair plan after slide replacement."""
from __future__ import annotations
import json
from pathlib import Path
from .slide_change_planner import changed_pages
from .figure_slide_impact import restored_figure_impact

def plan_repair(folder: Path, previous_pdf: Path,
                restored_figures: list[str] | None = None) -> dict:
    folder = Path(folder)
    impact = changed_pages(previous_pdf, folder / "slides.pdf")
    method = "pdf_comparison"
    if restored_figures is not None:
        mapped = restored_figure_impact(folder / "slides.tex",
                                       restored_figures, impact["affected"][-1]
                                       if impact["page_count_changed"] and impact["affected"]
                                       else _count_pages(folder / "slides.pdf"))
        if not impact["page_count_changed"] and not mapped["conservative_full_review"]:
            impact = mapped
            method = "latex_figure_reference_mapping"
    report = {
        **impact,
        "impact_method": method,
        "restored_figures": restored_figures or [],
        "semantic_review_required": bool(impact["affected"]),
        "automatic_narration_reuse_allowed": not bool(impact["affected"]),
        "automatic_narration_regeneration_performed": False,
        "audio_regeneration_performed": False,
        "video_publication_allowed": False,
        "instructions": (
            "Review affected slides against their narration; regenerate incorrect "
            "script blocks and WAVs, or explicitly approve unchanged narration. "
            "Validate all audio and slides before publishing the rebuilt MP4."
        ),
    }
    output = folder / ".microgen_figure_candidates" / "narration_repair_plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

def _count_pages(pdf: Path) -> int:
    import pymupdf
    with pymupdf.open(pdf) as doc:
        return len(doc)
