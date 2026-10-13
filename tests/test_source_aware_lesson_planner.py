"""End-to-end offline pre-generation planning tests with synthetic PDFs."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf
from jsonschema import Draft202012Validator

from selenium_pipeline.domains import load_profile
from selenium_pipeline.planning import (
    LessonPlanError, SourceScanError, plan_series,
    scan_pdf,
)

ROOT = Path(__file__).resolve().parents[1]
PAGE_SENTENCES = [
    "This is reviewed evidence for limits page one with clear definitions and examples.",
    "This is reviewed evidence for limits page two with linked graphs and examples.",
    "This is reviewed evidence for limits page three with an application.",
]


def outline(scan, *, seconds, profile="mathematics", reviewed=True,
            forbids=()):
    n = len(seconds)
    concepts = []
    for index, duration in enumerate(seconds):
        page = index % 3 + 1
        concepts.append({
            "concept_id": f"c{index+1:03d}",
            "title": f"Reviewed Concept {index+1}",
            "source_pages": [page],
            "evidence": [{"kind": "text", "page": page,
                          "excerpt": PAGE_SENTENCES[page-1][8:62]}],
            "estimated_teaching_s": duration,
            "prerequisites": [f"c{index:03d}"] if index else [],
            "boundary_after": "forbidden" if index in forbids else "preferred",
            "planned_slides": 2,
        })
    covered = sorted({(i % 3) + 1 for i in range(n)})
    excluded = [dict(page=p, reason="Explicitly outside the reviewed teaching scope.")
                for p in range(1, 4) if p not in covered]
    return {
        "schema_version": 1,
        "source_sha256": scan["source_sha256"],
        "profile": {"id": profile, "version": "1.0.0"},
        "title": "Synthetic Test Subchapter",
        "scope": {"included_pages": covered, "excluded_pages": excluded},
        "approval": {"status": "approved" if reviewed else "unreviewed",
                     "reviewed_by": "test reviewer",
                     "coverage_note": "Reviewed synthetic source and explicit scope."},
        "concepts": concepts,
    }


class SourceAwarePlannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.source_root = self.path / "PDF_Tree"
        sub = self.source_root / "2" / "2.2"
        sub.mkdir(parents=True)
        self.pdf = sub / "source.pdf"
        pdf = pymupdf.open()
        for sentence in PAGE_SENTENCES:
            page = pdf.new_page(width=595, height=842)
            page.insert_text((45, 85), sentence, fontsize=11)
        pdf.save(self.pdf)
        pdf.close()
        self.scan = scan_pdf(self.pdf, source_root=self.source_root)
        self.profile = load_profile("mathematics")

    def plan(self, seconds, **kwargs):
        proposal = outline(self.scan, seconds=seconds, **kwargs)
        return plan_series(proposal, self.scan, self.profile, source_pdf=self.pdf)

    def test_read_only_scan_creates_source_hash_and_page_ledger(self):
        original_bytes = self.pdf.read_bytes()
        self.assertEqual(self.scan["page_count"], 3)
        self.assertEqual(self.scan["coverage_status"], "unreviewed")
        self.assertTrue(all(p["char_count"] > 40 for p in self.scan["pages"]))
        self.assertEqual(original_bytes, self.pdf.read_bytes())

    def test_22_minutes_must_be_three_parts_not_two(self):
        plan = self.plan([60]*22)
        self.assertEqual(len(plan["parts"]), 3)
        self.assertEqual([p["index"] for p in plan["parts"]], [1,2,3])
        self.assertEqual(sorted(x for p in plan["parts"] for x in p["concept_ids"]),
                         sorted(x["concept_id"] for x in outline(self.scan,seconds=[60]*22)["concepts"]))
        self.assertTrue(all(p["estimated_duration_s"]["max"] <= 600
                            for p in plan["parts"]))
        self.assertIn("Part 1 of 3", plan["parts"][0]["continuity_intro"])
        self.assertIn("Part 2 of 3", plan["parts"][0]["continuity_outro"])
        self.assertNotIn("Next, Part 4", plan["parts"][-1]["continuity_outro"])

    def test_34_minutes_four_balanced_parts(self):
        plan = self.plan([60]*34)
        self.assertEqual(len(plan["parts"]), 4)
        self.assertEqual(sum(len(p["concept_ids"]) for p in plan["parts"]), 34)
        self.assertTrue(all(380 < p["estimated_duration_s"]["min"] < 600 for p in plan["parts"]))
        self.assertTrue(all("Part" in p["continuity_intro"] for p in plan["parts"]))

    def test_short_single_video_has_correct_series_intro_end(self):
        plan = self.plan([90]*4)
        self.assertEqual(len(plan["parts"]), 1)
        self.assertIn("Part 1 of 1", plan["parts"][0]["continuity_intro"])
        self.assertIn("This completes", plan["parts"][0]["continuity_outro"])

    def test_reject_long_unsplittable_concept(self):
        with self.assertRaisesRegex(LessonPlanError, "No pedagogically legal"):
            self.plan([590])

    def test_forbidden_boundaries_may_block_unsafe_split(self):
        with self.assertRaisesRegex(LessonPlanError, "No pedagogically legal"):
            self.plan([60]*11, forbids=tuple(range(10)))

    def test_explicit_coverage_approval_required(self):
        with self.assertRaisesRegex(LessonPlanError, "explicitly approved"):
            self.plan([60]*6, reviewed=False)

    def test_source_hash_drift_blocks(self):
        source = outline(self.scan, seconds=[60]*4)
        source["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(LessonPlanError, "source hash"):
            plan_series(source, self.scan, self.profile, source_pdf=self.pdf)

    def test_wrong_figure_or_text_evidence_blocks(self):
        source = outline(self.scan, seconds=[60]*4)
        source["concepts"][0]["evidence"][0]["excerpt"] = "This passage never appeared in the PDF."
        with self.assertRaisesRegex(LessonPlanError, "Source evidence failed"):
            plan_series(source, self.scan, self.profile, source_pdf=self.pdf)

    def test_bad_prerequisite_is_rejected(self):
        source = outline(self.scan, seconds=[60]*4)
        source["concepts"][0]["prerequisites"] = ["c002"]
        with self.assertRaisesRegex(LessonPlanError, "Prerequisites"):
            plan_series(source, self.scan, self.profile, source_pdf=self.pdf)

    def test_unaccounted_source_page_blocks(self):
        source = outline(self.scan, seconds=[60]*2)
        source["scope"]["excluded_pages"] = []
        with self.assertRaisesRegex(LessonPlanError, "account for every page"):
            plan_series(source, self.scan, self.profile, source_pdf=self.pdf)

    def test_source_outside_selected_root_blocks(self):
        outside_root = self.path / "Other_Tree"
        outside_root.mkdir()
        with self.assertRaisesRegex(SourceScanError, "inside the selected source root"):
            scan_pdf(self.pdf, source_root=outside_root)

    def test_schema_roundtrip_for_scan_outline_plan(self):
        source = outline(self.scan, seconds=[70]*5)
        plan = plan_series(source, self.scan, self.profile, source_pdf=self.pdf)
        for name, data in (("source_scan", self.scan),
                           ("concept_outline", source),
                           ("lesson_plan", plan)):
            s = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
            Draft202012Validator.check_schema(s)
            Draft202012Validator(s).validate(data)

    def test_cli_produces_files_without_overwriting_source(self):
        outline_path = self.path / "outline.json"
        outline_path.write_text(json.dumps(outline(self.scan, seconds=[90]*4)))
        scan_path = self.path / "scan.json"
        plan_path = self.path / "lesson_plan.json"
        cmd = [sys.executable, "-m", "selenium_pipeline.planning"]
        source_args = ["--source-root", str(self.source_root), "--source-pdf", str(self.pdf)]
        a = subprocess.run([*cmd, "scan", *source_args, "--out", str(scan_path)],
                           cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(a.returncode, 0, a.stderr)
        b = subprocess.run([*cmd, "plan", *source_args, "--domain", "mathematics",
                            "--outline", str(outline_path), "--out", str(plan_path)],
                           cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(len(json.loads(plan_path.read_text())["parts"]), 1)
        third = subprocess.run([*cmd, "plan", *source_args, "--domain", "mathematics",
                                "--outline", str(outline_path), "--out", str(plan_path)],
                               cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(third.returncode, 2)
        self.assertIn("File exists", third.stderr)

    def test_visual_review_provenance_is_explicit_but_not_magic_validation(self):
        source = outline(self.scan, seconds=[60]*3)
        source["concepts"][0]["evidence"] = [{
            "kind": "visual_reviewed", "page": 1,
            "description": "Manually reviewed graph panel labels and scale."
        }]
        plan = plan_series(source, self.scan, self.profile, source_pdf=self.pdf)
        self.assertTrue(plan["parts"])

    def test_draft_is_review_required_not_approved(self):
        from selenium_pipeline.planning.draft_outline import draft_page_outline
        draft = draft_page_outline(self.pdf, self.scan, self.profile)
        self.assertEqual(draft["approval"]["status"], "unreviewed")
        self.assertEqual(len(draft["concepts"]), 3)
        schema = json.loads((ROOT / "schemas/concept_outline.schema.json").read_text())
        Draft202012Validator(schema).validate(draft)
        with self.assertRaisesRegex(LessonPlanError, "explicitly approved"):
            plan_series(draft, self.scan, self.profile, source_pdf=self.pdf)

    def test_cli_draft_then_plan_blocks_until_review(self):
        cmd = [sys.executable, "-m", "selenium_pipeline.planning"]
        source_args = ["--source-root", str(self.source_root), "--source-pdf", str(self.pdf)]
        path = self.path / "draft.json"
        proc = subprocess.run([*cmd, "draft", *source_args,
                               "--domain", "mathematics", "--out", str(path)],
                              cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        blocked = subprocess.run([*cmd, "plan", *source_args, "--domain", "mathematics",
                                  "--outline", str(path), "--out", str(self.path / "should_not_exist.json")],
                                 cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("explicitly approved", blocked.stderr)
        self.assertFalse((self.path / "should_not_exist.json").exists())

    def test_physics_and_future_history_profiles_use_same_planner(self):
        from selenium_pipeline.domains import load_profile
        for name, kw in [
            ("physics", {}),
            ("history", {"profile_file": ROOT / "examples/history_profile.example.json"}),
        ]:
            with self.subTest(domain=name):
                profile = load_profile(name, **kw)
                source = outline(self.scan, seconds=[60]*9, profile=name)
                result = plan_series(source, self.scan, profile, source_pdf=self.pdf)
                self.assertEqual(result["profile"]["id"], name)
                self.assertEqual(sum(len(p["concept_ids"]) for p in result["parts"]), 9)
                # A structurally accepted experimental history plan is NOT a
                # historical-facts or history-lecture educational QA certificate.
                self.assertNotIn("certified", str(result))

    def test_iterative_planner_handles_500_tiny_concepts(self):
        result = self.plan([1] * 500)
        self.assertEqual(len(result["parts"]), 1)
        self.assertEqual(len(result["parts"][0]["concept_ids"]), 500)


if __name__ == "__main__":
    unittest.main()
