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
import json

FIGURE_UI_MODE = "flash-lite"
FIGURE_MODEL_ID = "gemini-3.5-flash-lite"
NONFIGURE_STAGES = frozenset(("slides", "narration", "rich_mapping"))


class GeminiStagePolicyError(ValueError):
    pass


def _new_family_route_is_verified_for_task(stage: str, family: str) -> bool:
    """A new marketing family needs *actual* owned picker route evidence.

    Merely including Hydrogen/Argon in MODEL_SPECS must not make the model
    usable for any task. The historical figure-stage test caught this.
    The normal selector records an exact stage/family before a new Send.
    A subsequent worker can reuse only a separately persisted verified
    model AND Thinking default for this exact account/task.
    """
    from .gemini_dynamic_task_router import (
        MODEL_TIERS, read_task_default, dynamic_route_registered)
    if family not in MODEL_TIERS or not dynamic_route_registered():
        return False
    try:
        pending=json.loads(os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING") or "{}")
    except (TypeError,ValueError):
        pending={}
    if (type(pending) is dict and pending.get("schema_version")==1
            and pending.get("stage")==stage and pending.get("family")==family
            and isinstance(pending.get("catalog_sha256"),str)
            and len(pending["catalog_sha256"])==64):
        return True
    scope=("alternate" if os.getenv("MICROGEN_GEMINI_CHROME_PORT")=="9225"
           else "primary")
    prior=read_task_default(stage,scope=scope)
    return bool(prior and prior.get("family")==family
                and prior.get("status")=="EXACT_UI_MODEL_AND_TASK_THINKING_VERIFIED")


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
    from .gemini_model import MODEL_SPECS
    if (nonfigure_mode not in MODEL_SPECS or nonfigure_mode=="flash-lite"
            or (nonfigure_mode not in ("flash","pro")
                and not _new_family_route_is_verified_for_task(
                    stage,nonfigure_mode))):
        raise GeminiStagePolicyError(
            "Slides/narration require an independently verified reasoning-capable browser model")
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
    if active == "code_authoring":
        # Coding-model browser routing is deliberately separate from
        # scientific-review and lecture-task model requalification. Accept
        # only known higher-capability families, plus exact owned-tab model
        # and Medium/High thinking checks enforced by the sender.
        from .recovery_registry import lookup_mechanism
        registered = lookup_mechanism(
            "browser_coding_transport",
            "GEMINI_SELENIUM_CODING_ONE_CLAIM_NO_REPLAY",
        )
        if registered != "CLAIM_ONCE_CAPTURE_REPLY_STATIC_TEST_AND_HANDOFF":
            raise GeminiStagePolicyError(
                "Unregistered coding-mode verification; NO SEND")
        if selected not in ("hydrogen", "neon"):
            raise GeminiStagePolicyError(
                "Coding requires independently verified Hydrogen/Neon UI")
        return True
    if active == "figures":
        # Default Flash-Lite remains light and needs no effort submenu.
        # When physically unavailable, an independently verified full
        # Flash/Pro fallback MUST pass the normal thinking/effort gate.
        if selected == FIGURE_UI_MODE:
            return False
        if selected in ("flash","pro"):
            return True
        if selected in ("hydrogen","hydrogen-thinking","argon","carbon","neon"):
            if _new_family_route_is_verified_for_task(active,selected):
                return True
            raise GeminiStagePolicyError(
                "New figure-stage model has no registered task-specific UI proof")
        raise GeminiStagePolicyError("Unknown figure-stage fallback model")
    if selected == FIGURE_UI_MODE:
        raise GeminiStagePolicyError(
            "Flash-Lite without Thinking permitted ONLY for figures stage")
    if selected not in ("flash","pro"):
        if selected not in ("hydrogen","hydrogen-thinking","argon","carbon","neon"):
            raise GeminiStagePolicyError("Unknown Gemini browser model")
        if not _new_family_route_is_verified_for_task(active,selected):
            raise GeminiStagePolicyError(
                "New browser family requires verified task-specific routing")
    return True
