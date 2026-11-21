"""Fail-closed source-bound caption/diagram recovery regression tests."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

fitz = pytest.importorskip("fitz")
from selenium_pipeline import source_caption_figure_chain_v1 as crop


def test_only_exact_pdf_sha_and_complete_caption_are_eligible(tmp_path, monkeypatch):
    fake_module = tmp_path / "source_caption_figure_chain_v1.py"
    fake_module.write_text("# test")
    registry = tmp_path / "source_crop_overrides_v1.json"
    sha = "a" * 64
    box = [315, 60, 570, 231]
    registry.write_text(json.dumps({
        "schema_version": 1,
        "overrides": {sha: {"10.22": box}},
        "caption_inclusive": {sha: ["10.22"]},
    }))
    monkeypatch.setattr(crop, "__file__", str(fake_module))
    page = SimpleNamespace(rect=fitz.Rect(0, 0, 600, 800))
    row = {"id": "10.22", "caption_bbox": [328, 193, 482, 228]}
    result = crop._source_sha_bound_crop_override(sha, row, page)
    assert result is not None
    assert result[1] == "source_sha_bound_full_caption_recovery"
    assert crop._source_sha_bound_crop_override("b" * 64, row, page) is None
    registry.write_text(json.dumps({
        "schema_version": 1,
        "overrides": {sha: {"10.22": [410, 60, 570, 231]}},
        "caption_inclusive": {sha: ["10.22"]},
    }))
    with pytest.raises(crop.FigureChainError, match="Partial"):
        crop._source_sha_bound_crop_override(sha, row, page)
    registry.write_text(json.dumps({
        "schema_version": 1,
        "overrides": {sha: {"10.22": box}},
        "caption_inclusive": {sha: []},
    }))
    with pytest.raises(crop.FigureChainError, match="unregistered"):
        crop._source_sha_bound_crop_override(sha, row, page)


SERWAY_10_9 = Path(r"G:\My Drive\Serway\Serway_8_14\10\10.9\source.pdf")


@pytest.mark.skipif(not SERWAY_10_9.is_file(), reason="HP Serway source not mounted")
def test_real_hp_original_pdf_all_six_crops_verified(tmp_path):
    import shutil
    shutil.copy2(SERWAY_10_9, tmp_path / "source.pdf")
    record = crop.generate_candidates(SERWAY_10_9, tmp_path)
    assert record["figure_count"] == 6
    report = crop.verify_figure_crops(tmp_path)
    assert report["status"] == "ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert report["figure_count"] == 6
    assert report["figures"] == [f"Figure 10.{i}.png" for i in range(22, 28)]
    # No tampered figure may pass the source-pixel and SHA ledger.
    (tmp_path / "Figure 10.22.png").write_bytes(b"tampered")
    with pytest.raises(crop.FigureChainError):
        crop.verify_figure_crops(tmp_path)
