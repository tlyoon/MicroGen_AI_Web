"""A stale TTS manifest must not override corrected current narration."""
import json
from selenium_pipeline.tts_fidelity import _ground_truth_items

def test_stale_historical_tts_manifest_does_not_mask_corrected_title(tmp_path):
 (tmp_path/"script.txt").write_text("**Slide 1 [10 sec]:\nEnergy in Rotational Motion**\n",encoding="utf8")
 (tmp_path/"tts_input_manifest.json").write_text(json.dumps({"version":2,"slides":[
   {"slide":1,"source_text":"Energy in Rotational",
    "tts_text":"Energy in Rotational"}]}),encoding="utf8")
 assert _ground_truth_items(tmp_path)==[(1,"Energy in Rotational Motion")]

def test_current_manifest_can_still_use_transformed_tts_text(tmp_path):
 (tmp_path/"script.txt").write_text("**Slide 1 [10 sec]:\nWork equals tau delta theta.**\n",encoding="utf8")
 (tmp_path/"tts_input_manifest.json").write_text(json.dumps({"version":2,"slides":[
   {"slide":1,"source_text":"Work equals tau delta theta.",
    "tts_text":"Work equals torque times delta theta."}]}),encoding="utf8")
 assert _ground_truth_items(tmp_path)==[(1,"Work equals torque times delta theta.")]

def test_manifest_with_unknown_source_text_falls_back_fail_closed(tmp_path):
 (tmp_path/"script.txt").write_text("**Slide 1 [10 sec]:\nCurrent source sentence**\n",encoding="utf8")
 (tmp_path/"tts_input_manifest.json").write_text(json.dumps({"version":2,"slides":[
   {"slide":1,"source_text":"Old source sentence",
    "tts_text":"Older transformed sentence"}]}),encoding="utf8")
 assert _ground_truth_items(tmp_path)==[(1,"Current source sentence")]

def test_missing_source_identity_cannot_authorize_historical_tts_text(tmp_path):
 (tmp_path/"script.txt").write_text("**Slide 1 [10 sec]:\\nCurrent approved words**\\n".replace("\\n","\n"),encoding="utf8")
 (tmp_path/"tts_input_manifest.json").write_text(json.dumps({"version":2,"slides":[
   {"slide":1,"tts_text":"Different unbound words"}]}),encoding="utf8")
 assert _ground_truth_items(tmp_path)==[(1,"Current approved words")]


def test_one_stale_input_invalidates_manifest_as_whole(tmp_path):
 (tmp_path/"script.txt").write_text(
   "**Slide 1 [10 sec]:\\nCurrent A**\\n\\n**Slide 2 [10 sec]:\\nNew B**\\n".replace("\\n","\n"),encoding="utf8")
 (tmp_path/"tts_input_manifest.json").write_text(json.dumps({"version":2,"slides":[
   {"slide":1,"source_text":"Current A","tts_text":"Transformed A"},
   {"slide":2,"source_text":"Old B","tts_text":"Transformed old B"}]}),encoding="utf8")
 assert _ground_truth_items(tmp_path)==[(1,"Current A"),(2,"New B")]
