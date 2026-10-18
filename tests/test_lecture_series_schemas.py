"""Structural schema contract tests; semantic consistency comes in Phase 2."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
HASH = "a" * 64


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def fixtures():
    inventory = {
        "schema_version": 1, "source_pdf": "source.pdf",
        "source_sha256": HASH, "domain_hint": "mathematics",
        "concepts": [{
            "concept_id": "limits", "source_pages": [1, 2],
            "summary": "Informal limits", "required": True, "prerequisites": [],
        }],
        "figures": [],
    }
    plan = {
        "schema_version": 1, "source_sha256": HASH,
        "profile": {"id": "mathematics", "version": "1.0.0"},
        "coverage": {"required_concept_ids": ["limits"],
                     "assigned_concept_ids": ["limits"],
                     "review_required_concept_ids": []},
        "title": "Limits", "planner_version": "1.0.0",
        "parts": [{
            "part_id": "part_01", "index": 1, "part_count": 1,
            "title": "Understanding limits",
            "concept_ids": ["limits"], "source_pages": [1, 2],
            "estimated_duration_s": {"min": 480, "max": 530},
            "speech_budget_s": 505,
            "continuity_intro": "Part 1 of 1: understanding limits.",
            "continuity_outro": "This completes the limits introduction.",
            "boundary_rationale": "A single coherent topic.",
            "planned_slide_count": 10,
        }],
    }
    board = {
        "schema_version": 1, "part_id": "part_01",
        "plan_sha256": HASH,
        "slides": [{
            "slide_id": "s01", "title": "Limit of a function",
            "elements": [{
                "element_id": "s01.e01", "kind": "equation",
                "source_concept_ids": ["limits"], "source_page": 1,
            }],
        }],
        "narration_segments": [{
            "segment_id": "seg01", "slide_id": "s01",
            "element_ids": ["s01.e01"],
            "spoken_text": "The limit approaches a value.", "estimated_duration_s": 6,
        }],
    }
    alignment = {
        "schema_version": 1, "part_id": "part_01",
        "slide_pdf_sha256": HASH, "audio_sha256": HASH,
        "storyboard_sha256": HASH, "duration_ms": 10000,
        "events": [{
            "slide_id": "s01", "segment_id": "seg01",
            "element_ids": ["s01.e01"], "start_ms": 100,
            "end_ms": 6500, "timing_method": "speech_segment",
            "confidence": 0.9,
        }],
    }
    manifest = {
        "schema_version": 1, "source_sha256": HASH,
        "lesson_plan_sha256": HASH,
        "profile": {"id": "mathematics", "version": "1.0.0"},
        "parts": [{
            "part_id": "part_01", "index": 1, "status": "planned",
            "mp4_sha256": None, "duration_s": None,
            "qa_receipt_sha256": None,
        }],
        "overall_status": "planned",
    }
    return dict(source_inventory=inventory, lesson_plan=plan,
                storyboard=board, alignment=alignment,
                series_manifest=manifest)


class SchemaTests(unittest.TestCase):
    def test_all_schemas_comply_with_draft_202012(self):
        for name in ("domain_profile", *fixtures()):
            with self.subTest(name=name):
                Draft202012Validator.check_schema(schema(name))

    def test_valid_examples_of_all_structures(self):
        for name, data in fixtures().items():
            with self.subTest(name=name):
                Draft202012Validator(schema(name)).validate(data)

    def test_built_in_and_custom_domain_profiles_match_schema(self):
        for f in list((ROOT/"selenium_pipeline/domains/profiles").glob("*.json")) + [
                ROOT/"examples/history_profile.example.json"]:
            with self.subTest(profile=f.name):
                Draft202012Validator(schema("domain_profile")).validate(
                    json.loads(f.read_text(encoding="utf-8")))

    def test_600_seconds_excluded_even_at_planning_schema_level(self):
        for n in (600, 620, 629.9, 630, 700):
            plan = copy.deepcopy(fixtures()["lesson_plan"])
            plan["parts"][0]["estimated_duration_s"]["max"] = n
            with self.subTest(duration=n), self.assertRaises(ValidationError):
                Draft202012Validator(schema("lesson_plan")).validate(plan)
        plan["parts"][0]["estimated_duration_s"]["max"] = 599.9
        Draft202012Validator(schema("lesson_plan")).validate(plan)

    def test_no_unknown_executable_hooks_in_profiles(self):
        profile = json.loads((ROOT/"examples/history_profile.example.json").read_text())
        profile["python_hook"] = "import os"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema("domain_profile")).validate(profile)

    def test_no_source_traversal_in_inventory(self):
        inventory = copy.deepcopy(fixtures()["source_inventory"])
        inventory["source_pdf"] = "../../source.pdf"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema("source_inventory")).validate(inventory)

    def test_timeline_rejects_negative_timestamp_and_bad_confidence(self):
        alignment = fixtures()["alignment"]
        for field, value in (("start_ms", -1), ("confidence", 2)):
            bad = copy.deepcopy(alignment)
            bad["events"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                Draft202012Validator(schema("alignment")).validate(bad)

    def test_series_manifest_cannot_claim_unknown_status(self):
        manifest = fixtures()["series_manifest"]
        manifest["parts"][0]["status"] = "perfect"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema("series_manifest")).validate(manifest)


if __name__ == "__main__":
    unittest.main()
