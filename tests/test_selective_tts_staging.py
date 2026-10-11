import wave
from pathlib import Path
import pytest
from selenium_pipeline.selective_tts_staging import prepare

def fixture(folder):
    (folder/"script.txt").write_text(
        "**Slide 1 [10 sec]:\nFirst text**\n\n**Slide 2 [10 sec]:\nSecond text**",
        encoding="utf-8")
    for n in (1,2):
        with wave.open(str(folder/f"slide{n}.wav"),"wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\0\0"*8000)

def test_selective_staging_preserves_unaffected_audio(tmp_path):
    fixture(tmp_path)
    output=tmp_path/"stage"
    report=prepare(tmp_path,[2],{2:"Updated second slide"},output)
    assert report["affected"]==[2]
    assert (output/".tts_candidate/slide1.wav").is_file()
    assert not (output/".tts_candidate/slide2.wav").exists()
    assert "Updated second slide" in (output/"script.txt").read_text()
    assert (tmp_path/"slide2.wav").is_file()

def test_missing_reviewed_replacement_fails(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError,match="reviewed narration"):
        prepare(tmp_path,[2],{},tmp_path/"stage")
    assert not (tmp_path/"stage").exists()

def test_populated_staging_directory_refused(tmp_path):
    fixture(tmp_path)
    (tmp_path/"stage").mkdir()
    (tmp_path/"stage"/"old.txt").write_text("do not overwrite")
    with pytest.raises(FileExistsError):
        prepare(tmp_path,[2],{2:"New"},tmp_path/"stage")
