"""Chapter 11 v3 real PDF/legacy candidate replay, no model/API sends."""
import hashlib,json,shutil,tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from selenium_pipeline import source_caption_figure_chain_v1 as crop
from selenium_pipeline.source_bound_v3_repair import (
  registered_and_complete,recover_source_figures_v3,
  publish_source_only_receipt,valid_source_only_figures,STAGE_RECEIPT)
from selenium_pipeline.figure_recovery_registry_v1 import lookup_mechanism

ROOT=Path(r"G:\My Drive\Serway\Serway_8_14\11")
SHA={
"11.1":"5dc3543cbbe3c73cba9924d10348fbe84d70f1fd5e35cebbffddbd99f032c683",
"11.3":"ccf736c348e95830d352e415400bd4c7660403487d259a575dc3e80d5a2b1a62",
"11.5":"10e0607f79648751c8fec7783f69d793bbbce62e76d1ca758d9ded1a3ca4b056",
}
EXPECTED={"11.1":["Figure 11.1.png","Figure 11.2.png"],
"11.3":["Figure 11.7.png","Figure 11.8.png"],
"11.5":["Figure 11.12.png"]}

def sha(p):
 return hashlib.sha256(p.read_bytes()).hexdigest()

def test_v3_registry_is_normal_executable_handler():
 assert lookup_mechanism("source_figure_recovery","SOURCE_SHA_BOUND_V3_COMPLETE_FIGURES")==(
 "RECOVER_SHA_PINNED_SOURCE_CROPS_WITH_NO_LEGACY_MAPPING_SEND")

@pytest.mark.parametrize("sec",list(SHA))
@pytest.mark.skipif(not ROOT.exists(),reason="original Serway Chapter 11 G drive not mounted")
def test_real_source_only_repair_replays_without_model_send(sec,tmp_path):
 source=ROOT/sec/"source.pdf"
 assert sha(source)==SHA[sec]
 assert registered_and_complete(source)
 folder=tmp_path/"lecture";folder.mkdir()
 shutil.copy2(source,folder/"source.pdf")
 # Simulate previous failed work and its immutable forensic candidate names.
 old=ROOT/sec/".microgen_work"
 preserved={}
 for name in (".microgen_source_caption_crop_stage_v1",
              ".microgen_source_caption_crop_stage_v1_retry1"):
  src=old/name
  if src.is_dir():
   dst=folder/name;dst.mkdir()
   for f in src.iterdir():
    if f.is_file() and f.suffix.lower() in {".pdf",".png",".json"}:
     shutil.copy2(f,dst/f.name);preserved[str(dst/f.name)]=sha(dst/f.name)
 with patch("selenium_pipeline.gemini_model.ensure_mode",side_effect=AssertionError("Model send attempted")):
  response=recover_source_figures_v3(folder)
 assert response["v3_source_bound"] is True
 assert crop.verify_figure_crops(folder)["figures"]==EXPECTED[sec]
 assert sha(folder/"source.pdf")==SHA[sec]
 assert all(sha(Path(name))==digest for name,digest in preserved.items())
 pages=folder/"pages";pages.mkdir()
 (pages/"page_1").mkdir()
 (pages/"page_1"/"page_1.png").write_bytes(b"page_placeholder_not_publication")
 (folder/"crops").mkdir()
 record=publish_source_only_receipt(folder)
 assert record["count"]==len(EXPECTED[sec])
 assert valid_source_only_figures(folder)
 fig=folder/EXPECTED[sec][0]
 fig.write_bytes(b"torn unverified crop")
 assert not valid_source_only_figures(folder)

def test_unregistered_v3_recovery_is_fail_closed(tmp_path):
 fake=tmp_path/"source.pdf";fake.write_bytes(b"not real pdf")
 assert not registered_and_complete(tmp_path/"nothing.pdf")
 with patch("selenium_pipeline.source_bound_v3_repair.registered_and_complete",
            return_value=False),pytest.raises(crop.FigureChainError,match="incomplete"):
  recover_source_figures_v3(tmp_path)
