"""Deterministic, source-referenced multipart lecture planning (offline foundation).

This module does not call Gemini, create slides, synthesize speech, or certify
media. Planned narration estimates are *not* actual TTS/MP4 durations.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Sequence

SCHEMA_VERSION = 1
TARGET_PART_SECONDS = 510.0       # 8 min 30 s
MAX_PLANNED_SECONDS = 570.0      # 30 s headroom before normal 10 min limit
NORMAL_MAX_SECONDS = 600.0       # strict: <600 s
EXCEPTION_MAX_SECONDS = 630.0    # strict: <630 s with explicit approval
INTRO_RESERVE_SECONDS = 15.0
OUTRO_RESERVE_SECONDS = 15.0


class LessonPlanError(ValueError):
    """Invalid lesson plan input or impossible source-faithful partition."""


@dataclass(frozen=True)
class Scene:
    scene_id: str
    title: str
    objective: str
    source_pages: tuple[int, ...]
    estimated_narration_seconds: float
    natural_break_after: bool = False


@dataclass(frozen=True)
class Part:
    part_id: str
    title: str
    scene_ids: tuple[str, ...]
    source_pages: tuple[int, ...]
    estimated_total_seconds: float
    intro_brief: str
    outro_brief: str


@dataclass(frozen=True)
class LessonPlan:
    schema_version: int
    lesson_title: str
    discipline: str
    source_sha256: str
    target_seconds: float
    max_planned_seconds: float
    intro_reserve_seconds: float
    outro_reserve_seconds: float
    parts: tuple[Part, ...]

    def as_dict(self) -> dict:
        return asdict(self)

    def canonical_sha256(self) -> str:
        payload = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DurationAssessment:
    status: str
    actual_seconds: float
    explicit_exception_approved: bool
    reason: str


def _positive_finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LessonPlanError(f"{name} must be a positive finite number") from exc
    if not math.isfinite(number) or number <= 0:
        raise LessonPlanError(f"{name} must be a positive finite number")
    return number


def assess_actual_duration(
    actual_seconds: float, *, explicit_exception_approved: bool = False
) -> DurationAssessment:
    """Classify a *probed final MP4* duration, not a script estimate.

    Exactly 600 s cannot get the ordinary pass; exactly 630 s is blocked.
    A narrow exception can pass only when explicit approval is supplied.
    """
    actual = _positive_finite(actual_seconds, "actual_seconds")
    if actual < NORMAL_MAX_SECONDS:
        return DurationAssessment("passed", actual, False, "Under 10:00")
    if actual < EXCEPTION_MAX_SECONDS:
        if explicit_exception_approved:
            return DurationAssessment(
                "passed_exception", actual, True,
                "Under 10:30; explicit overshoot approval is required and recorded",
            )
        return DurationAssessment(
            "review_required", actual, False,
            "10:00 to under 10:30; requires explicit review and approval",
        )
    return DurationAssessment(
        "blocked", actual, False,
        "At least 10:30; re-plan and regenerate affected parts upstream",
    )


def _validate_scenes(scenes: Sequence[Scene]) -> tuple[Scene, ...]:
    if not scenes:
        raise LessonPlanError("Cannot plan a lecture without source-grounded scenes")
    validated = tuple(scenes)
    seen: set[str] = set()
    for number, scene in enumerate(validated, start=1):
        if not isinstance(scene, Scene):
            raise LessonPlanError(f"Scene {number} must be a Scene")
        if not scene.scene_id.strip() or not scene.title.strip() or not scene.objective.strip():
            raise LessonPlanError(f"Scene {number} needs ID, title, and objective")
        if scene.scene_id in seen:
            raise LessonPlanError(f"Duplicate scene ID: {scene.scene_id}")
        seen.add(scene.scene_id)
        if not scene.source_pages or any(
            not isinstance(p, int) or isinstance(p, bool) or p < 1
            for p in scene.source_pages
        ):
            raise LessonPlanError(f"Scene {scene.scene_id} needs positive source page numbers")
        if len(set(scene.source_pages)) != len(scene.source_pages):
            raise LessonPlanError(f"Scene {scene.scene_id} has duplicate page references")
        _positive_finite(scene.estimated_narration_seconds,
                         f"{scene.scene_id}.estimated_narration_seconds")
        if not isinstance(scene.natural_break_after, bool):
            raise LessonPlanError(f"{scene.scene_id}.natural_break_after must be boolean")
    return validated


def plan_lesson(
    *,
    lesson_title: str,
    discipline: str,
    source_sha256: str,
    scenes: Sequence[Scene],
    target_seconds: float = TARGET_PART_SECONDS,
    max_planned_seconds: float = MAX_PLANNED_SECONDS,
    intro_reserve_seconds: float = INTRO_RESERVE_SECONDS,
    outro_reserve_seconds: float = OUTRO_RESERVE_SECONDS,
) -> LessonPlan:
    """Plan concept-coherent parts globally, before final slides or TTS exist.

    The dynamic program prefers 8-9 minute parts and topic boundaries. Each
    scene is indivisible; oversized scenes are rejected instead of cut. Estimates
    leave headroom and must be checked later against actual final audio/video.
    """
    if not lesson_title.strip() or not discipline.strip():
        raise LessonPlanError("Lesson title and explicit discipline are required")
    if len(source_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in source_sha256):
        raise LessonPlanError("source_sha256 must be an actual 64-hex source digest")
    items = _validate_scenes(scenes)
    target = _positive_finite(target_seconds, "target_seconds")
    ceiling = _positive_finite(max_planned_seconds, "max_planned_seconds")
    intro = _positive_finite(intro_reserve_seconds, "intro_reserve_seconds")
    outro = _positive_finite(outro_reserve_seconds, "outro_reserve_seconds")
    if not intro + outro < ceiling < NORMAL_MAX_SECONDS:
        raise LessonPlanError("Reserves must fit; planning ceiling must be under 600 s")
    if target > ceiling:
        raise LessonPlanError("Target must not exceed planning ceiling")

    n = len(items)
    sums = [0.0]
    for scene in items:
        sums.append(sums[-1] + scene.estimated_narration_seconds)
        if scene.estimated_narration_seconds + intro + outro > ceiling + 1e-8:
            raise LessonPlanError(
                f"Atomic scene {scene.scene_id} exceeds the part budget; "
                "revise the source-grounded scene upstream, never cut its MP4"
            )

    # dp[j] is the lowest cost for the first j complete scenes. Reconstruct
    # globally rather than greedily cutting at a time or by equal video lengths.
    dp = [math.inf] * (n + 1)
    previous = [-1] * (n + 1)
    dp[0] = 0.0
    for end in range(1, n + 1):
        for start in range(end - 1, -1, -1):
            seconds = sums[end] - sums[start] + intro + outro
            if seconds > ceiling + 1e-8:
                break
            if not math.isfinite(dp[start]):
                continue
            dev = ((seconds - target) / target) ** 2
            undersized = (max(0.0, 420.0 - seconds) / 420.0) ** 2
            break_penalty = 0.0 if end == n or items[end - 1].natural_break_after else 1.75
            cost = dp[start] + 0.20 + dev + 1.25 * undersized + break_penalty
            # Stable tie-break: prefer fewer parts / earlier natural boundaries.
            if cost < dp[end] - 1e-10:
                dp[end], previous[end] = cost, start

    if not math.isfinite(dp[n]):
        raise LessonPlanError("Could not partition source-grounded scenes into safe parts")
    ranges: list[tuple[int, int]] = []
    cursor = n
    while cursor:
        start = previous[cursor]
        if start < 0:
            raise LessonPlanError("Internal partition reconstruction failed")
        ranges.append((start, cursor))
        cursor = start
    ranges.reverse()

    parts: list[Part] = []
    for number, (start, end) in enumerate(ranges, start=1):
        covered = items[start:end]
        previous_topic = items[start - 1].title if start else None
        next_topic = items[end].title if end < n else None
        intro_brief = (
            f"Connect from {previous_topic}; introduce {covered[0].title}."
            if previous_topic
            else f"Introduce {lesson_title} and the focus {covered[0].title}."
        )
        outro_brief = (
            f"Summarize through {covered[-1].title}; preview {next_topic}."
            if next_topic
            else f"Summarize {covered[-1].title} and conclude {lesson_title}."
        )
        pages = tuple(dict.fromkeys(p for scene in covered for p in scene.source_pages))
        seconds = round(
            sums[end] - sums[start] + intro + outro, 3
        )
        parts.append(Part(
            part_id=f"part_{number:02d}",
            title=f"{lesson_title} — Part {number}: {covered[0].title}",
            scene_ids=tuple(s.scene_id for s in covered),
            source_pages=pages,
            estimated_total_seconds=seconds,
            intro_brief=intro_brief,
            outro_brief=outro_brief,
        ))

    if tuple(scene for p in parts for scene in p.scene_ids) != tuple(s.scene_id for s in items):
        raise LessonPlanError("Internal source scene omission/reordering detected")

    return LessonPlan(
        schema_version=SCHEMA_VERSION,
        lesson_title=lesson_title,
        discipline=discipline,
        source_sha256=source_sha256.lower(),
        target_seconds=target,
        max_planned_seconds=ceiling,
        intro_reserve_seconds=intro,
        outro_reserve_seconds=outro,
        parts=tuple(parts),
    )
