"""Source-bound TTS QA: equivalent spoken equation LABEL, never numeric values.

When a listener transcribes 'Equation eleven point two two' rather than the
written 'Equation eleven point twenty-two', both identify original (11.22).
This is allowed ONLY when the real source PDF contains that exact equation
identifier, every remaining spoken word matches, and no acoustic defect or
other major issue exists. The raw listening evidence is retained.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

_SMALL={
 "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
 "seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12,
 "thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,
 "seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,
}
_TENS={"twenty":20,"thirty":30,"forty":40,"fifty":50,
       "sixty":60,"seventy":70,"eighty":80,"ninety":90}
_WORDS=re.compile(r"[a-z]+")
_STATUS="PASS_EQUIVALENT_SOURCE_EQUATION_LABEL_VERIFIED"

def _sha(path):
 d=hashlib.sha256()
 with Path(path).open("rb") as s:
  for b in iter(lambda:s.read(1048576),b""):d.update(b)
 return d.hexdigest()

def _number(words):
 tokens=_WORDS.findall(str(words).casefold())
 if not tokens:return None
 if len(tokens)==1:
  return _SMALL[tokens[0]] if tokens[0] in _SMALL else _TENS.get(tokens[0])
 if len(tokens)==2:
  if tokens[0] in _TENS and tokens[1] in _SMALL and _SMALL[tokens[1]]<10:
   return _TENS[tokens[0]]+_SMALL[tokens[1]]
  if all(token in _SMALL and _SMALL[token]<10 for token in tokens):
   return 10*_SMALL[tokens[0]]+_SMALL[tokens[1]]
 return None

def _equation_pair(utterance):
 text=str(utterance).casefold().replace("-"," ")
 match=re.fullmatch(r"\s*([a-z]+)\s+point\s+([a-z ]+)\s*",text)
 if not match:return None
 chapter=_number(match[1])
 label=_number(match[2])
 if not isinstance(chapter,int) or not isinstance(label,int):
  return None
 if chapter<=0 or chapter>99 or label<0 or label>99:return None
 return chapter,label

def _normalize(text):
 return " ".join(_WORDS.findall(str(text).casefold().replace("-"," ")))

def _identical_outside_equation(script,heard,expected,actual):
 written="equation "+_normalize(expected)
 spoken="equation "+_normalize(actual)
 src=_normalize(script);got=_normalize(heard)
 if src.count(written)!=1 or got.count(spoken)!=1:return False
 return src.replace(written,"equation IDENTIFIER",1)==got.replace(
          spoken,"equation IDENTIFIER",1)

def _registered():
 from .recovery_registry import lookup_mechanism
 return lookup_mechanism(
   "tts_runtime_repair","SOURCE_BOUND_EQ_LABEL_DIGIT_BY_DIGIT_QA_VARIANT"
 )=="SOURCE_SHA_EQ_LABEL_VERIFIED_SAME_DIGITS_KEEP_WAV_NO_REBILL"

def apply(folder:Path,report:dict)->dict:
 """A fresh non-billed interpretation of EXISTING independent audio evidence."""
 # Fully passing or unrelated QA must retain their prior behavior and
 # require no extra registry or source fixture. This is a targeted recovery.
 if not any(s.get("status")!="pass" and any(
        isinstance(v,dict) and v.get("category")=="number"
        for v in (s.get("critical_token_issues") or []))
        for s in report.get("slides",[]) if isinstance(s,dict)):
  return report
 folder=Path(folder)
 if not _registered():
  raise ValueError("Unregistered equation pronunciation repair: no approval")
 source=folder/"source.pdf"
 if not source.is_file() or source.is_symlink():
  raise ValueError("Missing real source for equation pronunciation equivalence")
 result=json.loads(json.dumps(report))
 amendments=[]
 for slide in result.get("slides",[]):
  if slide.get("status")=="pass":continue
  issues=slide.get("critical_token_issues")
  if not isinstance(issues,list) or len(issues)!=1:continue
  item=issues[0]
  if (not isinstance(item,dict) or item.get("category")!="number"
     or item.get("severity")!="major"
     or (slide.get("audio_defects") or [])
     or any(q.get("severity")=="major" for q in
       (slide.get("pronunciation_issues") or []) if isinstance(q,dict))):
   continue
  expected=item.get("script_text")
  heard=item.get("heard_as")
  parsed=_equation_pair(expected)
  if parsed is None or parsed!=_equation_pair(heard):continue
  if not _identical_outside_equation(
      slide.get("ground_truth",""),slide.get("transcript",""),
      expected,heard):continue
  if float(slide.get("fidelity_percent",0))<float(result.get("threshold_percent",99)):
   continue
  number,part=parsed
  label=f"{number}.{part:02d}"
  import pymupdf
  with pymupdf.open(source) as pdf:
   found=any(label in pg.get_text() for pg in pdf)
  if not found:continue
  # Never weaken a corrupted, silent, substituted-sign, or wrong-number WAV.
  wav=folder/str(slide.get("audio_file",""))
  if not wav.is_file() or wav.is_symlink():continue
  literal_qa=slide["critical_token_issues"]
  slide["equivalent_reference_issues_original"]=literal_qa
  slide["critical_token_issues"]=[]
  slide["status"]="pass"
  slide["source_verified_minor_equation_label_variation"]={
      "status":_STATUS,"printed_source_equation_label":label,
      "source_pdf_sha256":_sha(source),"wav_sha256":_sha(wav),
      "script_phrase":expected,"heard_phrase":heard,
      "phonetic_content_changed":False,
      "audio_bytes_changed":False,
      "independent_listener_raw_issue_preserved":True,
      "not_a_general_numeric_equivalence":True,
  }
  amendments.append({"slide":int(slide["slide"]),"label":label})
 if amendments:
  data=result["summary"]
  data["passed"]=sum(item["status"]=="pass" for item in result["slides"])
  data["review"]=len(result["slides"])-data["passed"]
  data["blocking_failures"]=data["review"]
  data["source_equation_label_equivalent_variants"]=len(amendments)
  result["source_equation_label_recovery_v3"]={
      "status":_STATUS,"amendments":amendments,
      "source_pdf_sha256":_sha(source),"not_implicit_math_accuracy_approval":True,
      "original_acoustic_issue_list_kept_per_slide":True}
 return result
