"""Chapter 13 original-source provenance and cross-renderer regression.

Real-PDF integration cases are Dell-only and skip in public CI.
The pure negative test is portable and rejects arbitrary near-identical PNGs.
"""
from pathlib import Path
import hashlib
import shutil
import pytest
from PIL import Image

from selenium_pipeline.source_caption_figure_chain_v1 import verify_figure_crops, printed_source_captions
from selenium_pipeline.source_crop_renderer_parity_v1 import (
    verified_renderer_parity, EXACT_CROSS_RENDERER_VARIANTS,
)

CHAPTER = Path(r"G:\My Drive\Serway\Serway_8_14\13")
COUNTS = {"13.1":3,"13.3":1,"13.4":7,"13.5":4,"13.6":5}


@pytest.mark.parametrize("section,count", list(COUNTS.items()))
def test_real_ch13_source_figures_and_unmodified_original_pdf(section, count):
    folder=CHAPTER/section
    if not folder.is_dir():
        pytest.skip("original Serway Chapter13 not mounted")
    source=folder/"source.pdf"
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    proof=verify_figure_crops(folder)
    assert proof["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
    assert proof["figure_count"]==count
    assert len(printed_source_captions(source))==count
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before


def test_registered_cross_renderer_exception_has_exactly_two_sha_locked_pairs():
    assert len(EXACT_CROSS_RENDERER_VARIANTS)==2
    for pair in EXACT_CROSS_RENDERER_VARIANTS:
        assert len(pair)==2
        assert all(len(x)==64 and all(c in "0123456789abcdef" for c in x) for x in pair)


def test_unregistered_single_pixel_difference_remains_blocked(tmp_path):
    original=tmp_path/"original.png"
    candidate=tmp_path/"candidate.png"
    Image.new("RGB",(96,96),(235,235,235)).save(original)
    with Image.open(original) as img:
        img=img.copy()
        img.putpixel((50,50),(213,213,213))
        img.save(candidate)
    with pytest.raises(ValueError,match="bounded cross-renderer antialiasing drift"):
        verified_renderer_parity(reconstructed=candidate,ledger_png=original)


@pytest.mark.parametrize("figure", ("13.14","13.17"))
def test_known_exact_same_source_cross_renderer_pair_and_tamper_rejection(tmp_path,figure):
    folder=CHAPTER/"13.6"
    if not folder.is_dir():
        pytest.skip("original Serway Chapter13 not mounted")
    reference=folder/".microgen_ch13_20261124_source_fig_stage"/f"Figure {figure}.png"
    docling=folder/".microgen_ch13_20261124_docling_fig_stage"/f"Figure {figure}.png"
    if not (reference.is_file() and docling.is_file()):
        pytest.skip("original dual renderer captures not mounted")
    verified_renderer_parity(reconstructed=docling,ledger_png=reference)
    tampered=tmp_path/"tampered.png"
    with Image.open(docling) as src:
        img=src.copy().convert("RGB")
        p=img.getpixel((50,50))
        img.putpixel((50,50),(p[0]^1,p[1],p[2]))
        img.save(tampered)
    with pytest.raises(ValueError,match="bounded cross-renderer antialiasing drift"):
        verified_renderer_parity(reconstructed=tampered,ledger_png=reference)


@pytest.mark.parametrize("model",("flash","pro","hydrogen","hydrogen-thinking"))
def test_ui_verified_browser_mode_is_import_safe_for_tts_worker(model):
    """TTS helper must not crash merely because browser chose a verified fallback."""
    import subprocess,sys,os
    env=dict(os.environ)
    env["MICROGEN_GEMINI_UI_MODE"]=model
    result=subprocess.run(
        [sys.executable,"-c",
         "from selenium_pipeline import runner,tts; assert runner.DEFAULT_BROWSER_UI_MODE"],
        env=env,capture_output=True,text=True,timeout=25,
    )
    assert result.returncode==0,result.stderr


def test_unknown_browser_mode_still_fails_closed():
    import subprocess,sys,os
    env=dict(os.environ)
    env["MICROGEN_GEMINI_UI_MODE"]="unsupported-unverified-mode"
    result=subprocess.run(
        [sys.executable,"-c","from selenium_pipeline import runner"],
        env=env,capture_output=True,text=True,timeout=25,
    )
    assert result.returncode!=0
    assert "supported, UI-verified model family" in result.stderr


@pytest.mark.parametrize("apostrophe", ("'", "\u2018", "\u2019", "\u02bc", "\uff07"))
def test_tts_fidelity_curly_possessive_typography_matches_heard_speech(apostrophe):
    from selenium_pipeline.tts_fidelity import word_error_stats
    script=f"Newton{apostrophe}s Law of Universal Gravitation"
    heard="Newton's Law of Universal Gravitation"
    result=word_error_stats(script,heard)
    assert result["word_errors"]==0
    assert result["fidelity_percent"]==100.0


def test_tts_fidelity_never_masks_real_scientific_substitution():
    from selenium_pipeline.tts_fidelity import word_error_stats
    assert word_error_stats("Newton’s second law","Newton's first law")["word_errors"]>0
