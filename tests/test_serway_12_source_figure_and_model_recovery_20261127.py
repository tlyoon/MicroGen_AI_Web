"""Regression: HP source Figure 1.2-1.5 and transient model menu recovery.

All model tests are pre-Send with mocked browser controls. Real PDF test is
Windows-on-HP only; GitHub CI cannot access copyrighted source PDF.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from selenium_pipeline.source_caption_figure_chain_v1 import (
    _source_sha_bound_crop_override, generate_candidates, verify_figure_crops,
    FigureChainError,
)
from selenium_pipeline.gemini_model import (
    select_owned_gemini_with_recovery, GeminiModelError,
)

SHA="814ce3e174b730271b04bbec4284bb4a15930d5026a2fcbb5148e0cf5ec018cb"
BOXES={
 "1.2":[335,567,583,685],
 "1.3":[464,60,568,262],
 "1.4":[453,309,578,429],
 "1.5":[452,476,579,542],
}
SOURCE=Path(r"G:\My Drive\Serway\Serway_1_7\1\1.2\source.pdf")

def test_all_four_figure_geometry_is_exact_source_sha_pinned():
    import pymupdf as fitz
    registry=Path(__file__).resolve().parents[1]/"selenium_pipeline"/"source_crop_overrides_v1.json"
    data=json.loads(registry.read_text(encoding="utf8"))
    assert data["overrides"][SHA]==BOXES
    captions={
        "1.2":[342.892,688.313,571.204,730.195],
        "1.3":[452.997,266.418,573.525,298.284],
        "1.4":[452.994,432.656,575.122,464.522],
        "1.5":[452.958,544.993,578.014,586.859],
    }
    page=SimpleNamespace(rect=fitz.Rect(0,0,612,783))
    for fig,box in BOXES.items():
        recovered=_source_sha_bound_crop_override(SHA,{"id":fig,"caption_bbox":captions[fig]},page)
        assert recovered is not None and list(recovered[0])==box
        assert recovered[1]=="source_sha_bound_geometry_recovery"
        assert not fitz.Rect(box).intersects(fitz.Rect(captions[fig]))
        assert _source_sha_bound_crop_override("0"*64,{"id":fig,"caption_bbox":captions[fig]},page) is None

@pytest.mark.skipif(not SOURCE.exists(),reason="Original HP Serway source not mounted on CI")
def test_original_12_pdf_four_crops_and_old_failed_candidate_preservation(tmp_path):
    import shutil
    from selenium_pipeline.source_caption_figure_chain_v1 import recover_printed_source_figures
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
    shutil.copy2(SOURCE,tmp_path/"source.pdf")
    for name in (".microgen_source_caption_crop_stage_v1",
                 ".microgen_source_caption_crop_stage_v1_retry1"):
        old=tmp_path/name;old.mkdir();shutil.copy2(SOURCE,old/"source.pdf")
    result=recover_printed_source_figures(tmp_path)
    assert result["figure_count"]==4
    assert verify_figure_crops(tmp_path)["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert all((tmp_path/name/"source.pdf").is_file()
               for name in (".microgen_source_caption_crop_stage_v1",
                            ".microgen_source_caption_crop_stage_v1_retry1"))
    (tmp_path/"Figure 1.3.png").write_bytes(b"tampered")
    with pytest.raises(FigureChainError):
        verify_figure_crops(tmp_path)

class Picker:
    def get_attribute(self,key):
        return "false" if key=="aria-expanded" else None

class FakeDriver:
    current_window_handle="owned"
    current_url="https://gemini.google.com/app"

def _scenario(offerings):
    from selenium_pipeline.gemini_dynamic_task_router import Decision
    opts=[("hydrogen",SimpleNamespace(label="Everyday help 4 Hydrogen",disabled=False))]
    decision=Decision("figures","hydrogen","Everyday help 4 Hydrogen",
       "flash","PREFERRED_MODEL_MISSING_OFFICIAL_AND_LIVE_UI_FALLBACK",
       "low",("hydrogen",),"FRESH_VERIFIED_CACHE","0"*64)
    def select(_driver,_handle,*,mode,timeout):
        if mode=="flash":
            raise GeminiModelError(
              "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND; current=Hydrogen")
        assert mode=="hydrogen"
        return "Open mode picker, currently Hydrogen Low"
    with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",side_effect=select),\
         patch("selenium_pipeline.gemini_model.visible_offered_gemini_families",side_effect=offerings) as offered,\
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=Picker()),\
         patch("selenium_pipeline.gemini_thinking._open_owned_mode_picker_with_verified_fallback") as reopen,\
         patch("selenium_pipeline.gemini_model._visible_model_options",return_value=opts),\
         patch("selenium_pipeline.gemini_dynamic_task_router.read_task_default",return_value=None),\
         patch("selenium_pipeline.gemini_dynamic_task_router.dynamic_route_registered",return_value=True),\
         patch("selenium_pipeline.gemini_dynamic_task_router.find_dynamic_replacement",return_value=decision),\
         patch("selenium_pipeline.gemini_model.update_dynamic_selected_family") as update,\
         patch("selenium_pipeline.gemini_model.time.sleep",return_value=None):
        if "hydrogen" in sum(offerings,[]):
            label=select_owned_gemini_with_recovery(FakeDriver(),"owned",mode="flash",stage="figures")
            assert "Hydrogen" in label
            assert offered.call_count>=2
            reopen.assert_called_once()
            update.assert_called_once()
        else:
            with pytest.raises(GeminiModelError,match="WITHOUT_EXACT_MENU_EVIDENCE"):
                select_owned_gemini_with_recovery(FakeDriver(),"owned",mode="flash",stage="figures")
            update.assert_not_called()

def test_transient_empty_menu_recovers_only_from_new_positive_owned_ui_evidence():
    _scenario([[],["hydrogen"]])

def test_permanently_empty_menu_still_blocks_without_model_send():
    _scenario([[]]*8)
