"""No-network tests for source-bound draft comparison, reject unsafe promotions."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.element_draft_drift_audit import (
    MappingDriftError, compare, load, main, markdown,
)


def fixture():
    originals = ["Integrating the first term gives a logarithm.",
                 "The second uses the power rule."]
    blocks = []
    for i, spoken in enumerate(originals, 1):
        unit = {
            "proposal_id": f"s{i:03d}.utterance.001",
            "verbatim_script_fragment": spoken,
            "candidate_target_rankings_unverified": [],
            "mapping_ambiguous": True,
            "manual_target_selection_required": True,
            "spoken_word_fidelity_verified": False,
            "approved_for_tts": False,
        }
        blocks.append({
            "slide_number": i,
            "verbatim_slide_narration": spoken,
            "original_script_block_sha256": hashlib.sha256(
                spoken.encode("utf8")).hexdigest(),
            "review_required": True,
            "approved_for_stage": False,
            "source_page_approved": False,
            "source_quote_approved": False,
            "proposed_utterances": [unit],
        })
    return {
        "schema_version": 1,
        "status": "REVIEW_REQUIRED_NOT_TTS_READY",
        "draft_kind": "PDF_GEOMETRY_PLUS_EXISTING_VERBATIM_SLIDE_SCRIPT",
        "can_stage_or_synthesize_audio": False,
        "cannot_be_used_as_authored_element_plan": True,
        "source_meaning_reviewed": False,
        "manual_mapping_reviewed": False,
        "automatic_author_approval": False,
        "academic_approval": False,
        "student_publication": False,
        "no_new_narration_words": True,
        "source_sha256": "a"*64,
        "slides_sha256": "b"*64,
        "script_sha256": "c"*64,
        "slide_count": 2,
        "utterance_count": 2,
        "candidate_target_count": 3,
        "figure_panel_slide_count": 0,
        "ambiguous_utterance_count": 2,
        "slides": blocks,
    }


class MappingDriftTests(unittest.TestCase):
    def setUp(self):
        self.old = fixture()
        self.new = copy.deepcopy(self.old)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def change(self):
        unit = self.new["slides"][0]["proposed_utterances"][0]
        unit["mapping_ambiguous"] = False
        unit["candidate_target_rankings_unverified"] = [
            {"draft_element_id": "s001.text.006", "overlap_hint": 0.35}]
        self.new["ambiguous_utterance_count"] = 1

    def test_unchanged_is_valid_but_creates_zero_approvals(self):
        result = compare(self.old, self.new)
        self.assertEqual(result["ranking_or_score_changed"], 0)
        self.assertEqual(result["ambiguity_classification_changed"], 0)
        self.assertFalse(result["approved_for_tts"])
        self.assertFalse(result["student_published"])
        self.assertTrue(result["manual_mapping_required_all_utterances"])

    def test_changed_ranking_and_ambiguity_is_review_only(self):
        self.change()
        result = compare(self.old,self.new,"a"*64,"b"*64)
        self.assertEqual(result["ranking_or_score_changed"], 1)
        self.assertEqual(result["ambiguity_classification_changed"], 1)
        self.assertEqual(len(result["changes"]), 1)
        self.assertEqual(result["changes"][0]["utterance_id"],
                         "s001.utterance.001")
        self.assertIn("s001.text.006",markdown(result))
        self.assertFalse(result["changes"][0]["human_mapping_approved"])

    def test_score_change_without_ambiguity_change_still_reported(self):
        self.change()
        self.new["slides"][0]["proposed_utterances"][0]["mapping_ambiguous"] = True
        self.new["ambiguous_utterance_count"] = 2
        result = compare(self.old,self.new)
        self.assertEqual(result["ranking_or_score_changed"], 1)
        self.assertEqual(result["ambiguity_classification_changed"], 0)

    def test_changed_original_text_fails_closed(self):
        self.new["slides"][0]["proposed_utterances"][0][
            "verbatim_script_fragment"] = "The answer is suddenly different."
        with self.assertRaisesRegex(MappingDriftError,"narration"):
            compare(self.old,self.new)

    def test_changed_original_source_hash_fails_closed(self):
        self.new["source_sha256"] = "e"*64
        with self.assertRaisesRegex(MappingDriftError,"source"):
            compare(self.old,self.new)

    def test_false_approval_refused(self):
        self.new["slides"][0]["proposed_utterances"][0]["approved_for_tts"] = True
        with self.assertRaisesRegex(MappingDriftError,"Unsafe proposed utterance"):
            compare(self.old,self.new)
        self.new = copy.deepcopy(self.old)
        self.new["academic_approval"] = True
        with self.assertRaisesRegex(MappingDriftError,"explicitly unapproved"):
            compare(self.old,self.new)

    def test_misreported_ambiguity_count_refused(self):
        self.change()
        self.new["ambiguous_utterance_count"] = 2
        with self.assertRaisesRegex(MappingDriftError,"counts inconsistent"):
            compare(self.old,self.new)

    def test_cli_creates_new_reports_outside_evidence_only(self):
        self.change()
        original=self.root/"historical"/"old.json"
        refreshed=self.root/"refreshed"/"new.json"
        original.parent.mkdir()
        refreshed.parent.mkdir()
        original.write_text(json.dumps(self.old),encoding="utf-8")
        refreshed.write_text(json.dumps(self.new),encoding="utf-8")
        out=self.root/"review"
        out.mkdir()
        result=out/"drift.json"
        md=out/"drift.md"
        before=(original.read_bytes(),refreshed.read_bytes())
        self.assertEqual(main(["--historical",str(original),"--refreshed",
                               str(refreshed),"--output-json",str(result),
                               "--output-md",str(md)]),0)
        saved=json.loads(result.read_text())
        self.assertEqual(saved["ambiguous_classification_changed"],1)
        self.assertEqual(saved["historical_draft_sha256"],
                         hashlib.sha256(before[0]).hexdigest())
        self.assertEqual((original.read_bytes(),refreshed.read_bytes()),before)
        with self.assertRaisesRegex(MappingDriftError,"new review"):
            main(["--historical",str(original),"--refreshed",
                  str(refreshed),"--output-json",str(result),"--output-md",str(md)])

    def test_cli_source_directory_overwrite_blocked(self):
        old=self.root/"old.json"
        new=self.root/"new.json"
        old.write_text(json.dumps(self.old))
        new.write_text(json.dumps(self.new))
        other=self.root/"external"
        other.mkdir()
        with self.assertRaisesRegex(MappingDriftError,"outside"):
            main(["--historical",str(old),"--refreshed",str(new),
                  "--output-json",str(self.root/"not_allowed.json"),
                  "--output-md",str(other/"allowed.md")])


if __name__=="__main__":
    unittest.main()
