"""Regression for source-bound zero-in-year QA, indexed area A, and saved Selenium narration."""
import json,hashlib
import pymupdf
from selenium_pipeline.tts_year_zero_recovery_v1 import apply
from selenium_pipeline.vendor_template_v2.script_tts_risk import collect_tts_risks,analyze_script_text
from selenium_pipeline.narration_saved_selenium_recovery_v1 import recover_saved_selenium_candidate

def _pdf(path,text):
    d=pymupdf.open()
    p=d.new_page()
    p.insert_text((40,40),text)
    d.save(path)
    d.close()

def _report(text="sixteen o eight", defects=None):
    reference="Torricelli lived from sixteen zero eight to sixteen forty-seven."
    spoken=f"Torricelli lived from {text} to sixteen forty-seven."
    return {"threshold_percent":99.0,"summary":{"slides":1,"passed":0,"review":1,"blocking_failures":1},
       "slides":[{"slide":4,"status":"review","audio_file":"slide4.wav",
        "ground_truth":reference,"transcript":spoken,"fidelity_percent":99.265,
        "audio_defects":defects or [],"pronunciation_issues":[],
        "critical_token_issues":[{"category":"number","script_text":"sixteen zero eight",
        "heard_as":text,"severity":"major"}]}]}

def test_year_source_printed_equivalent_speech_passes(tmp_path):
    _pdf(tmp_path/"source.pdf","Evangelista Torricelli (1608-1647).")
    (tmp_path/"slide4.wav").write_bytes(b"RIFF" + b"X"*44)
    before=hashlib.sha256((tmp_path/"slide4.wav").read_bytes()).hexdigest()
    approved=apply(tmp_path,_report())
    assert approved["summary"]["passed"]==1
    assert approved["slides"][0]["source_verified_spoken_year_zero_variant"]["year"]==1608
    assert hashlib.sha256((tmp_path/"slide4.wav").read_bytes()).hexdigest()==before
    assert approved["slides"][0]["original_critical_token_issues"]

def test_year_not_general_numeric_equivalence(tmp_path):
    _pdf(tmp_path/"source.pdf","Torricelli lived in 1618.")
    (tmp_path/"slide4.wav").write_bytes(b"RIFF" + b"X"*44)
    assert apply(tmp_path,_report())["summary"]["review"]==1
    _pdf(tmp_path/"another.pdf","Torricelli 1608.")
    (tmp_path/"source.pdf").write_bytes((tmp_path/"another.pdf").read_bytes())
    assert apply(tmp_path,_report("sixteen o nine"))["summary"]["review"]==1
    assert apply(tmp_path,_report(defects=["clipping"]))["summary"]["review"]==1

def test_indexed_area_is_warning_not_blocker():
    s="At point two the cross-sectional area is A two and the velocity is v two."
    issues=collect_tts_risks(s,slide=8)
    assert not any(x["severity"]=="blocking" for x in issues)
    assert any(x["kind"]=="contextual_letter" and x["text"]=="A" for x in issues)
    assert any(x["severity"]=="blocking" for x in collect_tts_risks("A cat is in the yard. We see A big cat.",slide=2))

def test_saved_selenium_candidate_requires_matching_source_and_slide_count(tmp_path):
    source=tmp_path/"original.pdf";folder=tmp_path/"work";folder.mkdir()
    _pdf(source,"Textbook source.")
    (folder/"source.pdf").write_bytes(source.read_bytes())
    _pdf(folder/"slides.pdf","Fluid Dynamics")
    (folder/".selenium_pipeline_state.json").write_text(json.dumps({"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"completed":{"slides":{"model":"test"}}}))
    (folder/"slide_titles_exact.json").write_text(json.dumps({"slide_count":1,"titles":[{"slide":1,"title":"Fluid Dynamics"}]}))
    p=folder/"script.rejected_selenium_attempt_1.txt"
    p.write_text("**Slide 1 [8 sec]:\nFluid Dynamics**")
    result=recover_saved_selenium_candidate(folder,source)
    assert result and result["zero_new_model_sends"]
    assert (folder/"script.txt").read_text()==p.read_text()
    assert recover_saved_selenium_candidate(folder,source) is None


def test_recovered_script_is_published_source_adjacent_with_same_hash(tmp_path):
    from selenium_pipeline.output_paths import publish_stage_outputs
    import hashlib
    source=tmp_path/"14.5"/"source.pdf"
    source.parent.mkdir()
    source.write_bytes(b"%PDF-1.5 source")
    workspace=source.parent/".microgen_work"
    workspace.mkdir()
    script=workspace/"script.txt"
    script.write_text("**Slide 1 [8 sec]:\\nFluid Dynamics**",encoding="utf8")
    sent=publish_stage_outputs(workspace,source,"narration")
    assert source.parent/"script.txt" in sent
    assert hashlib.sha256((source.parent/"script.txt").read_bytes()).digest()==hashlib.sha256(script.read_bytes()).digest()
