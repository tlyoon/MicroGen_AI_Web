"""Serway 2.2 strict original-source two-vector figure recovery."""
from pathlib import Path
import hashlib,json,shutil
import pytest
import pymupdf as fitz
from selenium_pipeline.source_bound_v3_repair import registered_and_complete,recover_source_figures_v3
from selenium_pipeline.source_caption_figure_chain_v1 import verify_figure_crops,_source_sha_bound_crop_override
SHA="026258917852b91379749b7d26592dcbc80420cb04c6b694347646edebb508de"
BOXES={"2.3":[60,66,473,225],"2.4":[411.597,384.445,557.597,588.445]}
SOURCE=Path(r"G:\My Drive\Serway\Serway_1_7\2\2.2\source.pdf")
def test_22_source_registry_exact_and_no_figure_caption_clipping():
 reg=Path(__file__).resolve().parents[1]/"selenium_pipeline/source_crop_overrides_v1.json"
 saved=json.loads(reg.read_text("utf8"))
 assert saved["overrides"][SHA]==BOXES
 caps={
  "2.3":[71.997,229.432,424.764,251.298],
  "2.4":[417.594,594.445,547.979,656.328],
 }
 page=type("P",(),{"rect":fitz.Rect(0,0,612,783)})()
 for name,bbox in BOXES.items():
  row={"id":name,"caption_bbox":caps[name]}
  src,reason=_source_sha_bound_crop_override(SHA,row,page)
  assert all(abs(x-y)<0.002 for x,y in zip(src,bbox))
  assert reason=="source_sha_bound_geometry_recovery"
  assert not src.intersects(fitz.Rect(caps[name]))
  assert _source_sha_bound_crop_override("0"*64,row,page) is None
@pytest.mark.skipif(not SOURCE.exists(),reason="Original Serway PDF not on Windows CI")
def test_original_pdf_22_two_panels_for_both_and_source_sha_validated(tmp_path):
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
 shutil.copy2(SOURCE,tmp_path/"source.pdf")
 assert registered_and_complete(tmp_path/"source.pdf")
 actual=recover_source_figures_v3(tmp_path)
 assert actual["figure_count"]==2
 passed=verify_figure_crops(tmp_path)
 assert passed["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
 assert passed["figure_count"]==2
 assert (tmp_path/"Figure 2.3.png").stat().st_size>50000
 assert (tmp_path/"Figure 2.4.png").stat().st_size>30000
 (tmp_path/"Figure 2.4.png").write_bytes(b"changed")
 with pytest.raises(ValueError):verify_figure_crops(tmp_path)
