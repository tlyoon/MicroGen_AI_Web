"""Chapter 9 source-hash crop overrides: current reusable registry, not a v3 fork."""
from __future__ import annotations
import hashlib
import json
import tempfile
from pathlib import Path
import pytest
fitz=pytest.importorskip("fitz")
from selenium_pipeline import source_caption_figure_chain_v1 as crop

REGISTRY=Path(crop.__file__).with_name("source_crop_overrides_v1.json")
CHAPTER=Path(r"G:\My Drive\Serway\Serway_8_14\9")

def chapter9_entries():
 data=json.loads(REGISTRY.read_text(encoding="utf8"))
 assert data["schema_version"]==1
 return {sha:figs for sha,figs in data["overrides"].items()
         if any(name.startswith("9.") for name in figs)}

def test_migrated_chapter9_sha_profiles_are_complete_and_disjoint():
 groups=chapter9_entries()
 assert len(groups)==6
 entries=[(sha,fig,rect) for sha,figs in groups.items()
          for fig,rect in figs.items() if fig.startswith("9.")]
 assert len(entries)==18
 assert {fig for _,fig,_ in entries}>={"9.10","9.13","9.14","9.17","9.19","9.22","9.23"}
 assert all(len(sha)==64 and len(rect)==4 for sha,fig,rect in entries)
 assert all(0<=rect[0]<rect[2]<=620 and 0<=rect[1]<rect[3]<=785
            for _,_,rect in entries)
 assert not any(fig.startswith("10.") for _,fig,_ in entries)
 old10={sha:figs for sha,figs in json.loads(REGISTRY.read_text("utf8"))["overrides"].items()
        if any(name.startswith("10.") for name in figs)}
 assert len(old10)>=4 and sum(len(figs) for figs in old10.values())>=10
 assert set(groups).isdisjoint(old10)

def test_source_bound_override_requires_exact_sha_and_does_not_absorb_caption():
 sha,nextfig=next((s,f) for s,figs in chapter9_entries().items()
                  for f in figs if f=="9.14")
 page=type("Page",(),{"rect":fitz.Rect(0,0,612,783)})()
 row={"id":nextfig,"caption_bbox":[443,451,580,510]}
 applied=crop._source_sha_bound_crop_override(sha,row,page)
 assert applied is not None
 assert applied[1]=="source_sha_bound_geometry_recovery"
 assert list(applied[0])==chapter9_entries()[sha][nextfig]
 assert crop._source_sha_bound_crop_override("a"*64,row,page) is None
 crossing=dict(row,caption_bbox=[440,200,580,340])
 with pytest.raises(crop.FigureChainError):
  crop._source_sha_bound_crop_override(sha,crossing,page)

@pytest.mark.skipif(not CHAPTER.exists(),reason="Original Chapter 9 source PDFs not mounted in CI")
def test_verified_source_bound_geometry_generates_all_eighteen_real_source_crops():
 groups=chapter9_entries()
 matched={}
 for f in sorted(CHAPTER.glob("9.*/source.pdf")):
  sha=hashlib.sha256(f.read_bytes()).hexdigest()
  if sha in groups: matched[sha]=f
 assert set(matched)==set(groups)
 count=0
 for sha,source in sorted(matched.items()):
  with tempfile.TemporaryDirectory() as temp:
   dst=Path(temp)
   import shutil
   shutil.copy2(source,dst/"source.pdf")
   report=crop.generate_candidates(source,dst)
   verified=crop.verify_figure_crops(dst)
   assert report["source_sha256"]==sha
   assert verified["status"]=="ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED"
   assert verified["figure_count"]==report["figure_count"]
   tested={row["id"] for row in report["figures"]}
   assert tested.issuperset(groups[sha])
   count+=len(groups[sha])
 assert count==18
