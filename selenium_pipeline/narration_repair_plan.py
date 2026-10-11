"""Create a fail-closed narration repair plan after a PDF replacement."""
from __future__ import annotations
import json
from pathlib import Path
from .slide_change_planner import changed_pages

def plan_repair(folder: Path, previous_pdf: Path) -> dict:
    folder = Path(folder)
    impact = changed_pages(previous_pdf, folder / "slides.pdf")
    report = {
        **impact,
        "semantic_review_required": bool(impact["affected"]),
        "automatic_narration_reuse_allowed": not bool(impact["affected"]),
        "automatic_narration_regeneration_performed": False,
        "audio_regeneration_performed": False,
        "video_publication_allowed": False,
        "instructions": (
            "Review each affected slide against its narration; regenerate "
            "incorrect script blocks and matching WAVs, or explicitly approve "
            "unchanged narration after semantic review. Validate every slide "
            "and audio pair before publishing the rebuilt MP4."
        ),
    }
    output = folder / ".microgen_figure_candidates" / "narration_repair_plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
