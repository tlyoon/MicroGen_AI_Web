import json
import wave
from pathlib import Path
import pymupdf
import pytest
from selenium_pipeline.slide_narration_sync import inspect, verify, record_structural_alignment

def fixture(tmp_path):
    doc=pymupdf.open()
    doc.new_page().insert_text((70,70),"Original")
    doc.save(tmp_path/"slides.pdf")
    (tmp_path/"script.txt").write_text("**Slide 1 [10 sec]:\nNarration text**",encoding="utf-8")
    with wave.open(str(tmp_path/"slide1.wav"),"wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\0\0"*8000)
    return tmp_path

def test_matching_count_does_not_prove_sync(tmp_path):
    folder=fixture(tmp_path)
    assert inspect(folder)["pages"]==1
    with pytest.raises(ValueError,match="receipt"):
        verify(folder)

def test_pdf_image_change_invalidates_receipt_even_when_count_unchanged(tmp_path):
    folder=fixture(tmp_path)
    record_structural_alignment(folder)
    verify(folder)
    doc=pymupdf.open(folder/"slides.pdf")
    doc[0].insert_text((70,120),"Restored figure")
    doc.save(folder/"new.pdf")
    doc.close()
    (folder/"new.pdf").replace(folder/"slides.pdf")
    with pytest.raises(ValueError,match="changed"):
        verify(folder)

def test_script_change_invalidates_receipt(tmp_path):
    folder=fixture(tmp_path)
    record_structural_alignment(folder)
    (folder/"script.txt").write_text("**Slide 1 [10 sec]:\nChanged narration**",encoding="utf-8")
    with pytest.raises(ValueError,match="changed"):
        verify(folder)

def test_page_count_mismatch(tmp_path):
    folder=fixture(tmp_path)
    (folder/"script.txt").write_text("**Slide 1 [10 sec]:\nA**\n**Slide 2 [10 sec]:\nB**",encoding="utf-8")
    with pytest.raises(ValueError,match="count mismatch"):
        inspect(folder)

