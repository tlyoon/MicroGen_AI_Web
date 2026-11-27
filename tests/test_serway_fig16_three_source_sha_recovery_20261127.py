"""Source-bound Serway 1.3–1.5 figure 1.6 recovery.

No model/API calls, no source mutation. The figure is the same image
physically repeated in three subchapter PDFs, each with its distinct SHA.
"""
import hashlib,json,shutil
from pathlib import Path
import pytest
import pymupdf as fitz
from selenium_pipeline.source_bound_v3_repair import registered_and_complete,recover_source_figures_v3
from selenium_pipeline.source_caption_figure_chain_v1 import (
 printed_source_captions, verify_figure_crops, _source_sha_bound_crop_override,
)
ROOT=Path(r"G:\My Drive\Serway\Serway_1_7\1")
SOURCES={
 "1.3":"181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8",
 "1.4":"9dc28034e807304e242101d066790068477865f19d9a4bc04e5e474c2f7df3c5",
 "1.5":"7f757fee2d28d29d35f395a1400e5f81d9d3bdf4049bf313ba94c8b0dbcc6c62",
}
BOUNDS=[376,453,549,625]

@pytest.mark.parametrize("section,source_sha",SOURCES.items())
def test_exact_original_sha_figure16_crop_and_caption_isolation(section,source_sha):
    registry=Path(__file__).resolve().parents[1]/"selenium_pipeline/source_crop_overrides_v1.json"
    obj=json.loads(registry.read_text("utf8"))
    assert obj["overrides"][source_sha]=={"1.6":BOUNDS}
    page=type("P",(),{"rect":fitz.Rect(0,0,612,783)})()
    row={"id":"1.6","caption_bbox":[383.996,627.547,534.708,659.413]}
    rect,mode=_source_sha_bound_crop_override(source_sha,row,page)
    assert list(rect)==BOUNDS and mode=="source_sha_bound_geometry_recovery"
    assert not rect.intersects(fitz.Rect(row["caption_bbox"]))
    assert _source_sha_bound_crop_override("0"*64,row,page) is None

@pytest.mark.parametrize("section,source_sha",SOURCES.items())
def test_original_hp_fig16_full_raster_pixel_qa(tmp_path,section,source_sha):
    source=ROOT/section/"source.pdf"
    if not source.is_file():
        pytest.skip("Private original Serway textbook PDF is not available on this Windows CI host")
    assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
    shutil.copy2(source,tmp_path/"source.pdf")
    assert registered_and_complete(tmp_path/"source.pdf")
    evidence=recover_source_figures_v3(tmp_path)
    assert evidence["figure_count"]==1
    report=verify_figure_crops(tmp_path)
    assert report["figure_count"]==1
    assert report["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert (tmp_path/"Figure 1.6.png").stat().st_size>1000
    # Detection must remain fatal if a source crop is modified externally.
    (tmp_path/"Figure 1.6.png").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        verify_figure_crops(tmp_path)
