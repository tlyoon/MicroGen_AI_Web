"""Offline regression tests for the Thomas / multidisciplinary part planner."""
import json
import unittest
from dataclasses import replace

from selenium_pipeline.lesson_plan import (
    LessonPlanError, Scene, assess_actual_duration, plan_lesson,
)

SOURCE_HASH = "a" * 64


def make_scene(index, seconds=70.0, *, natural_break=False):
    return Scene(
        scene_id=f"scene_{index:02d}",
        title=f"Concept {index}",
        objective=f"Explain concept {index} with a source-grounded example",
        source_pages=(index,),
        estimated_narration_seconds=seconds,
        natural_break_after=natural_break,
    )


def plan(scenes, **options):
    return plan_lesson(
        lesson_title="Thomas Calculus — Limits",
        discipline="calculus",
        source_sha256=SOURCE_HASH,
        scenes=scenes,
        **options,
    )


class LessonPlanningTests(unittest.TestCase):
    def test_two_coherent_eight_to_nine_minute_parts(self):
        scenes = [make_scene(i, natural_break=(i == 7)) for i in range(1, 15)]
        result = plan(scenes)
        self.assertEqual([p.part_id for p in result.parts], ["part_01", "part_02"])
        self.assertEqual([p.estimated_total_seconds for p in result.parts], [520, 520])
        self.assertEqual(result.parts[0].scene_ids, tuple(s.scene_id for s in scenes[:7]))
        self.assertEqual(result.parts[1].scene_ids, tuple(s.scene_id for s in scenes[7:]))

    def test_short_subchapter_kept_as_one_part(self):
        result = plan([make_scene(1, 130), make_scene(2, 110)])
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].estimated_total_seconds, 270)

    def test_explicit_continuity_between_parts(self):
        result = plan([make_scene(i, natural_break=(i == 7)) for i in range(1, 15)])
        self.assertIn("Introduce", result.parts[0].intro_brief)
        self.assertIn("preview", result.parts[0].outro_brief)
        self.assertIn("Connect from", result.parts[1].intro_brief)
        self.assertIn("conclude", result.parts[-1].outro_brief)

    def test_no_scene_is_omitted_or_duplicated(self):
        scenes = [make_scene(i) for i in range(1, 20)]
        result = plan(scenes)
        self.assertEqual(
            [scene_id for part in result.parts for scene_id in part.scene_ids],
            [s.scene_id for s in scenes],
        )
        self.assertLess(max(p.estimated_total_seconds for p in result.parts), 600)

    def test_indivisible_overlong_scene_fails_instead_of_cut(self):
        with self.assertRaisesRegex(LessonPlanError, "Atomic scene"):
            plan([make_scene(1, 541)])

    def test_exact_planned_limit_is_allowed(self):
        self.assertEqual(plan([make_scene(1, 540)]).parts[0].estimated_total_seconds, 570)

    def test_invalid_source_hash_is_blocked(self):
        with self.assertRaisesRegex(LessonPlanError, "source_sha256"):
            plan_lesson(
                lesson_title="Limits", discipline="calculus", source_sha256="made-up",
                scenes=[make_scene(1)],
            )

    def test_duplicate_scene_id_is_blocked(self):
        with self.assertRaisesRegex(LessonPlanError, "Duplicate"):
            plan([make_scene(1), make_scene(1)])

    def test_missing_pages_is_blocked(self):
        with self.assertRaisesRegex(LessonPlanError, "positive source page"):
            plan([replace(make_scene(1), source_pages=())])

    def test_boolean_page_is_not_an_integer_page(self):
        with self.assertRaisesRegex(LessonPlanError, "positive source page"):
            plan([replace(make_scene(1), source_pages=(True,))])

    def test_missing_discipline_is_blocked(self):
        with self.assertRaisesRegex(LessonPlanError, "explicit discipline"):
            plan_lesson(
                lesson_title="A lecture", discipline="", source_sha256=SOURCE_HASH,
                scenes=[make_scene(1)],
            )

    def test_missing_objective_is_blocked(self):
        with self.assertRaisesRegex(LessonPlanError, "objective"):
            plan([replace(make_scene(1), objective="")])

    def test_invalid_estimates_are_blocked(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(LessonPlanError):
                    plan([make_scene(1, value)])

    def test_cannot_relax_planning_ceiling_past_ten_minutes(self):
        with self.assertRaisesRegex(LessonPlanError, "under 600"):
            plan([make_scene(1)], max_planned_seconds=610)

    def test_canonical_hash_binds_scene_objective_and_source(self):
        scenes = [make_scene(1, 130)]
        a = plan(scenes)
        b = plan([replace(scenes[0], objective="A revised objective")])
        c = plan_lesson(
            lesson_title="Thomas Calculus — Limits", discipline="calculus",
            source_sha256="b" * 64, scenes=scenes,
        )
        self.assertEqual(len(a.canonical_sha256()), 64)
        self.assertNotEqual(a.canonical_sha256(), b.canonical_sha256())
        self.assertNotEqual(a.canonical_sha256(), c.canonical_sha256())
        self.assertEqual(a.canonical_sha256(), plan(scenes).canonical_sha256())

    def test_caller_mutation_cannot_alter_approved_source_pages(self):
        pages = [1]
        scene = replace(make_scene(1), source_pages=pages)
        result = plan([scene])
        original_hash = result.canonical_sha256()
        pages[0] = 99
        self.assertEqual(result.scenes[0].source_pages, (1,))
        self.assertEqual(result.canonical_sha256(), original_hash)

    def test_plan_json_serialization(self):
        result = plan([make_scene(1), make_scene(2)])
        decoded = json.loads(json.dumps(result.as_dict(), ensure_ascii=False))
        self.assertEqual(decoded["schema_version"], 1)
        self.assertEqual(decoded["scenes"][0]["source_pages"], [1])
        self.assertEqual(decoded["parts"][0]["scene_ids"], ["scene_01", "scene_02"])

    def test_normal_mp4_duration_is_strictly_under_600(self):
        self.assertEqual(assess_actual_duration(599.999).status, "passed")
        self.assertEqual(assess_actual_duration(600).status, "review_required")

    def test_exception_requires_explicit_approval(self):
        self.assertEqual(assess_actual_duration(625).status, "review_required")
        approved = assess_actual_duration(625, explicit_exception_approved=True)
        self.assertEqual(approved.status, "passed")
        self.assertTrue(approved.explicit_exception_approved)
        self.assertEqual(assess_actual_duration(629.999).status, "review_required")

    def test_overshoot_at_or_above_630_is_blocked_even_with_approval(self):
        self.assertEqual(assess_actual_duration(630).status, "blocked")
        self.assertEqual(
            assess_actual_duration(660, explicit_exception_approved=True).status,
            "blocked",
        )

    def test_actual_duration_cannot_be_missing_or_non_finite(self):
        for value in (0, -1, float("nan"), float("inf"), None):
            with self.subTest(value=value):
                with self.assertRaises(LessonPlanError):
                    assess_actual_duration(value)

    def test_no_media_or_tts_is_produced_during_planning(self):
        result = plan([make_scene(1)])
        self.assertEqual(result.discipline, "calculus")
        self.assertEqual(result.parts[0].source_pages, (1,))


if __name__ == "__main__":
    unittest.main()
