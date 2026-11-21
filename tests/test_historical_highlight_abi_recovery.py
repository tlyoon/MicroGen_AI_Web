"""Source-pixel highlight recovery from real historical renderer, not a mock."""
from __future__ import annotations

import hashlib

import pytest
from PIL import Image

from selenium_pipeline.highlight_frames import emphasize_source_rectangles
from selenium_pipeline.pdf_element_geometry import ElementGeometryError


# Original output, independently computed on Dell-115 from the intact
# 20261025_pr307_untimed_original_visual_pixels/highlight_frames.py.
HISTORICAL_RGB_SHA256 = (
    "4c22969ac60ca76e3f173f3d9ba5e96dc28b28d3dedaddde988b90bd5c13a894"
)


def test_exact_historical_source_emphasis_pixel_witness():
    original = Image.new("RGB", (160, 100), (255, 255, 255))
    raw_before = original.tobytes()
    result = emphasize_source_rectangles(
        original, [[15.0, 10.0, 50.0, 30.0],
                   [55.0, 20.0, 75.0, 40.0]], scale=2.0)
    assert result.mode == "RGB"
    assert result.size == original.size
    assert hashlib.sha256(result.tobytes()).hexdigest() == HISTORICAL_RGB_SHA256
    assert original.tobytes() == raw_before


@pytest.mark.parametrize("scale,boxes", [
    (0.4, [[10, 10, 20, 20]]),
    (4.1, [[10, 10, 20, 20]]),
    (2, []),
    (2, [[-1, 1, 20, 20]]),
    (2, [[10, 10, 80, 20]]),
    (2, [[10, 10, 5, 20]]),
    (2, [[10, 10, 30]]),
])
def test_corrupt_or_unsupported_source_geometry_fails_closed(scale, boxes):
    with pytest.raises(ElementGeometryError):
        emphasize_source_rectangles(
            Image.new("RGB", (120, 80), (255, 255, 255)),
            boxes, scale=scale)


def test_real_downstream_media_verifiers_import_the_restored_helper():
    from selenium_pipeline import offline_corrected_bundle_verify as source_bundle
    from selenium_pipeline import offline_corrected_audio_intake as audio
    from selenium_pipeline import offline_original_slide4_highlight_mp4 as movie
    assert source_bundle.emphasize_source_rectangles is emphasize_source_rectangles
    assert audio.verify_original_five_bundle is source_bundle.verify_original_five_bundle
    assert movie.verify_original_five_bundle is source_bundle.verify_original_five_bundle


def test_single_pixel_change_is_detectable_by_verifier():
    original = Image.new("RGB", (160, 100), (255, 255, 255))
    result = emphasize_source_rectangles(
        original, [[15.0, 10.0, 50.0, 30.0]], scale=2.0)
    corrupted = result.copy()
    x, y = 32, 22
    old = corrupted.getpixel((x, y))
    corrupted.putpixel((x, y), ((old[0] + 1) % 256, old[1], old[2]))
    assert hashlib.sha256(result.tobytes()).digest() != (
        hashlib.sha256(corrupted.tobytes()).digest())


def test_exact_historical_highlight_recovery_registered_and_enabled():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(
        "source_highlight_abi",
        "HISTORICAL_SOURCE_PIXEL_PREVIEW_PRODUCER_SYMBOL_MISSING",
    ) == "RESTORE_PIXEL_EQUIVALENT_SINGLE_HIGHLIGHT_ROUTINE"


def test_disabled_registry_prevents_visual_bundle_admission(tmp_path, monkeypatch):
    import json
    from selenium_pipeline import recovery_registry
    from selenium_pipeline.offline_corrected_bundle_verify import (
        verify_original_five_bundle,
    )
    entry = json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
    for row in entry["entries"]:
        if row["match_type"] == "source_highlight_abi":
            row["enabled"] = False
            break
    else:
        pytest.fail("Missing historical highlight recovery entry")
    changed = tmp_path / "disabled_registry.json"
    changed.write_text(json.dumps(entry), encoding="utf8")
    monkeypatch.setattr(recovery_registry, "REGISTRY_PATH", changed)
    with pytest.raises(ValueError, match="retired or disabled"):
        verify_original_five_bundle(original=tmp_path, bundle=tmp_path)
