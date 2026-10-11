"""Interrupted repairs must invalidate downstream checkpoints."""
import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.runner import STAGES, invalidate_downstream, save_pipeline_state

class DownstreamInvalidationTests(unittest.TestCase):
    def test_slide_change_invalidates_audio_and_video_receipts(self):
        state = {"completed": {name: {"model": "old"} for name in STAGES}}
        dropped = invalidate_downstream(state, "slides")
        self.assertEqual(dropped, list(STAGES[2:]))
        self.assertIn("slides", state["completed"])
        for stage in STAGES[2:]:
            self.assertNotIn(stage, state["completed"])

    def test_invalidation_saved_before_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            state = {"completed": {name: {"model": "old"} for name in STAGES}}
            stamp = Path(temp) / ".selenium_pipeline_state.json"
            save_pipeline_state(stamp, state)
            invalidate_downstream(state, "figures")
            save_pipeline_state(stamp, state)
            reloaded = json.loads(stamp.read_text(encoding="utf-8"))
            self.assertEqual(set(reloaded["completed"]), {"figures"})

    def test_last_stage_has_no_future_dependents(self):
        state = {"completed": {"video": {"model": "done"}}}
        self.assertEqual(invalidate_downstream(state, "video"), [])
        self.assertIn("video", state["completed"])

    def test_unknown_stage_is_refused(self):
        with self.assertRaises(ValueError):
            invalidate_downstream({"completed": {}}, "invalid")
