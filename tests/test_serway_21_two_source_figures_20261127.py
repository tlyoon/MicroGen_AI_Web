"""Original SHA-pinned two-figure source-only recovery for Serway 2.1."""
from pathlib import Path
import hashlib,json,shutil
import pytest
import pymupdf as fitz
from selenium_pipeline.source_bound_v3_repair import registered_and_complete,recover_source_figures_v3
from selenium_pipeline.source_caption_figure_chain_v1 import verify_figure_crops,_source_sha_bound_crop_override
SHA="dfdd2090462074af43211f71027d559dda326e2cc48c9535eeece69420dcafde"
BOXES={"2.1":[25,53,560,278],"2.2":[28,366,169,465]}
SOURCE=Path(r"G:\My Drive\Serway\Serway_1_7\2\2.1\source.pdf")

def test_sha_source_registry_and_crop_intervals_disjoint():
    root=Path(__file__).resolve().parents[1]
    overrides=json.loads((root/"selenium_pipeline/source_crop_overrides_v1.json").read_text("utf8"))
    assert overrides["overrides"][SHA]==BOXES
    page=type("P",(),{"rect":fitz.Rect(0,0,612,783)})()
    caps={
        "2.1":[176.997,282.982,537.98,334.848],
        "2.2":[35.997,468.032,157.077,569.898],
    }
    for k,bbox in BOXES.items():
        row={"id":k,"caption_bbox":caps[k]}
        selected,reason=_source_sha_bound_crop_override(SHA,row,page)
        assert list(selected)==bbox and reason=="source_sha_bound_geometry_recovery"
        assert not selected.intersects(fitz.Rect(caps[k]))
        assert _source_sha_bound_crop_override("0"*64,row,page) is None
    assert not fitz.Rect(BOXES["2.1"]).intersects(fitz.Rect(BOXES["2.2"]))

@pytest.mark.skipif(not SOURCE.is_file(),reason="Private Serway source absent on Windows CI")
def test_original_pdf_source_only_fig21_has_both_panels_and_fig22_isolated_raster(tmp_path):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
    shutil.copy2(SOURCE,tmp_path/"source.pdf")
    assert registered_and_complete(tmp_path/"source.pdf")
    result=recover_source_figures_v3(tmp_path)
    assert result["figure_count"]==2
    report=verify_figure_crops(tmp_path)
    assert report["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert report["figure_count"]==2
    assert (tmp_path/"Figure 2.1.png").stat().st_size>50000
    assert (tmp_path/"Figure 2.2.png").stat().st_size>100000
    (tmp_path/"Figure 2.1.png").write_bytes(b"corrupted")
    with pytest.raises(ValueError):verify_figure_crops(tmp_path)
