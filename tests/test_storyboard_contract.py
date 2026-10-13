"""Phase 3 joint slide/narration contract tests, no external LLM or media calls."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf
from jsonschema import Draft202012Validator

from selenium_pipeline.domains import load_profile
from selenium_pipeline.planning import scan_pdf, plan_series
from selenium_pipeline.storyboard_authoring import draft_storyboard, build_authoring_brief
from selenium_pipeline.storyboard_gate import (
    StoryboardError, canonical_sha256, inspect_storyboard,
)
from selenium_pipeline.beamer_anchor_contract import (
    collect_tex_anchor_ids, verify_tex_anchor_coverage,
)

ROOT = Path(__file__).resolve().parents[1]


class StoryboardContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        folder = root/"Sources"/"2"/"2.2"
        folder.mkdir(parents=True)
        self.pdf = folder/"source.pdf"
        with pymupdf.open() as doc:
            for i in range(3):
                page = doc.new_page()
                page.insert_text((55, 100),
                                 f"This source page {i+1} explains an approved limit "
                                 "concept with definitions and examples.")
            doc.save(self.pdf)
        self.scan = scan_pdf(self.pdf, source_root=root/"Sources")
        self.profile = load_profile("mathematics")
        self.outline = {
            "schema_version": 1, "source_sha256": self.scan["source_sha256"],
            "profile": {"id": "mathematics", "version": "1.0.0"},
            "title": "Limits and continuity",
            "scope": {"included_pages": [1, 2, 3], "excluded_pages": []},
            "approval": {"status": "approved", "reviewed_by": "Independent teacher",
                         "coverage_note": "All three synthetic pages are assigned."},
            "concepts": [],
        }
        for i in range(3):
            self.outline["concepts"].append({
                "concept_id": f"concept{i+1}", "title": f"Concept {i+1}",
                "source_pages": [i+1], "evidence": [{
                    "page": i+1, "kind": "text",
                    "excerpt": f"This source page {i+1} explains an approved limit concept",
                }],
                "estimated_teaching_s": 105, "prerequisites": [],
                "boundary_after": "preferred", "planned_slides": 2,
            })
        self.plan = plan_series(self.outline, self.scan, self.profile, source_pdf=self.pdf)
        self.assertEqual(len(self.plan["parts"]), 1)
        self.part_id = self.plan["parts"][0]["part_id"]
        self.board = draft_storyboard(
            self.plan, self.outline, self.part_id, self.profile,
        )
        # Simulate an authored/review-pending structured script, never scientific approval.
        for seg in self.board["narration_segments"]:
            if "REVIEW REQUIRED" in seg["spoken_text"]:
                seg["spoken_text"] = (
                    "Explain the approved concept using accurate mathematical "
                    "terminology and relevant definitions from this source."
                )

    def accept(self, board=None):
        return inspect_storyboard(
            self.board if board is None else board,
            self.plan, self.outline, self.profile,
            source_pdf=self.pdf, scan=self.scan,
        )

    def test_valid_structural_storyboard_never_claims_semantic_certification(self):
        result = self.accept()
        self.assertEqual(result["slide_count"], 8)
        self.assertEqual(result["element_count"], 8)
        self.assertEqual(result["segment_count"], 8)
        self.assertTrue(result["source_revalidated"])
        self.assertEqual(result["status"], "structural_pass_semantic_review_required")
        self.assertIn("tts_timing", result["unverified"])
        self.assertIn("figure_panel_visual_fidelity", result["unverified"])

    def test_phase1_storyboard_schema_roundtrip(self):
        schema = json.loads((ROOT/"schemas/storyboard.schema.json").read_text())
        Draft202012Validator(schema).validate(self.board)

    def test_no_authored_content_means_placeholder_rejected(self):
        draft = draft_storyboard(self.plan, self.outline, self.part_id, self.profile)
        self.assertIn("REVIEW REQUIRED", draft["narration_segments"][1]["spoken_text"])
        with self.assertRaisesRegex(StoryboardError, "placeholder"):
            self.accept(draft)

    def test_plan_hash_mismatch_is_detected(self):
        edited = copy.deepcopy(self.board)
        edited["plan_sha256"] = "0" * 64
        with self.assertRaisesRegex(StoryboardError, "hash"):
            self.accept(edited)

    def test_source_revision_rejected_before_structural_check(self):
        changed = copy.deepcopy(self.outline)
        changed["approval"]["status"] = "unreviewed"
        with self.assertRaisesRegex(StoryboardError, "Unapproved"):
            inspect_storyboard(self.board, self.plan, changed, self.profile,
                               scan=self.scan, source_pdf=self.pdf)

    def test_bad_element_cross_slide_reference_rejected(self):
        changed = copy.deepcopy(self.board)
        changed["narration_segments"][1]["element_ids"] = [
            changed["slides"][2]["elements"][0]["element_id"]
        ]
        with self.assertRaisesRegex(StoryboardError, "another slide"):
            self.accept(changed)

    def test_no_missing_concept_allowed(self):
        changed = copy.deepcopy(self.board)
        changed["slides"][3]["elements"][0]["source_concept_ids"] = ["concept1"]
        changed["slides"][4]["elements"][0]["source_concept_ids"] = ["concept1"]
        with self.assertRaisesRegex(StoryboardError, "source concept/page"):
            self.accept(changed)

    def test_missing_narration_link_rejected(self):
        changed = copy.deepcopy(self.board)
        changed["narration_segments"].pop(3)
        with self.assertRaisesRegex(StoryboardError, "no linked narration"):
            self.accept(changed)

    def test_ordered_narration_required(self):
        changed = copy.deepcopy(self.board)
        changed["narration_segments"][2], changed["narration_segments"][4] = (
            changed["narration_segments"][4], changed["narration_segments"][2]
        )
        with self.assertRaisesRegex(StoryboardError, "not ordered"):
            self.accept(changed)

    def test_intro_outro_are_required_and_consistent(self):
        changed = copy.deepcopy(self.board)
        changed["narration_segments"][0]["spoken_text"] = (
            "A generic welcoming phrase without the appropriate part label."
        )
        with self.assertRaisesRegex(StoryboardError, "Intro narration"):
            self.accept(changed)
        changed = copy.deepcopy(self.board)
        changed["slides"][-1]["title"] = "A generic summary"
        with self.assertRaisesRegex(StoryboardError, "closing-slide"):
            self.accept(changed)

    def test_budget_change_propagates_upstream(self):
        changed = copy.deepcopy(self.board)
        changed["narration_segments"][3]["estimated_duration_s"] = 295
        with self.assertRaisesRegex(StoryboardError, "budget"):
            self.accept(changed)

    def test_slide_count_cannot_change_silently(self):
        changed = copy.deepcopy(self.board)
        changed["slides"].pop()
        with self.assertRaisesRegex(StoryboardError, "slide count"):
            self.accept(changed)

    def test_unknown_ids_rejected(self):
        changed = copy.deepcopy(self.board)
        changed["slides"][0]["elements"][0]["source_concept_ids"] = ["notInOutline"]
        with self.assertRaisesRegex(StoryboardError, "outside assigned"):
            self.accept(changed)

    def test_tex_anchor_coverage_and_comment_filtering(self):
        tags = [e["element_id"] for slide in self.board["slides"]
                for e in slide["elements"]]
        latex = "\n".join(
            f"\\MGElement{{{tag}}}{{Sample visual}}" for tag in tags
        ) + "\n% \\MGElement{not_real}{commented out}\n"
        self.assertEqual(collect_tex_anchor_ids(latex), tags)
        receipt = verify_tex_anchor_coverage(latex, self.board)
        self.assertIn("geometry_unverified", receipt["status"])
        with self.assertRaisesRegex(StoryboardError, "Duplicate"):
            verify_tex_anchor_coverage(latex + f"\n\\MGElement{{{tags[0]}}}{{duplicate}}", self.board)

    def test_missing_figure_panel_anchor_blocks(self):
        changed = copy.deepcopy(self.board)
        changed["slides"][4]["elements"][0]["kind"] = "figure_panel"
        self.accept(changed)  # Structural only, NOT panel-content verification.
        all_tags = [e["element_id"] for slide in changed["slides"]
                    for e in slide["elements"]]
        latex = "\n".join(f"\\MGElement{{{t}}}{{region}}" for t in all_tags[:-1])
        with self.assertRaisesRegex(StoryboardError, "missing="):
            verify_tex_anchor_coverage(latex, changed)

    def test_profile_aware_brief_is_source_bound_and_pre_tts(self):
        prompt = build_authoring_brief(self.plan, self.outline,
                                       self.part_id, self.profile)
        self.assertIn("source-faithful", prompt)
        self.assertIn("part_01", prompt)
        self.assertIn(canonical_sha256(self.plan), prompt)
        self.assertIn("mathematical", prompt.lower())
        self.assertIn("Part 1 of 1", prompt)
        self.assertIn("before any TTS work", prompt)

    def test_authoring_brief_preserves_source_scope_and_within_page_cautions(self):
        reviewed = copy.deepcopy(self.outline)
        warning = ("PDF page 1 contains the previous section\'s final exercise "
                   "above this section\'s heading; do not teach it as this lesson.")
        reviewed["approval"]["coverage_note"] = warning
        prompt = build_authoring_brief(self.plan, reviewed,
                                       self.part_id, self.profile)
        self.assertIn(warning, prompt)
        self.assertIn("included_pdf_pages", prompt)
        self.assertIn("excluded_pdf_pages", prompt)
        self.assertIn("reviewer_coverage_note", prompt)
        self.assertIn("within-page boundary cautions", prompt)

    def test_custom_future_profile_uses_same_contract(self):
        history = load_profile(
            "history", profile_file=ROOT/"examples/history_profile.example.json"
        )
        edited_plan = copy.deepcopy(self.plan)
        edited_outline = copy.deepcopy(self.outline)
        edited_plan["profile"] = {"id": "history", "version": "1.0.0"}
        edited_outline["profile"] = edited_plan["profile"]
        draft = draft_storyboard(edited_plan, edited_outline, self.part_id, history)
        self.assertEqual(draft["plan_sha256"], canonical_sha256(edited_plan))
        brief = build_authoring_brief(edited_plan, edited_outline, self.part_id, history)
        self.assertIn("chronolog", brief.lower())
        self.assertNotIn("certified", brief)

    def test_invalid_source_page_blocks(self):
        changed = copy.deepcopy(self.board)
        changed["slides"][2]["elements"][0]["source_page"] = 999
        with self.assertRaisesRegex(StoryboardError, "source concept/page"):
            self.accept(changed)

    def test_cli_draft_brief_and_inspect_receipts_never_certify(self):
        import subprocess
        import sys
        sandbox = Path(self.temp.name)
        plan_path = sandbox/"plan.json"
        outline_path = sandbox/"outline.json"
        board_path = sandbox/"board.json"
        for path, value in [
            (plan_path, self.plan), (outline_path, self.outline),
            (board_path, self.board),
        ]:
            path.write_text(json.dumps(value), encoding="utf-8")
        root = sandbox/"Sources"
        args = [
            "--source-root", str(root), "--source-pdf", str(self.pdf),
            "--plan", str(plan_path), "--outline", str(outline_path),
            "--domain", "mathematics", "--part", self.part_id,
        ]
        def run(action, out, extra=()):
            return subprocess.run(
                [sys.executable, "-m", "selenium_pipeline.storyboard_cli",
                 action, *args, *extra, "--out", str(out)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
        draft_path = sandbox/"unreviewed.json"
        response = run("draft", draft_path)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertIn("REVIEW REQUIRED", draft_path.read_text())
        self.assertEqual(run("draft", draft_path).returncode, 2)

        brief_path = sandbox/"authoring_brief.txt"
        response = run("brief", brief_path)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertIn("source-faithful", brief_path.read_text())

        receipt = sandbox/"structural_receipt.json"
        response = run("inspect", receipt, extra=[
            "--storyboard", str(board_path),
        ])
        self.assertEqual(response.returncode, 0, response.stderr)
        report = json.loads(receipt.read_text())
        self.assertEqual(report["status"],
                         "structural_pass_semantic_review_required")
        self.assertIn("highlight_alignment", report["unverified"])

    def test_cli_rejects_placeholder_narration_without_receipt(self):
        import subprocess
        import sys
        sandbox = Path(self.temp.name)
        plan_path, outline_path, board_path = [
            sandbox/s for s in ("plan.json", "outline.json", "unreviewed.json")
        ]
        plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        outline_path.write_text(json.dumps(self.outline), encoding="utf-8")
        board_path.write_text(json.dumps(draft_storyboard(
            self.plan, self.outline, self.part_id, self.profile)), encoding="utf-8")
        receipt = sandbox/"should_not_exist.json"
        response = subprocess.run(
            [sys.executable, "-m", "selenium_pipeline.storyboard_cli",
             "inspect", "--source-root", str(sandbox/"Sources"),
             "--source-pdf", str(self.pdf), "--plan", str(plan_path),
             "--outline", str(outline_path), "--domain", "mathematics",
             "--part", self.part_id, "--storyboard", str(board_path),
             "--out", str(receipt)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(response.returncode, 2)
        self.assertIn("placeholder", response.stderr)
        self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
