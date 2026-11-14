"""Provider UI drift policy: safe stage-aware Flash-first capability recovery.

Decision is based on *observed visible options* from the exact owned Gemini
model menu. Never use option order, unknown marketed names, a second tab,
provider API, inferred model equivalence, or a post-Send retry.

The preferred standard lecture family is Flash; figures prefer Flash-Lite.
Only documented, unambiguously observed families are eligible fallbacks.
Model identity and actual thinking choice must be verified separately at
the Send boundary by gemini_model and gemini_thinking.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


class GeminiAdaptivePolicyError(ValueError):
    pass


FAMILIES=("flash","flash-lite","pro")
STAGES=frozenset(("figures","slides","narration","academic_review",
                  "rich_mapping"))
LEVELS=("low","medium","high")


@dataclass(frozen=True)
class Route:
    requested: str
    chosen: str
    stage: str
    reason: str
    thinking_required: bool
    offered: tuple[str, ...]


def normalized_family(label: str) -> str | None:
    """Only one distinct known model family in an individual model label.

    Do not mistake a mixed menu or Flash-Lite for the standard Flash family.
    Version, description and capitalization are deliberately irrelevant.
    An unknown new model is NOT implicitly equated to Flash.
    """
    if not isinstance(label,str):
        return None
    words=re.findall(
        r"(?<![\w])(?:flash[\s\-_]*lite|flash|pro)(?![\w])",
        label,flags=re.I)
    matched={re.sub(r"[\s_]+","-",x.casefold()) for x in words}
    if len(matched)!=1:
        return None
    return matched.pop()


def choose_family(*,requested: str, offered: list[str] | tuple[str,...],
                  stage: str) -> Route:
    if (requested not in FAMILIES or stage not in STAGES or
        not isinstance(offered,(list,tuple)) or
        any(x not in FAMILIES for x in offered)):
        raise GeminiAdaptivePolicyError("UNVERIFIED_GEMINI_MODEL_CAPABILITY")
    unique=tuple(sorted(set(offered)))
    if requested in unique:
        chosen=requested
        reason="EXACT_PREFERRED_FAMILY_OFFERED"
    else:
        # A deliberately requested Pro benchmark is not a disposable default;
        # its absence is a capability failure, not permission to substitute.
        if requested == "pro":
            raise GeminiAdaptivePolicyError(
                "EXPLICIT_PRO_BENCHMARK_UNAVAILABLE_NO_SEND")
        # A fallback is allowed only after authoritative, positive model
        # menu evidence proves the requested mode is ABSENT. It must never
        # mask ambiguous/missing picker semantics or authentication errors.
        if stage=="figures":
            ranked=("flash-lite","flash","pro")
        elif stage in ("slides","narration","academic_review",
                          "rich_mapping"):
            ranked=("flash","pro")
        else:
            ranked=()
        chosen=next((x for x in ranked if x in unique),None)
        if not chosen:
            raise GeminiAdaptivePolicyError(
                "NO_VERIFIABLE_TASK_COMPATIBLE_GEMINI_MODEL_NO_SEND")
        reason="EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK"
    # The relaxed figure-stage no-thinking gate is valid ONLY for Lite.
    # If a full Flash or Pro fallback is needed, independently verify
    # Medium (or a strictly non-downgrading verified effort substitute).
    return Route(requested,chosen,stage,reason,
                 chosen!="flash-lite",unique)


def choose_thinking(*,requested:str,offered:list[str]|tuple[str,...],
                    stage:str)->str:
    """Allow only non-downgrading, explicitly checked alternatives.

    High may replace missing Medium. No unknown "Balanced", "Auto" or
    marketing mode counts as proven Medium without a checked radio.
    """
    if requested not in LEVELS or stage not in STAGES:
        raise GeminiAdaptivePolicyError("UNVERIFIED_THINKING_REQUEST")
    if (not isinstance(offered,(list,tuple))
        or any(x not in LEVELS for x in offered)):
        raise GeminiAdaptivePolicyError("UNVERIFIED_THINKING_OPTIONS")
    found=set(offered)
    if requested in found:
        return requested
    higher=LEVELS[LEVELS.index(requested)+1:]
    for level in higher:
        if level in found:
            return level
    raise GeminiAdaptivePolicyError(
        "NO_VERIFIABLE_NON_DOWNGRADING_THINKING_LEVEL_NO_SEND")
