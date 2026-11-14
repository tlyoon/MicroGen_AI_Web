"""Source-independent Gemini model policy for the actual lecture stages.

Figure caption mapping is an image-to-label extraction job, not lecture
reasoning. It uses an exact Flash-Lite UI family with NO Thinking submenu.
Slides and narration retain an explicitly verified Flash (or explicitly
chosen Pro benchmark) model AND configured Thinking level.

This module selects a model. It never clicks Gemini Send or weakens any
mapping, academic, science or evidence gate.
"""
from __future__ import annotations

import os

FIGURE_UI_MODE = "flash-lite"
FIGURE_MODEL_ID = "gemini-3.5-flash-lite"
NONFIGURE_STAGES = frozenset(("slides", "narration", "rich_mapping"))


class GeminiStagePolicyError(ValueError):
    pass


def stage_ui_contract(stage: str, *, nonfigure_mode: str = "flash",
                      nonfigure_model: str = "gemini-3.8-flash") -> dict:
    """A new worker always receives a stage-scoped immutable model policy."""
    if stage == "figures":
        return {
            "stage": stage, "ui_mode": FIGURE_UI_MODE,
            "requested_model_id": FIGURE_MODEL_ID,
            "thinking_required": False, "thinking_level": "not_required",
            "policy": "source_figure_caption_lite_no_thinking",
        }
    if stage not in NONFIGURE_STAGES:
        raise GeminiStagePolicyError("No Gemini generation model for this stage")
    if nonfigure_mode not in ("flash", "pro"):
        raise GeminiStagePolicyError(
            "Slides/narration require Flash or an explicit Pro benchmark")
    from .gemini_thinking import configured_thinking_level
    return {
        "stage": stage, "ui_mode": nonfigure_mode,
        "requested_model_id": nonfigure_model,
        "thinking_required": True,
        "thinking_level": configured_thinking_level(),
        "policy": "lecture_generation_verified_thinking",
    }


def browser_stage_needs_thinking(*, mode: str | None = None,
                                 stage: str | None = None) -> bool:
    """Fail closed on any attempt to bypass the Medium gate on lecture stages."""
    from .gemini_model import configured_ui_mode
    selected = mode if mode is not None else configured_ui_mode()
    active = (stage if stage is not None else
              os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE", "").strip().lower())
    if active == "figures":
        # Default Flash-Lite remains light and needs no effort submenu.
        # When physically unavailable, an independently verified full
        # Flash/Pro fallback MUST pass the normal thinking/effort gate.
        if selected == FIGURE_UI_MODE:
            return False
        if selected in ("flash","pro"):
            return True
        raise GeminiStagePolicyError("Unknown figure-stage fallback model")
    if selected == FIGURE_UI_MODE:
        raise GeminiStagePolicyError(
            "Flash-Lite without Thinking permitted ONLY for figures stage")
    if selected not in ("flash", "pro"):
        raise GeminiStagePolicyError("Unknown Gemini browser model")
    return True
