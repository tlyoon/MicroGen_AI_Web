"""Read-only verification of model/effort recovery in normal stage logs.

A parent runner records preferred Flash; a child can independently verify a
different currently available family. The stage auditor must not mistake a
verified *compatible* route for an accidental change or accept a forged,
unchecked, cross-task model switch. Source/math/MP4 QA remains independent.

Only exactly anchored local owned-vendor log markers are eligible. The stage
auditor separately checks final exact model picker and checked effort proof.
"""
from __future__ import annotations

import re

from .gemini_ui_adaptive_protocol import (
    choose_family,choose_thinking,GeminiAdaptivePolicyError)

STAMP=r"\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[INFO\] "
MODEL=re.compile(
    r"(?m)^"+STAMP+
    r"\[GEMINI-MODE\] ADAPTIVE_VERIFIED_FALLBACK "+
    r"requested=(flash-lite|flash|pro) "+
    r"selected=(flash-lite|flash|pro) "+
    r"offered=([a-z,-]+) "+
    r"reason=EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK\s*$"
)
EFFORT=re.compile(
    r"(?m)^"+STAMP+
    r"\[GEMINI-THINKING\] ADAPTIVE_VERIFIED_EFFORT "+
    r"requested=(low|medium|high) "+
    r"selected=(low|medium|high) "+
    r"offered=([a-z,]+) "+
    r"reason=REQUESTED_LEVEL_UNAVAILABLE_VERIFIED_NON_DOWNGRADING\s*$"
)
MODEL_PREFIX="[GEMINI-MODE] ADAPTIVE_VERIFIED_FALLBACK"
EFFORT_PREFIX="[GEMINI-THINKING] ADAPTIVE_VERIFIED_EFFORT"


def inspect_stage_route(*,raw:str,original_mode:str|None,
                        original_effort:str|None)->dict:
    if not isinstance(raw,str):
        raise ValueError("Stage log must be literal observed text")
    model_lines=raw.count(MODEL_PREFIX)
    effort_lines=raw.count(EFFORT_PREFIX)
    model_matches=list(MODEL.finditer(raw))
    effort_matches=list(EFFORT.finditer(raw))
    rejected=(
        model_lines!=len(model_matches) or
        effort_lines!=len(effort_matches) or
        len(model_matches)>1 or len(effort_matches)>1
    )
    effective=original_mode
    thinking=original_effort
    model_accepted=False
    effort_accepted=False
    stage="figures" if original_mode=="flash-lite" else "slides"
    if model_matches and not rejected:
        requested,selected,offered_raw=model_matches[0].groups()
        offered=offered_raw.split(",")
        try:
            route=choose_family(
                requested=requested,offered=offered,stage=stage)
        except GeminiAdaptivePolicyError:
            rejected=True
        else:
            if (requested!=original_mode or
                route.chosen!=selected or selected==requested or
                requested in offered):
                rejected=True
            else:
                effective=selected
                model_accepted=True
    if effort_matches and not rejected:
        requested,selected,offered_raw=effort_matches[0].groups()
        offered=offered_raw.split(",")
        try:
            choice=choose_thinking(
                requested=requested,offered=offered,stage=stage)
        except GeminiAdaptivePolicyError:
            rejected=True
        else:
            if (requested in offered or selected!=choice or
                selected==requested or
                (original_effort is not None and original_effort!=requested)):
                rejected=True
            else:
                thinking=selected
                effort_accepted=True
    if rejected:
        effective=original_mode
        thinking=original_effort
        model_accepted=False
        effort_accepted=False
    return {
        "status":("REJECTED_ADAPTIVE_UI_ROUTE"
                  if rejected else "VERIFIED_ADAPTIVE_UI_ROUTE"
                  if model_accepted or effort_accepted else
                  "NO_ADAPTIVE_UI_ROUTE"),
        "route_rejected":rejected,
        "requested_model":original_mode,
        "effective_model":effective,
        "requested_thinking":original_effort,
        "effective_thinking":thinking,
        "model_fallback_verified":model_accepted,
        "effort_fallback_verified":effort_accepted,
        "provider_outage_proven":False,
        "academic_approval":False,
        "G2_approved":False,
        "student_publication_authorized":False,
    }
