"""Windows-only regression: frontier task routing bootstrap and exact-source photo panel recovery."""
from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "selenium_pipeline" / "vendor_template_v2"

class DynamicFrontierStageBootstrapTests(unittest.TestCase):
    def test_new_task_can_select_owned_picker_before_task_specific_qualification(self):
        source = (VENDOR/"selenium.py").read_text(encoding="utf8")
        tree = ast.parse(source)
        method = next(node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "open_clean_gemini_chat")
        body_source = ast.get_source_segment(source, method)
        self.assertIn('adaptive_allowed and target_mode in',body_source)
        self.assertIn('("hydrogen","hydrogen-thinking","argon","carbon","neon")',body_source)
        self.assertIn('requires_thinking = True',body_source)
        initial_idx = body_source.index('requires_thinking = True')
        select_idx = body_source.index('selected_mode = select_owned_gemini_with_recovery(')
        final_check_idx = body_source.index('requires_thinking=browser_stage_needs_thinking(mode=target_mode)')
        self.assertLess(initial_idx, select_idx)
        self.assertLess(select_idx, final_check_idx)
        # Source upload and Send are later methods, not a fallback allowed
        # to circumvent the second, task-specific verification check.
        self.assertNotIn('click_send_with_fallbacks(',body_source[:final_check_idx])
        self.assertNotIn('upload_files(',body_source[:final_check_idx])

    def test_unknown_family_remains_fatal_in_no_send_stage_policy(self):
        from selenium_pipeline.gemini_stage_policy import browser_stage_needs_thinking, GeminiStagePolicyError
        with self.assertRaises(GeminiStagePolicyError):
            browser_stage_needs_thinking(mode="unregistered_future_family",stage="narration")

class Section11SourcePanelCropTests(unittest.TestCase):
    def test_exact_pdf_checksum_pinned_two_photo_figure(self):
        p=VENDOR.parent/"source_crop_overrides_v1.json"
        data=json.loads(p.read_text(encoding="utf8"))
        sha="a9727afee30282deeb22f34ce67323e168ab6a3b6a2893f2754f27f683ab28b9"
        self.assertEqual(data["overrides"][sha]["1.1"],[35.0,114.0,164.0,571.5])
        from selenium_pipeline.source_caption_figure_chain_v1 import _source_sha_bound_crop_override
        import pymupdf as fitz
        class FakePage:
            rect=fitz.Rect(0,0,612,783)
        row={"id":"1.1","caption_bbox":[35.997,575.026,159.901,686.893]}
        clip,mode=_source_sha_bound_crop_override(sha,row,FakePage())
        self.assertEqual(tuple(clip),(35.0,114.0,164.0,571.5))
        self.assertLess(clip.y1,row["caption_bbox"][1])
        self.assertEqual(mode,"source_sha_bound_geometry_recovery")
        self.assertIsNone(_source_sha_bound_crop_override("0"*64,row,FakePage()))

if __name__=="__main__":
    unittest.main()
