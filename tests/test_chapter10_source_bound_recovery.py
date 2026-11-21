"""Serway Chapter 10 source-PDF-SHA figure recovery and negative fault injection.

Source PDF files are private lecture assets and are not shipped in Git.
CI checks the hash-bound registry and security guarantees without them.
Yoga 6 additionally regenerates and verifies every source figure in all
five newly registered exact source PDFs.
"""
from __future__ import annotations
import hashlib,json,shutil,tempfile
from pathlib import Path
import pytest
fitz=pytest.importorskip("fitz")
from selenium_pipeline import source_caption_figure_chain_v1 as source

REGISTRY=Path(source.__file__).with_name("source_crop_overrides_v1.json")
ROOT=Path(r"G:\My Drive\Serway\Serway_8_14\10")
SOURCE_MAP={
 "10.2":"2e0b49a4d7e07b04c2adc734602af4e4abd16b636409c0426b1f3e1f2ae9e942",
 "10.4":"d7eed00e9916b9c9c71ba9ed850c37cd65324f379a2d03ce998f01364ef34354",
 "10.5":"3354bb7e40c35f50cd61b7bfc873678f0afe5b5be79ee5cd1d28e5934a86d172",
 "10.6":"651d713ef9a99f5f5147775b16fb74a7fc47cbfceeae84203802d0778b241d69",
 "10.8":"d4ec095e2c06cc800072e2dad42a1bb8e225179a1013730c969ae5b65b795d69",
}
FIG_COUNT={"10.2":1,"10.4":5,"10.5":5,"10.6":5,"10.8":4}

def registry():
 data=json.loads(REGISTRY.read_text(encoding="utf8"))
 assert data["schema_version"]==1
 return data

def test_all_exact_pdf_sha_profiles_and_panels_present_and_do_not_replace_history():
 data=registry()
 assert set(SOURCE_MAP.values()).issubset(data["overrides"])
 for subtopic,sha in SOURCE_MAP.items():
  figs=data["overrides"][sha]
  assert len(figs)==FIG_COUNT[subtopic]
  assert all(name.startswith("10.") for name in figs)
  assert len(sha)==64
  for id,bbox in figs.items():
   assert type(bbox)==list and len(bbox)==4
   assert all(type(x) in (float,int) for x in bbox)
   assert 0<=bbox[0]<bbox[2]<=613 and 0<=bbox[1]<bbox[3]<=784
 assert sum(FIG_COUNT.values())==20
 assert data["caption_inclusive"][SOURCE_MAP["10.6"]]==["10.16"]
 assert set(data["caption_inclusive"][SOURCE_MAP["10.8"]])=={"10.20","10.22","10.23"}
 assert SOURCE_MAP["10.4"] not in data.get("caption_inclusive",{})
 assert SOURCE_MAP["10.2"] not in data.get("caption_inclusive",{})
 # Maintain previously verified Serway 9 and 10, source-hash-bound.
 assert sum(any(k.startswith("9.") for k in v) for v in data["overrides"].values())>=6

def test_exact_sha_is_required_and_partial_unregistered_caption_fails_closed():
 data=registry()
 valid_sha=SOURCE_MAP["10.4"]
 fake_page=type("SourcePDFPage",(),{"rect":fitz.Rect(0,0,612,783)})()
 row={"id":"10.11","caption_bbox":[452.995,687.787,576.808,739.653]}
 box,mode=source._source_sha_bound_crop_override(valid_sha,row,fake_page)
 assert mode=="source_sha_bound_geometry_recovery"
 assert [round(x,3) for x in list(box)]==[444,487,584,683]
 assert source._source_sha_bound_crop_override("f"*64,row,fake_page) is None
 # Accidental overlap on an unregistered diagram may never be accepted.
 illegal=dict(row,caption_bbox=[445,665,580,681])
 with pytest.raises(source.FigureChainError,match="Partial/unregistered"):
  source._source_sha_bound_crop_override(valid_sha,illegal,fake_page)

@pytest.mark.skipif(not ROOT.exists(),reason="Original lecture source PDFs are not available in public CI")
def test_real_five_source_pdfs_all_twenty_figures_regenerated_and_tamper_rejected():
 actual=0
 for subtopic,sha in SOURCE_MAP.items():
  pdf=ROOT/subtopic/"source.pdf"
  assert pdf.is_file(),f"Original source {subtopic} missing on Yoga 6"
  assert hashlib.sha256(pdf.read_bytes()).hexdigest()==sha
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t)
   shutil.copy2(pdf,folder/"source.pdf")
   record=source.generate_candidates(pdf,folder)
   result=source.verify_figure_crops(folder)
   assert record["source_sha256"]==sha
   assert result["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
   assert result["figure_count"]==FIG_COUNT[subtopic]
   expected={f"Figure {id}.png" for id in registry()["overrides"][sha]}
   assert set(result["figures"])==expected
   actual+=len(expected)
   victim=folder/next(iter(expected))
   victim.write_bytes(victim.read_bytes()+b"tampered")
   with pytest.raises(source.FigureChainError):
    source.verify_figure_crops(folder)
 assert actual==20
